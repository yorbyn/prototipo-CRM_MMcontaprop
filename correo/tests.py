"""Pruebas del correo. Django usa el backend en memoria (mail.outbox) durante las
pruebas: no se conecta a Gmail ni se necesitan credenciales reales."""
from django.contrib.auth.models import User
from django.core import mail
from django.core.mail.backends.base import BaseEmailBackend
from django.test import override_settings
from django.urls import reverse

from actividades.models import Actividad
from comercial.models import Oportunidad
from contactos.models import Contacto
from core.pruebas import CLAVE, BasePruebas
from correo.models import Mensaje, PlantillaCorreo


class BackendQueFalla(BaseEmailBackend):
    def send_messages(self, mensajes):
        raise OSError("Conexión rechazada por smtp.gmail.com")


@override_settings(DEFAULT_FROM_EMAIL="MMCONTAPROP SPA <corredora@gmail.com>",
                   CORREO_RESPONDER_A="corredora@gmail.com", CORREO_COPIA_OCULTA=False)
class CorreoTests(BasePruebas):
    def setUp(self):
        super().setUp()
        self.entrar_como_admin()
        self.juan = Contacto.objects.create(nombre="Juan Pérez", email="juan@example.com", es_interesado=True)
        self.url = reverse("correo:redactar")

    def enviar(self, **datos):
        base = {"contacto": self.juan.pk, "asunto": "Hola {nombre}", "cuerpo": "Mensaje para {nombre}."}
        base.update(datos)
        return self.client.post(self.url, base)

    def test_envio_y_registro_en_el_historial(self):
        r = self.enviar()
        self.assertRedirects(r, self.juan.get_absolute_url() + "#historial", fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertEqual((m.to, m.subject, m.body), (["juan@example.com"], "Hola Juan Pérez", "Mensaje para Juan Pérez."))
        self.assertEqual((m.from_email, m.reply_to, m.bcc),
                         ("MMCONTAPROP SPA <corredora@gmail.com>", ["corredora@gmail.com"], []))
        guardado = Mensaje.objects.get()
        self.assertEqual((guardado.estado, guardado.creado_por.username), ("enviado", "admin"))
        a = Actividad.objects.get(tipo="correo")
        self.assertEqual(a.contacto, self.juan)
        self.assertIn("Hola Juan Pérez", a.descripcion)

    @override_settings(CORREO_COPIA_OCULTA=True)
    def test_copia_oculta_opcional(self):
        self.enviar()
        self.assertEqual(mail.outbox[0].bcc, ["corredora@gmail.com"])

    def test_plantilla_con_variables_y_solo_datos_publicos(self):
        r = self.client.get(self.url, {"contacto": self.juan.pk, "propiedad": self.prop.pk, "plantilla": "envio-ficha"})
        cuerpo = r.context["form"].initial["cuerpo"]
        self.assertIn("Hola Juan Pérez", cuerpo)
        self.assertIn(self.prop.codigo, cuerpo)
        self.assertIn("$ 150.000.000", cuerpo)
        self.assertIn(f"http://testserver/propiedad/{self.prop.codigo}/", cuerpo)  # publicada: con enlace
        for privado in ("Calle Escondida", "11.111.111-1", "María Secreta"):
            self.assertNotIn(privado, cuerpo)
        self.client.post(self.url, {"contacto": self.juan.pk, "propiedad": self.prop.pk, "plantilla": "envio-ficha",
                                    "volver": "propiedad", "asunto": r.context["form"].initial["asunto"],
                                    "cuerpo": cuerpo})
        m = Mensaje.objects.get()
        self.assertEqual((m.propiedad, m.plantilla.clave), (self.prop, "envio-ficha"))
        self.assertTrue(self.prop.actividades.filter(tipo="correo").exists())

    def test_desde_una_oportunidad(self):
        op = Oportunidad.objects.create(contacto=self.juan, propiedad=self.prop)
        r = self.client.post(self.url, {"oportunidad": op.pk, "contacto": self.duena.pk,   # se ignora: manda la oportunidad
                                        "asunto": "Seguimiento", "cuerpo": "x"})
        self.assertRedirects(r, op.get_absolute_url() + "#historial", fetch_redirect_response=False)
        self.assertEqual(mail.outbox[0].to, ["juan@example.com"])
        a = Actividad.objects.get(tipo="correo")
        self.assertEqual((a.oportunidad, a.contacto, a.propiedad), (op, self.juan, self.prop))

    def test_cabecera_sin_saltos_de_linea(self):
        self.enviar(asunto="Hola\r\nBcc: victima@example.com")
        self.assertEqual(mail.outbox[0].subject, "Hola Bcc: victima@example.com")
        self.assertEqual(mail.outbox[0].bcc, [])

    def test_contacto_sin_correo(self):
        sin = Contacto.objects.create(nombre="Sin correo", es_interesado=True)
        self.client.post(self.url, {"contacto": sin.pk, "asunto": "x", "cuerpo": "y"})
        self.client.post(self.url + f"?contacto={sin.pk}", {"contacto": sin.pk, "asunto": "x", "cuerpo": "y"})
        self.assertEqual((len(mail.outbox), Mensaje.objects.count()), (0, 0))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
                       EMAIL_HOST_USER="", EMAIL_HOST_PASSWORD="")
    def test_sin_configurar_no_intenta_enviar(self):
        r = self.enviar()
        self.assertContains(r, "no está configurado")
        self.assertEqual(Mensaje.objects.count(), 0)

    @override_settings(EMAIL_BACKEND="correo.tests.BackendQueFalla")
    def test_error_de_envio_queda_registrado_sin_historial(self):
        r = self.enviar()
        self.assertContains(r, "No se pudo enviar el correo")
        m = Mensaje.objects.get()
        self.assertEqual(m.estado, "error")
        self.assertIn("Conexión rechazada", m.error)
        self.assertFalse(Actividad.objects.filter(tipo="correo").exists())
        self.assertContains(self.client.get(reverse("correo:enviados")), "Conexión rechazada")

    @override_settings(CORREO_LIMITE_DIARIO=2)
    def test_limite_diario_de_gmail(self):
        for _ in range(3):
            self.enviar()
        self.assertEqual(len(mail.outbox), 2)

    def test_plantillas_iniciales_y_variables_desconocidas(self):
        self.assertEqual(set(PlantillaCorreo.objects.values_list("clave", flat=True)),
                         {"envio-ficha", "confirmacion-visita", "seguimiento"})
        url = reverse("correo:plantilla_crear")
        self.client.post(url, {"nombre": "Mala", "clave": "mala", "asunto": "Hola", "cuerpo": "Dirección: {direccion}"})
        self.assertFalse(PlantillaCorreo.objects.filter(clave="mala").exists())
        self.client.post(url, {"nombre": "Buena", "clave": "buena", "asunto": "Hola {nombre}", "cuerpo": "{empresa}"})
        self.assertEqual(PlantillaCorreo.objects.get(clave="buena").creado_por.username, "admin")

    def test_permisos(self):
        self.client.force_login(User.objects.create_user("x", password=CLAVE, is_staff=True))
        for url in (self.url, reverse("correo:enviados"), reverse("correo:plantillas")):
            self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.enviar().status_code, 403)
        self.assertEqual(len(mail.outbox), 0)

    def test_settings_leen_la_contrasena_desde_el_entorno(self):
        """La contraseña de aplicación nunca está en el código: viene de .env/entorno."""
        import pathlib
        codigo = pathlib.Path(__file__).resolve().parent.parent / "config" / "settings" / "base.py"
        texto = codigo.read_text(encoding="utf-8")
        self.assertIn('os.environ.get("GMAIL_CONTRASENA_APLICACION", "")', texto)


class ModoConsolaTests(BasePruebas):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_aviso_de_modo_desarrollo(self):
        from correo.envio import correo_configurado
        self.entrar_como_admin()
        self.assertTrue(correo_configurado())
        self.assertContains(self.client.get(reverse("correo:redactar")), "Modo desarrollo")
        self.assertContains(self.client.get(reverse("correo:enviados")), "Modo desarrollo")

    def test_sin_aviso_con_correo_real(self):
        self.entrar_como_admin()   # en pruebas Django usa el backend en memoria
        self.assertNotContains(self.client.get(reverse("correo:redactar")), "Modo desarrollo")
