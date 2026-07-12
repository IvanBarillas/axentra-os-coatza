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
        fields = [
            "nombre",
            "codigo_presupuestal",
            "parent",
            "encargado_departamento",
        ]

        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "placeholder": "Ej: Dirección General de Innovación",
                }
            ),
            "codigo_presupuestal": forms.TextInput(
                attrs={
                    "placeholder": "Ej: 012",
                    "maxlength": "3",
                    "inputmode": "numeric",
                }
            ),
            "parent": forms.Select(),
            "encargado_departamento": forms.Select(),
        }

        labels = {
            "nombre": "Nombre de la dependencia",
            "codigo_presupuestal": "Código presupuestal",
            "parent": "Dependencia padre",
            "encargado_departamento": "Servidor público titular",
        }

        help_texts = {
            "codigo_presupuestal": "Clave de 3 dígitos usada para folios patrimoniales ORFIS/SIGMAVER. Ejemplo: 012.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        instancia_actual = self.instance if self.instance and self.instance.pk else None
        dependencias_padre = Dependencia.objects.filter(is_deleted=False).order_by("nombre")

        if instancia_actual:
            dependencias_padre = dependencias_padre.exclude(pk=instancia_actual.pk)
            ids_descendientes = self._obtener_ids_descendientes(instancia_actual)

            if ids_descendientes:
                dependencias_padre = dependencias_padre.exclude(pk__in=ids_descendientes)

        if self.fields.get("codigo_presupuestal"):
            self.fields["codigo_presupuestal"].required = False

        if self.fields.get("parent"):
            self.fields["parent"].queryset = dependencias_padre
            self.fields["parent"].required = False
            self.fields["parent"].empty_label = "--- Sin dependencia padre / Nodo raíz ---"

        if self.fields.get("encargado_departamento"):
            self.fields["encargado_departamento"].required = False
            self.fields["encargado_departamento"].empty_label = "--- Seleccione Servidor Público Titular (Opcional) ---"

        self.aplicar_estilos_institucionales()

    def clean_codigo_presupuestal(self):
        codigo = (self.cleaned_data.get("codigo_presupuestal") or "").strip()

        if not codigo:
            return ""

        if not codigo.isdigit():
            raise forms.ValidationError("El código presupuestal debe contener sólo números.")

        if len(codigo) > 3:
            raise forms.ValidationError("El código presupuestal no puede tener más de 3 dígitos.")

        codigo = codigo.zfill(3)

        queryset = Dependencia.objects.filter(
            codigo_presupuestal=codigo,
            is_deleted=False,
        )

        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError("Ya existe una dependencia con este código presupuestal.")

        return codigo

    def clean_parent(self):
        parent = self.cleaned_data.get("parent")

        if not parent:
            return parent

        if self.instance and self.instance.pk:
            if parent.pk == self.instance.pk:
                raise forms.ValidationError("Una dependencia no puede ser padre de sí misma.")

            if parent.pk in self._obtener_ids_descendientes(self.instance):
                raise forms.ValidationError("No puedes asignar como padre una dependencia hija o descendiente.")

        return parent

    def _obtener_ids_descendientes(self, dependencia):
        """
        Obtiene los IDs de todas las dependencias hijas y descendientes.
        Esto evita ciclos recursivos en la estructura del organigrama.
        """
        ids_descendientes = set()
        pendientes = [dependencia.pk]

        while pendientes:
            hijos = Dependencia.objects.filter(
                parent_id__in=pendientes,
                is_deleted=False,
            ).values_list("id", flat=True)

            nuevos_ids = set(hijos) - ids_descendientes

            if not nuevos_ids:
                break

            ids_descendientes.update(nuevos_ids)
            pendientes = list(nuevos_ids)

        return ids_descendientes


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

        argumento_completo = dependencia and sede_fisica and nombre

        if self.instance._state.adding and argumento_completo:
            generated_slug = slugify(nombre)
            if AreaOperativa.objects.filter(
                dependencia=dependencia, 
                sede_fisica=sede_fisica, 
                slug=generated_slug, 
                is_deleted=False
            ).exists():
                raise ValidationError(
                    "🚨 Operación Cancelada: Esta oficina ya se encuentra registrada y operando para esa Dependencia dentro del Edificio seleccionado."
                )
        return cleaned_data