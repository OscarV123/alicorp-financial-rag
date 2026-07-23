const API_BASE_URL = "";
const PDF_VIEWER_URL = `${API_BASE_URL}/pdfjs/web/viewer.html`;

const documentNames = {
  "ReporteNoAuditado_4T-2024": "Reportes de resultados 4T (2024)",
  "Informe_Auditado_EEFF_Separados_2022": "Estados financieros separados (2022)",
  "Informe_Auditado_EEFF_Consolidados_2023": "Estados financieros consolidados (2023)",
  "HechosDeImportancia_Otros_Diciembre-2022": "Hechos de importancia (Diciembre-2022)",
  "HechosDeImportancia_ConvocatoriaAJuntaDeAccionistas_Febrero-2023": "Hechos de importancia (Febrero-2023)",
  "HechosDeImportancia_EmisionDeValores_Diciembre-2023": "Hechos de importancia (Diciembre-2023)",
  "HechosDeImportancia_ConvocatoriaAJuntaDeAccionistas_Febrero-2024": "Hechos de importancia (Febrero-2024)",
  "HechosDeImportancia_Recompra-Redencion-Rescate_Septiembre-2024": "Hechos de importancia (Septiembre-2024)"
};

function friendlyName(docId) {
  return documentNames[docId] || docId;
}

function buildPdfUrl(docId, pageNum = 1) {
  const safeDocId = encodeURIComponent(docId);

  const pdfPath = `/abrir-pdf/${safeDocId}.pdf`;

  return (
    `${PDF_VIEWER_URL}` +
    `?file=${encodeURIComponent(pdfPath)}` +
    `#page=${Number(pageNum) || 1}`
  );
}

function renderEvidencesInLeftPanel(evidences) {

  const container = document.querySelector(".left-panel .evidence-box");
  if (!container) return;

  const currentTheme = localStorage.getItem("theme") || "light";
  const isDark = currentTheme === "dark";

  const pdfIcon = isDark
    ? "./assets/inv_pdf_imagen.png"
    : "./assets/pdf_imagen.png";

  const title = container.querySelector("h2");
  container.innerHTML = "";
  if (title) container.appendChild(title);

  evidences.forEach((ev, index) => {
    const meta = ev.metadata || {};
    const docId = meta.doc_id || "Documento";
    const pageNum = meta.page_number || 1; 
    const pageNumText = meta.page_number ? `Pág. ${meta.page_number}` : "";

    const divEvidence = document.createElement("div");
    divEvidence.className = "evidences evidence-cascade";
    divEvidence.style.animationDelay = `${index * 150}ms`;
    
    divEvidence.style.cursor = "pointer";
    
    divEvidence.innerHTML = `
      <article class="work-card">
        <div class="work-meta">
          <div class="work-left">
            <div class="work-text">
              <img
                src="${pdfIcon}"
                alt=""
                class="doc-icon"
              >

              <div class="work-title">
                Evidencia ${index + 1}
              </div>

              <div class="work-subtitle">
                ${friendlyName(docId)}
              </div>

              <div class="work-subtitle">
                ${pageNumText}
              </div>
            </div>
          </div>
        </div>
      </article>
    `;

    divEvidence.addEventListener("click", () => {
      const urlPdf = buildPdfUrl(docId, pageNum);
      window.open(urlPdf, '_blank', 'noopener,noreferrer');
    });

    container.appendChild(divEvidence);
  });
}

function convertQuotesToLinks(texto) {
  const regex = /([\w-]+),\s*Pág\.\s*(\d+)/g;

  return texto.replace(regex, (match, docId, pageNum) => {
    const urlPdf = buildPdfUrl(docId, pageNum);

    return `<a href="${urlPdf}" target="_blank" rel="noopener noreferrer" class="pdf-inline-link">${friendlyName(docId)}, Pág. ${pageNum}</a>`;
  });
}

document.querySelectorAll(".doc-card").forEach(card => {
  card.style.cursor = "pointer";
  card.addEventListener("click", () => {
    const docId = card.dataset.docId;
    if (!docId) return;
    
    const urlPdf = buildPdfUrl(docId);
    window.open(urlPdf, '_blank', 'noopener,noreferrer');
  });
});
