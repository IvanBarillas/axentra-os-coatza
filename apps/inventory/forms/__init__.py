from apps.inventory.forms.asset_forms import *
from apps.inventory.forms.custody_forms import *
from apps.inventory.forms.disposal_forms import *
from apps.inventory.forms.document_forms import *
from apps.inventory.forms.financial_forms import *
from apps.inventory.forms.intake_forms import *
from apps.inventory.forms.loan_forms import *
from apps.inventory.forms.movement_forms import *
from apps.inventory.forms.physical_audit_forms import *

# Compatibilidad temporal de importación con inventory_views.py antiguo.
# Debe eliminarse al sustituir asset_create_view por el flujo de solicitudes.
AssetForm = AssetIntakeCreateForm

__all__ = [name for name in globals() if name.endswith("Form")]
