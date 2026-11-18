from django import forms

from core.forms import BootstrapMixin
from core.validators import normalizar_rut

from .models import Contacto

class ContactoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Contacto
        fields = [
            "nombre", "rut", "telefono", "email", "informacion_adicional",
            "es_propietario", "es_arrendatario", "es_interesado",
        ]
        widgets = {"informacion_adicional": forms.Textarea(attrs={"rows": 3})}

    def clean_rut(self):
        # Se normaliza antes de la validación de unicidad para detectar
        # duplicados aunque se escriba con o sin puntos.
        return normalizar_rut(self.cleaned_data.get("rut")) or None

    