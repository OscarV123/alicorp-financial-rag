const ta = document.getElementById("question");
const counter = document.getElementById("counter");
const sendBtn = document.getElementById("send-btn");
const chatArea = document.querySelector(".chat-area");

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

function appendBotMessage(text, isStreaming = false) {
  const wrap = document.createElement("div");
  wrap.className = "message-bot";

  const contentContainer = document.createElement("div");
  contentContainer.className = "msg-text-container"; 
  
  wrap.appendChild(contentContainer);
  chatArea.appendChild(wrap);
  scrollToBottom();

  const htmlFormateado = marked.parse(text, { breaks: true });

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
      }
    }
    
    typeWriterHTML();
  } else {
    contentContainer.innerHTML = htmlFormateado;
    scrollToBottom();
  }
}

async function handleSend() {
  enforceMaxChars();

  const question = getNormalized();

  if (ta.value !== question) ta.value = question;
  autoGrow();
  updateCharCount();

  if (!question) return;

  appendUserMessage(question);

  ta.value = "";
  autoGrow();
  updateCharCount();

  sendBtn.disabled = true;

  const loadingWrap = document.createElement("div");
  loadingWrap.className = "message-bot loading-container"; // Cambiamos/añadimos clase
  
  loadingWrap.innerHTML = `
    <span class="loading-text">Buscando evidencias</span>
    <div class="dots-wrapper">
      <span></span>
      <span></span>
      <span></span>
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
    const apiKey = "";

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "RAG-API-KEY": apiKey
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

    setTimeout(() => {
      loadingWrap.remove();
      appendBotMessage(resultado.answer, true); 

      if (resultado.evidences && resultado.evidences.length > 0) {
        renderEvidencesInLeftPanel(resultado.evidences);
    }
    }, 300);

  } catch (err) {
    console.error(err);

    if (loadingWrap && loadingWrap.parentNode) {
      loadingWrap.remove();
    }

    appendBotMessage("Ocurrió un error al enviar la consulta.");

  } finally {
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
    const pageNum = meta.page_number ? `Pág. ${meta.page_number}` : "";

    const divEvidence = document.createElement("div");
    divEvidence.className = "evidences evidence-cascade";
    
    divEvidence.style.animationDelay = `${index * 150}ms`;

    divEvidence.innerHTML = `
      <article class="work-card">
          <div class="work-meta">
              <div class="work-left">
                  <div class="work-text">
                      <div class="work-title">Evidencia #${index + 1}</div>
                      <div class="work-subtitle">${docId} - ${pageNum}</div>
                  </div>
              </div>
          </div>
      </article>
    `;
    container.appendChild(divEvidence);
  });
}


/* Eventos */
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
