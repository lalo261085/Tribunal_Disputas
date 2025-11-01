# Tribunal (backend de disputas)

Repositorio centralizado para registrar disputas, administrar votaciones y moderar comentarios sin depender de IPFS ni procesos peer-to-peer. Incluye una interfaz web minima y un API JSON para integraciones externas.

## Componentes principales

- `tribunal/data_store.py`: persiste toda la informacion en un fichero JSON (`var/disputes.json`) con bloqueo en memoria.
- `tribunal/routes.py`: vistas HTML para registro, login, alta de disputas, votacion y debate.
- `tribunal/api.py`: endpoints REST (`/api`) para crear disputas, emitir votos y anadir comentarios.
- Suite de pruebas `pytest` que valida los flujos principales (UI y API).

## Requisitos

- Python 3.11+
- Dependencias declaradas en `requirements.txt` (`pip install -r requirements.txt`).

## Variables de entorno

| Nombre | Valor por defecto | Descripcion |
| --- | --- | --- |
| `TRIBUNAL_SECRET_KEY` | `change-me` | Clave de sesion para Flask |
| `TRIBUNAL_FLASK_HOST` | `127.0.0.1` | Host donde corre el servidor |
| `TRIBUNAL_FLASK_PORT` | `5002` | Puerto de escucha |
| `TRIBUNAL_DATA_DIR` | `Tribunal/var` | Carpeta donde se almacena `disputes.json` |
| `TRIBUNAL_DATA_FILE` | `disputes.json` | Nombre del fichero de datos |
| `TRIBUNAL_API_TOKEN` | *(vacio)* | Token requerido por el API cuando se establece |
| `TRIBUNAL_FORBIDDEN_WORDS` | `insulto1,insulto2` | Palabras vetadas en comentarios |
| `VOTING_WINDOW_HOURS` | `24` | Duracion (horas) de la etapa de votacion |

## Uso

### Servidor

```bash
pip install -r requirements.txt
python run.py
```

La UI se sirve en `http://localhost:5002/` y el API en `http://localhost:5002/api/`.

Si `TRIBUNAL_API_TOKEN` esta definido, todas las solicitudes al API deben incluir la cabecera `X-API-Key` con el token (o `Authorization: Bearer <token>`).

### Endpoints API destacados

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| `POST` | `/api/disputes` | Crea una disputa (`creator`, `descripcion`, `descripcion_parte_a`, `descripcion_parte_b`) |
| `GET` | `/api/disputes` | Lista disputas con votos y comentarios |
| `GET` | `/api/disputes/<id>` | Obtiene detalle de una disputa |
| `POST` | `/api/disputes/<id>/vote` | Registra un voto (`usuario`, `voto` = `A` o `B`) |
| `POST` | `/api/disputes/<id>/comments` | Agrega comentario durante la fase de debate |

### Pruebas

```bash
pytest
```

### Build para macOS

```bash
chmod +x scripts/build_mac.sh
scripts/build_mac.sh
```

El binario se genera en `dist/TribunalServer` listo para ejecutarse en macOS (requiere Python 3 y PyInstaller en la maquina de build).

## Estructura

```
Tribunal/
|- run.py
|- requirements.txt
|- tribunal/
|  |- __init__.py
|  |- api.py
|  |- auth.py
|  |- config.py
|  |- data_store.py
|  |- routes.py
|- templates/
|- static/
|- tests/
|- var/
   \- .gitkeep
```
