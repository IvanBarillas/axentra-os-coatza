# apps/security/forms/security_forms.py
import re
from django import forms
from apps.security.forms.base_styler import AxentraFormStylerMixin
from apps.security.models import TenantConfig

class TenantConfigForm(AxentraFormStylerMixin, forms.ModelForm):
    """Formulario del Singleton de Identidad Corporativa."""
    class Meta:
        model = TenantConfig
        fields = ['app_name', 'entidad_nombre', 'siglas', 'direccion_oficial', 'rfc', 'logo_light', 'primary_color_class']
        widgets = {
            'app_name': forms.TextInput(attrs={'placeholder': 'Ej: Axentra OS'}),
            'entidad_nombre': forms.TextInput(attrs={'placeholder': 'Ej: H. Ayuntamiento Constitucional'}),
            'siglas': forms.TextInput(attrs={'placeholder': 'Ej: AXA'}),
            'direccion_oficial': forms.Textarea(attrs={'placeholder': 'Dirección legal completa...', 'rows': 2}),
            'rfc': forms.TextInput(attrs={'placeholder': 'Ej: MCO850101AAA'}),
            'primary_color_class': forms.Select(
                choices=[
                    ('slate-950', 'Negro Corporativo'), 
                    ('blue-600', 'Azul Eléctrico'), 
                    ('indigo-600', 'Morado Tecnológico'), 
                    ('emerald-700', 'Verde Institucional')
                ]
            ),
            'logo_light': forms.ClearableFileInput(attrs={
                'class': 'block w-full text-xs text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-[10px] file:font-black file:uppercase file:tracking-widest file:bg-slate-950 file:text-white hover:file:bg-slate-900 file:transition-colors file:cursor-pointer'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_estilos_institucionales()

    def clean_rfc(self):
        rfc_crudo = self.cleaned_data.get('rfc', '').strip().upper()
        if not rfc_crudo:
            return rfc_crudo

        patron_rfc = r'^[A-Z&Ñ]{3,4}\d{6}[A-Z0-9]{3}$'
        if not re.match(patron_rfc, rfc_crudo):
            raise forms.ValidationError(
                "⚠️ Estructura Inválida: El RFC ingresado no coincide con el formato oficial del SAT."
            )
        return rfc_crudo