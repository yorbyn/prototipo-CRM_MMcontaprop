from django.db import models


class Auditado(models.Model):
    """Modelo base (abstracto): agrega la fecha de creación y la de última modificación.
    Los demás modelos heredan de él, por ejemplo: class Contacto(Auditado)."""
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True