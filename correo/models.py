"""
Correo, nivel 1: enviar correos desde el CRM con plantillas y dejarlos en el
historial. Se envía por el SMTP de Gmail con una contraseña de aplicación
(configurada en .env). Las respuestas llegan a la bandeja habitual (Reply-To).
"""
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from core.models import Auditado
from core.templatetags.formato import precio

# Variables disponibles en las plantillas y qué significan.
VARIABLES = {
    "nombre": "Nombre del contacto",
    "propiedad": "Título de la propiedad",
    "codigo": "Código de la propiedad",
    "precio": "Precio de la propiedad",
    "comuna": "Comuna de la propiedad",
    "enlace": "Enlace a la ficha pública (solo si está publicada)",
    "empresa": "Nombre de la corredora",
    "telefono_empresa": "Teléfono de la corredora",
}
PATRON = re.compile(r"\{(\w+)\}")


def variables_desconocidas(texto):
    return sorted({v for v in PATRON.findall(texto or "") if v not in VARIABLES})


def reemplazar(texto, valores):
    """Sustituye {variable} por su valor. Solo usa las variables de la lista cerrada;
    nunca datos privados como la dirección exacta o el RUT."""
    return PATRON.sub(lambda m: str(valores.get(m.group(1), m.group(0))), texto or "")


class PlantillaCorreo(Auditado):
    nombre = models.CharField(max_length=80)
    clave = models.SlugField(max_length=40, unique=True,
                             help_text="Identificador interno, sin espacios. Ej.: envio-ficha")
    asunto = models.CharField(max_length=150)
    cuerpo = models.TextField(max_length=5000)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "plantilla de correo"
        verbose_name_plural = "plantillas de correo"

    def __str__(self):
        return self.nombre

    def clean(self):
        desconocidas = variables_desconocidas(f"{self.asunto} {self.cuerpo}")
        if desconocidas:
            raise ValidationError("Variables no reconocidas: " + ", ".join("{" + v + "}" for v in desconocidas)
                                  + ". Use solo las de la lista.")


class Mensaje(Auditado):
    """Cada correo enviado (o que falló) desde el CRM."""

    class Estado(models.TextChoices):
        ENVIADO = "enviado", "Enviado"
        ERROR = "error", "Error al enviar"

    contacto = models.ForeignKey("contactos.Contacto", on_delete=models.PROTECT, related_name="mensajes")
    propiedad = models.ForeignKey("propiedades.Propiedad", on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="mensajes")
    oportunidad = models.ForeignKey("comercial.Oportunidad", on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="mensajes")
    plantilla = models.ForeignKey(PlantillaCorreo, on_delete=models.SET_NULL, null=True, blank=True)
    para = models.EmailField()
    destinatarios = models.PositiveSmallIntegerField(default=1, editable=False,
                                                     help_text="Para + copia oculta (Gmail cuenta destinatarios).")
    asunto = models.CharField(max_length=150)
    cuerpo = models.TextField()
    estado = models.CharField(max_length=8, choices=Estado.choices)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-creado", "-id"]
        verbose_name = "correo enviado"
        verbose_name_plural = "correos enviados"

    def __str__(self):
        return f"{self.asunto} → {self.para}"


def valores_para(contacto, propiedad=None, request=None):
    """Valores de las variables. De la propiedad solo se usan datos PÚBLICOS."""
    empresa = settings.EMPRESA
    v = {"nombre": contacto.nombre, "empresa": empresa["nombre"], "telefono_empresa": empresa["telefono"],
         "propiedad": "", "codigo": "", "precio": "", "comuna": "", "enlace": ""}
    if propiedad is not None:
        v.update(propiedad=propiedad.titulo, codigo=propiedad.codigo or "", comuna=propiedad.comuna,
                 precio=precio(propiedad.precio, propiedad.moneda))
        if propiedad.publicada and request is not None:
            v["enlace"] = request.build_absolute_uri(reverse("portal:ficha", args=[propiedad.codigo]))
    return v
