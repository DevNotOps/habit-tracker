document.addEventListener("click", (event) => {
  const toggle = event.target.closest(".menu-toggle");
  document.querySelectorAll(".menu-panel").forEach((panel) => {
    if (!toggle || !toggle.parentElement.contains(panel)) {
      panel.hidden = true;
      const button = panel.parentElement.querySelector(".menu-toggle");
      if (button) button.setAttribute("aria-expanded", "false");
    }
  });
  if (toggle) {
    const panel = toggle.parentElement.querySelector(".menu-panel");
    panel.hidden = !panel.hidden;
    toggle.setAttribute("aria-expanded", String(!panel.hidden));
  }
});

document.addEventListener("submit", (event) => {
  const message = event.target.dataset.confirm;
  if (message && !window.confirm(message)) event.preventDefault();
});

document.addEventListener("change", (event) => {
  if (!event.target.matches("[data-frequency]")) return;
  const goal = document.querySelector("[data-goal-field]");
  if (goal) goal.hidden = event.target.value === "daily";
});

document.querySelectorAll("[data-frequency]").forEach((select) => {
  const goal = document.querySelector("[data-goal-field]");
  if (goal) goal.hidden = select.value === "daily";
});
