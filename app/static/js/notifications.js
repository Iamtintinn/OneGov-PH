(function () {
    var menus = document.querySelectorAll("details.icon-menu");

    menus.forEach(function (menu) {
        menu.addEventListener("toggle", function () {
            if (!menu.open) {
                return;
            }
            menus.forEach(function (other) {
                if (other !== menu) {
                    other.open = false;
                }
            });
        });
    });

    document.addEventListener("click", function (event) {
        menus.forEach(function (menu) {
            if (menu.open && !menu.contains(event.target)) {
                menu.open = false;
            }
        });
    });

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") {
            return;
        }
        if (document.body.classList.contains("sidebar-open")) {
            setSidebar(false);
            if (toggle) {
                toggle.focus();
            }
        }
        menus.forEach(function (menu) {
            if (!menu.open) {
                return;
            }
            menu.open = false;
            var summary = menu.querySelector("summary");
            if (summary) {
                summary.focus();
            }
        });
    });

    var sidebar = document.getElementById("citizen-sidebar");
    var toggle = document.querySelector(".sidebar-toggle");
    var backdrop = document.querySelector(".sidebar-backdrop");
    var sidebarQuery = window.matchMedia("(max-width: 980px)");
    var sidebarMemory = "onegov-sidebar-open";

    function rememberSidebar(open) {
        try {
            sessionStorage.setItem(sidebarMemory, open ? "1" : "0");
        } catch (error) {
            return;
        }
    }

    function sidebarWasOpen() {
        try {
            return sessionStorage.getItem(sidebarMemory) === "1";
        } catch (error) {
            return false;
        }
    }

    function setSidebar(open) {
        if (!sidebar || !toggle) {
            return;
        }
        document.body.classList.toggle("sidebar-open", open);
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
        toggle.querySelector(".visually-hidden").textContent = open ? "Close menu" : "Open menu";
        if (backdrop) {
            backdrop.hidden = !open;
        }
        if (sidebarQuery.matches) {
            rememberSidebar(open);
        }
    }

    if (toggle) {
        toggle.addEventListener("click", function () {
            setSidebar(!document.body.classList.contains("sidebar-open"));
        });
    }

    if (backdrop) {
        backdrop.addEventListener("click", function () {
            setSidebar(false);
            toggle.focus();
        });
    }

    if (sidebar && sidebarQuery.matches && sidebarWasOpen()) {
        setSidebar(true);
    }

    sidebarQuery.addEventListener("change", function (event) {
        if (event.matches && sidebarWasOpen()) {
            setSidebar(true);
            return;
        }
        if (!event.matches && document.body.classList.contains("sidebar-open")) {
            document.body.classList.remove("sidebar-open");
            if (toggle) {
                toggle.setAttribute("aria-expanded", "false");
                toggle.querySelector(".visually-hidden").textContent = "Open menu";
            }
            if (backdrop) {
                backdrop.hidden = true;
            }
        }
    });

    document.querySelectorAll("[data-open-details]").forEach(function (link) {
        link.addEventListener("click", function (event) {
            var menu = document.getElementById(link.getAttribute("data-open-details"));
            if (!menu) {
                return;
            }
            event.preventDefault();
            menu.open = true;
            var summary = menu.querySelector("summary");
            if (summary) {
                summary.focus();
            }
        });
    });
}());
