# apps/inventory/services/folio_service.py

"""GeneraciÃ³n transaccional de folios patrimoniales oficiales."""

from datetime import date
import re
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.inventory.dtos import FolioScope, GeneratedInventoryFolio
from apps.inventory.integrations.core_directory import (
    CoreDirectoryError,
    get_active_tenant,
    get_department,
)
from apps.inventory.models import (
    ExpenditureObject,
    InventoryAssetTypeCode,
    InventoryFolioPolicy,
    InventoryFolioSequence,
)
from apps.inventory.services.exceptions import (
    FolioGenerationError,
    FolioPolicyConflict,
    FolioPolicyNotFound,
    FolioSequenceExhausted,
    InventoryConfigurationError,
    InventoryValidationError,
)


_CODE_PATTERN = re.compile(r"^[A-Z0-9._]+$")
_FORMAT_TOKENS = frozenset(
    {
        "municipality",
        "fiscal_year",
        "year_short",
        "conac",
        "dependency",
        "asset_type",
        "progressive",
    }
)


def _normalize_code(
    value,
    *,
    field_name: str,
    max_length: int,
) -> str:
    normalized = str(value or "").strip().upper()

    if not normalized:
        raise InventoryValidationError(
            f"{field_name} es obligatorio.",
            details={"field": field_name},
        )

    if len(normalized) > max_length:
        raise InventoryValidationError(
            f"{field_name} excede {max_length} caracteres.",
            details={"field": field_name},
        )

    if not _CODE_PATTERN.fullmatch(normalized):
        raise InventoryValidationError(
            f"{field_name} contiene caracteres no permitidos.",
            details={"field": field_name, "value": normalized},
        )

    return normalized


def _validate_asset_type(asset_type_code) -> str:
    normalized = _normalize_code(
        asset_type_code,
        field_name="asset_type_code",
        max_length=2,
    )

    valid_values = {
        value
        for value, _label in InventoryAssetTypeCode.choices
    }

    if normalized not in valid_values:
        raise InventoryValidationError(
            "El tipo de bien debe ser BM, BI o BP.",
            details={"asset_type_code": normalized},
        )

    return normalized


def _validate_fiscal_year(fiscal_year: int) -> int:
    try:
        normalized = int(fiscal_year)
    except (TypeError, ValueError) as exc:
        raise InventoryValidationError(
            "El ejercicio fiscal debe ser numÃ©rico."
        ) from exc

    if normalized < 2000 or normalized > 9999:
        raise InventoryValidationError(
            "El ejercicio fiscal debe contener cuatro dÃ­gitos.",
            details={"fiscal_year": normalized},
        )

    return normalized


def _get_expenditure_object(expenditure_object_id):
    try:
        expenditure_object = (
            ExpenditureObject.objects
            .select_related("category", "accounting_account")
            .get(
                pk=expenditure_object_id,
                is_active=True,
                is_deleted=False,
            )
        )
    except (
        ExpenditureObject.DoesNotExist,
        DjangoValidationError,
        ValueError,
        TypeError,
    ) as exc:
        raise InventoryValidationError(
            "El objeto del gasto no existe o no estÃ¡ disponible."
        ) from exc

    if not expenditure_object.requires_inventory_control:
        raise InventoryConfigurationError(
            "El objeto del gasto no requiere control de inventario.",
            details={
                "expenditure_object_id": str(expenditure_object.pk),
                "code": expenditure_object.code,
            },
        )

    return expenditure_object


def get_effective_folio_policy(
    *,
    effective_on: date | None = None,
    lock: bool = False,
) -> InventoryFolioPolicy:
    effective_date = effective_on or timezone.localdate()

    queryset = (
        InventoryFolioPolicy.objects
        .filter(
            effective_from__lte=effective_date,
            is_active=True,
            is_deleted=False,
        )
        .filter(
            Q(effective_until__isnull=True)
            | Q(effective_until__gte=effective_date)
        )
        .order_by("-effective_from", "pk")
    )

    if lock:
        queryset = queryset.select_for_update()

    policies = list(queryset[:2])

    if not policies:
        raise FolioPolicyNotFound(
            "No existe una polÃ­tica de folios vigente.",
            details={"effective_on": effective_date.isoformat()},
        )

    if len(policies) > 1:
        raise FolioPolicyConflict(
            "Existe mÃ¡s de una polÃ­tica de folios vigente.",
            details={
                "effective_on": effective_date.isoformat(),
                "policy_ids": [str(policy.pk) for policy in policies],
            },
        )

    return policies[0]


def _build_scope(
    *,
    policy: InventoryFolioPolicy,
    fiscal_year: int,
    expenditure_object,
    department_id,
    asset_type_code: str,
) -> FolioScope:
    try:
        tenant = get_active_tenant()
    except CoreDirectoryError as exc:
        raise InventoryConfigurationError(str(exc)) from exc

    try:
        department = get_department(department_id)
    except CoreDirectoryError as exc:
        raise InventoryValidationError(str(exc)) from exc

    if not tenant.is_available:
        raise InventoryConfigurationError(
            "La configuraciÃ³n institucional no estÃ¡ disponible."
        )

    municipality = tenant.municipality
    if municipality is None:
        raise InventoryConfigurationError(
            "La configuraciÃ³n institucional no tiene un municipio asociado."
        )

    if not municipality.is_available:
        raise InventoryConfigurationError(
            "El municipio asociado a la configuraciÃ³n institucional "
            "no estÃ¡ disponible.",
            details={"municipality_id": str(municipality.id)},
        )

    dependency_code = department.normalized_code

    if not dependency_code:
        raise InventoryConfigurationError(
            "La dependencia no tiene cÃ³digo presupuestal para el folio.",
            details={"department_id": str(department.id)},
        )

    policy_municipality_code = _normalize_code(
        policy.municipality_code,
        field_name="municipality_code",
        max_length=10,
    )
    core_municipality_code = _normalize_code(
        municipality.code,
        field_name="core_municipality_code",
        max_length=10,
    )

    if policy_municipality_code.zfill(3) != core_municipality_code.zfill(3):
        raise InventoryConfigurationError(
            "La clave municipal de la polÃ­tica de folios no coincide "
            "con la configuraciÃ³n institucional.",
            details={
                "policy_id": str(policy.pk),
                "policy_municipality_code": policy_municipality_code,
                "core_municipality_code": core_municipality_code,
            },
        )

    municipality_code = core_municipality_code.zfill(3)
    conac_code = _normalize_code(
        expenditure_object.code,
        field_name="conac_code",
        max_length=10,
    )
    dependency_code = _normalize_code(
        dependency_code,
        field_name="dependency_code",
        max_length=20,
    ).zfill(3)

    return FolioScope(
        policy_id=policy.pk,
        municipality_code=municipality_code,
        fiscal_year=_validate_fiscal_year(fiscal_year),
        conac_code=conac_code,
        dependency_id=department.id,
        dependency_code=dependency_code,
        asset_type_code=_validate_asset_type(asset_type_code),
        progressive_length=policy.progressive_length,
    )


def _render_folio(
    *,
    policy: InventoryFolioPolicy,
    scope: FolioScope,
    progressive_number: int,
) -> str:
    maximum_progressive = (10 ** scope.progressive_length) - 1

    if progressive_number > maximum_progressive:
        raise FolioSequenceExhausted(
            "La secuencia agotÃ³ la longitud configurada.",
            details={
                "policy_id": str(scope.policy_id),
                "maximum_progressive": maximum_progressive,
            },
        )

    values = {
        "municipality": scope.municipality_code,
        "fiscal_year": str(scope.fiscal_year),
        "year_short": str(scope.fiscal_year)[-2:],
        "conac": scope.conac_code,
        "dependency": scope.dependency_code,
        "asset_type": scope.asset_type_code,
        "progressive": str(progressive_number).zfill(
            scope.progressive_length
        ),
    }

    try:
        rendered = policy.format_template.format_map(values)
    except (KeyError, ValueError) as exc:
        raise InventoryConfigurationError(
            "La plantilla institucional de folios es invÃ¡lida.",
            details={
                "policy_id": str(policy.pk),
                "format_template": policy.format_template,
            },
        ) from exc

    normalized = rendered.strip().upper()

    if not normalized:
        raise FolioGenerationError(
            "La plantilla generÃ³ un folio vacÃ­o."
        )

    if len(normalized) > 100:
        raise FolioGenerationError(
            "El folio generado excede 100 caracteres.",
            details={"folio": normalized},
        )

    return normalized


def preview_inventory_folio(
    *,
    acquisition_date: date,
    expenditure_object_id,
    department_id,
    asset_type_code: str,
    effective_on: date | None = None,
) -> str:
    """Muestra el siguiente folio posible sin reservarlo."""

    if not isinstance(acquisition_date, date):
        raise InventoryValidationError(
            "acquisition_date debe ser una fecha vÃ¡lida."
        )

    policy = get_effective_folio_policy(effective_on=effective_on)
    expenditure_object = _get_expenditure_object(
        expenditure_object_id
    )
    scope = _build_scope(
        policy=policy,
        fiscal_year=acquisition_date.year,
        expenditure_object=expenditure_object,
        department_id=department_id,
        asset_type_code=asset_type_code,
    )
    sequence = (
        InventoryFolioSequence.objects
        .filter(
            policy_id=scope.policy_id,
            fiscal_year=scope.fiscal_year,
            conac_code=scope.conac_code,
            dependency_code=scope.dependency_code,
            asset_type_code=scope.asset_type_code,
            is_deleted=False,
        )
        .first()
    )
    next_number = (sequence.current_number if sequence else 0) + 1

    return _render_folio(
        policy=policy,
        scope=scope,
        progressive_number=next_number,
    )


@transaction.atomic
def generate_inventory_folio(
    *,
    acquisition_date: date,
    expenditure_object_id,
    department_id,
    asset_type_code: str,
    effective_on: date | None = None,
) -> GeneratedInventoryFolio:
    """
    Reserva y genera el siguiente folio oficial.

    Bloquear la polÃ­tica serializa tambiÃ©n la creaciÃ³n de secuencias nuevas,
    evitando que dos capturistas creen el mismo scope simultÃ¡neamente.
    """

    if not isinstance(acquisition_date, date):
        raise InventoryValidationError(
            "acquisition_date debe ser una fecha vÃ¡lida."
        )

    policy = get_effective_folio_policy(
        effective_on=effective_on,
        lock=True,
    )
    expenditure_object = _get_expenditure_object(
        expenditure_object_id
    )
    scope = _build_scope(
        policy=policy,
        fiscal_year=acquisition_date.year,
        expenditure_object=expenditure_object,
        department_id=department_id,
        asset_type_code=asset_type_code,
    )

    sequence, _created = (
        InventoryFolioSequence.objects
        .select_for_update()
        .get_or_create(
            policy=policy,
            fiscal_year=scope.fiscal_year,
            conac_code=scope.conac_code,
            dependency_code=scope.dependency_code,
            asset_type_code=scope.asset_type_code,
            defaults={
                "current_number": 0,
                "is_active": True,
                "is_deleted": False,
            },
        )
    )

    if sequence.is_deleted or not sequence.is_active:
        raise InventoryConfigurationError(
            "La secuencia correspondiente estÃ¡ inactiva.",
            details={"sequence_id": str(sequence.pk)},
        )

    next_number = sequence.current_number + 1
    official_folio = _render_folio(
        policy=policy,
        scope=scope,
        progressive_number=next_number,
    )

    sequence.current_number = next_number
    sequence.full_clean()
    sequence.save(
        update_fields=["current_number", "updated_at"]
    )

    return GeneratedInventoryFolio(
        official_inventory_number=official_folio,
        internal_inventory_number=official_folio,
        progressive_number=next_number,
        sequence_id=sequence.pk,
        scope=scope,
    )


__all__ = [
    "FolioScope",
    "GeneratedInventoryFolio",
    "generate_inventory_folio",
    "get_effective_folio_policy",
    "preview_inventory_folio",
]
