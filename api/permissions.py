from rest_framework.exceptions import PermissionDenied
from usuarios.roles import RolPermission

class RolPermisoMixin:
    """
    Mixin para validar permisos basados en roles definidos
    en la clase RolPermission.
    """
    permiso_nombre: str = None

    def initial(self, request, *args, **kwargs):
        initial = getattr(super(), "initial", None)
        if callable(initial):
            initial(request, *args, **kwargs)

        if self.permiso_nombre:
            tiene = RolPermission().check_permission(request, self.permiso_nombre)
            if not tiene:
                raise PermissionDenied(
                    f"No tienes permiso para {self.permiso_nombre.replace('_', ' ')}."
                )