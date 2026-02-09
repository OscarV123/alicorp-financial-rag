const ta = document.getElementById("question");
const counter = document.getElementById("counter");
const sendBtn = document.getElementById("send-btn");

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

function preventOverflow(e) {
  const n = getNormalized();

  const allowedKeys = [
    "Backspace", "Delete", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown",
    "Home", "End", "Tab"
  ];
  if (allowedKeys.includes(e.key) || e.ctrlKey || e.metaKey) return;

  if (n.length >= MAX_CHARS) e.preventDefault();
}

async function handleSend() {
  const question = getNormalized();

  if (ta.value !== question) ta.value = question;

  autoGrow();
  updateCharCount();

  if (!question) return;

  sendBtn.disabled = true;

  try {
    // TODO: reemplaza por tu fetch real
    // await fetch("/query", { method:"POST", headers:{...}, body: JSON.stringify({ question }) });

    console.log("Enviando:", question);

    ta.value = "";
    autoGrow();
    updateCharCount();
  } catch (err) {
    console.error(err);
  } finally {
    sendBtn.disabled = false;
    ta.focus();
  }
}

/* Eventos */
ta.addEventListener("keydown", (e) => {
  preventOverflow(e);

  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
});

ta.addEventListener("input", () => {
  autoGrow();
  updateCharCount();
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
});
