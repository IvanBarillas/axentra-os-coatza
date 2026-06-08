# apps/security/forms/organigrama_forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from apps.security.forms.base_styler import AxentraFormStylerMixin, AXENTRA_DISABLED_CLASS
from apps.security.models import Dependencia, AreaOperativa, Sede

class SedeForm(AxentraFormStylerMixin, forms.ModelForm):
    class Meta:
        model = Sede
        fields = ['nombre', 'direccion']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Palacio Municipal Central'}),
            'direccion': forms.TextInput(attrs={'placeholder': 'Ej: Av. Colón #150, Col. Centro'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos_institucionales()


class DependenciaForm(AxentraFormStylerMixin, forms.ModelForm):
    class Meta:
        model = Dependencia
        fields = ['nombre', 'encargado_departamento']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Dirección General de Innovación'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.fields.get('encargado_departamento'):
            self.fields['encargado_departamento'].empty_label = "--- Seleccione Servidor Público Titular (Opcional) ---"
        self.aplicar_estilos_institucionales()


class AreaOperativaForm(AxentraFormStylerMixin, forms.ModelForm):
    class Meta:
        model = AreaOperativa
        fields = ['dependencia', 'sede_fisica', 'nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Departamento de Soporte Técnico'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['sede_fisica'].queryset = Sede.objects.filter(is_active=True).order_by('nombre')
        self.fields['sede_fisica'].empty_label = "--- Seleccione Ubicación Física (Sede) ---"
        
        self.fields['dependencia'].queryset = Dependencia.objects.filter(is_active=True, is_deleted=False).order_by('nombre')
        self.fields['dependencia'].empty_label = "--- Seleccione Dirección General Responsable ---"

        # 🔒 ESCUDO JERÁRQUICO EN EDICIÓN
        if self.instance and not self.instance._state.adding:
            for campo in ['dependencia', 'sede_fisica']:
                self.fields[campo].widget.attrs['disabled'] = 'disabled'
                self.fields[campo].widget.attrs['class'] = AXENTRA_DISABLED_CLASS
                self.fields[campo].required = False

        self.aplicar_estilos_institucionales()

    def clean_dependencia(self):
        if self.instance and not self.instance._state.adding:
            return self.instance.dependencia
        return self.cleaned_data.get('dependencia')

    def clean_sede_fisica(self):
        if self.instance and not self.instance._state.adding:
            return self.instance.sede_fisica
        return self.cleaned_data.get('sede_fisica')

    def clean(self):
        cleaned_data = super().clean()
        dependencia = cleaned_data.get('dependencia')
        sede_fisica = cleaned_data.get('sede_fisica')
        nombre = cleaned_data.get('nombre')

        if self.instance._state.adding and argumento_completo := (dependencia and sede_fisica and nombre):
            generated_slug = slugify(nombre)
            if AreaOperativa.objects.filter(dependencia=dependencia, sede_fisica=sede_fisica, slug=generated_slug, is_deleted=False).exists():
                raise ValidationError(
                    "🚨 Operación Cancelada: Esta oficina ya se encuentra registrada y operando para esa Dependencia dentro del Edificio seleccionado."
                )
        return cleaned_data