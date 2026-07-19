from django.test import SimpleTestCase

from apps.shared.workflows import (
    WorkflowActor,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowTransition,
    build_mermaid_source,
    build_stepper,
)


def sample_workflow():
    return WorkflowDefinition(
        code="tests.approval",
        name="Aprobación de prueba",
        description="Flujo sin acceso a base de datos.",
        actors=(
            WorkflowActor("requester", "Solicitante"),
            WorkflowActor("reviewer", "Revisor"),
        ),
        steps=(
            WorkflowStep("draft", "DRAFT", "Borrador", "requester"),
            WorkflowStep("review", "REVIEW", "Revisión", "reviewer"),
            WorkflowStep(
                "closed",
                "CLOSED",
                "Cerrado",
                "reviewer",
                terminal=True,
            ),
        ),
        transitions=(
            WorkflowTransition("draft", "review", "Enviar"),
            WorkflowTransition("review", "closed", "Aprobar", "success"),
        ),
        primary_path=("draft", "review", "closed"),
    )


class WorkflowRendererTests(SimpleTestCase):
    def test_mermaid_marks_current_status(self):
        source = build_mermaid_source(
            sample_workflow(),
            current_status="REVIEW",
        )
        self.assertIn("flowchart TD", source)
        self.assertIn("class S1 current", source)

    def test_stepper_calculates_progress(self):
        items = build_stepper(
            sample_workflow(),
            current_status="REVIEW",
        )
        self.assertEqual(
            [item["state"] for item in items],
            ["completed", "current", "pending"],
        )
