import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class Cliente(models.Model):
    nombre = models.CharField(max_length=80)
    apellido = models.CharField(max_length=80, blank=True, default="")
    dni = models.CharField(max_length=30, blank=True, default="", db_index=True)
    email = models.EmailField(blank=True, default="")
    celular = models.CharField(max_length=30, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["dni"]),
            models.Index(fields=["apellido", "nombre"]),
        ]

    def __str__(self):
        full = f"{self.nombre} {self.apellido}".strip()
        return full or f"Cliente {self.id}"


class Orden(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        DIAGNOSTICADO = "diagnosticado", "Diagnosticado"
        EN_PROGRESO = "en_progreso", "En progreso"
        REPARADO = "reparado", "Reparado"
        FINALIZADO = "finalizado", "Finalizado"
        RETIRADO = "retirado", "Retirado"

    class BloqueoTipo(models.TextChoices):
        NONE = "none", "Sin contraseña"
        PIN = "pin", "Código (PIN)"
        TEXTO = "texto", "Texto"
        PATRON = "patron", "Patrón"

    public_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    cliente = models.ForeignKey(
        Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordenes"
    )

    creado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="ordenes_creadas"
    )

    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PENDIENTE
    )

    dispositivo_tipo = models.CharField(max_length=50, blank=True, default="")
    marca = models.CharField(max_length=50, blank=True, default="")
    modelo = models.CharField(max_length=80, blank=True, default="")
    imei_serial = models.CharField(max_length=50, blank=True, default="")

    falla_reportada = models.TextField(blank=True, default="")
    condicion_equipo = models.CharField(max_length=120, blank=True, default="")
    accesorios_entregados = models.TextField(blank=True, default="")
    observaciones = models.TextField(blank=True, default="")

    diagnostico = models.TextField(blank=True, default="")
    trabajo_realizado = models.TextField(blank=True, default="")
    repuestos = models.TextField(blank=True, default="")

    presupuesto = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    senia = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)]
    )

    costo_final = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    garantia_descuento = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        validators=[MinValueValidator(0)]
    )
    garantia_dias = models.PositiveIntegerField(default=0)
    observaciones_finales = models.TextField(blank=True, default="")

    bloqueo_tipo = models.CharField(
        max_length=10,
        choices=BloqueoTipo.choices,
        default=BloqueoTipo.NONE
    )
    bloqueo_valor = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="PIN, texto o secuencia de patrón tipo '1-2-5-8'"
    )

    fecha_finalizado = models.DateTimeField(null=True, blank=True)

    # NUEVO: datos de retiro
    retirado_por_nombre = models.CharField(max_length=120, blank=True, default="")
    retirado_por_dni = models.CharField(max_length=30, blank=True, default="")
    observaciones_retiro = models.TextField(blank=True, default="")
    fecha_retirado = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def cobro_final(self):
        if self.costo_final is None:
            return None
        return max(self.costo_final - (self.garantia_descuento or 0), 0)

    def __str__(self):
        return f"Orden #{self.id} - {self.estado}"


class OrdenFoto(models.Model):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name="fotos")
    imagen = models.ImageField(upload_to="ordenes/")
    descripcion = models.CharField(max_length=140, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Foto Orden #{self.orden_id}"