
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.models import Auditado

# Create your models here.

class ActividadQuerySet(models.QuerySet):
    def agenda(self):
        """Visitas y tareas programadas que siguen pendientes."""
        return self.filter(tipo__in=Actividad.TIPOS_AGENDA, estado=Actividad.Estado.PENDIENTE)

    def vencidas(self):
        return self.agenda().filter(fecha__lt=timezone.now())

    def proximas(self):
        return self.agenda().filter(fecha__gte=timezone.now())


class Actividad(Auditado):
    class Tipo(models.TextChoices):
        NOTA = "nota", "Nota"
        LLAMADA = "llamada", "Llamada"
        REUNION = "reunion", "Reunión"
        VISITA = "visita", "Visita"
        TAREA = "tarea", "Tarea"
        CORREO = "correo", "Correo"
        SISTEMA = "sistema", "Registro automático"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        REALIZADA = "realizada", "Realizada"
        CANCELADA = "cancelada", "Cancelada"

    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.NOTA)
    descripcion = models.TextField("descripción")
    fecha = models.DateTimeField(default=timezone.now,
                                 help_text="Fecha de realización o fecha programada.")
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.REALIZADA)
    contacto = models.ForeignKey("contactos.Contacto", on_delete=models.CASCADE, null=True, blank=True,
                                 related_name="actividades")
    propiedad = models.ForeignKey("propiedades.Propiedad", on_delete=models.CASCADE, null=True, blank=True,
                                  related_name="actividades")
    oportunidad = models.ForeignKey("comercial.Oportunidad", on_delete=models.CASCADE, null=True, blank=True,
                                    related_name="actividades")

    objects = ActividadQuerySet.as_manager()

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "actividad"
        verbose_name_plural = "actividades"

    # ------.,----------------------------
    TIPOS_AGENDA = (Tipo.VISITA, Tipo.TAREA)

    def __str__(self):
        return f"{self.get_tipo_display()} {self.fecha:%d-%m-%Y}"

    @property
    def en_agenda(self):
        return self.tipo in self.TIPOS_AGENDA and self.estado == self.Estado.PENDIENTE

    @property
    def vencida(self):
        return self.en_agenda and self.fecha < timezone.now()

    def clean(self):
        if not (self.contacto_id or self.propiedad_id or self.oportunidad_id):
            raise ValidationError("La actividad debe asociarse a un contacto, una propiedad o una oportunidad.")

    @classmethod
    def registrar_sistema(cls, texto, usuario=None, contacto=None, propiedad=None, oportunidad=None, fecha=None):
        """Deja constancia automática de un hecho (cambio de estado, creación, etc.).
        Si se indica una oportunidad, el registro también aparece en su contacto y propiedad."""
        if oportunidad is not None:
            contacto = contacto or oportunidad.contacto
            propiedad = propiedad or oportunidad.propiedad
        actividad = cls(tipo=cls.Tipo.SISTEMA, descripcion=texto, contacto=contacto, propiedad=propiedad,
                        oportunidad=oportunidad)
        if fecha is not None:
            actividad.fecha = fecha
        actividad.guardar_por(usuario)
        return actividad
