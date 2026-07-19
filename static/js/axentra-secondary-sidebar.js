(function () {
    "use strict";

    const SIDEBAR_SELECTOR = "#module-sidebar";
    const LINK_SELECTOR = [
        "a[href]",
        "[hx-target='#page-content']",
        "[hx-push-url]",
    ].join("");

    function normalizePath(value) {
        let pathname;

        try {
            pathname = new URL(value || window.location.href, window.location.origin).pathname;
        } catch (_error) {
            pathname = window.location.pathname;
        }

        pathname = pathname.replace(/\/{2,}/g, "/");

        if (pathname.length > 1 && !pathname.endsWith("/")) {
            pathname += "/";
        }

        return pathname;
    }

    function sidebarLinks() {
        const sidebar = document.querySelector(SIDEBAR_SELECTOR);

        if (!sidebar) {
            return [];
        }

        return Array.from(sidebar.querySelectorAll(LINK_SELECTOR)).filter(function (link) {
            const href = link.getAttribute("href");

            if (!href || href === "#") {
                return false;
            }

            try {
                return new URL(href, window.location.origin).origin === window.location.origin;
            } catch (_error) {
                return false;
            }
        });
    }

    function matchingScore(link, currentPath) {
        const linkPath = normalizePath(link.href);

        if (linkPath === currentPath) {
            return 100000 + linkPath.length;
        }

        if (linkPath !== "/" && currentPath.startsWith(linkPath)) {
            return linkPath.length;
        }

        return -1;
    }

    function markCurrent(selectedLink) {
        sidebarLinks().forEach(function (link) {
            const isCurrent = link === selectedLink;

            link.dataset.axentraSidebarCurrent = isCurrent ? "true" : "false";

            if (isCurrent) {
                link.setAttribute("aria-current", "page");
            } else {
                link.removeAttribute("aria-current");
            }
        });
    }

    function selectByPath(path) {
        const currentPath = normalizePath(path);
        let selectedLink = null;
        let selectedScore = -1;

        sidebarLinks().forEach(function (link) {
            const score = matchingScore(link, currentPath);

            if (score > selectedScore) {
                selectedLink = link;
                selectedScore = score;
            }
        });

        markCurrent(selectedLink);
        return selectedLink;
    }

    function selectRequestedLink(event) {
        const element = event.detail && event.detail.elt;
        const link = element && element.closest
            ? element.closest(SIDEBAR_SELECTOR + " a[href]")
            : null;

        if (link) {
            markCurrent(link);
        }
    }

    function synchronizeFromEvent(event) {
        const detail = event.detail || {};
        const path = detail.path || detail.url || window.location.href;

        window.requestAnimationFrame(function () {
            selectByPath(path);
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        selectByPath(window.location.href);
    });

    document.body.addEventListener("htmx:beforeRequest", selectRequestedLink);
    document.body.addEventListener("htmx:pushedIntoHistory", synchronizeFromEvent);
    document.body.addEventListener("htmx:replacedInHistory", synchronizeFromEvent);
    document.body.addEventListener("htmx:historyRestore", synchronizeFromEvent);
    document.body.addEventListener("htmx:afterSwap", function () {
        selectByPath(window.location.href);
    });
    document.body.addEventListener("htmx:responseError", function () {
        selectByPath(window.location.href);
    });
    document.body.addEventListener("htmx:sendError", function () {
        selectByPath(window.location.href);
    });
    window.addEventListener("popstate", function () {
        selectByPath(window.location.href);
    });

    window.AxentraSecondarySidebar = {
        synchronize: selectByPath,
    };
})();
