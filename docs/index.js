const ta = document.getElementById("question");
const counter = document.getElementById("counter");
const sendBtn = document.getElementById("send-btn");
const chatArea = document.querySelector(".chat-area");
const evidenciasMap = new Map();
let evidenciaCounter = 0;
let isSending = false;

const MAX_CHARS = 500;
const MAX_HEIGHT = 160;

function normalizeQuestion(s) {
  return s.replace(/\s+/g, " ").trim();
}

function getNormalized() {
  return normalizeQuestion(ta.value);
}

function updateCharCount() {
  const n = getNormalized();
  counter.textContent = `${n.length}/${MAX_CHARS}`;
}

function autoGrow() {
  ta.style.height = "27px";
  const h = Math.min(ta.scrollHeight, MAX_HEIGHT);
  ta.style.height = h + "px";
  ta.style.overflowY = ta.scrollHeight > MAX_HEIGHT ? "auto" : "hidden";
}

function scrollToBottom() {
  requestAnimationFrame(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  });
}

function preventOverflow(e) {
  const allowedKeys = [
    "Backspace", "Delete", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown",
    "Home", "End", "Tab", "Enter"
  ];
  if (allowedKeys.includes(e.key) || e.ctrlKey || e.metaKey) return;

  const hasSelection = ta.selectionStart !== ta.selectionEnd;
  if (hasSelection) return;

  const n = getNormalized();
  if (n.length >= MAX_CHARS) e.preventDefault();
}

function enforceMaxChars() {
  let n = ta.value;
  if (n.length > MAX_CHARS) n = n.slice(0, MAX_CHARS);
  if (ta.value !== n) ta.value = n;
  autoGrow();
  updateCharCount();
}

function appendUserMessage(text) {
  const wrap = document.createElement("div");
  wrap.className = "message-user";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const p = document.createElement("p");
  p.className = "msg-text";
  p.textContent = text;

  bubble.appendChild(p);
  wrap.appendChild(bubble);
  chatArea.appendChild(wrap);

  scrollToBottom();
}

function appendBotMessage(text, isStreaming = false, messageId = null) {
  const wrap = document.createElement("div");
  wrap.className = "message-bot";
  if (messageId) wrap.id = messageId;

  const contentContainer = document.createElement("div");
  contentContainer.className = "msg-text-container"; 
  
  wrap.appendChild(contentContainer);
  
  const actionBar = document.createElement("div");
  actionBar.className = "message-action-bar";
  actionBar.innerHTML = `
    <button class="action-btn" title="Ver libro">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
      </svg>
    </button>
  `;
  wrap.appendChild(actionBar);

  chatArea.appendChild(wrap);
  scrollToBottom();

  const actionBtn = actionBar.querySelector(".action-btn");
  actionBtn.addEventListener("click", () => {
    if (messageId && evidenciasMap.has(messageId)) {
      const evidencias = evidenciasMap.get(messageId);
      renderEvidencesInLeftPanel(evidencias);
    }

    const btnLeft = document.getElementById("btn-left");
    const leftPanel = document.querySelector(".left-panel");
    if (btnLeft && leftPanel && !leftPanel.classList.contains("is-open")) {
      btnLeft.click();
    }
  });

  const textoConEnlaces = convertQuotesToLinks(text);
  const htmlFormateado = DOMPurify.sanitize(marked.parse(textoConEnlaces, { breaks: true }),
    {
      ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'code', 'pre', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'table', 'thead', 'tbody', 'tr', 'th', 'td'],
      ALLOWED_ATTR: ['href', 'target', 'class']
    }
  );

  return new Promise((resolve) => {
    if (isStreaming) {
      const tempDiv = document.createElement("div");
      tempDiv.innerHTML = htmlFormateado;

      const childNodes = Array.from(tempDiv.childNodes);
      let index = 0;
      const speed = 100;

      function typeWriterHTML() {
        if (index < childNodes.length) {
          const nodeClone = childNodes[index].cloneNode(true);

          if (nodeClone.nodeType === Node.ELEMENT_NODE) {
            nodeClone.classList.add("fade-blur-in");
          } else if (nodeClone.nodeType === Node.TEXT_NODE) {
            const span = document.createElement("span");
            span.className = "fade-blur-in";
            span.textContent = nodeClone.textContent;
            contentContainer.appendChild(span);
            index++;
            scrollToBottom();
            setTimeout(typeWriterHTML, speed);
            return;
          }

          contentContainer.appendChild(nodeClone);
          index++;

          scrollToBottom();
          setTimeout(typeWriterHTML, speed);
          return;
        }
        resolve();
      }
      typeWriterHTML();
    } else {
      contentContainer.innerHTML = htmlFormateado;
      scrollToBottom();
      resolve();
    }
  });
}

async function handleSend() {

  if (isSending) return;

  enforceMaxChars();

  const question = getNormalized();

  if (ta.value !== question) ta.value = question;
  autoGrow();
  updateCharCount();

  if (!question) return;

  isSending = true;
  appendUserMessage(question);

  if (typeof hideSuggestions === "function") hideSuggestions();

  ta.value = "";
  autoGrow();
  updateCharCount();

  sendBtn.disabled = true;

  const loadingWrap = document.createElement("div");
  loadingWrap.className = "message-bot loading-container";
  
  loadingWrap.innerHTML = `
    <span class="loading-text">Buscando evidencias</span>
    <div class="dots-wrapper"><span></span><span></span><span></span>
    </div>
  `;
  
  chatArea.appendChild(loadingWrap);
  scrollToBottom();

  const topKInput = document.getElementById("responseTopK");
  const topKValue = topKInput ? parseInt(topKInput.value, 10) : 5;

  const modeToggle = document.getElementById("responseMode");
  const modeValue = (modeToggle && modeToggle.checked) ? "explanatory" : "strict";

  const yearSelect = document.getElementById("fYear");
  const docSelect = document.getElementById("fDoc");
  
  let explicitWhere = null;
  const condiciones = {};

  if (yearSelect && yearSelect.value) {
    condiciones["year"] = yearSelect.value;
  }
  if (docSelect && docSelect.value) {
    condiciones["document_type"] = docSelect.value;
  }

  
  if (Object.keys(condiciones).length > 0) {
    
    explicitWhere = condiciones; 
  }

  try {
    const url = "http://127.0.0.1:8000/query";

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question: question,
        top_k: topKValue,
        explicit_where: explicitWhere,
        mode: modeValue
      })
    });

    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Error en el pipeline del servidor.");
    }

    const resultado = await response.json();

    loadingWrap.classList.add("fade-out");

    setTimeout(async () => {
      loadingWrap.remove();

      const messageId = `msg-${++evidenciaCounter}`;
      if (resultado.evidences && resultado.evidences.length > 0) {
        evidenciasMap.set(messageId, resultado.evidences);
      }

      await appendBotMessage(resultado.answer, true, messageId);

      if (resultado.evidences && resultado.evidences.length > 0) {
        renderEvidencesInLeftPanel(resultado.evidences);
      }

      isSending = false;
      sendBtn.disabled = false;
      ta.focus();
    }, 300);

  } catch (err) {
    console.error(err);

    if (loadingWrap && loadingWrap.parentNode) {
      loadingWrap.remove();
    }

    await appendBotMessage("Ocurrió un error al enviar la consulta.");

    isSending = false;
    sendBtn.disabled = false;
    ta.focus();
  }
}

function renderEvidencesInLeftPanel(evidences) {
  const container = document.querySelector(".left-panel .evidence-box");
  if (!container) return;

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
                      <div class="work-title">Evidencia ${index + 1}</div>
                      <div class="work-subtitle">${docId} - ${pageNum}</div>
                  </div>
              </div>
          </div>
      </article>
    `;

    divEvidence.addEventListener("click", () => {
      const urlPdf = `http://127.0.0.1:8000/abrir-pdf/${docId}.pdf#page=${pageNum}`;
      window.open(urlPdf, '_blank', 'noopener,noreferrer');
    });

    container.appendChild(divEvidence);
  });
}

function convertQuotesToLinks(texto) {
  const regex = /([\w-]+),\s*Pág\.\s*(\d+)/g;

  return texto.replace(regex, (match, docId, pageNum) => {
    const url = `http://127.0.0.1:8000/abrir-pdf/${docId}.pdf#page=${pageNum}`;

    return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="pdf-inline-link">${docId}, Pág. ${pageNum}</a>`;
  });
}




/* Eventos */
document.querySelectorAll(".doc-card").forEach(card => {
  card.style.cursor = "pointer";
  card.addEventListener("click", () => {
    const docId = card.dataset.docId;
    if (!docId) return;
    const urlPdf = `http://127.0.0.1:8000/abrir-pdf/${docId}.pdf`;
    window.open(urlPdf, '_blank', 'noopener,noreferrer');
  });
});

ta.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSend();
    return;
  }

  preventOverflow(e);
});

ta.addEventListener("input", () => {
  enforceMaxChars();
});

ta.addEventListener("paste", () => {
  requestAnimationFrame(() => enforceMaxChars());
});

ta.addEventListener("blur", () => {
  const question = getNormalized();
  if (ta.value !== question) {
    ta.value = question;
    autoGrow();
    updateCharCount();
  }
});

sendBtn.addEventListener("click", (e) => {
  e.preventDefault();
  handleSend();
});

window.addEventListener("load", () => {
  autoGrow();
  updateCharCount();
  scrollToBottom(0);
});
