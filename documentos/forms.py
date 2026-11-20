from django import forms

from core.forms import BootstrapMixin

from .models import Documento


class DocumentoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Documento
        fields = ["nombre", "archivo"]
        widgets = {"nombre": forms.TextInput(attrs={"placeholder": "Nombre (ej.: Escritura, Cédula, Mandato)"})}