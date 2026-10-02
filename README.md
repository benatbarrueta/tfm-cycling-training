# TFM — Cycling Training

Sistema híbrido que estima la respuesta aeróbica del ciclista y adapta un
generador determinista de planes de entrenamiento.

El proyecto combina:

- Procesamiento de datos de GoldenCheetah OpenData.
- Auditoría de potencia y frecuencia cardiaca.
- Construcción de datasets sin fuga temporal.
- Comparación de modelos entre atletas.
- Estimación personalizada de la respuesta aeróbica.
- Adaptación de la carga semanal.
- Generación determinista de sesiones de entrenamiento.

## Entorno y pruebas

Crear y activar el entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instalar las dependencias:

```bash
python -m pip install -r requirements.txt
```

Ejecutar todos los tests:

```bash
python -m pytest
```

## Demostración del plan personalizado

El ejemplo completo construye un ciclista, incorpora su historial de carga y
respuesta aeróbica, adapta la carga semanal y genera las sesiones:

```bash
python -m app.demo_training_plan
```

El resultado incluye:

- Desacoplamiento aeróbico esperado.
- Clasificación de la respuesta aeróbica.
- Decisión de aumentar, mantener o reducir la carga.
- TSS objetivo de la semana.
- Día, tipo, duración, potencia y TSS de cada sesión.

El flujo principal es:

```text
actividades históricas
        ↓
estimación de la respuesta aeróbica
        ↓
clasificación de la respuesta
        ↓
decisión de carga
        ↓
TSS semanal objetivo
        ↓
generador determinista
        ↓
sesiones concretas
```

Un resultado simplificado tiene esta estructura:

```json
{
  "target_tss": 263.5,
  "expected_aerobic_decoupling": 7.0,
  "aerobic_response": "ELEVATED",
  "load_decision": "REDUCE",
  "workouts": [
    {
      "day": "TUESDAY",
      "workout_type": "ENDURANCE",
      "duration_minutes": 90,
      "estimated_tss": 98.5,
      "target_power_min": 150,
      "target_power_max": 190
    }
  ]
}
```

## Datos de GoldenCheetah OpenData

Los datos originales se guardan localmente en:

```text
data/raw/
```

Los resultados del procesamiento se guardan en:

```text
data/processed/
```

Estas carpetas pueden contener información deportiva sensible y archivos de
gran tamaño. Los datos originales y los datasets generados no deben subirse
al repositorio.

Los informes pequeños y reproducibles pueden versionarse cuando sean
necesarios para documentar un experimento.

## Importación de resúmenes semanales

El módulo `app.data.goldencheetah` importa los resúmenes JSON de varios
atletas:

```bash
python -m app.data.goldencheetah \
  /ruta/al/atleta-1 \
  /ruta/al/atleta-2 \
  --output data/processed/pilot
```

Cada entrada puede ser:

- Una carpeta con un único resumen JSON.
- La ruta directa al resumen JSON.

El importador genera:

```text
activities.csv
weekly.csv
audit.json
```

Reutilizar el mismo directorio de salida sobrescribe estos tres archivos.

### Normalización

La importación aplica las siguientes reglas:

- Sólo se conservan actividades cuyo deporte sea `Bike`.
- Las fechas del resumen se interpretan en UTC.
- Las semanas se organizan de lunes a domingo.
- Las métricas pueden ser escalares o pares `[valor, peso]`.
- En los pares seleccionados se conserva el primer componente.
- Los valores negativos, no numéricos o no finitos se consideran ausentes.
- Se utilizan `coggan_tss`, `coggan_np` y `coggan_if`.
- No se mezclan las variantes `a_coggan_*`.
- No se inventa el FTP a partir de `cp_setting`.
- La duración se conserva en segundos para las actividades.
- La duración semanal se expresa en minutos decimales.

Los duplicados idénticos por fecha se omiten y quedan registrados en la
auditoría. Los duplicados conflictivos o las entradas repetidas del mismo
atleta provocan un error.

Las fechas inválidas se omiten y se contabilizan en `audit.json`.

### Calidad semanal

`observed_tss` es la suma de los valores TSS disponibles. Puede representar
una carga parcial.

`tss_coverage` mide la cobertura de TSS de las actividades registradas, pero
no garantiza que el atleta haya registrado todos sus entrenamientos.

`weekly_tss` sólo se rellena cuando:

- Todas las actividades de la semana tienen TSS.
- No existen alertas de duración.
- La semana no es una semana de borde.

`usable_load_week` identifica el cumplimiento de estos criterios técnicos.
No supone una validación fisiológica.

Las semanas sin actividades registradas tienen carga desconocida. No se
interpretan automáticamente como semanas con cero TSS.

La primera y la última semana de cada exportación se marcan como
`boundary_week`, porque se desconoce la cobertura fuera del intervalo
exportado.

Las actividades con duración inferior a un minuto o superior a doce horas
requieren revisión. El límite superior se puede modificar con:

```text
--max-duration-hours
```

## Auditoría de la respuesta aeróbica

El módulo `app.data.response_audit` trabaja directamente con los ZIP de
GoldenCheetah OpenData.

Cada ZIP debe contener:

- Un resumen JSON del atleta.
- Los CSV con las series temporales de las actividades.

Para ejecutar la auditoría:

```bash
python -u -m app.data.response_audit \
  data/raw/*.zip \
  --signal-coverage \
  --decoupling-output data/processed/decoupling_comparisons.csv \
  --response-output data/processed/response_dataset.csv
```

La opción `-u` hace que Python muestre la salida inmediatamente mientras
procesa los archivos.

### Emparejamiento de actividades

Las actividades del resumen JSON se emparejan con los CSV utilizando:

- La fecha UTC de la actividad.
- La fecha codificada en el nombre del CSV.
- Los posibles desfases horarios detectados para cada atleta.

La auditoría contabiliza:

- Actividades emparejadas.
- Actividades sin pareja.
- Coincidencias ambiguas.
- CSV inválidos.
- CSV vacíos.
- Desfases horarios encontrados.

### Calidad de las señales

Para cada actividad candidata se revisa:

- Cobertura conjunta de potencia y frecuencia cardiaca.
- Duración de la señal.
- Orden del eje temporal.
- Saltos temporales.
- Duración del tramo continuo más largo.
- Variabilidad de potencia.
- Proporción de muestras con potencia cero.
- Equilibrio de potencia entre las dos mitades.

Una actividad sólo se utiliza para construir el dataset de respuesta cuando
cumple los controles de calidad configurados.

Los criterios actuales incluyen:

- Al menos veinte minutos de señal continua emparejada.
- Coeficiente de variación de potencia menor o igual a `0.75`.
- Proporción de potencia cero menor o igual a `0.20`.
- Relación de potencia entre mitades mayor o igual a `0.80`.
- Cobertura completa de TSS en las ventanas históricas.
- Carga crónica positiva.
- Al menos tres respuestas aeróbicas anteriores del atleta.

## Cálculo del desacoplamiento aeróbico

El desacoplamiento compara la relación potencia/frecuencia cardiaca entre las
dos mitades de un tramo continuo:

```text
ratio_primera_mitad = potencia_media_1 / frecuencia_cardiaca_media_1
ratio_segunda_mitad = potencia_media_2 / frecuencia_cardiaca_media_2
```

A partir de esas relaciones se calcula el cambio porcentual.

La auditoría conserva tanto el valor calculado como el valor informado por
GoldenCheetah para poder compararlos:

```text
reported_decoupling
calculated_decoupling
difference
```

El dataset principal utiliza como objetivo:

```text
target_aerobic_decoupling
```

## Dataset de respuesta

El dataset final se guarda normalmente en:

```text
data/processed/response_dataset.csv
```

Cada fila representa una actividad elegible y contiene información de la
sesión, del historial anterior y de la respuesta observada.

### Variables de la sesión

```text
session_duration_minutes
session_intensity_factor
session_tss
```

### Variables de carga histórica

```text
previous_7d_tss
previous_7d_activity_count
previous_7d_tss_coverage
previous_28d_tss
previous_28d_activity_count
previous_28d_tss_coverage
```

### Variables relativas de carga

```text
acute_chronic_load_ratio
session_to_chronic_load_ratio
```

### Historial de respuesta personal

```text
previous_response_median
previous_response_count
```

### Variable objetivo

```text
target_aerobic_decoupling
```

Todas las variables históricas se calculan utilizando exclusivamente
actividades anteriores a la actividad objetivo.

La respuesta de la propia actividad nunca se incluye entre sus variables de
entrada.

## Evaluación de modelos de respuesta

La evaluación se realiza por atleta. En cada iteración se deja fuera un atleta
completo, se entrena con los demás y se evalúa sobre el atleta no visto.

Esto evita que actividades del mismo ciclista aparezcan simultáneamente en
entrenamiento y evaluación.

Para ejecutar la validación completa:

```bash
python -m app.data.response_evaluation \
  data/processed/response_dataset.csv \
  --full-cv
```

El experimento actual contiene:

- 1324 actividades elegibles.
- 10 atletas.

### Métodos comparados

Se comparan los siguientes métodos:

1. Mediana global del conjunto de entrenamiento.
2. Mediana histórica personal.
3. Regresión lineal.
4. Regresión lineal equilibrada por atleta.
5. Regresión Ridge.
6. Random Forest.

La métrica principal es el error absoluto medio por atleta:

```text
MAE medio por atleta
```

Primero se calcula el MAE de cada ciclista y después se promedian los
resultados. De esta forma, los atletas con muchas actividades no dominan la
métrica final.

### Resultados

| Método | MAE medio por atleta |
|---|---:|
| Mediana global | 5,83 |
| Mediana personal | **5,50** |
| Regresión lineal | 5,57 |
| Regresión lineal equilibrada | 5,70 |
| Ridge | 5,57 |
| Random Forest | 5,77 |

La mediana histórica personal obtiene el menor error medio por atleta.

Los modelos más complejos no muestran una mejora consistente frente a esta
referencia. Por ese motivo, la primera integración con el generador utiliza
la mediana personal.

Las regresiones y Random Forest se conservan como comparaciones
experimentales.

## Integración con el generador determinista

El motor utiliza las actividades anteriores del ciclista para estimar su
respuesta aeróbica.

Se requieren al menos tres valores anteriores de desacoplamiento.

La estimación utilizada actualmente es:

```text
mediana de los desacoplamientos anteriores del ciclista
```

La respuesta se clasifica en:

- `UNKNOWN`: no existe historial suficiente.
- `STABLE`: el desacoplamiento esperado es menor o igual al 5 %.
- `ELEVATED`: el desacoplamiento esperado es superior al 5 %.

### Política de adaptación

La decisión original basada en la evolución semanal de TSS se combina con la
respuesta aeróbica:

- Una respuesta `STABLE` conserva la decisión basada en la carga.
- Una respuesta `UNKNOWN` conserva la decisión basada en la carga.
- Una respuesta `ELEVATED` impide aumentar la carga.
- Si la respuesta es elevada y la carga estaba creciendo, se reduce.
- Si la respuesta es elevada y la carga estaba estable o descendiendo, se
  mantiene.

### Decisiones posibles

```text
INCREASE
MAINTAIN
REDUCE
```

La decisión se convierte en un objetivo semanal:

- `INCREASE`: aumenta el TSS objetivo un 5 %.
- `MAINTAIN`: mantiene el TSS actual.
- `REDUCE`: reduce el TSS objetivo un 15 %.

Después, el generador determinista distribuye ese objetivo entre los días
disponibles y prescribe sesiones compatibles con:

- Modalidad.
- Nivel.
- FTP.
- Horas semanales.
- Días disponibles.
- Objetivo deportivo.
- Fase de preparación.

## Resultado del plan

El modelo `TrainingPlan` contiene:

```text
target_tss
expected_aerobic_decoupling
aerobic_response
load_decision
workouts
```

Cada `Workout` puede contener:

```text
day
workout_type
target_tss
estimated_tss
duration_minutes
target_power_min
target_power_max
warmup
intervals
cooldown
```

El servicio `build_training_plan_summary` convierte el plan en un diccionario
preparado para:

- Serialización JSON.
- Una futura API.
- Una interfaz web o móvil.
- Informes de resultados.
- Demostraciones del sistema.

## Experimento exploratorio de carga semanal

Antes de seleccionar el enfoque de respuesta aeróbica se realizó un
experimento para predecir el TSS de la semana siguiente.

El módulo `app.data.weekly_features` construye ventanas de cuatro semanas
consecutivas.

Una ventana se acepta cuando:

- Las cuatro fechas están separadas por siete días.
- Todas las semanas tienen `usable_load_week=True`.
- Ninguna semana tiene `weekly_tss` ausente.

Las variables utilizadas son:

```text
tss_latest
tss_previous
tss_mean_4w
tss_change_pct
```

La etiqueta es:

```text
next_week_tss
```

Para construir el dataset:

```bash
python -m app.data.weekly_features \
  data/processed/weekly.csv \
  --output data/processed/tss_labeled.csv \
  --with-target
```

Para evaluar los métodos:

```bash
python -m app.data.evaluation \
  data/processed/tss_labeled.csv \
  --test-athletes \
  025bad5c-1cfc-4c22-a2e3-2be1ccb70008 \
  031c70de-6ccd-48f8-ac62-d50eb3d75387
```

Este experimento se conserva como trabajo exploratorio. Predecir la carga que
un ciclista realizará no equivale a determinar qué carga debería recomendar
el sistema.

Por ese motivo, el enfoque principal pasó a estimar la respuesta del ciclista
y utilizarla para adaptar un generador determinista.

## Estructura principal del proyecto

```text
app/
├── config/
│   ├── cold_start_rules.py
│   ├── objective_rules.py
│   ├── power_zones.py
│   └── training_rules.py
├── data/
│   ├── evaluation.py
│   ├── goldencheetah.py
│   ├── linear_model.py
│   ├── ml_dataset.py
│   ├── response_audit.py
│   ├── response_evaluation.py
│   └── weekly_features.py
├── models/
│   ├── activity.py
│   ├── aerobic_response.py
│   ├── cyclist.py
│   ├── load_decision.py
│   ├── training_plan.py
│   ├── training_state.py
│   └── workout.py
├── services/
│   ├── aerobic_response_service.py
│   ├── cold_start_service.py
│   ├── load_decision_service.py
│   ├── metrics.py
│   ├── training_engine_service.py
│   ├── training_plan_service.py
│   └── training_plan_summary_service.py
└── demo_training_plan.py

tests/
├── test_response_audit.py
├── test_response_evaluation.py
├── test_aerobic_response_service.py
├── test_load_decision_service.py
├── test_training_engine_service.py
└── test_training_plan_summary_service.py
```

## Privacidad y control de versiones

No deben subirse a Git:

- ZIP originales de atletas.
- CSV de series temporales.
- Resúmenes JSON originales.
- Datasets procesados con identificadores de atletas.
- Entornos virtuales.
- Variables de entorno.

El `.gitignore` excluye:

```text
.venv/
venv/
__pycache__/
.pytest_cache/
.env
.env.*
data/raw/
data/processed/
```

Los informes versionados deben evitar datos personales y contener únicamente
resultados necesarios para reproducir o documentar los experimentos.

## Limitaciones

El proyecto presenta actualmente estas limitaciones:

- El dataset contiene únicamente diez atletas.
- La distribución de actividades por atleta está desequilibrada.
- GoldenCheetah OpenData no garantiza el registro completo del entrenamiento.
- El desacoplamiento depende de la calidad de potencia y frecuencia cardiaca.
- La mediana personal no utiliza todavía las características de una sesión
  futura concreta.
- La clasificación del 5 % simplifica una respuesta fisiológica continua.
- La política de adaptación no representa una validación clínica.
- No existe todavía una API ni una interfaz de usuario.
- La generalización debe evaluarse con más atletas y datos externos.

## Estado actual

Están implementados:

- Importación de resúmenes GoldenCheetah.
- Procesamiento de múltiples atletas.
- Auditoría de emparejamiento entre JSON y CSV.
- Control de calidad de potencia, frecuencia cardiaca y tiempo.
- Comparación del desacoplamiento calculado e informado.
- Construcción del dataset sin fuga temporal.
- Validación dejando fuera un atleta completo.
- Comparación de referencias y modelos de aprendizaje automático.
- Estimación personalizada de la respuesta aeróbica.
- Adaptación de la decisión de carga.
- Generación determinista de sesiones.
- Trazabilidad de la recomendación.
- Resumen serializable del plan.
- Demostración ejecutable de extremo a extremo.

## Siguientes pasos

Los siguientes desarrollos previstos son:

1. Convertir datos reales del ciclista en objetos `Activity`.
2. Persistir el historial de actividades y respuestas.
3. Exponer el generador mediante una API.
4. Añadir una interfaz para consultar el calendario semanal.
5. Mostrar al ciclista la explicación de cada adaptación.
6. Ampliar el número y variedad de atletas.
7. Evaluar la calibración temporal en ciclistas conocidos.
8. Revisar la política de adaptación con un especialista en entrenamiento.