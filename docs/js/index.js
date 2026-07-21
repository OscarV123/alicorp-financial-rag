function getQueryParams() {
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

  return { topKValue, explicitWhere, modeValue };
}

function createLoadingMessage() {
  const loadingWrap = document.createElement("div");
  loadingWrap.className = "message-bot loading-container";
  
  loadingWrap.innerHTML = `
    <span class="loading-text">
      Buscando evidencias
    </span>
    <div class="dots-wrapper">
      <span></span>
      <span></span>
      <span></span>
    </div>
  `;
  
  chatArea.appendChild(loadingWrap);
  scrollToBottom();

  return loadingWrap;
}

async function sendQuery(question, { topKValue, explicitWhere, modeValue }) {

  const response = await fetch(`${API_BASE_URL}/query`, {
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

    const error = new Error(
      errorData.detail ||
      "Error en el pipeline del servidor."
    );

    error.status = response.status;

    throw error;
  }
  
  return await response.json();
}

function prepareSend(question) {
  isSending = true;
  appendUserMessage(question);

  if (typeof hideSuggestions === "function") hideSuggestions();

  ta.value = "";
  autoGrow();
  updateCharCount();

  sendBtn.disabled = true;
}

function finishSend() {
  isSending = false;
  sendBtn.disabled = false;
  ta.focus();
}

async function processBotResponse(response) {
  const messageId = `msg-${++evidenciaCounter}`;
  
  if (response.evidences && response.evidences.length > 0) {
    evidenciasMap.set(messageId, response.evidences);
  }

  await appendBotMessage(response.answer, true, messageId);

  if (response.evidences && response.evidences.length > 0) {
    renderEvidencesInLeftPanel(response.evidences);
  }
}

async function handleSend() {

  if (isSending) return;

  enforceMaxChars();

  const question = getNormalized();

  if (ta.value !== question) ta.value = question;
  
  autoGrow();
  updateCharCount();

  if (!question) return;

  prepareSend(question);

  const loadingWrap = createLoadingMessage();

  const { topKValue, explicitWhere, modeValue } = getQueryParams();

  try {
    const resultado = await sendQuery(question, { topKValue, explicitWhere, modeValue });

    loadingWrap.classList.add("fade-out");

    setTimeout(async () => {
      loadingWrap.remove();

      await processBotResponse(resultado);

      finishSend();
    }, 300);

  } catch (err) {
    loadingWrap?.remove();

    let mensaje = "Ocurrió un error al enviar la consulta.";

    if (err instanceof TypeError && err.message.includes("Failed to fetch")) {
      mensaje = "No se pudo conectar con el servidor.";
    } else if (err.status === 429) {
      mensaje = "Has alcanzado el límite de consultas permitido: 20 por minuto o 70 por día.";
    }

    await appendBotMessage(mensaje);

    finishSend();
  }
}