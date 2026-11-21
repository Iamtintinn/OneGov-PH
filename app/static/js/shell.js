(function () {
    "use strict";

    var root = document.documentElement;
    var themeKey = "onegov-theme";
    var collapseKey = "onegov-sidebar-collapsed";
    var desktopQuery = window.matchMedia("(min-width: 981px)");

    function storedTheme() {
        try {
            return localStorage.getItem(themeKey) === "dark" ? "dark" : "light";
        } catch (error) {
            return "light";
        }
    }

    function applyTheme(theme) {
        if (theme === "dark") {
            root.setAttribute("data-theme", "dark");
        } else {
            root.removeAttribute("data-theme");
        }

        document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
            button.setAttribute("aria-pressed", theme === "dark" ? "true" : "false");
            button.setAttribute("title", theme === "dark" ? "Switch to light mode" : "Switch to dark mode");
            button.setAttribute("aria-label", theme === "dark" ? "Switch to light mode" : "Switch to dark mode");
        });
    }

    function toggleTheme() {
        var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
        applyTheme(next);
        try {
            localStorage.setItem(themeKey, next);
        } catch (error) {
            return;
        }
    }

    var themeButtons = document.querySelectorAll("[data-theme-toggle]");

    themeButtons.forEach(function (button) {
        button.addEventListener("click", toggleTheme);
    });

    if (themeButtons.length) {
        applyTheme(storedTheme());
    }

    var collapseButton = document.querySelector(".sidebar-collapse");

    function setCollapsed(collapsed) {
        var active = Boolean(collapsed) && desktopQuery.matches;
        document.body.classList.toggle("sidebar-collapsed", active);

        if (!collapseButton) {
            return;
        }

        collapseButton.setAttribute("aria-expanded", active ? "false" : "true");
        var label = collapseButton.querySelector(".collapse-label");
        if (label) {
            label.textContent = active ? "Show" : "Hide";
        }
        collapseButton.setAttribute("title", active ? "Expand sidebar" : "Collapse sidebar");
    }

    function storedCollapsed() {
        try {
            return localStorage.getItem(collapseKey) === "1";
        } catch (error) {
            return false;
        }
    }

    if (collapseButton) {
        setCollapsed(document.body.classList.contains("sidebar-collapsed"));
        collapseButton.addEventListener("click", function () {
            var next = !document.body.classList.contains("sidebar-collapsed");
            setCollapsed(next);
            try {
                localStorage.setItem(collapseKey, next ? "1" : "0");
            } catch (error) {
                return;
            }
        });
    }

    function handleDesktopChange(event) {
        if (!event.matches) {
            document.body.classList.remove("sidebar-collapsed");
            return;
        }
        setCollapsed(storedCollapsed());
    }

    if (typeof desktopQuery.addEventListener === "function") {
        desktopQuery.addEventListener("change", handleDesktopChange);
    } else if (typeof desktopQuery.addListener === "function") {
        desktopQuery.addListener(handleDesktopChange);
    }

    var sidebar = document.getElementById("citizen-sidebar");
    var backdrop = document.querySelector(".sidebar-backdrop");
    var mobileToggle = document.querySelector(".sidebar-toggle");

    function closeMobileSidebar() {
        if (!document.body.classList.contains("sidebar-open")) {
            return;
        }
        document.body.classList.remove("sidebar-open");
        if (mobileToggle) {
            mobileToggle.setAttribute("aria-expanded", "false");
            var label = mobileToggle.querySelector(".visually-hidden");
            if (label) {
                label.textContent = "Open menu";
            }
        }
        if (backdrop) {
            backdrop.hidden = true;
        }
    }

    if (sidebar) {
        sidebar.querySelectorAll("a.sidebar-link").forEach(function (link) {
            link.addEventListener("click", closeMobileSidebar);
        });
    }
}());
