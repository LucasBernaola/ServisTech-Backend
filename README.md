# ServisTech Backend

Backend de ServisTech, un sistema de gestión para talleres de reparación técnica. Esta API cubre el flujo interno del taller: clientes, órdenes de reparación, estados de trabajo, importes, fotos, datos de retiro y seguimiento público para el cliente.

El proyecto está construido con Django, Django REST Framework y autenticación JWT mediante cookies HttpOnly.

## Stack

- Python
- Django 5.2
- Django REST Framework
- Simple JWT
- SQLite para desarrollo local
- PostgreSQL para producción
- WhiteNoise para archivos estáticos
- Pillow para imágenes
- django-cors-headers
- django-grappelli para el admin

## Qué resuelve

- Gestión de clientes del taller.
- Gestión de órdenes de reparación.
- Flujo de estados: pendiente, diagnosticado, en progreso, reparado, finalizado y retirado.
- Presupuesto, seña, costo final, descuento por garantía y cobro final.
- Registro de retiro del equipo.
- Carga de fotos asociadas a una orden.
- Ficha técnica e impresión de orden desde el frontend.
- Seguimiento público por URL.
- Login con JWT guardado en cookies HttpOnly.
- Protección de datos sensibles del equipo, como PIN, texto o patrón de bloqueo.

## Estructura del proyecto

```txt
backend/
  api/
    authentication.py      Autenticación por cookies JWT
    middleware.py          Refresh automático de cookies
    pagination.py          Paginación estándar
    permissions.py         Permisos auxiliares
    serializers.py         Serializers de usuarios, clientes y órdenes
    urls.py                Rutas de la API
    views.py               ViewSets y endpoints principales
    tests.py               Tests de API
  ordenes/
    models.py              Modelos de Cliente, Orden y OrdenFoto
    admin.py               Registro en Django Admin
    tests.py               Tests del módulo
    migrations/            Migraciones
  servicio_tecnico/
    settings.py            Configuración principal
    settings_testing.py    Configuración para tests
    urls.py                URLs globales
    asgi.py
    wsgi.py
  manage.py
  requirements.txt
```

## Modelos principales

### Cliente

Representa a una persona que deja un equipo en el taller.

Campos principales:

- nombre;
- apellido;
- DNI;
- email;
- celular;
- fechas de creación y actualización.

La eliminación de clientes está bloqueada desde la API para no perder historial de órdenes.

### Orden

Representa una reparación o trabajo técnico.

Campos principales:

- cliente asociado;
- usuario que creó la orden;
- estado;
- tipo de dispositivo;
- marca, modelo e IMEI/serial;
- falla reportada;
- condición del equipo;
- accesorios entregados;
- diagnóstico;
- trabajo realizado;
- repuestos;
- presupuesto;
- seña;
- costo final;
- garantía;
- datos de bloqueo;
- datos de retiro;
- token público de seguimiento.

### OrdenFoto

Permite asociar imágenes a una orden, por ejemplo fotos de ingreso, estado del equipo o evidencia del trabajo.

## Estados de una orden

El flujo de trabajo usa estos estados:

```txt
pendiente
diagnosticado
en_progreso
reparado
finalizado
retirado
```

El cambio de estado se realiza desde:

```txt
PATCH /api/ordenes/{id}/estado/
```

Algunas transiciones validan datos obligatorios:

- Para pasar a `diagnosticado`, se requiere presupuesto.
- Para pasar a `finalizado`, se requiere costo final.
- Para pasar a `retirado`, se requiere nombre de quien retira y costo final cargado.

El backend también limpia datos cuando se vuelve hacia atrás desde ciertos estados, por ejemplo al revertir una orden retirada.

## Datos sensibles

Las órdenes pueden guardar un dato de bloqueo del equipo:

- sin contraseña;
- PIN;
- texto;
- patrón.

El valor completo del bloqueo se considera información sensible.

Reglas aplicadas:

- El listado de órdenes no devuelve `bloqueo_valor`.
- El listado devuelve `bloqueo_resumen`, por ejemplo `PIN cargado`.
- El detalle interno autenticado sí puede devolver el valor completo.
- El seguimiento público nunca devuelve datos de bloqueo.

## Variables de entorno

Crear un archivo `.env` dentro de `backend/`.

```env
SECRET_KEY=change-me
DJANGO_DEBUG=True
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

Base de datos:

- Si `DB_HOST` queda vacío, Django usa SQLite local.
- Si `DB_HOST` tiene valor, Django usa PostgreSQL con `DB_NAME`, `DB_USER`, `DB_PASSWORD` y `DB_PORT`.

Seguridad:

- `DJANGO_DEBUG=True` es para desarrollo local.
- `DJANGO_DEBUG=False` activa configuración de producción: cookies seguras, redirect HTTPS y HSTS.

## Instalación local

Desde la carpeta `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Aplicar migraciones:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

Crear un superusuario:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
```

Levantar el servidor:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

Servidor local:

```txt
http://127.0.0.1:8000
```

Admin de Django:

```txt
http://127.0.0.1:8000/admin/
```

## Endpoints principales

Todos los endpoints internos viven bajo `/api/`.

### Autenticación y usuario

| Método | Ruta | Descripción |
| --- | --- | --- |
| POST | `/api/token/` | Login. Devuelve y setea cookies JWT. |
| POST | `/api/logout/` | Cierra sesión borrando cookies. |
| GET/PATCH | `/api/profile/` | Lee o actualiza el usuario autenticado. |
| POST | `/api/profile/change-password/` | Cambia la contraseña del usuario autenticado. |
| GET | `/api/verificar-admin/` | Devuelve 200 si el usuario es superuser. |

### Clientes

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/api/clientes/` | Lista clientes con paginación. |
| POST | `/api/clientes/` | Crea un cliente. |
| GET | `/api/clientes/{id}/` | Detalle de cliente. |
| PATCH | `/api/clientes/{id}/` | Actualiza un cliente. |
| GET | `/api/clientes/recent/` | Últimos clientes cargados. |

Búsqueda:

```txt
/api/clientes/?search=juan
/api/clientes/?search=30111222
```

Ordenamiento:

```txt
/api/clientes/?ordering=apellido
/api/clientes/?ordering=-created_at
```

### Órdenes

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/api/ordenes/` | Lista órdenes con paginación. |
| POST | `/api/ordenes/` | Crea una orden. |
| GET | `/api/ordenes/{id}/` | Detalle completo de una orden. |
| PATCH | `/api/ordenes/{id}/` | Actualiza datos de una orden. |
| PATCH | `/api/ordenes/{id}/estado/` | Cambia el estado de trabajo. |
| POST | `/api/ordenes/{id}/fotos/` | Sube una o varias fotos. |
| GET | `/api/ordenes/recent/` | Últimas órdenes cargadas. |
| GET | `/api/ordenes/{id}/print/ficha-tecnica/` | Redirige a la ficha técnica del frontend. |
| GET | `/api/ordenes/{id}/print/seguimiento/` | Redirige a la impresión de orden del frontend. |

Filtros:

```txt
/api/ordenes/?tab=pendiente
/api/ordenes/?tab=finalizado
/api/ordenes/?estado=diagnosticado
/api/ordenes/?search=samsung
```

### Seguimiento público

| Método | Ruta | Descripción |
| --- | --- | --- |
| GET | `/api/public/orden/{token}/` | Devuelve información pública de una orden. No requiere login. |

Este endpoint devuelve datos mínimos para el cliente:

- id de orden;
- estado;
- cliente;
- equipo;
- falla reportada;
- fecha de actualización;
- datos de retiro si corresponde.

No devuelve información interna ni datos de bloqueo.

## Autenticación

El backend usa Simple JWT, pero los tokens se guardan como cookies HttpOnly:

- `access_token`: duración corta;
- `refresh_token`: duración más larga.

La clase `CookieJWTAuthentication` permite autenticar leyendo el token desde la cookie. También se mantiene soporte para `Authorization: Bearer` en casos donde haga falta.

El middleware `CookieRefreshMiddleware` se encarga de renovar cookies cuando corresponde.

## CORS y frontend

El backend está preparado para trabajar con frontend separado. En desarrollo se aceptan orígenes como:

```txt
http://localhost:3000
http://localhost:4321
```

Además, `CORS_ALLOW_CREDENTIALS=True` permite que el navegador trabaje con cookies.

## Archivos subidos y estáticos

En desarrollo:

- las fotos se guardan en `media/`;
- los estáticos recolectados van a `staticfiles/`.

Ambas carpetas están ignoradas por Git porque son archivos generados o subidos localmente.

## Tests

Ejecutar tests:

```powershell
.\.venv\Scripts\python.exe manage.py test --settings=servicio_tecnico.settings_testing
```

Check de Django:

```powershell
.\.venv\Scripts\python.exe manage.py check
```

Cobertura actual:

- login con cookies HttpOnly;
- perfil de usuario;
- creación y búsqueda de clientes;
- bloqueo de eliminación de clientes;
- creación de órdenes;
- validación de cambio de estado;
- ocultamiento de datos sensibles en listados;
- seguimiento público sin autenticación.

## Relación con el frontend

El frontend consume esta API para:

- autenticar usuarios;
- listar y buscar clientes;
- crear y editar órdenes;
- cambiar estados;
- subir fotos;
- generar URLs de seguimiento;
- abrir vistas imprimibles.

Las URLs de impresión y seguimiento se configuran con:

```env
FRONTEND_TRACKING_URL_TEMPLATE
FRONTEND_PRINT_URL_TEMPLATE
FRONTEND_FICHA_URL_TEMPLATE
```

Esto permite cambiar el dominio del frontend sin tocar lógica de negocio.

## Validaciones recomendadas antes de subir cambios

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test --settings=servicio_tecnico.settings_testing
```

También conviene probar manualmente:

- login;
- creación de cliente;
- creación de orden;
- cambio de estado;
- carga de fotos;
- seguimiento público;
- redirecciones de impresión.

## Estado actual

El backend está listo para demo de portfolio: tiene API REST, autenticación por cookies, reglas de negocio, seguimiento público, manejo de datos sensibles y tests sobre los flujos principales.

Mejoras posibles a futuro:

- sumar tests para subida de fotos;
- agregar roles más específicos dentro del taller;
- documentar el deploy final cuando el hosting quede cerrado;
- agregar auditoría de cambios de estado si el proyecto crece.
