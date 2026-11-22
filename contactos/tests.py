from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Contacto, PreferenciaBusqueda


class ContactoTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "admin@ejemplo.cl", "clave"))

    def test_crear_contacto_normaliza_el_rut(self):
        r = self.client.post(reverse("contactos:contacto_crear"),
                             {"nombre": "Ana", "rut": "12.345.678-5", "es_propietario": "on"})
        ana = Contacto.objects.get(nombre="Ana")
        self.assertEqual(ana.rut, "12345678-5")
        self.assertRedirects(r, ana.get_absolute_url())

    def test_rut_repetido_escrito_distinto(self):
        Contacto.objects.create(nombre="Ana", rut="12345678-5", es_propietario=True)
        self.client.post(reverse("contactos:contacto_crear"), {"nombre": "Otra", "rut": "12.345.678-5", "es_interesado": "on"})
        self.assertFalse(Contacto.objects.filter(nombre="Otra").exists())

    def test_validaciones_de_roles(self):
        r = self.client.post(reverse("contactos:contacto_crear"), {"nombre": "Sin rol"})
        self.assertContains(r, "al menos un rol")
        r = self.client.post(reverse("contactos:contacto_crear"), {"nombre": "Prop", "es_propietario": "on"})
        self.assertContains(r, "obligatorio para un propietario")

    def test_editar_contacto(self):
        ana = Contacto.objects.create(nombre="Ana", es_interesado=True)
        self.client.post(reverse("contactos:contacto_editar", args=[ana.pk]), {"nombre": "Ana María", "es_interesado": "on"})
        ana.refresh_from_db()
        self.assertEqual(ana.nombre, "Ana María")

    def test_lista_filtra_por_rol_y_busca_por_rut(self):
        Contacto.objects.create(nombre="Ana", rut="12345678-5", es_propietario=True)
        Contacto.objects.create(nombre="Juan", es_interesado=True)
        r = self.client.get(reverse("contactos:contacto_lista") + "?rol=propietario")
        self.assertContains(r, "Ana")
        self.assertNotContains(r, "Juan")
        self.assertContains(self.client.get(reverse("contactos:contacto_lista") + "?q=12.345.678"), "Ana")

    def test_preferencias(self):
        juan = Contacto.objects.create(nombre="Juan", es_interesado=True)
        url = reverse("contactos:preferencia_crear", args=[juan.pk])
        self.client.post(url, {"operacion": "venta", "moneda": "CLP", "precio_min": "10", "precio_max": "5"})
        self.assertFalse(PreferenciaBusqueda.objects.exists())  # mínimo mayor que el máximo
        self.client.post(url, {"operacion": "venta", "moneda": "CLP"})
        preferencia = PreferenciaBusqueda.objects.get()
        url_eliminar = reverse("contactos:preferencia_eliminar", args=[preferencia.pk])
        self.assertEqual(self.client.get(url_eliminar).status_code, 405)
        self.client.post(url_eliminar)
        self.assertFalse(PreferenciaBusqueda.objects.exists())

    def test_ficha_abre(self):
        juan = Contacto.objects.create(nombre="Juan", es_interesado=True)
        r = self.client.get(juan.get_absolute_url())
        self.assertContains(r, 'id="historial"')
        self.assertContains(r, 'id="documentos"')
