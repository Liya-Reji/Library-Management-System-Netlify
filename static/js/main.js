// Library Management System JavaScript
document.addEventListener("DOMContentLoaded", function () {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert:not(.alert-permanent)");
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Form confirmation prompts
    const confirmButtons = document.querySelectorAll("[data-confirm]");
    confirmButtons.forEach(function (button) {
        button.addEventListener("click", function (e) {
            const message = button.getAttribute("data-confirm") || "Are you sure you want to proceed?";
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });

    // Book Form: dynamic check for available copies <= total copies
    const totalCopiesInput = document.getElementById("total_copies");
    const availableCopiesInput = document.getElementById("available_copies");

    if (totalCopiesInput && availableCopiesInput) {
        function validateCopies() {
            const total = parseInt(totalCopiesInput.value, 10) || 0;
            const available = parseInt(availableCopiesInput.value, 10) || 0;
            if (available > total) {
                availableCopiesInput.setCustomValidity("Available copies cannot exceed total copies.");
            } else {
                availableCopiesInput.setCustomValidity("");
            }
        }
        totalCopiesInput.addEventListener("input", validateCopies);
        availableCopiesInput.addEventListener("input", validateCopies);
    }
});
