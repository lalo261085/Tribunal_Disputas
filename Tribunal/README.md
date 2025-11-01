# Tribunal (refactor)

Proyecto reorganizado del sistema Tribunal, con responsabilidades separadas en modulos reutilizables y pruebas automatizadas.

## Cambios clave

- Paquete `tribunal/` con factoria de aplicacion, rutas, persistencia y Socket.IO.
- Servicio de datos (`DataRepository`) que abstrae IPFS y ofrece respaldo local opcional.
- Plantillas y estilos renovados en `templates/` y `static/`.
- Lanzador de escritorio (`tribunal/desktop.py`) equivalente al script original de PyQt5.
- Dependencias documentadas y pruebas `pytest` que cubren registro, login, ciclo de conflictos y moderacion.

## Requisitos

- Python 3.11+
- Dependencias de `requirements.txt`
- Daemon de IPFS disponible (opcional si se trabaja solo con respaldo local)

## Variables de entorno relevantes

| Nombre | Valor por defecto | Descripcion |
| --- | --- | --- |
| `TRIBUNAL_SECRET_KEY` | `change-me` | Clave de sesion Flask |
| `TRIBUNAL_FLASK_HOST` / `TRIBUNAL_FLASK_PORT` | `127.0.0.1` / `5002` | Host y puerto del servidor |
| `TRIBUNAL_IPFS_ENABLED` | `1` | Habilita el uso de IPFS |
| `TRIBUNAL_IPFS_AUTOSTART` | `1` | Arranca el daemon de IPFS si no esta corriendo |
| `TRIBUNAL_PUBSUB_TOPIC` | `conflictos-app` | Tema PubSub para notificaciones |
| `TRIBUNAL_FORBIDDEN_WORDS` | `insulto1,insulto2` | Palabras prohibidas separadas por comas |

Los artefactos de estado (`current_cid.txt`, respaldo local) se generan en `Tribunal/var/` por defecto.

## Uso

### Servidor web

```bash
pip install -r requirements.txt
python run.py
```

### Aplicacion de escritorio (PyQt5)

```bash
python -m tribunal.desktop
```

### Pruebas

```bash
pytest
```

## Estructura

```
Tribunal/
|- run.py
|- requirements.txt
|- tribunal/
|  |- __init__.py
|  |- auth.py
|  |- config.py
|  |- data_store.py
|  |- desktop.py
|  |- ipfs_service.py
|  |- routes.py
|  \- sockets.py
|- templates/
|- static/
|- hooks/
\- tests/
```
