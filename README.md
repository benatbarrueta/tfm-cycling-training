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

Este módulo es independiente de `Activity` y del motor de recomendaciones para
conservar datos incompletos sin forzar campos obligatorios del modelo de dominio.
Todavía no genera etiquetas `y`, ventanas históricas de features ni entrena ML.
El siguiente paso es revisar anomalías, incorporar otros atletas y definir la
etiqueta y la separación temporal/por atleta antes de construir `X`/`y`.
