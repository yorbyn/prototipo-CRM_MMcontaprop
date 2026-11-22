from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from usuarios.models import TRABAJADOR, Perfil, Rol

from .templatetags.formato import precio, rut
from .validators import normalizar_rut, validar_rut

CLAVE = "Clave-Segura-2026"


class LoginTests(TestCase):
    def setUp(self):
        self.trabajador = User.objects.create_user("trab", password=CLAVE)
        Perfil.objects.create(user=self.trabajador, rol=Rol.objects.create(nombre=TRABAJADOR))
        User.objects.create_user("sinperfil", password=CLAVE)

    def test_sin_sesion_redirige_al_login(self):
        r = self.client.get(reverse("contactos:contacto_lista"))
        self.assertRedirects(r, reverse("core:login") + "?next=" + reverse("contactos:contacto_lista"))

    def test_login_correcto_vuelve_a_next(self):
        r = self.client.post(reverse("core:login"), {"username": "trab", "password": CLAVE,
                                                     "next": reverse("contactos:contacto_lista")})
        self.assertRedirects(r, reverse("contactos:contacto_lista"))

    def test_clave_incorrecta(self):
        r = self.client.post(reverse("core:login"), {"username": "trab", "password": "mala"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_usuario_sin_perfil_no_entra(self):
        r = self.client.post(reverse("core:login"), {"username": "sinperfil", "password": CLAVE})
        self.assertContains(r, "no tiene acceso al CRM")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_next_externo_se_ignora(self):
        r = self.client.post(reverse("core:login"), {"username": "trab", "password": CLAVE, "next": "https://malo.com/"})
        self.assertRedirects(r, reverse("core:dashboard"))

    def test_cerrar_sesion_solo_por_post(self):
        self.client.force_login(self.trabajador)
        self.assertEqual(self.client.get(reverse("core:logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("core:logout")), reverse("core:login"))
        self.assertNotIn("_auth_user_id", self.client.session)


class UtilidadesTests(TestCase):
    def test_rut(self):
        self.assertEqual(normalizar_rut("12.345.678-k"), "12345678-K")
        self.assertEqual(rut("12345678-5"), "12.345.678-5")
        validar_rut("12.345.678-5")  # no lanza error

    def test_rut_con_digito_incorrecto(self):
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            validar_rut("12.345.678-9")

    def test_precio(self):
        self.assertEqual(precio(150000000), "$ 150.000.000")
        self.assertEqual(precio("4500.5", "UF"), "UF 4.500,50")
        self.assertEqual(precio(None), "Precio a consultar")
