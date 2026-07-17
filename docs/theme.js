document.addEventListener("DOMContentLoaded", () => {
  const btns = document.querySelectorAll(".theme-btn");

  const lightImg = document.querySelector('[data-theme="light"] img');
  const darkImg  = document.querySelector('[data-theme="dark"] img');

  const leftHamburgerImg  = document.querySelector("#btn-left .hamburger-icon");
  const rightHamburgerImg = document.querySelector("#btn-right .hamburger-icon");

  const docIcons = document.querySelectorAll(".doc-icon");

  function setTheme(theme) {
    const isDark = theme === "dark";

    document.body.classList.toggle("theme-dark", isDark);

    btns.forEach(b =>
      b.classList.toggle("is-active", b.dataset.theme === theme)
    );

    if (lightImg && darkImg) {
      if (isDark) {
        lightImg.src = "../assets/inv_tema_claro.png";
        darkImg.src  = "../assets/inv_tema_oscuro.png";
      } else {
        lightImg.src = "../assets/tema_claro.png";
        darkImg.src  = "../assets/tema_oscuro.png";
      }
    }

    if (leftHamburgerImg) {
      leftHamburgerImg.src = isDark ? "../assets/inv_libro_abierto.png" : "../assets/libro_abierto.png";
    }

    if (rightHamburgerImg) {
      rightHamburgerImg.src = isDark ? "../assets/inv_filtrar.png" : "../assets/filtrar.png";
    }

    docIcons.forEach(icon => {
      icon.src = isDark ? "../assets/inv_pdf_imagen.png" : "../assets/pdf_imagen.png";
    });

    localStorage.setItem("theme", theme);
  }

  const saved = localStorage.getItem("theme") || "light";
  setTheme(saved);

  btns.forEach(btn => {
    btn.addEventListener("click", () => setTheme(btn.dataset.theme));
  });
});