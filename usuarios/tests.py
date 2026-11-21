from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

CLAVE = "Clave-Segura-2026"


class UsuariosTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin1", password=CLAVE, is_staff=True)
        self.admin.groups.add(Group.objects.get(name=settings.GRUPO_CRM))
        self.trabajador = User.objects.create_user("trab1", password=CLAVE, is_staff=True)
        self.trabajador.groups.add(Group.objects.get(name=settings.GRUPO_TRABAJADORES))

    def entrar(self, usuario):
        self.client.force_login(usuario)

    def test_admin_crea_trabajador_que_entra_al_crm(self):
        self.entrar(self.admin)
        r = self.client.post(reverse("usuarios:usuario_crear"), {
            "username": "nuevo", "first_name": "Ana", "email": "ana@ejemplo.cl", "rol": "trabajador",
            "password1": CLAVE, "password2": CLAVE,
        })
        self.assertRedirects(r, reverse("usuarios:usuario_lista"))
        nuevo = User.objects.get(username="nuevo")
        self.assertTrue(nuevo.is_staff)
        self.assertTrue(nuevo.groups.filter(name=settings.GRUPO_TRABAJADORES).exists())
        self.client.force_login(nuevo)
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 200)

    def test_admin_crea_otro_admin(self):
        self.entrar(self.admin)
        self.client.post(reverse("usuarios:usuario_crear"), {
            "username": "jefa", "first_name": "Marta", "rol": "administrador",
            "password1": CLAVE, "password2": CLAVE,
        })
        jefa = User.objects.get(username="jefa")
        self.client.force_login(jefa)
        self.assertEqual(self.client.get(reverse("usuarios:usuario_lista")).status_code, 200)

    def test_trabajador_no_gestiona_usuarios(self):
        self.entrar(self.trabajador)
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("usuarios:usuario_lista")).status_code, 403)
        self.assertNotContains(self.client.get(reverse("core:dashboard")), reverse("usuarios:usuario_lista"))

    def test_contrasenas_distintas_y_correo_repetido(self):
        self.entrar(self.admin)
        self.trabajador.email = "repetido@ejemplo.cl"
        self.trabajador.save()
        r = self.client.post(reverse("usuarios:usuario_crear"), {
            "username": "x", "first_name": "X", "email": "REPETIDO@ejemplo.cl", "rol": "trabajador",
            "password1": CLAVE, "password2": "otra",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="x").exists())

    def test_cambiar_rol_y_desactivar(self):
        self.entrar(self.admin)
        self.client.post(reverse("usuarios:usuario_editar", args=[self.trabajador.pk]), {
            "first_name": "T", "rol": "administrador"})
        self.assertTrue(self.trabajador.groups.filter(name=settings.GRUPO_CRM).exists())
        self.assertFalse(self.trabajador.groups.filter(name=settings.GRUPO_TRABAJADORES).exists())
        self.client.post(reverse("usuarios:usuario_activar", args=[self.trabajador.pk]))
        self.trabajador.refresh_from_db()
        self.assertFalse(self.trabajador.is_active)

    def test_no_se_desactiva_ni_se_quita_el_rol_a_si_mismo(self):
        self.entrar(self.admin)
        self.client.post(reverse("usuarios:usuario_activar", args=[self.admin.pk]))
        self.client.post(reverse("usuarios:usuario_editar", args=[self.admin.pk]), {
            "first_name": "A", "rol": "trabajador"})
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertTrue(self.admin.groups.filter(name=settings.GRUPO_CRM).exists())

    def test_desactivar_solo_por_post(self):
        self.entrar(self.admin)
        self.assertEqual(self.client.get(reverse("usuarios:usuario_activar", args=[self.trabajador.pk])).status_code, 405)
