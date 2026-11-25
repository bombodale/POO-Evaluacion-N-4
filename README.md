# Viajes Aventura

Aplicacion de consola en Python para administrar destinos, paquetes turisticos,
usuarios y reservas. La aplicacion usa MySQL/MariaDB de XAMPP para conservar los
datos entre ejecuciones.

## Requisitos

- Python 3.10 o superior.
- XAMPP con MySQL/MariaDB iniciado.
- Una base de datos llamada `viajes_aventura`, creada desde phpMyAdmin.
- El conector de MySQL para Python, instalado desde `requirements.txt`.

La aplicacion crea sus tablas cuando se conecta por primera vez, pero no crea ni
elimina la base de datos. Las tablas utilizan claves foraneas para proteger las
relaciones entre usuarios, destinos, paquetes y reservas.

## Instalacion

Abre PowerShell en la carpeta raiz del proyecto. Si ya existe el entorno virtual
del proyecto, instala ahi el conector:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Si no tienes un entorno virtual, puedes usar `python` en lugar de la ruta
`.venv\Scripts\python.exe`.

## Configuracion de MySQL

La configuracion predeterminada es:

| Variable | Valor predeterminado |
| --- | --- |
| `VIAJES_DB_HOST` | `127.0.0.1` |
| `VIAJES_DB_PORT` | `3306` |
| `VIAJES_DB_USER` | `root` |
| `VIAJES_DB_PASSWORD` | vacio |
| `VIAJES_DB_NAME` | `viajes_aventura` |

Estos valores suelen coincidir con una instalacion local de XAMPP. Si tu
configuracion es distinta, define las variables necesarias en PowerShell antes
de iniciar el programa. Por ejemplo:

```powershell
$env:VIAJES_DB_HOST = "127.0.0.1"
$env:VIAJES_DB_PORT = "3306"
$env:VIAJES_DB_USER = "root"
$env:VIAJES_DB_PASSWORD = "tu_contrasena"
$env:VIAJES_DB_NAME = "viajes_aventura"
```

No escribas contrasenas reales en el codigo ni las subas al repositorio.

## Ejecucion

Con MySQL iniciado en XAMPP y la terminal situada en la raiz del proyecto,
puedes iniciar la aplicacion de cualquiera de estas formas:

```powershell
.\.venv\Scripts\python.exe -m viajes_aventura
```

O ejecutando directamente el archivo de entrada:

```powershell
.\.venv\Scripts\python.exe .\viajes_aventura\__main__.py
```

En la primera ejecucion, la aplicacion crea las tablas que falten y solicita
registrar la cuenta de administrador. Luego permite iniciar sesion o registrar
clientes usando un nombre de usuario unico y una contrasena.

## Funcionalidades

- El administrador puede registrar, listar, modificar y eliminar destinos.
- No se permite eliminar destinos asociados a paquetes.
- El administrador puede crear paquetes con varios destinos y fechas; el costo
  se calcula sumando los costos base de esos destinos.
- Los clientes pueden listar destinos y paquetes, reservar paquetes disponibles
  y consultar su historial de reservas.
- Los nombres de usuario admiten de 3 a 30 caracteres: letras ASCII, numeros,
  punto, guion y guion bajo. No distinguen entre mayusculas y minusculas.
- Las contrasenas se almacenan con PBKDF2-HMAC-SHA256, no en texto plano.
- Se validan campos obligatorios, nombres de usuario, montos y fechas.

## Persistencia y estructura

La interfaz CLI utiliza exclusivamente `MySQLRepository`, implementado con
`mysql-connector-python`. `TravelService` contiene las reglas del sistema y
depende del contrato `Repository`. `InMemoryRepository` se utiliza en las
pruebas unitarias para probar las reglas de negocio sin conectarse a XAMPP.

Si la tabla `users` de MySQL ya existia con el esquema anterior, la aplicacion
agrega la columna `username` y migra los nombres de usuario a partir de la
parte anterior al simbolo `@` del correo anterior. La columna anterior se
conserva para no descartar datos, pero la aplicacion ya no la solicita ni la
consulta para registrar o iniciar sesion.

## Pruebas

Ejecuta la suite desde la raiz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas unitarias utilizan `InMemoryRepository`; no se conectan ni modifican
la base `viajes_aventura` de XAMPP.

## Pendiente

El proyecto todavia no implementa tokens de autenticacion.
