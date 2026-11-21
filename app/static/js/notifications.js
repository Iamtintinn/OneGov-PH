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

    var notifyRoots = document.querySelectorAll("[data-notify-root]");

    function closeNotify(root, focusToggle) {
        if (!root || !root.classList.contains("open")) {
            if (root) {
                var t = root.querySelector(".shell-notify-toggle");
                if (t) t.setAttribute("aria-expanded", "false");
            }
            return;
        }
        var panel = root.querySelector(".notify-dropdown");
        var toggleBtn = root.querySelector(".shell-notify-toggle");
        root.classList.remove("open");
        if (toggleBtn) {
            toggleBtn.setAttribute("aria-expanded", "false");
            if (focusToggle) {
                toggleBtn.focus();
            }
        }
        if (!panel) {
            return;
        }
        panel.classList.remove("is-open");
        var done = false;
        function finish() {
            if (done) return;
            done = true;
            panel.hidden = true;
            panel.removeEventListener("transitionend", onEnd);
        }
        function onEnd(e) {
            if (e.target === panel) finish();
        }
        panel.addEventListener("transitionend", onEnd);
        window.setTimeout(finish, 220);
    }

    function openNotify(root) {
        var panel = root.querySelector(".notify-dropdown");
        var toggleBtn = root.querySelector(".shell-notify-toggle");
        if (!panel || !toggleBtn) {
            return;
        }
        notifyRoots.forEach(function (other) {
            if (other !== root) {
                closeNotify(other, false);
            }
        });
        menus.forEach(function (menu) {
            menu.open = false;
        });
        panel.hidden = false;
        panel.classList.remove("is-open");
        void panel.offsetWidth;
        panel.classList.add("is-open");
        toggleBtn.setAttribute("aria-expanded", "true");
        root.classList.add("open");
    }

    notifyRoots.forEach(function (root) {
        var toggleBtn = root.querySelector(".shell-notify-toggle");
        var panel = root.querySelector(".notify-dropdown");
        if (!toggleBtn || !panel) {
            return;
        }
        toggleBtn.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            var expanded = toggleBtn.getAttribute("aria-expanded") === "true";
            if (expanded) {
                closeNotify(root, false);
            } else {
                openNotify(root);
            }
        });
        panel.addEventListener("click", function (event) {
            event.stopPropagation();
        });
    });

    document.addEventListener("click", function (event) {
        notifyRoots.forEach(function (root) {
            if (root.classList.contains("open") && !root.contains(event.target)) {
                closeNotify(root, false);
            }
        });
    });

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") {
            return;
        }
        var notifyClosed = false;
        notifyRoots.forEach(function (root) {
            if (root.classList.contains("open")) {
                closeNotify(root, true);
                notifyClosed = true;
            }
        });
        if (notifyClosed) {
            return;
        }
        if (document.body.classList.contains("sidebar-open")) {
            setSidebar(false);
            if (toggle) {
                toggle.focus();
            }
            return;
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
