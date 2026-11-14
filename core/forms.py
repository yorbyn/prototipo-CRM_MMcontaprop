from django import forms


class CampoTrampaMixin(forms.Form):
    """Campo trampa contra spam: invisible para personas; los bots suelen llenarlo.
    En la plantilla va dentro de <div class="campo-trampa" aria-hidden="true">."""
    sitio_web = forms.CharField(required=False, label="No completar",
                                widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    def clean_sitio_web(self):
        if self.cleaned_data.get("sitio_web"):
            raise forms.ValidationError("No se pudo enviar el formulario.")
        return ""

    def cleaned_data_sin_trampa(self):
        return {k: v for k, v in self.cleaned_data.items() if k != "sitio_web"}


class BootstrapMixin:
    """Agrega las clases de Bootstrap a los campos del formulario."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            w = campo.widget
            if isinstance(w, (forms.CheckboxInput,)):
                clase = "form-check-input"
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                clase = "form-select"
            else:
                clase = "form-control"
            w.attrs["class"] = (w.attrs.get("class", "") + " " + clase).strip()
