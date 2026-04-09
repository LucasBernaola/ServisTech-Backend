import base64
import io
import logging

from django.db.models.functions import Lower
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string

from django.contrib.auth import authenticate
from django.db.models import Q
from django.utils import timezone

from rest_framework import generics, viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.decorators import action
from django.shortcuts import redirect
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import ChangePasswordSerializer
from .authentication import CookieJWTAuthentication
from rest_framework import generics, permissions
from ordenes.models import Cliente, Orden, OrdenFoto
from .serializers import (
    UserSerializer,
    ClienteSerializer,
    OrdenSerializer,
    OrdenFotoSerializer
)
from rest_framework.exceptions import MethodNotAllowed


logger = logging.getLogger(__name__)


# -----------------------------
# Helpers (cookies + print)
# -----------------------------

def _cookie_secure_from_request_or_settings(request) -> bool:
    """
    En dev puede ser http; en prod detrás de proxy request.is_secure() puede fallar
    si no está SECURE_PROXY_SSL_HEADER. Preferimos settings.
    """
    return bool(getattr(settings, "SESSION_COOKIE_SECURE", False))


def _cookie_samesite_from_settings(default: str = "Lax") -> str:
    # Si luego querés, definís ACCESS_COOKIE_SAMESITE en settings.
    return getattr(settings, "ACCESS_COOKIE_SAMESITE", default)


def _build_tracking_url(request, orden: Orden) -> str:
    """
    URL pública para seguimiento (QR).
    Por ahora apunta al endpoint público del backend.
    Más adelante podés cambiarlo para que apunte al frontend:
      FRONTEND_TRACKING_URL_TEMPLATE="https://app.tu-dominio.com/seguimiento/{token}"
    """
    tpl = getattr(settings, "FRONTEND_TRACKING_URL_TEMPLATE", "").strip()
    if tpl:
        return tpl.format(token=str(orden.public_token), orden_id=orden.id)

    # Backend público
    return request.build_absolute_uri(f"/api/public/orden/{orden.public_token}/")


def _qr_data_uri(text: str) -> str:
    """
    Genera un QR como data URI (PNG base64).
    Requiere: pip install qrcode[pil]
    Si no está instalado, devolvemos "" y el template puede ocultarlo.
    """
    try:
        import qrcode  # type: ignore
    except Exception:
        logger.warning("QR: paquete 'qrcode' no instalado. Instalar con: pip install qrcode[pil]")
        return ""

    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


# -----------------------------
# Auth / Sesión
# -----------------------------

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/profile/  -> devuelve info del usuario logueado
    PATCH /api/profile/ -> actualiza username, first_name, last_name, email
    """
    serializer_class = UserSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class CustomTokenObtainPairView(TokenObtainPairView):
    """
    POST /api/token/ -> login, guarda JWT en cookies HttpOnly.
    Devuelve { message } + flags admin/staff.
    """
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code != status.HTTP_200_OK:
            return Response({"message": "Credenciales inválidas"}, status=status.HTTP_401_UNAUTHORIZED)

        access = response.data.get("access")
        refresh = response.data.get("refresh")

        secure_cookie = _cookie_secure_from_request_or_settings(request)
        samesite = _cookie_samesite_from_settings(default="Lax" if settings.DEBUG else "None")

        response.set_cookie(
            key="access_token",
            value=access,
            max_age=60 * 30,
            httponly=True,
            secure=secure_cookie,
            samesite=samesite,
            path="/",
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh,
            max_age=60 * 60 * 24 * 7,
            httponly=True,
            secure=secure_cookie,
            samesite=samesite,
            path="/",
        )

        user = authenticate(
            username=request.data.get("username"),
            password=request.data.get("password"),
        )

        response.data = {
            "message": "Login exitoso",
            "is_admin": bool(user.is_superuser) if user else False,
            "is_staff": bool(user.is_staff) if user else False,
        }
        return response


class LogoutView(APIView):
    """
    POST /api/logout/ -> borra cookies.
    """
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        resp = Response({"detail": "Sesión cerrada"}, status=status.HTTP_200_OK)

        secure_cookie = _cookie_secure_from_request_or_settings(request)
        samesite = _cookie_samesite_from_settings(default="Lax" if settings.DEBUG else "None")

        resp.set_cookie(
            key="access_token",
            value="",
            expires=0,
            path="/",
            samesite=samesite,
            secure=secure_cookie,
        )
        resp.set_cookie(
            key="refresh_token",
            value="",
            expires=0,
            path="/",
            samesite=samesite,
            secure=secure_cookie,
        )
        return resp


class VerificarAdminView(APIView):
    """
    GET /api/verificar-admin/
    200 si es superuser, 403 si no.
    """
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_superuser:
            return Response({"detail": "Es admin"}, status=status.HTTP_200_OK)
        return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)


# -----------------------------
# Clientes (internos, NO users)
# -----------------------------

class ClienteViewSet(viewsets.ModelViewSet):
    """
    CRUD /api/clientes/
    + búsqueda: ?search=juan | dni | telefono
    + orden: ?ordering=apellido|-apellido|nombre|-nombre|dni|-dni|celular|-celular|id|-id|created_at|-created_at
    """

    serializer_class = ClienteSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    # 🔒 BLOQUEAR ELIMINACIÓN
    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed("DELETE", detail="Los clientes no se pueden eliminar.")

    def get_queryset(self):
        qs = Cliente.objects.all()

        search = (self.request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) |
                Q(apellido__icontains=search) |
                Q(dni__icontains=search) |
                Q(celular__icontains=search)
            )

        ordering = (self.request.query_params.get("ordering") or "").strip()

        # default estable (alfabético case-insensitive)
        def default_order(q):
            return q.order_by(Lower("apellido"), Lower("nombre"), "id")

        if not ordering:
            return default_order(qs)

        desc = ordering.startswith("-")
        field = ordering[1:] if desc else ordering

        if field in ("apellido", "nombre"):
            expr = Lower(field)
            return qs.order_by(expr.desc() if desc else expr.asc(), "id")

        if field in ("dni", "celular", "id", "created_at"):
            return qs.order_by(f"-{field}" if desc else field, "id")

        # fallback seguro
        return default_order(qs)

    @action(detail=False, methods=["get"], url_path="recent")
    def recent(self, request):
        qs = Cliente.objects.order_by("-created_at")[:5]
        return Response(self.get_serializer(qs, many=True).data)
    
# -----------------------------
# Órdenes
# -----------------------------

class OrdenViewSet(viewsets.ModelViewSet):
    """
    CRUD /api/ordenes/
    + tabs: ?tab=pendiente|finalizado
    + search: ?search=3|juan|samsung|j7
    + filtro exacto de estado: ?estado=diagnosticado
    """
    queryset = Orden.objects.select_related("cliente").all().order_by("-id")
    serializer_class = OrdenSerializer
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()

        tab = (self.request.query_params.get("tab") or "").strip().lower()
        if tab == "finalizado":
            qs = qs.filter(estado__in=[Orden.Estado.FINALIZADO, Orden.Estado.RETIRADO])
        elif tab == "pendiente":
            qs = qs.exclude(estado__in=[Orden.Estado.FINALIZADO, Orden.Estado.RETIRADO])

        estado = (self.request.query_params.get("estado") or "").strip().lower()
        if estado:
            qs = qs.filter(estado=estado)

        search = (self.request.query_params.get("search") or "").strip()
        if search:
            if search.isdigit():
                qs = qs.filter(id=int(search))
            else:
                qs = qs.filter(
                    Q(cliente__nombre__icontains=search)
                    | Q(cliente__apellido__icontains=search)
                    | Q(cliente__dni__icontains=search)
                    | Q(marca__icontains=search)
                    | Q(modelo__icontains=search)
                    | Q(imei_serial__icontains=search)
                    | Q(retirado_por_nombre__icontains=search)
                    | Q(retirado_por_dni__icontains=search)
                )

        return qs

    @action(detail=False, methods=["get"], url_path="recent")
    def recent(self, request):
        qs = Orden.objects.select_related("cliente").order_by("-created_at")[:5]
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=["patch"], url_path="estado")
    def cambiar_estado(self, request, pk=None):
        """
        PATCH /api/ordenes/<id>/estado/

        Ejemplos:
          {"estado":"diagnosticado", "presupuesto":20000, "senia":10000}
          {"estado":"finalizado", "costo_final":20000, "garantia_descuento":0, "garantia_dias":0}
          {"estado":"retirado", "retirado_por_nombre":"Juan Pérez", "retirado_por_dni":"30111222", "observaciones_retiro":"Retira hermano"}
        """
        orden: Orden = self.get_object()
        nuevo = (request.data.get("estado") or "").strip()

        if nuevo not in dict(Orden.Estado.choices):
            raise ValidationError("Estado inválido.")

        estado_anterior = orden.estado

        updatable = [
            "presupuesto",
            "senia",
            "diagnostico",
            "trabajo_realizado",
            "repuestos",
            "costo_final",
            "garantia_descuento",
            "garantia_dias",
            "observaciones_finales",
            "bloqueo_tipo",
            "bloqueo_valor",
            "retirado_por_nombre",
            "retirado_por_dni",
            "observaciones_retiro",
        ]
        for f in updatable:
            if f in request.data:
                setattr(orden, f, request.data.get(f))

        # Si volvés atrás desde FINALIZADO a un estado previo, limpiar fecha_finalizado
        # OJO: si pasa de FINALIZADO -> RETIRADO, NO se limpia.
        if (
            estado_anterior == Orden.Estado.FINALIZADO
            and nuevo not in [Orden.Estado.FINALIZADO, Orden.Estado.RETIRADO]
        ):
            orden.fecha_finalizado = None

        # Si volvés atrás desde RETIRADO, limpiar datos de retiro
        if estado_anterior == Orden.Estado.RETIRADO and nuevo != Orden.Estado.RETIRADO:
            orden.fecha_retirado = None
            orden.retirado_por_nombre = ""
            orden.retirado_por_dni = ""
            orden.observaciones_retiro = ""

        # Validaciones
        if nuevo == Orden.Estado.DIAGNOSTICADO:
            if orden.presupuesto is None:
                raise ValidationError("Para 'diagnosticado' se requiere presupuesto.")

        if nuevo == Orden.Estado.FINALIZADO:
            if orden.costo_final is None:
                raise ValidationError("Para 'finalizado' se requiere costo_final.")
            if (orden.garantia_descuento or 0) > orden.costo_final:
                raise ValidationError("garantia_descuento no puede ser mayor que costo_final.")
            if orden.fecha_finalizado is None:
                orden.fecha_finalizado = timezone.now()

        if nuevo == Orden.Estado.RETIRADO:
            if not (orden.retirado_por_nombre or "").strip():
                raise ValidationError("Para 'retirado' se requiere el nombre de quien retira.")

            # Si por alguna razón saltearon finalizado, al menos exigimos costo final cargado
            if orden.costo_final is None:
                raise ValidationError("Para 'retirado' la orden debe tener costo_final cargado.")

            if orden.fecha_finalizado is None:
                orden.fecha_finalizado = timezone.now()

            orden.fecha_retirado = timezone.now()

        orden.estado = nuevo
        orden.save()

        return Response(OrdenSerializer(orden).data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
        url_path="fotos",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_fotos(self, request, pk=None):
        """
        POST /api/ordenes/<id>/fotos/
        multipart/form-data
        - imagen: archivo (puede repetirse)
        - descripcion: opcional (aplica a todas si mandás múltiples)
        """
        orden: Orden = self.get_object()

        files = request.FILES.getlist("imagen")
        if not files:
            return Response(
                {"detail": "Se requiere al menos una imagen."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created = []
        desc = (request.data.get("descripcion") or "").strip()

        for f in files:
            foto = OrdenFoto.objects.create(
                orden=orden,
                imagen=f,
                descripcion=desc,
            )
            created.append(foto)

        return Response(
            OrdenFotoSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path=r"print/ficha-tecnica")
    def print_ficha_tecnica(self, request, pk=None):
        orden: Orden = self.get_object()
        tpl = getattr(settings, "FRONTEND_FICHA_URL_TEMPLATE", "").strip()
        if not tpl:
            tpl = "http://localhost:3000/imprimir/ficha/{orden_id}"
        url = tpl.format(token=str(orden.public_token), orden_id=orden.id)
        return redirect(url)

    @action(detail=True, methods=["get"], url_path=r"print/seguimiento")
    def print_seguimiento(self, request, pk=None):
        orden: Orden = self.get_object()

        tpl = getattr(settings, "FRONTEND_PRINT_URL_TEMPLATE", "").strip()
        if not tpl:
            tpl = "http://localhost:3000/imprimir/orden/{orden_id}"

        url = tpl.format(token=str(orden.public_token), orden_id=orden.id)
        return redirect(url)
# -----------------------------
# Público: Seguimiento por token
# -----------------------------

class PublicOrdenRetrieveView(APIView):
    """
    GET /api/public/orden/<uuid:token>/
    No requiere login.
    Devuelve info mínima para seguimiento del cliente.
    """
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            orden = Orden.objects.select_related("cliente").get(public_token=token)
        except Orden.DoesNotExist:
            raise NotFound("Orden no encontrada")

        data = {
            "orden_id": orden.id,
            "estado": orden.estado,
            "cliente": {
                "nombre": orden.cliente.nombre if orden.cliente else "",
                "apellido": orden.cliente.apellido if orden.cliente else "",
                "celular": getattr(orden.cliente, "celular", "") if orden.cliente else "",
            },
            "equipo": {
                "dispositivo_tipo": orden.dispositivo_tipo,
                "marca": orden.marca,
                "modelo": orden.modelo,
            },
            "falla_reportada": orden.falla_reportada or "",
            "updated_at": orden.updated_at,

            # NUEVO: datos de retiro
            "retirado_por_nombre": orden.retirado_por_nombre or "",
            "retirado_por_dni": orden.retirado_por_dni or "",
            "observaciones_retiro": orden.observaciones_retiro or "",
            "fecha_retirado": orden.fecha_retirado,
        }
        return Response(data, status=status.HTTP_200_OK)
class ChangePasswordView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = ChangePasswordSerializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response({"detail": "Contraseña actualizada."}, status=status.HTTP_200_OK)