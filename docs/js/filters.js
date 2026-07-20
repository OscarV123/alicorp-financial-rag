const combinacionesValidas = {
    "2022": ["Estados financieros", "Hecho de importancia"],
    "2023": ["Estados financieros", "Hecho de importancia"],
    "2024": ["Hecho de importancia", "Reporte de resultados"]
};

const fYear = document.getElementById("fYear");
const fDoc = document.getElementById("fDoc");

function actualizarFiltroDocumentos() {
    const year = fYear.value;
    const opcionesValidas = combinacionesValidas[year];

    Array.from(fDoc.options).forEach(opt => {
        if (opt.value === "") return;

        const esValida = !year || (opcionesValidas && opcionesValidas.includes(opt.textContent));
        opt.style.display = esValida ? "" : "none"

        if (!esValida && fDoc.value === opt.textContent) {
            fDoc.value = "";
        }
    });
}

fYear.addEventListener("change", actualizarFiltroDocumentos);