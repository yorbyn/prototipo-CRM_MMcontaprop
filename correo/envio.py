"""Envío de correos desde el CRM."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.utils import timezone

from actividades.models import Actividad

from .models import Mensaje

SMTP = "django.core.mail.backends.smtp.EmailBackend"


def correo_configurado():
    """Con el SMTP real hacen falta la cuenta y la contraseña de aplicación. En las
    pruebas Django usa un backend en memoria y no se necesitan credenciales."""
    if settings.EMAIL_BACKEND != SMTP:
        return True
    return bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)


def correo_en_consola():
    """Desarrollo local sin Gmail: los correos se imprimen en la terminal de runserver."""
    return settings.EMAIL_BACKEND.endswith("console.EmailBackend")


def enviados_hoy():
    """Destinatarios de hoy (Gmail limita destinatarios, no mensajes: la copia oculta cuenta)."""
    from django.db.models import Sum
    inicio = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return (Mensaje.objects.filter(estado=Mensaje.Estado.ENVIADO, creado__gte=inicio)
            .aggregate(n=Sum("destinatarios"))["n"] or 0)


def enviar(*, contacto, asunto, cuerpo, usuario, propiedad=None, oportunidad=None, plantilla=None):
    """Envía el correo, lo guarda y lo deja en el historial del contacto (y de la
    propiedad u oportunidad). Devuelve el Mensaje. Lanza ValidationError si no se
    puede intentar el envío."""
    if not correo_configurado():
        raise ValidationError("El correo no está configurado: defina GMAIL_USUARIO y "
                              "GMAIL_CONTRASENA_APLICACION en el archivo .env.")
    if not contacto.email:
        raise ValidationError("El contacto no tiene correo electrónico.")
    responder_a = settings.CORREO_RESPONDER_A
    con_copia = bool(settings.CORREO_COPIA_OCULTA and responder_a)
    destinatarios = 2 if con_copia else 1
    if enviados_hoy() + destinatarios > settings.CORREO_LIMITE_DIARIO:
        raise ValidationError(f"Se alcanzó el límite diario de {settings.CORREO_LIMITE_DIARIO} correos de Gmail. "
                              "Inténtelo mañana.")
    asunto = " ".join(asunto.split())  # sin saltos de línea en la cabecera
    correo = EmailMessage(
        subject=asunto, body=cuerpo, from_email=settings.DEFAULT_FROM_EMAIL, to=[contacto.email],
        reply_to=[responder_a] if responder_a else None,
        bcc=[responder_a] if con_copia else None,
    )
    mensaje = Mensaje(contacto=contacto, propiedad=propiedad, oportunidad=oportunidad, plantilla=plantilla,
                      para=contacto.email, destinatarios=destinatarios, asunto=asunto, cuerpo=cuerpo)
    try:
        correo.send(fail_silently=False)
    except Exception as e:  # SMTP, red o credenciales: se registra y se informa
        mensaje.estado = Mensaje.Estado.ERROR
        mensaje.error = f"{type(e).__name__}: {e}"[:1000]
        mensaje.guardar_por(usuario)
        return mensaje
    mensaje.estado = Mensaje.Estado.ENVIADO
    mensaje.guardar_por(usuario)
    actividad = Actividad(tipo=Actividad.Tipo.CORREO, estado=Actividad.Estado.REALIZADA,
                          descripcion=f"Correo enviado a {contacto.email}: «{asunto}»\n\n{cuerpo}",
                          contacto=contacto, propiedad=propiedad, oportunidad=oportunidad)
    actividad.guardar_por(usuario)
    return mensaje
