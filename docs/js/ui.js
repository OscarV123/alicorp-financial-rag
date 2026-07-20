const preguntasSugeridas = [
    "Según el reporte de resultados del cuarto trimestre de 2024, ¿qué volumen total vendió Alicorp?",
    "Según el reporte de resultados del cuarto trimestre de 2024, ¿cuál fue el margen EBITDA ajustado consolidado de Alicorp?",
    "¿Cuál fue el EBITDA ajustado consolidado de Alicorp en el cuarto trimestre de 2024?",
    "Según los estados financieros separados, ¿cuál fue la utilidad neta de Alicorp durante 2022?",
    "Según los estados financieros separados, ¿cuánto ascendió el efectivo y equivalente de efectivo al 31 de diciembre de 2022?",
    "Según los estados financieros consolidados, ¿cuál fue la utilidad bruta de Alicorp?",
    "Según el estado consolidado de resultados publicado en febrero de 2024, ¿cuál fue el total de ventas netas de Alicorp y subsidiarias durante 2023?",
    "¿Qué monto colocó Alicorp en su emisión de bonos corporativos informada en diciembre de 2023?",
    "En diciembre de 2022, ¿cuántas acciones comunes había adquirido Alicorp al alcanzar el límite autorizado de recompra?",
    "Según el hecho de importancia de septiembre de 2024, ¿qué porcentaje de las acciones comunes emitidas representaban las acciones recompradas acumuladas por Alicorp?"
];

document.addEventListener("DOMContentLoaded", () => {
    const toggleBtn = document.getElementById("toggle-docs");
    const docsList = document.getElementById("docs-list");

    toggleBtn.addEventListener("click", (e) => {
        e.preventDefault();
        const isHidden = docsList.hidden;
        docsList.hidden = !isHidden;
        toggleBtn.textContent = isHidden ? "Ver menos" : "Ver más";
    });

    const input = document.getElementById("responseTopK");
    const minus = document.getElementById("minusBtn");
    const plus  = document.getElementById("plusBtn");

    input.addEventListener("keydown", (e) => {
        if (["e", "E", "+", "-"].includes(e.key)) {
            e.preventDefault();
        }
    });

    input.addEventListener("input", () => {
        input.value = input.value.replace(/[^0-9]/g, "");

        const min = parseInt(input.min, 10);
        const max = parseInt(input.max, 10);
        let value = parseInt(input.value, 10);

        if (!isNaN(value)) {
            if (value < min) input.value = min;
            if (value > max) input.value = max;
        }
    });

    minus.addEventListener("click", () => {
        const min = parseInt(input.min, 10);
        const current = parseInt(input.value, 10) || min;
        if (current > min) {
        input.value = current - 1;
        }
    });

    plus.addEventListener("click", () => {
        const max = parseInt(input.max, 10);
        const current = parseInt(input.value, 10) || max;
        if (current < max) {
        input.value = current + 1;
        }
    });
    
    const suggestedContainer = document.getElementById("suggested-questions");
    if (!suggestedContainer) return;

    function getRandomQuestions(n = 2) {
        const shuffled = [...preguntasSugeridas].sort(() => Math.random() - 0.5);
        return shuffled.slice(0, n);
    }

    function renderSuggestions() {
        suggestedContainer.innerHTML = "";

        getRandomQuestions(2).forEach(question => {
        const chip = document.createElement("button");
        chip.className = "suggestion-chip";
        chip.dataset.question = question;

        const arrow = document.createElement("span");
        arrow.className = "chip-arrow";
        arrow.textContent = "⤷";

        const text = document.createElement("span");
        text.textContent = question;

        chip.appendChild(arrow);
        chip.appendChild(text);

        chip.addEventListener("click", () => {
            ta.value = question;
            autoGrow();
            updateCharCount();
            handleSend();
            suggestedContainer.remove();
        });

        suggestedContainer.appendChild(chip);
        });
    }

    renderSuggestions();

    window.hideSuggestions = function () {
        suggestedContainer.remove();
    };

    if (!suggestedContainer) return;

    suggestedContainer.querySelectorAll(".suggestion-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const question = chip.dataset.question;
            autoGrow();
            updateCharCount();
            handleSend();
            suggestedContainer.remove();
        });
    });
    
    const randomBtn = document.getElementById("random-btn");
    if (!randomBtn) return;

    randomBtn.addEventListener("click", () => {
        if (typeof preguntasSugeridas === "undefined" || preguntasSugeridas.length === 0) return;

        const randomIndex = Math.floor(Math.random() * preguntasSugeridas.length);
        const question = preguntasSugeridas[randomIndex];

        ta.value = question;
        autoGrow();
        updateCharCount();
        ta.focus();
    });

});