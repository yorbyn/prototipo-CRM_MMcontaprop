from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from comercial.models import Oportunidad
from contactos.models import Contacto
from propiedades.models import Propiedad, TipoPropiedad

from .models import Actividad


class ActividadTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "admin@ejemplo.cl", "clave"))
        duena = Contacto.objects.create(nombre="Dueña", rut="11111111-1", es_propietario=True)
        self.juan = Contacto.objects.create(nombre="Juan", es_interesado=True)
        self.propiedad = Propiedad.objects.create(titulo="Casa", tipo=TipoPropiedad.objects.create(nombre="Casa"),
                                                  operacion="venta", zona="norte", comuna="A",
                                                  direccion_exacta="x", propietario=duena)
        self.op = Oportunidad.objects.create(contacto=self.juan, propiedad=self.propiedad)
        self.futuro = (timezone.localtime() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M")

    def test_registro_automatico_llega_al_contacto_y_la_propiedad(self):
        actividad = Actividad.registrar_sistema("Hecho", oportunidad=self.op)
        self.assertEqual((actividad.contacto, actividad.propiedad), (self.juan, self.propiedad))

    def test_programar_desde_la_agenda(self):
        url = reverse("actividades:programar")
        pasado = (timezone.localtime() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        self.assertContains(self.client.post(url, {"tipo": "tarea", "fecha": pasado, "descripcion": "x",
                                                   "contacto": self.juan.pk}), "no puede estar en el pasado")
        self.assertContains(self.client.post(url, {"tipo": "visita", "fecha": self.futuro, "descripcion": "x",
                                                   "contacto": self.juan.pk}), "propiedad y el contacto")
        self.client.post(url, {"tipo": "visita", "fecha": self.futuro, "descripcion": "Visita",
                               "contacto": self.juan.pk, "propiedad": self.propiedad.pk})
        self.assertEqual(Actividad.objects.agenda().count(), 1)

    def test_registrar_y_programar_desde_una_ficha(self):
        self.client.post(reverse("actividades:registrar", args=["contacto", self.juan.pk]),
                         {"tipo": "llamada", "descripcion": "Llamé"})
        self.client.post(reverse("actividades:programar_en", args=["oportunidad", self.op.pk]),
                         {"tipo": "tarea", "fecha": self.futuro, "descripcion": "Seguimiento"})
        self.assertTrue(self.juan.actividades.filter(descripcion="Llamé").exists())
        tarea = Actividad.objects.get(descripcion="Seguimiento")
        self.assertEqual((tarea.contacto, tarea.propiedad), (self.juan, self.propiedad))

    def test_no_se_crea_un_registro_automatico_a_mano(self):
        self.client.post(reverse("actividades:registrar", args=["contacto", self.juan.pk]),
                         {"tipo": "sistema", "descripcion": "trampa"})
        self.assertFalse(Actividad.objects.filter(descripcion="trampa").exists())

    def test_completar(self):
        tarea = Actividad.objects.create(tipo="tarea", estado="pendiente", descripcion="x", contacto=self.juan,
                                         fecha=timezone.now() + timedelta(days=1))
        url = reverse("actividades:completar", args=[tarea.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        r = self.client.post(url, {"next": "https://malo.com/"})
        self.assertRedirects(r, reverse("actividades:agenda"))  # un "next" externo se ignora
        tarea.refresh_from_db()
        self.assertEqual(tarea.estado, Actividad.Estado.REALIZADA)
