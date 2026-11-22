"""Envío de correos desde el CRM.

Con GMAIL_USUARIO y GMAIL_CONTRASENA_APLICACION en .env se envían por Gmail; sin ellos,
Django los muestra en la terminal donde corre runserver (ver config/settings.py)."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.utils import timezone

from actividades.models import Actividad

from .models import Mensaje


def correo_en_consola():
    """True en desarrollo sin Gmail: los correos se imprimen en la terminal."""
    return settings.EMAIL_BACKEND.endswith("console.EmailBackend")


def enviados_hoy():
    """Correos enviados hoy (Gmail permite un máximo por día)."""
    return Mensaje.objects.filter(estado=Mensaje.Estado.ENVIADO, creado__date=timezone.localdate()).count()


def enviar(*, contacto, asunto, cuerpo, propiedad=None, oportunidad=None, plantilla=None):
    """Envía el correo, lo guarda en «Correos enviados» y, si sale bien, lo deja en el historial
    del contacto (y de la propiedad u oportunidad). Devuelve el Mensaje.
    Lanza ValidationError si no se puede intentar el envío."""
    if not contacto.email:
        raise ValidationError("El contacto no tiene correo electrónico.")
    if enviados_hoy() >= settings.CORREO_LIMITE_DIARIO:
        raise ValidationError(f"Se alcanzó el límite diario de {settings.CORREO_LIMITE_DIARIO} correos de Gmail. "
                              "Inténtelo mañana.")
    asunto = " ".join(asunto.split())  # el asunto va en una sola línea
    correo = EmailMessage(subject=asunto, body=cuerpo, from_email=settings.DEFAULT_FROM_EMAIL, to=[contacto.email],
                          reply_to=[settings.CORREO_RESPONDER_A] if settings.CORREO_RESPONDER_A else None)
    mensaje = Mensaje(contacto=contacto, propiedad=propiedad, oportunidad=oportunidad, plantilla=plantilla,
                      para=contacto.email, asunto=asunto, cuerpo=cuerpo)
    try:
        correo.send()
    except Exception as e:  # sin conexión, credenciales malas, etc.: se registra el error y se informa
        mensaje.estado = Mensaje.Estado.ERROR
        mensaje.error = f"{type(e).__name__}: {e}"[:1000]
        mensaje.save()
        return mensaje
    mensaje.estado = Mensaje.Estado.ENVIADO
    mensaje.save()
    Actividad.objects.create(tipo=Actividad.Tipo.CORREO, estado=Actividad.Estado.REALIZADA,
                             descripcion=f"Correo enviado a {contacto.email}: «{asunto}»\n\n{cuerpo}",
                             contacto=contacto, propiedad=propiedad, oportunidad=oportunidad)
    return mensaje
