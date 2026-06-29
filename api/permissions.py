from rest_framework.exceptions import PermissionDenied

class RolPermisoMixin:
    """
    Permiso simple para vistas internas que necesitan usuario de staff.
    """
    permiso_nombre: str = None

    def initial(self, request, *args, **kwargs):
        initial = getattr(super(), "initial", None)
        if callable(initial):
            initial(request, *args, **kwargs)

        if self.permiso_nombre:
            user = getattr(request, "user", None)
            if not (user and user.is_authenticated and user.is_staff):
                raise PermissionDenied(
                    f"No tienes permiso para {self.permiso_nombre.replace('_', ' ')}."
                )
