import re

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from ordenes.models import Cliente, Orden, OrdenFoto


class UserSerializer(serializers.ModelSerializer):
    """
    Para /api/profile/ (mostrar y actualizar usuario logueado).
    """
    username = serializers.CharField(
        validators=[UniqueValidator(queryset=User.objects.all(), message="El nombre de usuario ya está en uso.")]
    )
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "is_superuser", "is_staff", "is_active"]
        read_only_fields = ["id", "is_superuser", "is_staff", "is_active"]


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ["id", "nombre", "apellido", "dni", "email", "celular", "created_at", "updated_at"]


class OrdenFotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdenFoto
        fields = ["id", "imagen", "descripcion", "created_at"]


class OrdenSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    cliente = ClienteSerializer(read_only=True)
    cliente_id = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.all(),
        source="cliente",
        write_only=True,
        required=False,
        allow_null=True
    )
    cobro_final = serializers.SerializerMethodField()
    fotos = OrdenFotoSerializer(many=True, read_only=True)

    class Meta:
        model = Orden
        fields = [
            "id",
            "public_token",
            "estado",
            "cliente",
            "cliente_id",
            "creado_por",
            "estado_display",

            "dispositivo_tipo", "marca", "modelo", "imei_serial",
            "falla_reportada", "condicion_equipo", "accesorios_entregados", "observaciones",
            "diagnostico", "trabajo_realizado", "repuestos",

            "presupuesto", "senia",
            "costo_final", "garantia_descuento", "garantia_dias",
            "cobro_final",

            "bloqueo_tipo",
            "bloqueo_valor",

            "observaciones_finales",
            "fecha_finalizado",

            "retirado_por_nombre",
            "retirado_por_dni",
            "observaciones_retiro",
            "fecha_retirado",

            "created_at", "updated_at",
            "fotos",
        ]
        read_only_fields = [
            "public_token",
            "creado_por",
            "fecha_finalizado",
            "fecha_retirado",
            "created_at",
            "updated_at",
            "cobro_final",
        ]

    def get_cobro_final(self, obj: Orden):
        return obj.cobro_final

    def validate(self, attrs):
        """
        Valida bloqueo_tipo / bloqueo_valor según el tipo.
        Soporta PATCH parcial: si no vienen campos, usa los del instance.
        """
        instance = getattr(self, "instance", None)

        tipo = attrs.get("bloqueo_tipo", instance.bloqueo_tipo if instance else "none")
        valor = attrs.get("bloqueo_valor", instance.bloqueo_valor if instance else "")

        valor = (valor or "").strip()

        if tipo == "none":
            attrs["bloqueo_valor"] = ""
            return attrs

        if tipo == "pin":
            if not re.fullmatch(r"\d{4}|\d{6}", valor):
                raise serializers.ValidationError({"bloqueo_valor": "El PIN debe ser de 4 o 6 dígitos."})

        elif tipo == "texto":
            if len(valor) < 1:
                raise serializers.ValidationError({"bloqueo_valor": "La contraseña no puede estar vacía."})

        elif tipo == "patron":
            if not re.fullmatch(r"[1-9](?:-[1-9])*", valor):
                raise serializers.ValidationError({"bloqueo_valor": "Formato inválido. Ej: '1-2-5-8'."})

            nodes = valor.split("-")
            if len(nodes) < 3:
                raise serializers.ValidationError({"bloqueo_valor": "El patrón debe tener al menos 3 puntos."})

        else:
            raise serializers.ValidationError({"bloqueo_tipo": "Tipo de bloqueo inválido."})

        attrs["bloqueo_valor"] = valor
        return attrs


class OrdenPublicSerializer(serializers.ModelSerializer):
    cliente = ClienteSerializer(read_only=True)

    class Meta:
        model = Orden
        fields = [
            "id",
            "public_token",
            "estado",
            "cliente",
            "dispositivo_tipo", "marca", "modelo",
            "falla_reportada",
            "diagnostico", "trabajo_realizado",
            "presupuesto", "senia",
            "costo_final", "garantia_dias",
            "observaciones_finales",
            "fecha_finalizado",
            "retirado_por_nombre",
            "retirado_por_dni",
            "observaciones_retiro",
            "fecha_retirado",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("La contraseña actual es incorrecta.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user