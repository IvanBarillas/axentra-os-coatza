"""Guía visual de construcción de la estructura institucional."""

from apps.shared.workflows import (
    WorkflowActor,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowTransition,
)


ORGANIZATION_STRUCTURE_WORKFLOW = WorkflowDefinition(
    code="organigrama.structure",
    name="¿Cómo se construye la organización?",
    description=(
        "Ayuda a distinguir edificios, dependencias y áreas de trabajo antes "
        "de asignar a los funcionarios."
    ),
    version="1.0",
    actors=(
        WorkflowActor("configuration", "Institución", "Aporta los datos oficiales de la organización.", "landmark"),
        WorkflowActor("planner", "Organización", "Registra edificios, dependencias y áreas de trabajo.", "git-fork"),
        WorkflowActor("rh", "Recursos Humanos", "Asigna a cada funcionario en su área correspondiente.", "users-round"),
        WorkflowActor("system", "Axentra", "Comprueba que la estructura sea coherente.", "cpu"),
    ),
    steps=(
        WorkflowStep("tenant", "TENANT", "Registrar la institución", "configuration", icon="landmark"),
        WorkflowStep("site", "SITE", "Registrar edificios o sedes", "planner", icon="map-pin"),
        WorkflowStep("department", "DEPARTMENT", "Crear las dependencias responsables", "planner", icon="building-2"),
        WorkflowStep("area", "AREA", "Crear las áreas de trabajo", "planner", icon="layout-grid"),
        WorkflowStep("validate", "STRUCTURE_VALIDATED", "Comprobar que todo esté relacionado", "system", icon="list-checks"),
        WorkflowStep("staff", "STAFF_ASSIGNED", "Asignar a los funcionarios", "rh", icon="user-round-plus"),
        WorkflowStep("available", "AVAILABLE", "Organización lista para usarse", "system", icon="network", terminal=True),
        WorkflowStep("inactive", "INACTIVE", "Desactivar sin borrar el historial", "planner", icon="archive-x", terminal=True),
    ),
    transitions=(
        WorkflowTransition("tenant", "site", "Agregar ubicaciones", permission="can_configure_tenant"),
        WorkflowTransition("site", "department", "Definir responsables", permission="can_manage_infrastructure", explanation="Una dependencia puede tener personal en más de un edificio."),
        WorkflowTransition("department", "area", "Organizar equipos de trabajo", permission="can_mutate_structure"),
        WorkflowTransition("area", "validate", "Revisar ubicación y responsable", explanation="Cada área indica a qué dependencia pertenece y en qué sede trabaja."),
        WorkflowTransition("validate", "staff", "Estructura correcta", "success"),
        WorkflowTransition("staff", "available", "Ponerla en uso", "success"),
        WorkflowTransition("site", "inactive", "Desactivar sede", "danger", permission="can_manage_infrastructure"),
        WorkflowTransition("department", "inactive", "Desactivar dependencia", "danger", permission="can_mutate_structure"),
        WorkflowTransition("area", "inactive", "Desactivar área", "danger", permission="can_mutate_structure"),
        WorkflowTransition("inactive", "validate", "Revisar personas relacionadas", "warning", explanation="Antes de desactivar se comprueba que ninguna persona quede sin área válida."),
    ),
    primary_path=("tenant", "site", "department", "area", "validate", "staff", "available"),
    notes=(
        "Sede es el lugar físico: por ejemplo, Palacio Municipal o Tesorería.",
        "Dependencia es quién responde por el trabajo: por ejemplo, Innovación Gubernamental.",
        "Área es el equipo concreto: por ejemplo, Soporte Técnico de Innovación en Palacio.",
    ),
)


__all__ = ["ORGANIZATION_STRUCTURE_WORKFLOW"]
