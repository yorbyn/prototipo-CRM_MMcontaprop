from django import forms


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
