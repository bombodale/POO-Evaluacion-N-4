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

La CLI usa SQLite y guarda destinos, paquetes, usuarios y reservas entre
ejecuciones. La base de datos se crea automaticamente en la carpeta personal
del usuario, dentro de `.viajes_aventura/viajes_aventura.db` (por ejemplo,
`%USERPROFILE%\.viajes_aventura\viajes_aventura.db` en Windows). Las contrasenas
se almacenan como hashes PBKDF2-HMAC-SHA256, no como texto plano.

Las pruebas pueden usar `InMemoryRepository` cuando necesitan datos temporales;
el servicio acepta ambos repositorios sin cambiar las operaciones CRUD.

## Pruebas

```powershell
python -m unittest discover -s tests -v
```
