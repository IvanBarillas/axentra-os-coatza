# apps/security/forms/base_styler.py
from django import forms

# Centralización de Tokens Estéticos Institucionales (Tailwind CSS v4)
AXENTRA_INPUT_CLASS = 'w-full px-4 py-3 border border-slate-200 rounded-xl text-sm bg-slate-50/50 text-slate-800 placeholder-slate-400 transition-all duration-300 focus:bg-white focus:border-blue-600 focus:ring-1 focus:ring-blue-600 outline-none'
AXENTRA_SELECT_CLASS = 'w-full px-4 py-3 border border-slate-200 rounded-xl text-sm bg-slate-50/50 text-slate-800 transition-all duration-300 focus:bg-white focus:border-blue-600 focus:ring-1 focus:ring-blue-600 outline-none cursor-pointer'
AXENTRA_DISABLED_CLASS = 'w-full px-4 py-3 border border-slate-200 rounded-xl text-sm bg-slate-100 text-slate-400 outline-none cursor-not-allowed select-none font-medium'

class AxentraFormStylerMixin:
    """Inyecta de forma masiva los tokens estéticos corporativos a los widgets del sistema."""
    def aplicar_estilos_institucionales(self):
        for name, field in self.fields.items():
            # Exclusión explícita para subida de archivos (FileInputs)
            if isinstance(field.widget, forms.ClearableFileInput):
                continue
                
            # Validar si el campo ya fue marcado externamente como deshabilitado
            if 'class' in field.widget.attrs and AXENTRA_DISABLED_CLASS in field.widget.attrs['class']:
                continue
                
            if isinstance(field.widget, (forms.Select, forms.NullBooleanSelect)):
                field.widget.attrs['class'] = AXENTRA_SELECT_CLASS
            else:
                field.widget.attrs['class'] = AXENTRA_INPUT_CLASS