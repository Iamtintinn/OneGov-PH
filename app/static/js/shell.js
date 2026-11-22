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

    // Global confirm modal for logout and destructive form actions
    var confirmModal, confirmTitle, confirmMsg, confirmOk, confirmCancel, pendingConfirmForm;
    function ensureConfirmModal(){
        if(confirmModal) return;
        confirmModal=document.createElement('div');
        confirmModal.className='og-confirm';
        confirmModal.hidden=true;
        confirmModal.innerHTML='<div class="og-confirm-backdrop" data-close="1"></div><div class="og-confirm-dialog" role="dialog" aria-modal="true" aria-labelledby="og-confirm-title"><div class="og-confirm-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M10 7V5H5v14h5v-2"/><path d="M10 12h9"/><path d="m16 9 3 3-3 3"/></svg></div><h3 id="og-confirm-title" class="og-confirm-title"></h3><p class="og-confirm-msg"></p><div class="og-confirm-actions"><button type="button" class="og-confirm-btn og-confirm-cancel">Cancel</button><button type="button" class="og-confirm-btn og-confirm-ok">Confirm</button></div></div>';
        document.body.appendChild(confirmModal);
        confirmTitle=confirmModal.querySelector('.og-confirm-title');
        confirmMsg=confirmModal.querySelector('.og-confirm-msg');
        confirmOk=confirmModal.querySelector('.og-confirm-ok');
        confirmCancel=confirmModal.querySelector('.og-confirm-cancel');
        confirmModal.addEventListener('click',function(e){ if(e.target.closest('[data-close]')||e.target===confirmCancel) closeConfirm(); });
        confirmOk.addEventListener('click',function(){
            if(!pendingConfirmForm) return closeConfirm();
            var f=pendingConfirmForm; pendingConfirmForm=null; closeConfirm();
            f.dataset.confirmed='1';
            if(typeof f.requestSubmit==='function') f.requestSubmit(); else f.submit();
        });
        document.addEventListener('keydown',function(e){ if(e.key==='Escape' && confirmModal && !confirmModal.hidden) closeConfirm(); });
    }
    function openConfirm(form){
        ensureConfirmModal();
        pendingConfirmForm=form;
        confirmTitle.textContent=form.dataset.confirmTitle||'Confirm action';
        confirmMsg.textContent=form.dataset.confirm||'Are you sure you want to continue?';
        confirmOk.textContent=form.dataset.confirmAction||'Confirm';
        confirmOk.className='og-confirm-btn og-confirm-ok'+(form.dataset.confirmDanger==='1'?' is-danger':'');
        confirmModal.hidden=false;
        document.body.classList.add('og-confirm-open');
        confirmCancel.focus();
    }
    function closeConfirm(){ if(!confirmModal) return; confirmModal.hidden=true; document.body.classList.remove('og-confirm-open'); pendingConfirmForm=null; }
    document.addEventListener('submit',function(e){
        var form=e.target;
        if(!form || !form.dataset) return;
        if(form.dataset.confirmed==='1'){ delete form.dataset.confirmed; form.dataset.confirmPassed='1'; return; }
        if(form.dataset.confirm && !form.dataset.confirmPassed){ e.preventDefault(); openConfirm(form); }
    }, true);

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
