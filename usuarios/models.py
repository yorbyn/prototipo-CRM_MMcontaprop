from django.contrib.auth.models import User
from django.db import models

# Roles del CRM:
# - Administrador: usa todo el CRM y además crea y edita usuarios.
# - Trabajador: usa el CRM, pero no la pantalla de usuarios.
# El superusuario (creado con «createsuperuser») siempre es administrador.
ADMINISTRADOR = "Administrador"
TRABAJADOR = "Trabajador"


class Rol(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "roles"

    def __str__(self):
        return self.nombre


class Perfil(models.Model):
    rol = models.ForeignKey(Rol, on_delete=models.RESTRICT)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "perfiles"

    def __str__(self):
        return f"{self.user.username} - {self.rol.nombre}"


def rol_de(usuario):
    """Nombre del rol del usuario, o "" si no tiene perfil."""
    perfil = Perfil.objects.filter(user=usuario).select_related("rol").first()
    return perfil.rol.nombre if perfil else ""


def es_admin_crm(usuario):
    if not (usuario.is_authenticated and usuario.is_active):
        return False
    return usuario.is_superuser or rol_de(usuario) == ADMINISTRADOR
