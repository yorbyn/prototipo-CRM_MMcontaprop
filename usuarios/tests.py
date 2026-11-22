from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import ADMINISTRADOR, TRABAJADOR, Perfil, Rol

CLAVE = "Clave-Segura-2026"


class UsuariosTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin1", password=CLAVE)
        Perfil.objects.create(user=self.admin, rol=Rol.objects.create(nombre=ADMINISTRADOR))
        self.trabajador = User.objects.create_user("trab1", password=CLAVE)
        Perfil.objects.create(user=self.trabajador, rol=Rol.objects.create(nombre=TRABAJADOR))

    def rol(self, usuario):
        return Perfil.objects.get(user=usuario).rol.nombre

    def test_admin_crea_trabajador_que_entra_al_crm(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("usuarios:usuario_crear"), {
            "username": "nuevo", "first_name": "Ana", "email": "ana@ejemplo.cl", "rol": TRABAJADOR,
            "password1": CLAVE, "password2": CLAVE,
        })
        self.assertRedirects(r, reverse("usuarios:usuario_lista"))
        nuevo = User.objects.get(username="nuevo")
        self.assertEqual(self.rol(nuevo), TRABAJADOR)
        self.client.force_login(nuevo)
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 200)

    def test_admin_crea_otro_admin(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("usuarios:usuario_crear"), {
            "username": "jefa", "first_name": "Marta", "rol": ADMINISTRADOR,
            "password1": CLAVE, "password2": CLAVE,
        })
        self.client.force_login(User.objects.get(username="jefa"))
        self.assertEqual(self.client.get(reverse("usuarios:usuario_lista")).status_code, 200)

    def test_trabajador_no_gestiona_usuarios(self):
        self.client.force_login(self.trabajador)
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("usuarios:usuario_lista")).status_code, 403)
        self.assertNotContains(self.client.get(reverse("core:dashboard")), reverse("usuarios:usuario_lista"))

    def test_usuario_sin_perfil_no_entra_al_crm(self):
        self.client.force_login(User.objects.create_user("sinperfil", password=CLAVE))
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 403)

    def test_superusuario_es_administrador_sin_perfil(self):
        self.client.force_login(User.objects.create_superuser("root", "r@r.cl", CLAVE))
        self.assertEqual(self.client.get(reverse("usuarios:usuario_lista")).status_code, 200)
        self.assertContains(self.client.get(reverse("core:dashboard")), reverse("usuarios:usuario_lista"))

    def test_contrasenas_distintas_y_correo_repetido(self):
        self.client.force_login(self.admin)
        self.trabajador.email = "repetido@ejemplo.cl"
        self.trabajador.save()
        r = self.client.post(reverse("usuarios:usuario_crear"), {
            "username": "x", "first_name": "X", "email": "REPETIDO@ejemplo.cl", "rol": TRABAJADOR,
            "password1": CLAVE, "password2": "otra",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="x").exists())

    def test_cambiar_rol_y_desactivar(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("usuarios:usuario_editar", args=[self.trabajador.pk]), {
            "first_name": "T", "rol": ADMINISTRADOR})
        self.assertEqual(self.rol(self.trabajador), ADMINISTRADOR)
        self.client.post(reverse("usuarios:usuario_activar", args=[self.trabajador.pk]))
        self.trabajador.refresh_from_db()
        self.assertFalse(self.trabajador.is_active)

    def test_no_se_desactiva_ni_se_quita_el_rol_a_si_mismo(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("usuarios:usuario_activar", args=[self.admin.pk]))
        self.client.post(reverse("usuarios:usuario_editar", args=[self.admin.pk]), {
            "first_name": "A", "rol": TRABAJADOR})
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertEqual(self.rol(self.admin), ADMINISTRADOR)

    def test_desactivar_solo_por_post(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("usuarios:usuario_activar", args=[self.trabajador.pk]))
        self.assertEqual(r.status_code, 405)
