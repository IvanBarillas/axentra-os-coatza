# apps/shared/forms/base_styler.py

from django import forms


AXENTRA_INPUT_CLASS = (
    "w-full rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3 "
    "text-sm font-semibold text-slate-800 placeholder-slate-400 outline-none "
    "transition-all duration-300 "
    "focus:border-slate-900 focus:bg-white focus:ring-2 focus:ring-slate-900/10"
)

AXENTRA_SELECT_CLASS = (
    "w-full rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3 "
    "text-sm font-semibold text-slate-800 outline-none transition-all duration-300 "
    "focus:border-slate-900 focus:bg-white focus:ring-2 focus:ring-slate-900/10"
)

AXENTRA_TEXTAREA_CLASS = (
    "w-full rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3 "
    "text-sm font-semibold text-slate-800 placeholder-slate-400 outline-none "
    "transition-all duration-300 min-h-28 "
    "focus:border-slate-900 focus:bg-white focus:ring-2 focus:ring-slate-900/10"
)

AXENTRA_CHECKBOX_CLASS = (
    "h-5 w-5 rounded border-slate-300 text-slate-900 "
    "focus:ring-2 focus:ring-slate-900/20"
)

AXENTRA_FILE_CLASS = (
    "w-full rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-3 "
    "text-sm font-semibold text-slate-600 file:mr-4 file:rounded-lg file:border-0 "
    "file:bg-slate-900 file:px-3 file:py-2 file:text-xs file:font-black file:text-white "
    "hover:bg-white"
)

AXENTRA_DISABLED_CLASS = (
    "w-full rounded-xl border border-slate-200 bg-slate-100 px-4 py-3 "
    "text-sm font-semibold text-slate-400 outline-none cursor-not-allowed select-none"
)


class AxentraFormStylerMixin:
    """
    Inyecta tokens visuales institucionales a formularios Django.

    Uso:
        class MyForm(AxentraFormStylerMixin, forms.ModelForm):
            ...
            def __init__(...):
                super().__init__(*args, **kwargs)
                self.aplicar_estilos_institucionales()
    """

    def aplicar_estilos_institucionales(self):
        for _name, field in self.fields.items():
            widget = field.widget

            if widget.attrs.get("disabled"):
                widget.attrs["class"] = AXENTRA_DISABLED_CLASS
                continue

            if isinstance(widget, forms.ClearableFileInput):
                widget.attrs["class"] = AXENTRA_FILE_CLASS
                continue

            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = AXENTRA_CHECKBOX_CLASS
                continue

            if isinstance(widget, (forms.Select, forms.NullBooleanSelect, forms.SelectMultiple)):
                widget.attrs["class"] = AXENTRA_SELECT_CLASS
                continue

            if isinstance(widget, forms.Textarea):
                widget.attrs["class"] = AXENTRA_TEXTAREA_CLASS
                continue

            widget.attrs["class"] = AXENTRA_INPUT_CLASS
            
