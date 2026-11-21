# Viajes Aventura

Aplicacion de consola en Python para gestionar destinos, paquetes turisticos,
usuarios y reservas siguiendo el documento de requerimientos.

## Requisitos

- Python 3.10 o superior
- No requiere dependencias externas

## Ejecutar

Desde la carpeta del proyecto:

```powershell
python -m viajes_aventura
```

En la primera ejecucion se solicita crear el administrador. Despues se puede
registrar clientes, iniciar sesion, administrar destinos y paquetes, y realizar
reservas. Las contrasenas se protegen con PBKDF2-HMAC-SHA256. Los costos de los
paquetes se calculan sumando el costo base de sus destinos y las fechas se
validan antes de guardar o reservar.

## Persistencia y SQLite

La aplicacion usa actualmente `InMemoryRepository`: los datos solo existen
durante la ejecucion y se pierden al cerrar el programa. SQLite esta preparado
en `SQLiteRepository`, con tablas, claves foraneas, restricciones y las mismas
operaciones que requiere el servicio. No se crea ni se usa un archivo de base de
datos al iniciar la CLI.

Para activar SQLite mas adelante, cambia la construccion del servicio en
`viajes_aventura/cli.py` por:

```python
from viajes_aventura.sqlite_repository import SQLiteRepository

service = TravelService(SQLiteRepository("data/viajes_aventura.db"))
```

La capa de servicios y la interfaz no necesitan cambiar. La carpeta `data`
debe existir antes de abrir una ruta de archivo SQLite.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```
