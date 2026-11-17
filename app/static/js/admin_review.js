(function () {
    var triggers = document.querySelectorAll("[data-review-modal]");

    function closeModal(dialog) {
        if (dialog && typeof dialog.close === "function") {
            dialog.close();
        } else if (dialog) {
            dialog.removeAttribute("open");
        }
    }

    triggers.forEach(function (trigger) {
        trigger.addEventListener("click", function () {
            var dialog = document.getElementById(trigger.getAttribute("data-review-modal"));
            if (!dialog) { return; }
            if (typeof dialog.showModal === "function") {
                dialog.showModal();
            } else {
                dialog.setAttribute("open", "");
            }
        });
    });

    document.querySelectorAll("[data-review-modal-close]").forEach(function (button) {
        button.addEventListener("click", function () {
            closeModal(button.closest("dialog"));
        });
    });

    document.querySelectorAll(".review-modal").forEach(function (dialog) {
        dialog.addEventListener("click", function (event) {
            if (event.target === dialog) {
                closeModal(dialog);
            }
        });
    });
})();
