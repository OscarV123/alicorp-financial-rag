document.addEventListener("DOMContentLoaded", () => {
  const btnLeft = document.getElementById("btn-left");
  const btnRight = document.getElementById("btn-right");

  const leftPanel = document.querySelector(".left-panel");
  const rightPanel = document.querySelector(".right-panel");
  const overlay = document.getElementById("overlay");

  const missing = [];
  if (!btnLeft) missing.push("btn-left");
  if (!btnRight) missing.push("btn-right");
  if (!leftPanel) missing.push(".left-panel");
  if (!rightPanel) missing.push(".right-panel");
  if (!overlay) missing.push("overlay");

  if (missing.length) {
    console.warn("Responsive panels: faltan elementos:", missing.join(", "));
    return;
  }

  function openPanel(panel) {
    panel.classList.add("is-open");
    overlay.hidden = false;
    document.body.style.overflow = "hidden";
  }

  function closePanels() {
    leftPanel.classList.remove("is-open");
    rightPanel.classList.remove("is-open");
    overlay.hidden = true;
    document.body.style.overflow = "";
  }

  btnLeft.addEventListener("click", () => {
    rightPanel.classList.remove("is-open");
    if (leftPanel.classList.contains("is-open")) closePanels();
    else openPanel(leftPanel);
  });

  btnRight.addEventListener("click", () => {
    leftPanel.classList.remove("is-open");
    if (rightPanel.classList.contains("is-open")) closePanels();
    else openPanel(rightPanel);
  });

  overlay.addEventListener("click", closePanels);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closePanels();
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 900) closePanels();
  });
});