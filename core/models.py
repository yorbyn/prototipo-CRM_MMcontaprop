from django.db import models
from django.conf import settings

# Create your models here.
class Auditado(models.Model):
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                   blank=True, editable=False, related_name="+")
    modificado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                       blank=True, editable=False, related_name="+")

    class Meta:
        abstract = True

    def guardar_por(self, usuario, **kwargs):
        """Guarda registrando al usuario responsable."""
        if usuario is not None and usuario.is_authenticated:
            if not self.pk:
                self.creado_por = usuario
            self.modificado_por = usuario
        self.save(**kwargs)