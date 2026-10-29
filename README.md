# Veloform — TFM de planificación ciclista adaptativa

Veloform es un sistema híbrido que estima la respuesta aeróbica del ciclista y
adapta un generador determinista de planes de entrenamiento.

El proyecto combina:

- Procesamiento de datos de GoldenCheetah OpenData.
- Auditoría de potencia y frecuencia cardiaca.
- Construcción de datasets sin fuga temporal.
- Comparación de modelos entre atletas.
- Predicción de la respuesta a sesiones futuras.
- Adaptación de la carga semanal.
- Generación determinista de entrenamientos.
- Trazabilidad de las decisiones del sistema.

## Entorno y pruebas

El entorno validado utiliza Python 3.14 y Node.js 24. `requirements.txt`
declara las dependencias Python directas y `requirements.lock` fija también
las transitivas. Las dependencias del frontend quedan fijadas en
`frontend/package-lock.json`.

Crear y activar el entorno virtual:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instalar las dependencias:

```bash
python -m pip install -r requirements.lock
```

Ejecutar todos los tests:

```bash
python -m pytest
```

El workflow `.github/workflows/ci.yml` ejecuta estas pruebas en cada `push` y
`pull_request`. También aplica todas las migraciones sobre una base vacía y,
para el frontend, instala con `npm ci`, ejecuta el linter y genera el build de
producción.

## Demostración con datos sintéticos

El proyecto incluye un ejemplo pequeño que construye manualmente un ciclista y
su historial:

```bash
python -m app.demo_training_plan
```

Este ejemplo permite comprobar el funcionamiento básico del generador sin
utilizar datos reales.

## Generación desde GoldenCheetah

Para generar un plan desde un ZIP real de GoldenCheetah:

```bash
python -u -m app.generate_plan \
  data/raw/atleta.zip \
  --ftp 250 \
  --weekly-hours 8 \
  --available-days TUESDAY WEDNESDAY FRIDAY SUNDAY \
  --modality XCO \
  --level INTERMEDIATE \
  --objective PERFORMANCE
```

El modelo de respuesta utilizado por defecto es:

```text
artifacts/response_balanced_linear.json
```

## Backend de autenticación

El backend FastAPI separa la identidad de Google de la sesión propia de
Veloform. Google será el único proveedor real; Veloform no recibe ni almacena
contraseñas de Google. El acceso demo solo está disponible en desarrollo.

Configura el entorno local:

```bash
cp .env.example .env
openssl rand -hex 32
```

Pega el secreto generado en `SESSION_SECRET` y configura `GOOGLE_CLIENT_ID`
cuando conectes Google Identity Services. No guardes el archivo `.env` en Git.

Instala las dependencias, aplica la migración y arranca la API:

```bash
python -m pip install -r requirements.txt
python -m alembic upgrade head
uvicorn app.main:app --reload
```

La documentación interactiva queda disponible en `http://localhost:8000/docs`.
Puedes comprobar el estado con `curl http://localhost:8000/api/health`.

Durante el desarrollo, `POST /api/auth/demo` crea una sesión demo. Las sesiones
usan cookies HttpOnly y solo guardan el hash del token en la base de datos.
Antes de exponer endpoints mutables protegidos en producción se debe revisar
la protección CSRF; esta primera fase utiliza `SameSite=Lax`, CORS con origen
exacto y cookies HttpOnly como base.

### Frontend y Google

Arranca el frontend en una segunda terminal:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Vite hace proxy de `/api` hacia `http://localhost:8000`, por lo que las
peticiones conservan la cookie de sesión sin configurar CORS adicional en el
navegador. La interfaz consulta `/api/auth/me` al arrancar y no guarda sesiones
ni tokens en `localStorage`.

Para activar Google, crea un cliente OAuth de tipo aplicación web en Google
Cloud Console y añade `http://localhost:5173` como origen autorizado. Copia el
Client ID en `frontend/.env`:

```dotenv
VITE_GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
VITE_ENABLE_DEMO_AUTH=true
```

Este flujo usa Google Identity Services para recibir un ID token y lo envía
inmediatamente a `POST /api/auth/google`. No necesitas un Client Secret en
React ni debes guardarlo en el frontend. El modo demo requiere
`APP_ENV=development` en el backend.

El perfil ciclista se guarda mediante `PUT /api/profile` en la base de datos y
se recupera con `GET /api/profile`. Antes de utilizar las rutas del dashboard,
un usuario autenticado sin perfil es dirigido a `/onboarding`; la fecha de
objetivo solo es obligatoria para el objetivo `RACE`.

### Conexión con Strava

El perfil incluye una sección de aplicaciones conectadas. Veloform puede
autorizar, mostrar y desconectar una cuenta de Strava. Tras elegir una fecha,
importa el historial de ciclismo y, al abrir el calendario, busca actividades
nuevas automáticamente. Las consultas incrementales tienen un intervalo mínimo
de cinco minutos y reutilizan siete días de solapamiento para detectar cargas
atrasadas sin crear duplicados.

La tarjeta de Strava del perfil permite ejecutar una revisión completa,
pausar o reanudar la sincronización y consultar el resultado de la última
ejecución. La revisión completa vuelve a consultar el historial desde la fecha
configurada; incorpora actividades nuevas, actualiza las modificadas y oculta
las eliminadas en Strava. El RPE y las notas introducidas en Veloform se
conservan. Si caduca la autorización, la interfaz solicita reconectar la cuenta;
los límites o caídas temporales de Strava no alteran las actividades guardadas.

Para probar la conexión, crea una aplicación en
`https://www.strava.com/settings/api`, usa `localhost` como dominio de callback
y añade al `.env` del backend:

```dotenv
STRAVA_CLIENT_ID=tu-client-id
STRAVA_CLIENT_SECRET=tu-client-secret
STRAVA_REDIRECT_URI=http://localhost:8000/api/integrations/strava/callback
EXTERNAL_TOKEN_ENCRYPTION_KEY=un-secreto-largo-y-aleatorio
```

La URL de callback registrada en Strava debe coincidir con
`STRAVA_REDIRECT_URI`. Los tokens se cifran antes de guardarse y nunca se
devuelven al frontend. El modo demostración no admite conexiones externas.
Si faltan las credenciales, el perfil muestra la integración como pendiente
de configuración.

### Actividades realizadas

Las actividades representan sesiones que el ciclista ha realizado y se
mantienen separadas de los `Workout`, que son sesiones planificadas. Cada
actividad pertenece al usuario autenticado y se gestiona mediante:

- `GET /api/activities` con `start`, `end`, `limit` y `offset`.
- `POST /api/activities` para registrar una actividad manual.
- `POST /api/activities/import/preview` para analizar un archivo FIT o TCX
  sin guardarlo todavía.
- `POST /api/activities/import/commit` para guardar los datos revisados de
  una importación.
- `GET /api/activities/{id}` para consultar el detalle.
- `PUT /api/activities/{id}` para editarla.
- `GET /api/activities/planned-workouts/available?date=YYYY-MM-DD` para
  consultar las sesiones que se pueden asociar en un día.
- `PUT /api/activities/{id}/planned-workout` para vincularla o desvincularla
  de una sesión planificada del mismo día.
- `DELETE /api/activities/{id}` para eliminarla.

Son obligatorios el título, `started_at` con zona horaria y la duración.
Las métricas restantes son opcionales. El backend normaliza `started_at` a
UTC y devuelve ISO 8601; el formulario web convierte correctamente el valor
`datetime-local` del navegador antes de enviarlo. La API limita las listas a
100 elementos y ordena las actividades de más reciente a más antigua.

El formulario propone automáticamente una sesión cuando solo existe una
opción disponible en esa fecha. El usuario también puede registrar una
actividad adicional. Cada sesión planificada admite una sola actividad
vinculada, y la API verifica que ambas pertenecen al mismo día según la zona
horaria del perfil.

Desde el calendario se puede abrir el detalle de una sesión para consultar su
estructura, potencias y respuesta prevista. La acción «Registrar actividad
realizada» abre el formulario con la fecha y la sesión seleccionadas. Cuando
ya existe una actividad vinculada, el detalle compara su duración y TSS con
los valores planificados y permite abrirla para editarla.

La tabla `activities` se crea con:

```bash
python -m alembic upgrade head
```

Las actividades manuales siempre se guardan con `source=MANUAL`; el cliente
no puede cambiar el propietario ni el origen. La web permite seleccionar un
archivo FIT o TCX de hasta 20 MB, revisar y corregir los datos extraídos y
vincular la actividad a una sesión planificada del mismo día. El archivo no
se conserva: se guarda la actividad con `source=FILE_IMPORT` y una huella
SHA-256 que impide importar dos veces el mismo archivo para un usuario. Las
importaciones directas desde GoldenCheetah quedan pendientes. Strava puede
autorizarse desde el perfil y sincroniza automáticamente las actividades de
ciclismo desde la fecha elegida, sin selección individual. El plan de
temporada, los workouts planificados, el dashboard, el calendario y la vista
Evolución consumen la API persistida.

Cuando una actividad no contiene TSS, el usuario puede indicar un esfuerzo
percibido entre 1 y 10. Veloform calcula `duración × RPE` y lo conserva como
carga estimada en `RPE·min`. Esta carga se mantiene separada del TSS porque
ambas métricas no comparten escala. Cuando no existe suficiente cobertura de
TSS, el cierre semanal usa el cumplimiento, la duración y el RPE mediano para
aplicar una adaptación conservadora, sin convertir RPE a TSS. La ausencia de
potencia tampoco impide vincular una actividad con su sesión planificada ni
contabilizar su duración.

### Cierre y adaptación semanal

Cuando termina la semana activa, Inicio muestra la acción «Revisar semana y
preparar la siguiente». Antes de confirmar, la interfaz consulta
`GET /api/season-plans/current/weekly-review-preview` y muestra las
actividades, el TSS, la duración, las sesiones vinculadas y los datos que
faltan. Esta vista previa no modifica la planificación.

Al confirmar, `POST /api/season-plans/current/advance` ejecuta el cierre de
forma atómica:

1. Reúne todas las actividades registradas dentro de la semana.
2. Calcula TSS y duración realizados, cobertura de TSS, sesiones vinculadas y
   mediana de desacoplamiento.
3. Guarda una revisión semanal y un evento de adaptación trazable.
4. Marca la semana terminada como `COMPLETED`.
5. Convierte la siguiente semana provisional en `ACTIVE` y genera sus
   sesiones con el historial actualizado.

Una actividad adicional cuenta para la carga semanal, pero sólo una actividad
vinculada a un workout cuenta como cumplimiento de esa sesión. La operación es
idempotente: repetirla no crea otra revisión ni vuelve a generar la semana.
Evolución muestra exclusivamente revisiones semanales reales, avisa cuando
faltan TSS o desacoplamiento y permite recalcular sus métricas si una actividad
se corrige después del cierre. Este recálculo actualiza los resultados
observados, pero conserva la decisión histórica que generó la semana siguiente.

La comparación entre el objetivo provisional y el objetivo adaptado puede
consultarse en el detalle de cada semana. Evolución conserva además el motivo
de cada decisión mediante `GET /api/season-plans/{plan_id}/adaptations`. Las
temporadas terminadas siguen disponibles con `GET /api/season-plans`, por lo
que cerrar la última semana no elimina su calendario ni su historial.

La trazabilidad distingue tres cantidades para evitar confundir una decisión
de mantener carga con la previsión inicial de la temporada:

- La previsión de temporada calculada al crear el plan.
- El objetivo solicitado después de revisar la respuesta semanal.
- El objetivo factible que cabe en los días y horas disponibles.

Si existen varias semanas vencidas, se revisan cronológicamente, una por una.
Cada confirmación recalcula únicamente la siguiente semana pendiente con la
información disponible hasta ese momento.

En desarrollo, Inicio muestra un selector de fecha simulada. Permite probar
el cierre de una semana activa sin cambiar el reloj del equipo ni modificar
las fechas almacenadas. La selección se conserva únicamente en el navegador
y puede desactivarse con «Usar fecha real». El backend sólo acepta este valor
cuando `APP_ENV=development`; en producción no está disponible.

Se puede indicar otro artefacto mediante:

```bash
--response-model /ruta/al/modelo.json
```

La salida incluye:

- Auditoría de las actividades importadas.
- Fecha de referencia del plan.
- Modelo de respuesta utilizado.
- TSS solicitado por la decisión.
- TSS finalmente factible.
- Respuesta aeróbica prevista para cada sesión.
- Variables situadas fuera de los rangos de entrenamiento.
- Decisión de aumentar, mantener o reducir la carga.
- Día, tipo, duración, potencia y TSS de cada entrenamiento.

El flujo principal es:

```text
GoldenCheetah OpenData
        ↓
actividades históricas
        ↓
plan candidato
        ↓
predicción de respuesta por sesión
        ↓
adaptación de carga
        ↓
plan final factible
        ↓
sesiones concretas
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

Reutilizar el mismo directorio de salida sobrescribe esos tres archivos.

### Normalización

La importación aplica las siguientes reglas:

- Sólo se conservan actividades cuyo deporte sea `Bike`.
- Las fechas del resumen se interpretan en UTC.
- Las semanas se organizan de lunes a domingo.
- Las métricas pueden ser escalares o pares `[valor, peso]`.
- En los pares seleccionados se conserva el primer componente.
- Las métricas de carga, potencia y duración negativas se consideran ausentes.
- El desacoplamiento aeróbico admite valores negativos finitos.
- Los valores no numéricos o no finitos se consideran ausentes.
- Se utilizan `coggan_tss`, `coggan_np` y `coggan_if`.
- No se mezclan las variantes `a_coggan_*`.
- No se inventa el FTP a partir de `cp_setting`.
- La duración se conserva en segundos en la exportación de actividades.
- La duración semanal se expresa en minutos decimales.

Los duplicados idénticos por fecha y hora se omiten y quedan registrados en la
auditoría.

Los duplicados conflictivos con la misma fecha y hora provocan un error.

Se permiten varias actividades diferentes durante el mismo día.

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
requieren revisión. El límite superior se puede modificar mediante:

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
GoldenCheetah:

```text
reported_decoupling
calculated_decoupling
difference
```

El valor informado se conserva para auditoría, pero el dataset utiliza como
objetivo el desacoplamiento calculado sobre el tramo continuo.

Esta decisión se tomó porque se encontraron diferencias extremas entre la
métrica informada y las señales observadas en determinadas actividades.

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

`target_aerobic_decoupling` contiene el desacoplamiento calculado a partir de
las series temporales.

Todas las variables históricas se calculan utilizando exclusivamente
actividades anteriores a la actividad objetivo.

La respuesta de la propia actividad nunca se incluye entre sus variables de
entrada.

## Evaluación de modelos de respuesta

La evaluación se realiza dejando fuera un atleta completo en cada iteración.

En cada partición:

1. Se entrena con nueve atletas.
2. Se evalúa con el atleta restante.
3. Se repite el proceso para los diez atletas.
4. Se calcula el MAE de cada atleta.
5. Se promedian los diez errores.

Esto evita que actividades del mismo ciclista aparezcan simultáneamente en
entrenamiento y evaluación.

Para ejecutar la validación completa:

```bash
python -m app.data.response_evaluation \
  data/processed/response_dataset.csv \
  --full-cv
```

El experimento actual contiene:

- 2039 actividades elegibles.
- 10 atletas.

### Métodos comparados

Se comparan los siguientes métodos:

1. Mediana global del conjunto de entrenamiento.
2. Mediana histórica personal.
3. Regresión lineal.
4. Regresión lineal equilibrada por atleta.
5. Regresión Ridge.
6. Random Forest.

La métrica principal es:

```text
MAE medio por atleta
```

Un valor menor representa un error medio menor en la predicción del
desacoplamiento aeróbico.

### Resultados

| Método | MAE medio por atleta |
|---|---:|
| Mediana global | 7,11 |
| Mediana personal | 6,49 |
| Regresión lineal | 6,44 |
| Regresión lineal equilibrada | **6,35** |
| Ridge | 6,44 |
| Random Forest | 6,70 |

La regresión lineal equilibrada obtiene el menor MAE medio y supera la mediana
personal en ocho de los diez atletas.

La mejora respecto a la mediana personal es de 0,14 puntos, aproximadamente
un 2,2 %. Es una mejora reducida, por lo que la mediana personal se conserva
como fallback.

Random Forest no mejora los resultados y no se utiliza en el motor.

## Artefacto del modelo

El modelo final se entrena con todas las filas elegibles:

```bash
python -m app.data.response_model \
  data/processed/response_dataset.csv \
  --output artifacts/response_balanced_linear.json
```

El artefacto JSON contiene:

- Tipo de modelo.
- Variable objetivo.
- Orden de las variables.
- Intercepto.
- Coeficientes.
- Rangos observados durante el entrenamiento.
- Número de filas.
- Número de atletas.
- Método de ponderación.

No contiene actividades ni identificadores de atletas.

Al tratarse de una regresión lineal, la predicción se realiza directamente a
partir del intercepto y los coeficientes guardados. No es necesario
deserializar un objeto interno de scikit-learn durante el uso del motor.

## Conversión al modelo de dominio

El módulo `app.data.activity_adapter` convierte las actividades de
GoldenCheetah en objetos `Activity`.

El adaptador conserva una actividad cuando:

- Tiene una fecha válida.
- Es una actividad de ciclismo.
- Tiene TSS, o dispone de duración y potencia normalizada para calcularlo.

Una actividad puede utilizarse para calcular carga aunque no tenga potencia
media o potencia normalizada, siempre que ya tenga TSS.

Las respuestas aeróbicas no se copian directamente desde el resumen JSON.

Cuando la entrada es un ZIP:

1. Se leen las series temporales.
2. Se calcula el desacoplamiento.
3. Se aplican los filtros de calidad.
4. Se adjunta a `Activity` únicamente una respuesta calculada y elegible.

Cuando sólo existe un resumen JSON, `aerobic_decoupling` permanece vacío porque
no se puede auditar la respuesta mediante sus series temporales.

## Integración con el generador determinista

El motor sigue este proceso:

```text
historial del ciclista
        ↓
decisión inicial basada en carga
        ↓
generación de un plan candidato
        ↓
predicción de cada sesión
        ↓
respuesta máxima del plan
        ↓
adaptación de carga
        ↓
plan final factible
```

La regresión evalúa cada sesión propuesta utilizando:

- Duración estimada.
- Intensidad estimada.
- TSS estimado.
- TSS de los siete días anteriores.
- Frecuencia de los siete días anteriores.
- TSS de los veintiocho días anteriores.
- Frecuencia de los veintiocho días anteriores.
- Relación entre carga aguda y crónica.
- Relación entre TSS de sesión y carga crónica.
- Mediana de respuestas anteriores.
- Número de respuestas anteriores.

Las sesiones anteriores de la misma semana se incorporan progresivamente a la
carga.

Por ejemplo, la predicción del viernes tiene en cuenta las sesiones
planificadas para el martes y el miércoles.

La respuesta semanal se define conservadoramente como la mayor predicción de
las sesiones del plan candidato.

Si no se pueden construir las variables del modelo, el motor utiliza la
mediana histórica personal.

Si tampoco existen al menos tres respuestas anteriores, la respuesta se
clasifica como `UNKNOWN`.

### Clasificación de la respuesta

- `UNKNOWN`: no existe información suficiente.
- `STABLE`: desacoplamiento esperado menor o igual al 5 %.
- `ELEVATED`: desacoplamiento esperado superior al 5 %.

### Política de adaptación

La decisión basada en la carga semanal se combina con la respuesta prevista:

- Una respuesta `STABLE` conserva la decisión basada en la carga.
- Una respuesta `UNKNOWN` conserva la decisión basada en la carga.
- Una respuesta `ELEVATED` impide aumentar la carga.
- Si la respuesta es elevada y la carga estaba creciendo, se reduce.
- Si la respuesta es elevada y la carga estaba estable o descendiendo, se
  mantiene.

El cierre registra también el método utilizado:

- `POWER_TSS`: hay al menos un 50 % de cobertura de TSS y se utiliza el flujo
  basado en potencia y respuesta aeróbica.
- `RPE_FALLBACK`: se usa el cumplimiento, la duración y el RPE mediano. Un RPE
  mediano de 8 o más, o superar la duración prevista en más de un 20 %, reduce
  el objetivo un 15 %. Un cumplimiento inferior al 60 % impide aumentarlo.
- `INSUFFICIENT_DATA`: no hay TSS ni RPE suficientes y se mantiene la previsión
  de temporada.

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

## Ajuste por viabilidad

Después de tomar la decisión, el generador intenta construir una semana que
respete:

- Horas disponibles.
- Días disponibles.
- Nivel del ciclista.
- Máximo de sesiones intensas.
- Modalidad.
- Objetivo deportivo.
- Fase de preparación.
- Duraciones y estructuras permitidas.

Si el objetivo solicitado no es factible, el generador lo reduce hasta
encontrar un plan válido.

Por eso se distinguen:

```text
requested_target_tss
target_tss
feasibility_adjusted
```

- `requested_target_tss` es el objetivo solicitado por la decisión.
- `target_tss` es el objetivo finalmente factible.
- `feasibility_adjusted` indica si fue necesario modificarlo.

## Control del rango del modelo

El artefacto guarda el mínimo y el máximo observado para cada variable.

Antes de presentar una predicción, el sistema comprueba si alguna variable
queda fuera de esos límites.

Cada sesión incluye:

```text
outside_training_range_features
```

Una lista vacía indica que todas las variables individuales están dentro de
los rangos observados durante el entrenamiento.

Este control detecta extrapolaciones univariantes. No garantiza que la
combinación completa de variables sea frecuente o esté bien representada.

## Resultado del plan

El modelo `TrainingPlan` contiene:

```text
requested_target_tss
target_tss
expected_aerobic_decoupling
response_prediction_method
response_evaluated_target_tss
workout_response_predictions
aerobic_response
load_decision
workouts
```

`response_prediction_method` puede contener:

```text
balanced_linear_regression
personal_median
unavailable
```

`response_evaluated_target_tss` indica el TSS del plan candidato sobre el que
se realizaron las predicciones que provocaron la decisión.

Cada predicción de sesión contiene:

```text
day
session_date
predicted_aerobic_decoupling
aerobic_response
outside_training_range_features
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

## Ejemplo de interpretación

En una ejecución real se obtuvo:

```text
Objetivo solicitado: 567,17 TSS
Objetivo factible: 438,88 TSS
Duración total: 477 minutos
Respuesta máxima prevista: 4,01 %
Clasificación: STABLE
Decisión: MAINTAIN
```

Predicciones por sesión:

| Día | Tipo | Desacoplamiento previsto |
|---|---|---:|
| Martes | VO2MAX | 4,01 % |
| Miércoles | ENDURANCE | 1,80 % |
| Viernes | THRESHOLD | 3,93 % |
| Domingo | ENDURANCE | 1,55 % |

Todas las variables de estas sesiones estaban dentro de los rangos
univariantes observados durante el entrenamiento.

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

Este experimento se conserva como trabajo exploratorio.

Predecir la carga que un ciclista realizará no equivale a determinar qué carga
debería recomendar el sistema.

Por ese motivo, el enfoque principal pasó a estimar la respuesta del ciclista
y utilizarla para adaptar el generador determinista.

## Estructura principal del proyecto

```text
app/
├── config/
│   ├── cold_start_rules.py
│   ├── objective_rules.py
│   ├── power_zones.py
│   └── training_rules.py
├── data/
│   ├── activity_adapter.py
│   ├── evaluation.py
│   ├── goldencheetah.py
│   ├── linear_model.py
│   ├── ml_dataset.py
│   ├── response_audit.py
│   ├── response_evaluation.py
│   ├── response_model.py
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
│   ├── response_prediction_service.py
│   ├── training_engine_service.py
│   ├── training_plan_service.py
│   └── training_plan_summary_service.py
├── demo_training_plan.py
└── generate_plan.py

artifacts/
└── response_balanced_linear.json

tests/
├── test_activity_adapter.py
├── test_aerobic_response_service.py
├── test_generate_plan.py
├── test_load_decision_service.py
├── test_metrics.py
├── test_response_audit.py
├── test_response_evaluation.py
├── test_response_model.py
├── test_response_prediction_service.py
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

El artefacto lineal puede versionarse porque sólo contiene coeficientes,
metadatos y rangos agregados. No contiene filas ni identificadores de atletas.

Los informes versionados deben evitar datos personales y contener únicamente
resultados necesarios para reproducir o documentar los experimentos.

## Limitaciones

El proyecto presenta actualmente estas limitaciones:

- El dataset contiene únicamente diez atletas.
- La distribución de actividades por atleta está desequilibrada.
- GoldenCheetah OpenData no garantiza el registro completo del entrenamiento.
- El desacoplamiento depende de la calidad de potencia y frecuencia cardiaca.
- La mejora de la regresión equilibrada frente a la mediana personal es
  reducida y debe confirmarse con más atletas.
- Los rangos mínimos y máximos sólo detectan extrapolación variable por
  variable.
- El desacoplamiento puede tener una interpretación limitada en sesiones
  interválicas o muy variables.
- La clasificación del 5 % simplifica una respuesta fisiológica continua.
- La política de adaptación no representa una validación clínica.
- La semana vencida pasa automáticamente a revisión al abrir la aplicación;
  el cierre requiere confirmación para permitir corregir o importar actividades.
- La detección funciona al consultar el plan. Un aviso externo sin abrir la
  aplicación requeriría un proceso programado en el entorno de despliegue.
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
- Conversión de ZIP reales en actividades del dominio.
- Entrenamiento y serialización de la regresión equilibrada.
- Predicción de la respuesta de cada sesión candidata.
- Comprobación de rangos de entrenamiento.
- Adaptación mediante la mayor respuesta prevista.
- Generación determinista de sesiones.
- Ajuste del plan a las restricciones del ciclista.
- Trazabilidad de la recomendación.
- Persistencia de perfiles, actividades, planes, semanas y sesiones.
- API FastAPI y aplicación web React.
- Asociación entre actividades realizadas y sesiones planificadas.
- Cierre semanal idempotente con auditoría de resultados.
- Regeneración adaptativa de la siguiente semana.
- Evolución basada en revisiones reales persistidas.
- Vista previa del cierre semanal y aviso de datos incompletos.
- Detección automática de semanas vencidas y estado `PENDING_REVIEW`.
- Aviso global de revisión pendiente sin cerrar la semana automáticamente.
- Importación revisable de actividades FIT y TCX con control de duplicados.
- Conexión OAuth con Strava y almacenamiento cifrado de tokens.
- Importación inicial de Strava desde una fecha elegida por el usuario.
- Sincronización incremental al abrir el calendario y revisión completa manual.
- Reconciliación de actividades nuevas, modificadas y eliminadas en Strava.
- Pausa, reanudación, renovación de token y recuperación segura ante fallos de Strava.
- Adaptación alternativa por cumplimiento, duración y RPE sin mezclar escalas.
- Historial permanente de adaptaciones y temporadas finalizadas.
- Detalle de cada semana con comparación provisional frente a adaptada.
- Resumen serializable del plan.
- Demostración ejecutable de extremo a extremo.

## Siguientes pasos

Los siguientes desarrollos previstos son:

1. Añadir un proceso programado y notificaciones externas para avisar sin que
   el usuario tenga que abrir la aplicación.
2. Conectar la importación directa con GoldenCheetah u otras fuentes externas.
3. Ampliar el número y variedad de atletas.
4. Evaluar la calibración temporal en ciclistas conocidos.
5. Analizar por separado sesiones continuas e interválicas.
6. Revisar la política de adaptación con un especialista en entrenamiento.
