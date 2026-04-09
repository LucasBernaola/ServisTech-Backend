from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    UserProfileView,
    ChangePasswordView,           # 👈 agregar
    CustomTokenObtainPairView,
    LogoutView,
    VerificarAdminView,
    ClienteViewSet,
    OrdenViewSet,
    PublicOrdenRetrieveView,
)

router = DefaultRouter()
router.register(r"clientes", ClienteViewSet, basename="clientes")
router.register(r"ordenes", OrdenViewSet, basename="ordenes")

urlpatterns = [
    path("profile/",  UserProfileView.as_view(), name="profile"),
    path("profile/change-password/", ChangePasswordView.as_view(), name="change-password"),  # 👈 nuevo

    path("token/",    CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("logout/",   LogoutView.as_view(), name="logout"),
    path("verificar-admin/", VerificarAdminView.as_view(), name="verificar-admin"),

    # público (seguimiento)
    path("public/orden/<uuid:token>/", PublicOrdenRetrieveView.as_view(), name="public-orden"),

    path("", include(router.urls)),
]