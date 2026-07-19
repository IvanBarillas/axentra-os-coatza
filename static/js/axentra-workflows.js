(function () {
    "use strict";

    let configured = false;
    let rendering = false;

    function configure() {
        if (configured || !window.mermaid) return Boolean(window.mermaid);
        window.mermaid.initialize({
            startOnLoad: false,
            securityLevel: "strict",
            theme: "base",
            flowchart: {
                htmlLabels: false,
                curve: "basis",
                useMaxWidth: true,
            },
            themeVariables: {
                fontFamily: "Source Sans 3, ui-sans-serif, system-ui, sans-serif",
                primaryColor: "#f8fafc",
                primaryTextColor: "#0f172a",
                primaryBorderColor: "#94a3b8",
                lineColor: "#64748b",
                secondaryColor: "#eff6ff",
                tertiaryColor: "#f1f5f9",
            },
        });
        configured = true;
        return true;
    }

    async function render(root) {
        if (rendering || !configure()) return;
        const scope = root && root.querySelectorAll ? root : document;
        const nodes = Array.from(scope.querySelectorAll(".ax-mermaid"))
            .filter((node) => !node.hasAttribute("data-processed"))
            .filter((node) => node.offsetParent !== null);

        if (!nodes.length) return;
        rendering = true;
        try {
            await window.mermaid.run({nodes});
        } catch (error) {
            console.error("Axentra Workflows: no fue posible renderizar Mermaid.", error);
        } finally {
            rendering = false;
            if (window.bootIcons) window.bootIcons();
        }
    }

    window.AxentraWorkflows = {render};

    document.addEventListener("DOMContentLoaded", function () {
        render(document);
    });
    document.body.addEventListener("htmx:afterSwap", function (event) {
        render(event.detail.target || document);
    });
    document.body.addEventListener("htmx:historyRestore", function () {
        render(document);
    });
    window.addEventListener("axentra:workflow-render", function () {
        render(document);
    });
})();
