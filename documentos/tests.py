import os
import tempfile

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from contactos.models import Contacto

from .models import Documento


@override_settings(PRIVATE_MEDIA_ROOT=tempfile.mkdtemp())  # los documentos de prueba no van a private_media/
class DocumentoTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "admin@ejemplo.cl", "clave"))
        self.contacto = Contacto.objects.create(nombre="Ana", rut="11111111-1", es_propietario=True)

    def subir(self, nombre_archivo="cedula.pdf"):
        return self.client.post(reverse("documentos:subir", args=["contacto", self.contacto.pk]),
                                {"nombre": "Cédula", "archivo": SimpleUploadedFile(nombre_archivo, b"%PDF-1 x")})

    def test_subir_queda_privado(self):
        r = self.subir()
        documento = Documento.objects.get()
        self.assertRedirects(r, self.contacto.get_absolute_url() + "#documentos", fetch_redirect_response=False)
        self.assertTrue(documento.archivo.path.startswith(settings.PRIVATE_MEDIA_ROOT))

    def test_extension_no_permitida(self):
        self.subir("virus.exe")
        self.assertFalse(Documento.objects.exists())

    def test_descargar_solo_con_sesion(self):
        self.subir()
        url = reverse("documentos:descargar", args=[Documento.objects.get().pk])
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        r.close()
        self.assertEqual(Client().get(url).status_code, 302)

    def test_eliminar_borra_el_archivo(self):
        self.subir()
        documento = Documento.objects.get()
        ruta = documento.archivo.path
        self.client.post(reverse("documentos:eliminar", args=[documento.pk]))
        self.assertFalse(Documento.objects.exists())
        self.assertFalse(os.path.exists(ruta))
