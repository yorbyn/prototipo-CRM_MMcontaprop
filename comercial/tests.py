from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from captacion.models import Encargo
from contactos.models import Contacto
from propiedades.models import Propiedad, TipoPropiedad

from .models import Oferta, Operacion, Oportunidad


class ComercialTests(TestCase):
    def setUp(self):
        self.client.force_login(User.objects.create_superuser("admin", "admin@ejemplo.cl", "clave"))
        self.hoy = timezone.localdate()
        casa = TipoPropiedad.objects.create(nombre="Casa")
        self.duena = Contacto.objects.create(nombre="Dueña", rut="11111111-1", es_propietario=True)
        self.juan = Contacto.objects.create(nombre="Juan", email="juan@x.cl", es_interesado=True)
        self.venta = Propiedad.objects.create(titulo="Casa venta", tipo=casa, operacion="venta", zona="norte",
                                              comuna="A", precio=Decimal("100000000"), direccion_exacta="x",
                                              propietario=self.duena, descripcion="d", estado="disponible")
        self.arriendo = Propiedad.objects.create(titulo="Casa arriendo", tipo=casa, operacion="arriendo",
                                                 modalidad_arriendo="permanente", zona="norte", comuna="A",
                                                 precio=Decimal("500000"), direccion_exacta="x",
                                                 propietario=self.duena, descripcion="d", estado="disponible")
        self.op = Oportunidad.objects.create(contacto=self.juan, propiedad=self.venta)

    def test_crear_oportunidad_manual(self):
        ana = Contacto.objects.create(nombre="Ana", es_interesado=True)
        self.client.post(reverse("comercial:crear"), {"contacto": ana.pk, "propiedad": self.venta.pk})
        self.assertTrue(Oportunidad.objects.filter(contacto=ana, origen=Oportunidad.Origen.MANUAL).exists())
        self.client.post(reverse("comercial:crear"), {"contacto": self.duena.pk, "propiedad": self.venta.pk})
        self.assertFalse(Oportunidad.objects.filter(contacto=self.duena).exists())  # el propietario no es interesado

    def test_cambiar_etapa_queda_en_el_historial(self):
        self.client.post(reverse("comercial:cambiar_etapa", args=[self.op.pk]), {"etapa": "contactado"})
        self.op.refresh_from_db()
        self.assertEqual(self.op.etapa, Oportunidad.Etapa.CONTACTADO)
        self.assertTrue(self.op.actividades.filter(descripcion__startswith="Etapa cambiada").exists())

    def test_oferta_pasa_a_negociacion_y_contraoferta(self):
        url = reverse("comercial:oferta_registrar", args=[self.op.pk])
        self.client.post(url, {"tipo": "oferta", "monto": "90000000", "moneda": "CLP", "fecha": self.hoy})
        self.op.refresh_from_db()
        self.assertEqual(self.op.etapa, Oportunidad.Etapa.NEGOCIACION)
        self.client.post(url, {"tipo": "contraoferta", "monto": "95000000", "moneda": "CLP", "fecha": self.hoy})
        self.assertEqual(Oferta.objects.get(tipo="oferta").respuesta, Oferta.Respuesta.CONTRAOFERTADA)

    def test_cierre_de_venta_con_comision_sugerida(self):
        Encargo.objects.create(propiedad=self.venta, comision_pct=Decimal("2"), fecha_inicio=self.hoy,
                               fecha_vencimiento=self.hoy + timedelta(days=90))
        r = self.client.get(reverse("comercial:cerrar", args=[self.op.pk]))
        self.assertEqual(r.context["form"].initial["comision_monto"], Decimal("2000000.00"))
        self.client.post(reverse("comercial:cerrar", args=[self.op.pk]), {
            "precio_final": "100000000", "moneda": "CLP", "comision_monto": "2000000", "comision_moneda": "CLP",
            "fecha_promesa": self.hoy})
        self.op.refresh_from_db()
        self.venta.refresh_from_db()
        self.assertEqual((self.op.etapa, self.venta.estado), (Oportunidad.Etapa.GANADA, Propiedad.Estado.VENDIDA))

    def test_cierre_de_arriendo_deja_al_arrendatario(self):
        op = Oportunidad.objects.create(contacto=self.juan, propiedad=self.arriendo)
        self.client.post(reverse("comercial:cerrar", args=[op.pk]), {
            "precio_final": "500000", "moneda": "CLP", "comision_monto": "250000", "comision_moneda": "CLP",
            "fecha_firma_contrato": self.hoy})
        self.arriendo.refresh_from_db()
        self.juan.refresh_from_db()
        self.assertEqual(self.arriendo.estado, Propiedad.Estado.ARRENDADA)
        self.assertEqual(self.arriendo.arrendatario, self.juan)
        self.assertTrue(self.juan.es_arrendatario)

    def test_anular_vuelve_a_negociacion_y_borrador(self):
        self.client.post(reverse("comercial:cerrar", args=[self.op.pk]), {
            "precio_final": "100000000", "moneda": "CLP", "comision_monto": "1", "comision_moneda": "CLP",
            "fecha_escritura": self.hoy})
        operacion = Operacion.objects.get()
        self.client.post(reverse("comercial:operacion_anular", args=[operacion.pk]), {"motivo": "Se cayó el crédito"})
        self.op.refresh_from_db()
        self.venta.refresh_from_db()
        self.assertEqual(self.op.etapa, Oportunidad.Etapa.NEGOCIACION)
        self.assertEqual(self.venta.estado, Propiedad.Estado.BORRADOR)

    def test_perder_exige_motivo(self):
        url = reverse("comercial:perder", args=[self.op.pk])
        self.client.post(url, {"motivo": ""})
        self.op.refresh_from_db()
        self.assertEqual(self.op.etapa, Oportunidad.Etapa.NUEVA)
        self.client.post(url, {"motivo": "Compró otra"})
        self.op.refresh_from_db()
        self.assertEqual(self.op.etapa, Oportunidad.Etapa.PERDIDA)

    def test_consulta_del_portal_no_duplica(self):
        _, ya_existia = Oportunidad.desde_portal(nombre="Juan", email="JUAN@x.cl", mensaje="Hola", propiedad=self.venta)
        self.assertTrue(ya_existia)
        self.assertEqual(Oportunidad.objects.count(), 1)

    def test_indicadores_y_csv(self):
        self.assertEqual(self.client.get(reverse("comercial:indicadores")).status_code, 200)
        r = self.client.get(reverse("comercial:exportar", args=["oportunidades"]))
        self.assertTrue(r.content.decode("utf-8").startswith("﻿"))  # BOM para Excel
        self.assertEqual(self.client.get(reverse("comercial:exportar", args=["otra"])).status_code, 404)
