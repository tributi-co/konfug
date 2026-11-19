# Konfug

Fuente de configuración para los proyectos de Tributi. Resuelve cada ajuste
desde variables de entorno, Google Cloud Datastore o valores por defecto, los
secretos desde Google Secret Manager y, opcionalmente, ajustes "calientes"
desde Firestore.

Requiere Python 3.13 a 3.15.

## Instalación

Como dependencia directa desde Git (así la consume customer-api):

```toml
[project]
dependencies = ["konfug"]

[tool.uv.sources]
konfug = { git = "https://github.com/tributi-co/konfug.git", rev = "main" }
```

## Uso

```python
import konfug

config = konfug.Konfug(
    project_id="mi-proyecto",
    namespace="staging",
    common_namespace="stg-common",
    settings_kind="Settings",
)

DEBUG = config.flag("DEBUG", False)
DB_HOST = config.string("DB_HOST")
ALLOWED = config.stringlist("ALLOWED_HOSTS", "localhost")
DB_PASSWORD = config.secret("DB_PASSWORD")
```

### Metaconfiguración

Cada parámetro se toma del argumento o, si falta, de la variable de entorno:

| Argumento | Variable de entorno | Requerido |
|---|---|---|
| `project_id` | `GOOGLE_CLOUD_PROJECT` | Sí |
| `settings_kind` | `KONFUG_DATASTORE_SETTINGS_KIND` | Sí |
| `namespace` | `KONFUG_DATASTORE_NAMESPACE` | Sí |
| `common_namespace` | `KONFUG_DATASTORE_COMMON_NAMESPACE` | No |
| `stringlist_separator` | `KONFUG_STRINGLIST_SEPARATOR` (por defecto `,`) | No |
| `force_datastore` | `KONFUG_FORCE_DATASTORE` | No |

Otros argumentos: `falsey_expressions`, `skip_datastore`,
`skip_secret_manager` y `skip_firebase`.

### Resolución de ajustes

Para `string`, `flag`, `integer`, `floatnum`, `stringlist`, `dictionary` y
`raw_setting`, la prioridad es:

1. Variable de entorno.
2. Datastore: la primera entidad del `settings_kind` en `namespace`; sobre ella
   se aplican los valores de `common_namespace` y prevalece el namespace propio.
3. `default_val`.

Si no hay valor ni `default_val`, lanza `KonfugMissingError`
(`raw_setting(..., nullable=True)` devuelve `None`). Si Datastore no está
disponible (sin credenciales o sin entidad), Konfug usa solo variables de
entorno, salvo con `force_datastore`, que propaga el error.

### Secretos

`config.secret(key, default_val=None, transform=None, encoding="UTF-8")` busca
primero la variable de entorno `key` y luego la última versión del secreto
`key` en Secret Manager. `transform` se aplica al valor obtenido.

### Ajustes calientes (Firestore)

```python
hot = config.hot_settings(credentials=cred_json, collection="hot-settings")
hot.limite = config.integer("limite", 10, hot=True)
hot.limite  # lee el documento "limite" de la colección en cada acceso
```

Cada acceso lee el campo `value` del documento cuyo id es la clave. Con
`skip_firebase=True`, `hot=True` se ignora.

## Desarrollo

Las dependencias se gestionan con [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run pytest
```

Las versiones de `dependencies` en `pyproject.toml` están fijadas porque son las
que valida customer-api. Subirlas exige probarlas allí (arranque contra
staging: Datastore, secretos y Firestore) antes de publicar, y subir la versión
del paquete.
