# TFM — Cycling Training

Motor determinista de planes de entrenamiento y preparación de datos para ML.

## Entorno y pruebas

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest
```

## Importar GoldenCheetah OpenData

Desde la raíz del repositorio, con el entorno activado:

```bash
python -m app.data.goldencheetah \
  /ruta/al/atleta-1 /ruta/al/atleta-2 \
  --output data/processed/pilot
```

Cada entrada es una carpeta con un único resumen JSON o la ruta al JSON.
No necesita pandas, acceso a Internet ni los CSV de series temporales.
Genera `activities.csv`, `weekly.csv` y `audit.json`. Reutilizar el directorio
sobrescribe esos tres archivos. No guardar datos de atletas en Git.

### Normalización

- Solo actividades `Bike`; fechas del JSON en UTC y semanas lunes-domingo.
- Métricas escalares o pares `[valor, peso]`; se conserva el primer componente
  de los pares seleccionados, no de arrays arbitrarios. Valores negativos,
  no numéricos y no finitos se consideran ausentes.
- Usa `coggan_tss`, `coggan_np` y `coggan_if` originales; no mezcla las variantes
  `a_coggan_*` ni inventa FTP a partir de `cp_setting`.
- Conserva duración en segundos en actividades y minutos decimales en semanas.
- Duplicados idénticos por fecha se omiten y auditan. Duplicados conflictivos
  o entradas repetidas del mismo atleta producen un error.
- Fechas inválidas se omiten y cuentan en la auditoría. Revisar ese contador
  antes de utilizar el dataset.

### Calidad semanal

`observed_tss` es la suma de los TSS disponibles, que puede ser parcial.
`tss_coverage` mide cobertura de las actividades registradas, no garantiza que
el atleta haya registrado todos sus entrenamientos. `weekly_tss` solo se rellena
si todas las actividades tienen TSS, no hay alertas de duración y no es una
semana de borde. `usable_load_week` identifica ese criterio técnico; no implica
una validación fisiológica ni que la fila ya sea apta para entrenar ML.

Las semanas sin registros tienen carga desconocida (celda vacía), nunca cero.
La primera y última semana de cada exportación se marcan conservadoramente como
`boundary_week`, porque no conocemos la cobertura fuera de sus extremos.
Duraciones inferiores a un minuto o superiores a 12 horas requieren revisión;
el límite superior se cambia con `--max-duration-hours`. Es una heurística de
calidad, no una razón para borrar automáticamente una actividad larga real.

Este importador es independiente de `Activity` y del motor de recomendaciones
para conservar datos incompletos sin forzar campos obligatorios del modelo
de dominio. La construcción del dataset y la evaluación de modelos se realizan
en los módulos descritos a continuación.

## Organización de datos

```text
data/
├── raw/                         # Datos originales de los atletas
└── processed/
    ├── weekly.csv               # Tabla semanal conjunta
    ├── tss_features.csv         # Ventanas sin etiqueta
    ├── tss_labeled.csv          # Ventanas con TSS de la semana siguiente
    └── evaluation/
        ├── linear_baseline_cv.csv
        └── balanced_linear_cv.csv
```

`data/raw/` y `data/processed/` están excluidos de Git. Los datos originales
deben conservarse por separado para poder reproducir el procesamiento.
El importador recibe carpetas descomprimidas o archivos JSON, no ZIP directamente.

## Construcción del dataset

El módulo `app.data.weekly_features` agrupa las semanas por atleta, las ordena
cronológicamente y construye ventanas de cuatro semanas consecutivas.

Una ventana se acepta únicamente si:

- Las cuatro fechas están separadas por siete días.
- Todas las semanas tienen `usable_load_week=True`.
- Ninguna tiene `weekly_tss` ausente.

Las ventanas se desplazan una semana cada vez, por lo que pueden solaparse.
No se unen semanas separadas por huecos.

### Variables

| Campo | Descripción |
|---|---|
| `athlete_id` | Identificador para agrupación y evaluación |
| `window_start` | Inicio de la primera semana de la ventana |
| `window_end` | Inicio de la última semana de la ventana |
| `tss_latest` | TSS de la última semana |
| `tss_previous` | TSS de la penúltima semana |
| `tss_mean_4w` | Media de TSS de las cuatro semanas |
| `tss_change_pct` | Cambio porcentual entre penúltima y última semana |

Si el TSS de la penúltima semana es cero, `tss_change_pct` queda ausente,
porque el cambio porcentual no está definido.

Para generar las variables:

```bash
python -m app.data.weekly_features \
  data/processed/weekly.csv \
  --output data/processed/tss_features.csv
```

### Variable objetivo

Con `--with-target` se añaden:

- `target_week`: inicio de la semana inmediatamente posterior a la ventana.
- `next_week_tss`: TSS observado durante esa semana.

Solo se conservan filas cuya semana objetivo existe, es utilizable y tiene TSS.
No se salta una semana ausente para buscar una etiqueta posterior.

```bash
python -m app.data.weekly_features \
  data/processed/weekly.csv \
  --output data/processed/tss_labeled.csv \
  --with-target
```

El objetivo es **predecir la carga observada**, no determinar la carga óptima
ni una recomendación validada de entrenamiento.

En el lote analizado se obtuvieron:

- 620 ventanas de cuatro semanas, correspondientes a 10 atletas.
- 526 ventanas con etiqueta de la semana siguiente.

Estos recuentos dependen de los archivos y controles de calidad utilizados.
Las ventanas solapadas no son observaciones independientes.

## Modelos y referencias

Se comparan cuatro métodos:

1. **Persistencia:** predice el TSS de la última semana.
2. **Media de cuatro semanas:** predice `tss_mean_4w`.
3. **Regresión lineal:** aprende a combinar tres variables de carga.
4. **Regresión lineal equilibrada:** usa las mismas variables, ponderando
   las filas para que cada atleta tenga el mismo peso total al entrenar.

Las entradas de ambas regresiones son:

```text
tss_latest
tss_previous
tss_mean_4w
```

El objetivo es `next_week_tss`. El identificador, las fechas y el objetivo
no se incluyen en las entradas. `tss_change_pct` todavía no se utiliza.

En el modelo equilibrado, el peso de cada fila es:

```text
1 / número de filas del atleta en el conjunto de entrenamiento
```

Los pesos se calculan exclusivamente con las filas utilizadas para entrenar
cada modelo.

## Evaluación

La métrica es el error absoluto medio, MAE, expresado en TSS.
Un valor menor indica menor error de predicción.

- **MAE global:** da el mismo peso a cada fila.
- **MAE medio por atleta:** calcula primero el MAE de cada atleta y después
  promedia esos valores, dando el mismo peso a cada ciclista.

La separación se realiza por atleta para que sus ventanas solapadas no
aparezcan simultáneamente en entrenamiento y evaluación.

### Separación utilizada

Se reservan estos dos atletas para evaluación:

```text
025bad5c-1cfc-4c22-a2e3-2be1ccb70008
031c70de-6ccd-48f8-ac62-d50eb3d75387
```

La partición contiene:

- 436 filas de ocho atletas para entrenamiento y validación interna.
- 90 filas de dos atletas reservados para evaluación.

Dentro de las 436 filas se realiza validación dejando fuera un atleta cada vez:
se entrena con siete atletas y se valida con el octavo, durante ocho iteraciones.

Esta evaluación estudia la generalización a atletas no vistos. No equivale
a una evaluación temporal de semanas futuras de atletas conocidos.

### Ejecutar solo la validación interna

```bash
python -m app.data.evaluation \
  data/processed/tss_labeled.csv \
  --test-athletes \
  025bad5c-1cfc-4c22-a2e3-2be1ccb70008 \
  031c70de-6ccd-48f8-ac62-d50eb3d75387 \
  --cv-only \
  --cv-output data/processed/evaluation/balanced_linear_cv.csv
```

`--cv-only` excluye los dos atletas reservados y termina después de la
validación interna. El CSV contiene una fila por atleta de validación.

Sin `--cv-only`, el comando también entrena la regresión original con las
436 filas y la evalúa, junto con las referencias, sobre las 90 filas reservadas.
La regresión equilibrada se compara actualmente en validación interna.

`--cv-output` permite elegir el archivo de resultados. Su valor predeterminado
es `data/processed/evaluation/linear_baseline_cv.csv`.
Reutilizar una ruta sobrescribe el archivo; usar nombres distintos para
conservar resultados de experimentos anteriores.

### Resultados de validación interna

Métrica principal: MAE medio por atleta.

| Método | MAE (TSS) |
|---|---:|
| Persistencia | 179,67 |
| Media de cuatro semanas | **140,79** |
| Regresión lineal | 155,87 |
| Regresión equilibrada por atleta | 146,11 |

La ponderación mejora la regresión en 9,76 TSS, pero no supera la media de
cuatro semanas en la métrica principal. La regresión equilibrada mejora
respecto a esa referencia en cinco de los ocho atletas.

### Primera evaluación en los dos atletas reservados

| Método | MAE global (TSS) | MAE medio por atleta (TSS) |
|---|---:|---:|
| Persistencia | 192,57 | 186,07 |
| Media de cuatro semanas | 179,92 | 174,95 |
| Regresión lineal | 176,51 | 172,92 |

La pequeña ventaja de la regresión en esta partición no se reproduce en
la validación interna. Estos resultados son exploratorios y no demuestran
una superioridad general del modelo.

Los resultados de los dos atletas reservados ya se han consultado durante
el desarrollo. Los siguientes ajustes se comparan mediante validación interna;
una evaluación final independiente requerirá datos adicionales no utilizados
para tomar decisiones.

### Diagnóstico de cobertura

`outside_range_count` cuenta las ventanas cuya media de cuatro semanas queda
fuera del mínimo y máximo observados en el entrenamiento de esa partición.

Se detectaron siete ventanas fuera de rango:

- Cinco del atleta `029abbce-69c2-42fc-ad44-a85541cd98b4`.
- Dos del atleta `02a72bf5-d3cf-4502-ac7f-1828abb367ae`.

En este último caso, las medias eran 34,80 y 36,87 TSS, mientras que el mínimo
de entrenamiento era 69,71 TSS. La regresión original sobreestimó ambas cargas.

Este indicador analiza solo una variable. Estar dentro del rango no garantiza
una predicción fiable. No se eliminan filas ni se sustituyen predicciones
automáticamente por este diagnóstico.

## Estado y siguientes pasos

La importación, las ventanas semanales, las etiquetas observadas, las
referencias y las dos variantes de regresión están implementadas.

La media de cuatro semanas sigue siendo la mejor referencia según la
validación interna. El siguiente experimento previsto es incorporar variables
de volumen y frecuencia a partir de las semanas históricas.

Los modelos todavía no están integrados en el generador determinista.
Antes de utilizarlos para adaptar entrenamientos será necesario justificar
cómo una predicción de carga observada se convierte en una recomendación.
