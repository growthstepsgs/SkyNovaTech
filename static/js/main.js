// Mobile nav toggle
const navToggle = document.getElementById("navToggle");
const navLinks = document.getElementById("navLinks");

if (navToggle && navLinks) {
    navToggle.addEventListener("click", () => {
        const isOpen = navLinks.classList.toggle("open");
        navToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });
}

// Dismissible flash messages (click to close, auto-fade after 5s)
document.querySelectorAll(".flash-close").forEach((btn) => {
    btn.addEventListener("click", () => {
        btn.closest(".flash").remove();
    });
});

document.querySelectorAll(".flash").forEach((flash) => {
    setTimeout(() => {
        flash.style.transition = "opacity .3s ease";
        flash.style.opacity = "0";
        setTimeout(() => flash.remove(), 300);
    }, 5000);
});