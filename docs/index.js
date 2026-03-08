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
  let n = getNormalized();

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

function appendBotMessage(text) {
  const wrap = document.createElement("div");
  wrap.className = "message-bot";

  const p = document.createElement("p");
  p.className = "msg-text";
  p.textContent = text;

  wrap.appendChild(p);
  chatArea.appendChild(wrap);

  scrollToBottom();
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

  try {
    appendBotMessage("sssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssss");
  } catch (err) {
    console.error(err);
    appendBotMessage("Ocurrió un error al enviar la consulta.");
  } finally {
    sendBtn.disabled = false;
    ta.focus();
  }
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