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

// =========================================================
// THEME TOGGLE
// =========================================================
const themeToggle = document.getElementById("themeToggle");
const html = document.documentElement;

function setTheme(theme) {
    html.setAttribute("data-theme", theme);
    localStorage.setItem("snt-theme", theme);
    updateThemeIcon(theme);
}

function updateThemeIcon(theme) {
    if (!themeToggle) return;
    if (theme === "dark-blue") {
        themeToggle.textContent = "🌙";  // moon = click to go darker
        themeToggle.title = "Switch to black theme";
    } else {
        themeToggle.textContent = "☀️";  // blue dot = click to go blue
        themeToggle.title = "Switch to dark blue theme";
    }
}

// Init on load
const savedTheme = localStorage.getItem("snt-theme") || "dark-blue";
setTheme(savedTheme);

if (themeToggle) {
    themeToggle.addEventListener("click", () => {
        const current = html.getAttribute("data-theme");
        setTheme(current === "dark-blue" ? "dark" : "dark-blue");
    });
}

// =========================================================
// CONTACT / LEAD CLICK TRACKING
// Fires a lightweight, non-blocking beacon so buttons (WhatsApp,
// mailto, tel, contact form) always complete their normal action
// even if tracking fails or the browser blocks the request.
// =========================================================
document.querySelectorAll("[data-track-action]").forEach((el) => {
    el.addEventListener("click", () => {
        const payload = JSON.stringify({
            action_type: el.getAttribute("data-track-action"),
            page: el.getAttribute("data-track-page") || window.location.pathname,
        });
        try {
            if (navigator.sendBeacon) {
                navigator.sendBeacon("/api/track", new Blob([payload], { type: "application/json" }));
            } else {
                fetch("/api/track", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: payload,
                    keepalive: true,
                }).catch(() => {});
            }
        } catch (e) {
            /* tracking must never block the visitor's action */
        }
    });
});