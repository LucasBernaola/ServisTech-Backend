# ServisTech - Sistema de Gestión de Reparaciones

Este proyecto es un sistema de gestión para un taller de reparaciones electrónicas, diseñado para manejar clientes, órdenes de reparación y técnicos. Está dividido en dos partes: backend y frontend. Este README documenta el estado actual del backend y se actualizará con el frontend cuando esté desarrollado.

---

## Backend

El backend está construido con **Django** y **Django REST Framework**, usando **PostgreSQL** como base de datos. Proporciona una API RESTful para gestionar usuarios, equipos, fichas de reparación y fichas técnicas, con roles definidos para `Cliente`, `Ventas` y `Técnico`.

### Herramientas y tecnologías
- **Lenguaje**: Python 3.9+
- **Framework**: Django 4.x
- **API**: Django REST Framework (DRF)
- **Autenticación**: JWT con `djangorestframework-simplejwt`
- **Base de datos**: PostgreSQL
- **Gestión de dependencias**: pip (`requirements.txt`)
- **Control de versiones**: Git (repositorio en GitHub)
- **Entorno**: Virtualenv para desarrollo local
- **Otras librerías**:
  - `psycopg2-binary`: Adaptador para PostgreSQL
  - (Pendiente) `cryptography`: Para encriptar datos sensibles en el futuro

### Estructura del proyecto

necotec/
├── necotec/              # Configuración del proyecto
│   ├── init.py
│   ├── settings.py       # Configuración de Django
│   ├── urls.py           # Rutas principales
│   └── wsgi.py           # Entrada WSGI
├── ordenes/              # App para gestionar reparaciones
│   ├── init.py
│   ├── admin.py
│   ├── models.py         # Modelos: Equipo, Ficha, FichaTecnica
│   ├── serializers.py    # Serializers para la API
│   ├── urls.py           # Rutas de la app ordenes
│   └── views.py          # Vistas de la API
├── usuarios/             # App para gestionar usuarios y roles
│   ├── init.py
│   ├── admin.py
│   ├── models.py         # Modelo: UserProfile
│   ├── roles.py          # Sistema de permisos por rol
│   ├── serializers.py    # Serializers para usuarios
│   ├── urls.py           # Rutas de la app usuarios
│   └── views.py          # Vistas de autenticación y perfil
├── manage.py             # Script de gestión de Django
└── requirements.txt      # Dependencias del proyecto


### Modelos principales
1. **Equipo**:
   - Campos: `imei`, `tipo`, `marca`, `modelo`, `falla_reportada`, `condicion`, `accesorios`, `cliente` (ForeignKey a `User`).
   - Descripción: Representa un dispositivo ingresado al taller.
2. **Ficha**:
   - Campos: `cliente`, `equipo`, `creado_por`, `tecnico_asignado` (nullable), `estado` (`ingresado`, `en_revision`, `reparado`, `entregado`), `fecha_ingreso`, `observaciones`.
   - Descripción: Orden de reparación con estado y asignación.
3. **FichaTecnica**:
   - Campos: `ficha` (OneToOne), `creado_por`, `presupuesto`, `repuestos`, `garantia_dias`, `fecha_reparacion`, `observaciones`.
   - Descripción: Detalles técnicos de la reparación.

### Endpoints de la API
#### Usuarios
- `POST /api/register/`: Registro de nuevos usuarios (rol `Cliente` por defecto).
- `POST /api/token/`: Obtener token JWT.
- `GET, PUT /api/profile/`: Ver y editar perfil del usuario autenticado.
- `GET /api/clientes/buscar/?q=<query>`: Buscar clientes por nombre, apellido o DNI (roles `Ventas`, `Técnico`).

#### Órdenes
- `POST /api/equipos/crear/`: Crear un equipo (roles `Ventas`, `Técnico`).
- `POST /api/fichas/crear/`: Crear una ficha con equipo (rol `Ventas`).
- `POST /api/fichas/tecnica/crear/`: Crear ficha técnica (rol `Técnico`).
- `GET /api/fichas/pendientes/`: Listar todas las fichas (todos los estados, roles `Técnico`).
- `GET, PATCH /api/fichas/<id>/`: Ver y actualizar una ficha (roles `Ventas`, `Técnico`).
- `PATCH /api/fichas/<id>/tomar/`: Asignar técnico a una ficha (rol `Técnico`).
- `PATCH /api/fichas/<id>/liberar/`: Liberar una ficha asignada (rol `Técnico`).
- `GET /api/fichas/tecnico/historial/`: Historial de fichas del técnico autenticado (rol `Técnico`).
- `GET /api/fichas/cliente/`: Historial de fichas del cliente autenticado (rol `Cliente`).

### Configuración de roles y permisos
- **Cliente**: Ver historial (`ver_historial_fichas`).
- **Ventas**: Crear/editar fichas (`registrar_cliente`, `actualizar_ficha`), buscar clientes (`buscar_cliente`).
- **Técnico**: Gestionar fichas (`tomar_ficha`, `crear_ficha_tecnica`, `actualizar_ficha`, `ver_historial_fichas`, `buscar_cliente`).

### Requisitos para ejecutar localmente
1. **Instalar dependencias**:

pip install -r requirements.txt

2. **Configurar entorno**:
   - Copiar `.env.example` a `.env` y completar los valores
     de las variables.
   - Un ejemplo de configuración es el siguiente:
     ```
     SECRET_KEY=changeme
     DEBUG=True
     DATABASE_URL=postgres://usuario:contraseña@localhost:5432/necotec_db
     ```
   - Instalar PostgreSQL localmente y crear la base `servicio_tecnico_db`.


3. **Migraciones**:

   python manage.py makemigrations
   python manage.py migrate

4. **Ejecutar servidor**:

    python manage.py runserver
5. **Ejecutar pruebas**:

   python manage.py test --settings=servicio_tecnico.settings_testing



### Repositorio
[GitHub](https://github.com/LucasBernaola/Necotec)

    
### Estado actual
- El backend está completo para el flujo básico: registro, creación de fichas, asignación a técnicos, liberación, y consulta por rol.
- Pendientes:
  - Notificaciones (email/WhatsApp).
  - Actualizaciones en tiempo real (WebSockets con Django Channels).
  - Encriptación de datos sensibles (ej. DNI).

---


