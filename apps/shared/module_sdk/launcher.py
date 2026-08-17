from django.core.paginator import Paginator


LAUNCHER_PAGE_SIZE = 12
LAUNCHER_FILTERS = (
    ("all", "Todas"),
    ("active", "Activas"),
    ("attention", "Requieren atención"),
    ("available", "No instaladas"),
)


def build_launcher_context(
    cards,
    *,
    is_root,
    query="",
    state="all",
    page=1,
    page_size=LAUNCHER_PAGE_SIZE,
):
    """Prepara el launcher sin conocer códigos de aplicaciones concretas."""
    query = str(query or "").strip()
    state = state if state in dict(LAUNCHER_FILTERS) else "all"
    normalized_query = query.casefold()

    core_cards = []
    application_cards = []
    for source in cards:
        card = dict(source)
        if card.get("kind") == "CORE":
            if is_root:
                core_cards.append(card)
            continue

        # Un operador sólo conoce aplicaciones instaladas, activas y que puede abrir.
        if not is_root and not (
            card.get("installed")
            and card.get("enabled")
            and card.get("can_open")
        ):
            continue

        searchable = " ".join(
            str(card.get(field, ""))
            for field in ("name", "description", "code")
        ).casefold()
        if normalized_query and normalized_query not in searchable:
            continue
        if state == "active" and not (
            card.get("installed") and card.get("enabled")
        ):
            continue
        if state == "attention" and not (
            card.get("installed")
            and card.get("enabled")
            and card.get("health") != "HEALTHY"
        ):
            continue
        if state == "available" and card.get("installed"):
            continue
        application_cards.append(card)

    application_cards.sort(
        key=lambda card: (
            not bool(card.get("can_open")),
            str(card.get("name", "")).casefold(),
            str(card.get("code", "")),
        )
    )
    core_cards.sort(key=lambda card: str(card.get("name", "")).casefold())
    paginator = Paginator(application_cards, page_size)

    return {
        "core_cards": tuple(core_cards),
        "application_page": paginator.get_page(page),
        "launcher_query": query,
        "launcher_state": state,
        "launcher_filters": LAUNCHER_FILTERS,
        "launcher_result_count": len(application_cards),
    }


__all__ = [
    "LAUNCHER_FILTERS",
    "LAUNCHER_PAGE_SIZE",
    "build_launcher_context",
]
