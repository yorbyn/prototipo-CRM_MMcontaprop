"""Pruebas del correo. Durante las pruebas Django guarda los correos en memoria (mail.outbox):
no se conecta a Gmail ni se necesitan credenciales."""
from django.contrib.auth.models import User
from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend
from django.test import TestCase, override_settings
from django.urls import reverse

from actividades.models import Actividad
from comercial.models import Oportunidad
from contactos.models import Contacto
from correo.models import Mensaje, PlantillaCorreo
from propiedades.models import Propiedad, TipoPropiedad


class BackendQueFalla(BaseEmailBackend):
    """Simula que Gmail rechaza la conexión."""
    def send_messages(self, mensajes):
        raise OSError("Conexión rechazada por smtp.gmail.com")


@override_settings(DEFAULT_FROM_EMAIL="MMCONTAPROP SPA <corredora@gmail.com>", CORREO_RESPONDER_A="corredora@gmail.com")
class CorreoTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "admin@ejemplo.cl", "clave"))
        self.juan = Contacto.objects.create(nombre="Juan Pérez", email="juan@example.com", es_interesado=True)
        self.duena = Contacto.objects.create(nombre="María Secreta", rut="11111111-1", es_propietario=True)
        self.prop = Propiedad.objects.create(
            titulo="Casa amplia", tipo=TipoPropiedad.objects.create(nombre="Casa"), operacion="venta",
            precio=150000000, zona="norte", comuna="Arica", direccion_exacta="Calle Escondida 123",
            propietario=self.duena, estado=Propiedad.Estado.DISPONIBLE, descripcion="x",
        )
        self.url = reverse("correo:redactar")

    def enviar(self, **datos):
        base = {"contacto": self.juan.pk, "asunto": "Hola {nombre}", "cuerpo": "Mensaje para {nombre}."}
        base.update(datos)
        return self.client.post(self.url, base)

    def test_envio_y_registro_en_el_historial(self):
        r = self.enviar()
        self.assertRedirects(r, self.juan.get_absolute_url() + "#historial", fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, ["juan@example.com"])
        self.assertEqual(correo.subject, "Hola Juan Pérez")
        self.assertEqual(correo.body, "Mensaje para Juan Pérez.")
        self.assertEqual(correo.reply_to, ["corredora@gmail.com"])
        self.assertEqual(Mensaje.objects.get().estado, Mensaje.Estado.ENVIADO)
        actividad = Actividad.objects.get(tipo=Actividad.Tipo.CORREO)
        self.assertEqual(actividad.contacto, self.juan)
        self.assertIn("Hola Juan Pérez", actividad.descripcion)

    def test_plantilla_con_variables_y_solo_datos_publicos(self):
        PlantillaCorreo.objects.create(nombre="Ficha", clave="envio-ficha", asunto="{nombre}, mira esta propiedad",
                                       cuerpo="Hola {nombre}: {propiedad} ({codigo}) a {precio}. {enlace}")
        r = self.client.get(self.url, {"contacto": self.juan.pk, "propiedad": self.prop.pk, "plantilla": "envio-ficha"})
        cuerpo = r.context["form"].initial["cuerpo"]
        self.assertIn("Hola Juan Pérez", cuerpo)
        self.assertIn(self.prop.codigo, cuerpo)
        self.assertIn("$ 150.000.000", cuerpo)
        self.assertIn(f"http://testserver/propiedad/{self.prop.codigo}/", cuerpo)  # publicada: con enlace
        for privado in ("Calle Escondida", "11.111.111-1", "María Secreta"):
            self.assertNotIn(privado, cuerpo)
        self.client.post(self.url, {"contacto": self.juan.pk, "propiedad": self.prop.pk, "plantilla": "envio-ficha",
                                    "volver": "propiedad", "asunto": "a", "cuerpo": cuerpo})
        mensaje = Mensaje.objects.get()
        self.assertEqual((mensaje.propiedad, mensaje.plantilla.clave), (self.prop, "envio-ficha"))
        self.assertTrue(self.prop.actividades.filter(tipo=Actividad.Tipo.CORREO).exists())

    def test_desde_una_oportunidad_manda_la_oportunidad(self):
        op = Oportunidad.objects.create(contacto=self.juan, propiedad=self.prop)
        r = self.client.post(self.url, {"oportunidad": op.pk, "contacto": self.duena.pk,  # se ignora
                                        "asunto": "Seguimiento", "cuerpo": "x"})
        self.assertRedirects(r, op.get_absolute_url() + "#historial", fetch_redirect_response=False)
        self.assertEqual(mail.outbox[0].to, ["juan@example.com"])
        actividad = Actividad.objects.get(tipo=Actividad.Tipo.CORREO)
        self.assertEqual((actividad.oportunidad, actividad.contacto, actividad.propiedad), (op, self.juan, self.prop))

    def test_asunto_sin_saltos_de_linea(self):
        self.enviar(asunto="Hola\r\nBcc: victima@example.com")
        self.assertEqual(mail.outbox[0].subject, "Hola Bcc: victima@example.com")
        self.assertEqual(mail.outbox[0].bcc, [])

    def test_contacto_sin_correo(self):
        sin_correo = Contacto.objects.create(nombre="Sin correo", es_interesado=True)
        self.client.post(self.url + f"?contacto={sin_correo.pk}", {"contacto": sin_correo.pk, "asunto": "x", "cuerpo": "y"})
        self.assertEqual((len(mail.outbox), Mensaje.objects.count()), (0, 0))

    @override_settings(EMAIL_BACKEND="correo.tests.BackendQueFalla")
    def test_error_de_envio_queda_registrado_sin_historial(self):
        r = self.enviar()
        self.assertContains(r, "No se pudo enviar el correo")
        mensaje = Mensaje.objects.get()
        self.assertEqual(mensaje.estado, Mensaje.Estado.ERROR)
        self.assertIn("Conexión rechazada", mensaje.error)
        self.assertFalse(Actividad.objects.filter(tipo=Actividad.Tipo.CORREO).exists())
        self.assertContains(self.client.get(reverse("correo:enviados")), "Conexión rechazada")

    @override_settings(CORREO_LIMITE_DIARIO=2)
    def test_limite_diario_de_gmail(self):
        for _ in range(3):
            self.enviar()
        self.assertEqual(len(mail.outbox), 2)

    def test_plantilla_con_variable_desconocida_se_rechaza(self):
        url = reverse("correo:plantilla_crear")
        self.client.post(url, {"nombre": "Mala", "clave": "mala", "asunto": "Hola", "cuerpo": "Dirección: {direccion}"})
        self.assertFalse(PlantillaCorreo.objects.filter(clave="mala").exists())
        self.client.post(url, {"nombre": "Buena", "clave": "buena", "asunto": "Hola {nombre}", "cuerpo": "{empresa}"})
        self.assertTrue(PlantillaCorreo.objects.filter(clave="buena").exists())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_aviso_de_modo_desarrollo(self):
        self.assertContains(self.client.get(self.url), "Modo desarrollo")
        self.assertContains(self.client.get(reverse("correo:enviados")), "Modo desarrollo")

    def test_sin_aviso_con_otro_backend(self):
        self.assertNotContains(self.client.get(self.url), "Modo desarrollo")

    def test_formulario_tiene_el_boton_enviar(self):
        r = self.client.get(self.url, {"contacto": self.juan.pk})
        self.assertContains(r, '<i class="bi bi-send"></i> Enviar</button>', html=False)

    def test_usuario_sin_acceso_al_crm(self):
        self.client.force_login(User.objects.create_user("x", password="clave"))
        for url in (self.url, reverse("correo:enviados"), reverse("correo:plantillas")):
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.enviar().status_code, 403)
        self.assertEqual(len(mail.outbox), 0)
