# apps/inventory/forms/base_styler.py

from django import forms


AXENTRA_INPUT_CLASS = (
    "w-full rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3 "
    "text-sm font-semibold text-slate-800 placeholder-slate-400 outline-none "
    "transition-all duration-300 "
    "focus:border-slate-900 focus:bg-white focus:ring-2 "
    "focus:ring-slate-900/10"
)

AXENTRA_SELECT_CLASS = (
    "w-full rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3 "
    "text-sm font-semibold text-slate-800 outline-none "
    "transition-all duration-300 "
    "focus:border-slate-900 focus:bg-white focus:ring-2 "
    "focus:ring-slate-900/10"
)

AXENTRA_TEXTAREA_CLASS = (
    "w-full min-h-28 rounded-xl border border-slate-200 bg-slate-50/70 "
    "px-4 py-3 text-sm font-semibold text-slate-800 "
    "placeholder-slate-400 outline-none transition-all duration-300 "
    "focus:border-slate-900 focus:bg-white focus:ring-2 "
    "focus:ring-slate-900/10"
)

AXENTRA_CHECKBOX_CLASS = (
    "h-5 w-5 rounded border-slate-300 text-slate-900 "
    "focus:ring-2 focus:ring-slate-900/20"
)

AXENTRA_RADIO_CLASS = (
    "h-5 w-5 border-slate-300 text-slate-900 "
    "focus:ring-2 focus:ring-slate-900/20"
)

AXENTRA_FILE_CLASS = (
    "w-full rounded-xl border border-dashed border-slate-300 bg-slate-50 "
    "px-4 py-3 text-sm font-semibold text-slate-600 "
    "file:mr-4 file:rounded-lg file:border-0 file:bg-slate-900 "
    "file:px-3 file:py-2 file:text-xs file:font-black file:text-white "
    "hover:bg-white"
)

AXENTRA_DISABLED_CLASS = (
    "w-full cursor-not-allowed select-none rounded-xl border "
    "border-slate-200 bg-slate-100 px-4 py-3 text-sm "
    "font-semibold text-slate-400 outline-none"
)


def _merge_css_classes(*values):
    """Combina clases CSS sin repetir tokens."""

    result = []

    for value in values:
        for token in str(value or "").split():
            if token not in result:
                result.append(token)

    return " ".join(result)


class AxentraFormStylerMixin:
    """
    Inyecta estilos institucionales a formularios Django.

    Puede utilizarse con ``forms.Form`` y ``forms.ModelForm``. Conserva las
    clases adicionales declaradas directamente en cada widget.
    """

    def aplicar_estilos_institucionales(self):
        for field_name, field in self.fields.items():
            widget = field.widget
            existing_classes = widget.attrs.get("class", "")

            if field.disabled or widget.attrs.get("disabled"):
                selected_classes = AXENTRA_DISABLED_CLASS
                widget.attrs["disabled"] = True

            elif isinstance(
                widget,
                (forms.ClearableFileInput, forms.FileInput),
            ):
                selected_classes = AXENTRA_FILE_CLASS

            elif isinstance(widget, forms.CheckboxInput):
                selected_classes = AXENTRA_CHECKBOX_CLASS

            elif isinstance(widget, forms.RadioSelect):
                selected_classes = AXENTRA_RADIO_CLASS

            elif isinstance(
                widget,
                (
                    forms.Select,
                    forms.NullBooleanSelect,
                    forms.SelectMultiple,
                ),
            ):
                selected_classes = AXENTRA_SELECT_CLASS

            elif isinstance(widget, forms.Textarea):
                selected_classes = AXENTRA_TEXTAREA_CLASS

            else:
                selected_classes = AXENTRA_INPUT_CLASS

            widget.attrs["class"] = _merge_css_classes(
                selected_classes,
                existing_classes,
            )

            widget.attrs.setdefault("data-field-name", field_name)

            if field.required:
                widget.attrs.setdefault("aria-required", "true")

            if field.help_text:
                widget.attrs.setdefault(
                    "aria-describedby",
                    f"help_{field_name}",
                )

        return self


__all__ = [
    "AXENTRA_CHECKBOX_CLASS",
    "AXENTRA_DISABLED_CLASS",
    "AXENTRA_FILE_CLASS",
    "AXENTRA_INPUT_CLASS",
    "AXENTRA_RADIO_CLASS",
    "AXENTRA_SELECT_CLASS",
    "AXENTRA_TEXTAREA_CLASS",
    "AxentraFormStylerMixin",
]

