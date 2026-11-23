from django import forms

from contactos.models import Contacto

from .models import PlantillaCorreo


class PlantillaForm(forms.ModelForm):
    class Meta:
        model = PlantillaCorreo
        fields = ["nombre", "clave", "asunto", "cuerpo"]
        widgets = {"cuerpo": forms.Textarea(attrs={"rows": 10})}


class RedactarForm(forms.Form):
    contacto = forms.ModelChoiceField(queryset=Contacto.objects.exclude(email="").order_by("nombre"),
                                      label="Para", help_text="Solo contactos con correo registrado.")
    asunto = forms.CharField(max_length=150)
    cuerpo = forms.CharField(label="Mensaje", max_length=10000, widget=forms.Textarea(attrs={"rows": 12}))

    def __init__(self, *args, contacto_fijo=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Si se escribe desde una ficha, el destinatario ya está decidido y no se pregunta.
        if contacto_fijo is not None:
            del self.fields["contacto"]
