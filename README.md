# ServisTech Backend

Backend de ServisTech, un sistema de gestion para talleres de reparacion tecnica. La idea del proyecto es cubrir el flujo interno de un taller: cargar clientes, crear ordenes, registrar el estado de cada equipo, guardar fotos, controlar importes y generar enlaces de seguimiento para el cliente.

Esta parte esta hecha con Django, Django REST Framework y Simple JWT.

## Que resuelve

- Gestion de clientes del taller.
- Gestion de ordenes de reparacion.
- Estados de trabajo: pendiente, diagnosticado, en progreso, reparado, finalizado y retirado.
- Presupuesto, senia, costo final, descuento por garantia y saldo final.
- Registro de datos de retiro del equipo.
- Fotos asociadas a una orden.
- Seguimiento publico por token, sin exponer toda la informacion interna.
- Login con JWT guardado en cookies HttpOnly.
- Admin de Django para mantenimiento interno.

## Stack

- Python
- Django 5
- Django REST Framework
- Simple JWT
- PostgreSQL en produccion o SQLite para desarrollo local
- Whitenoise para archivos estaticos
- Pillow para imagenes

## Estructura principal

```txt
backend/
  api/                 Endpoints, serializers, auth, tests y paginacion
  ordenes/             Modelos principales del negocio
  servicio_tecnico/    Settings, urls, asgi y wsgi
  media/               Archivos subidos en local
  staticfiles/         Archivos generados por collectstatic
```

`media/` y `staticfiles/` no deberian crecer como parte del codigo fuente. Quedan ignorados para nuevos archivos porque son salida local o de build.

## Variables de entorno

Crear un `.env` tomando como base `.env.example`.

```env
SECRET_KEY=change-me
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1

DB_HOST=
DB_NAME=servistech
DB_USER=postgres
DB_PASSWORD=postgres
DB_PORT=5432

FRONTEND_TRACKING_URL_TEMPLATE=http://localhost:3000/seguimiento/{token}
FRONTEND_PRINT_URL_TEMPLATE=http://localhost:3000/imprimir/orden/{orden_id}
FRONTEND_FICHA_URL_TEMPLATE=http://localhost:3000/imprimir/ficha/{orden_id}
```

Si `DB_HOST` queda vacio, Django usa SQLite local. Si se define `DB_HOST`, usa PostgreSQL con las variables `DB_NAME`, `DB_USER`, `DB_PASSWORD` y `DB_PORT`.

Para desarrollo local se puede usar:

```env
DEBUG=True
```

En produccion conviene mantener:

```env
DEBUG=False
```

## Instalacion local

Desde la carpeta `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Despues aplicar migraciones:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

Crear un usuario administrador:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Levantar el servidor:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Por defecto queda disponible en:

```txt
http://localhost:8000
```

## Endpoints principales

Todos los endpoints internos viven bajo `/api/`.

### Auth

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| POST | `/api/token/` | Login. Guarda `access_token` y `refresh_token` en cookies HttpOnly. |
| POST | `/api/logout/` | Cierra sesion borrando cookies. |
| GET/PATCH | `/api/profile/` | Lee o actualiza los datos del usuario logueado. |
| POST | `/api/profile/change-password/` | Cambia la password del usuario logueado. |
| GET | `/api/verificar-admin/` | Devuelve 200 si el usuario es superuser. |

### Clientes

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| GET | `/api/clientes/` | Lista clientes con paginacion. |
| POST | `/api/clientes/` | Crea un cliente. |
| GET | `/api/clientes/?search=texto` | Busca por nombre, apellido, DNI o celular. |
| GET | `/api/clientes/recent/` | Devuelve los ultimos clientes cargados. |
| PATCH | `/api/clientes/{id}/` | Actualiza un cliente. |

La eliminacion de clientes esta bloqueada para no perder historial de ordenes.

### Ordenes

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| GET | `/api/ordenes/` | Lista ordenes con paginacion. |
| POST | `/api/ordenes/` | Crea una orden. |
| GET | `/api/ordenes/{id}/` | Detalle de una orden. |
| PATCH | `/api/ordenes/{id}/` | Actualiza datos de una orden. |
| PATCH | `/api/ordenes/{id}/estado/` | Cambia el estado de trabajo. |
| POST | `/api/ordenes/{id}/fotos/` | Sube una o varias fotos. |
| GET | `/api/ordenes/recent/` | Ultimas ordenes cargadas. |
| GET | `/api/ordenes/{id}/print/ficha-tecnica/` | Redirige a la ficha imprimible del frontend. |
| GET | `/api/ordenes/{id}/print/seguimiento/` | Redirige a la impresion de seguimiento. |

Filtros utiles:

```txt
/api/ordenes/?tab=pendiente
/api/ordenes/?tab=finalizado
/api/ordenes/?estado=diagnosticado
/api/ordenes/?search=samsung
```

### Seguimiento publico

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| GET | `/api/public/orden/{token}/` | Seguimiento publico para el cliente. No requiere login. |

Este endpoint devuelve solo informacion minima: estado, cliente, equipo, falla reportada y datos de retiro si corresponde.

## Datos sensibles

Las ordenes pueden guardar un dato de bloqueo del equipo: PIN, texto o patron. Ese dato se trata como informacion sensible.

Por eso:

- En listados de ordenes no se devuelve `bloqueo_valor`.
- En listados se devuelve `bloqueo_resumen`, por ejemplo `PIN cargado`.
- El valor completo queda disponible solamente en el detalle interno autenticado de una orden, porque el taller puede necesitarlo para trabajar sobre el equipo.
- El seguimiento publico nunca devuelve el bloqueo del equipo.

## Tests

Los tests usan `servicio_tecnico.settings_testing`, SQLite en memoria y un hasher rapido para passwords.

```powershell
.\.venv\Scripts\python.exe manage.py test --settings=servicio_tecnico.settings_testing
```

Check general:

```powershell
.\.venv\Scripts\python.exe manage.py check
```

Actualmente hay tests para:

- Login con cookies HttpOnly.
- Perfil de usuario.
- Creacion y busqueda de clientes.
- Bloqueo de eliminacion de clientes.
- Creacion de ordenes.
- Validacion de cambio de estado.
- Ocultamiento de datos sensibles en listados.
- Seguimiento publico por token.

## Notas de desarrollo

- `DEBUG=True` esta pensado para local.
- Con `DEBUG=False` se activan cookies seguras, SSL redirect y HSTS.
- CORS esta configurado para el frontend local y el deploy actual.
- Los tokens se leen desde cookies HttpOnly, con fallback a `Authorization: Bearer` para algunos usos internos.
- El endpoint publico por token no requiere login, pero devuelve datos acotados.

## Pendiente tecnico

- Sacar del repo los archivos ya trackeados en `media/` y `staticfiles/` en un commit separado.
- Revisar si a futuro conviene separar permisos por roles reales dentro del taller.
- Agregar tests para subida de fotos.
- Agregar documentacion de deploy cuando quede definido el hosting final.
