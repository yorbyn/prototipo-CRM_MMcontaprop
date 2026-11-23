from django import forms

from .models import Documento


class DocumentoForm(forms.ModelForm):
    """Se dibuja campo por campo dentro de las fichas, por eso cada widget trae su clase de Bootstrap."""
    class Meta:
        model = Documento
        fields = ["nombre", "archivo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control",
                                             "placeholder": "Nombre (ej.: Escritura, Cédula, Mandato)"}),
            "archivo": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
