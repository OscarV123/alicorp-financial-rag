const ta = document.getElementById("question");
const counter = document.getElementById("counter");
const MAX_CHARS = 500;
const MAX_HEIGHT = 160;
const composer = document.querySelector(".composer");
const suggestedQuestions = document.getElementById("suggested-questions");

function adjustSuggestionsPosition() {
  if (!composer || !suggestedQuestions) return;
  const composerHeight = composer.getBoundingClientRect().height;
  suggestedQuestions.style.bottom = `${composerHeight}px`;
}

function normalizeQuestion(text) {
  return text.replace(/\s+/g, " ").trim();
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

if (composer && suggestedQuestions) {
  const resizeObserver = new ResizeObserver(adjustSuggestionsPosition);
  resizeObserver.observe(composer);
  adjustSuggestionsPosition();
}

ta.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSend();
    return;
  }

  preventOverflow(e);
});

ta.addEventListener("input", () => {
  const hasText = ta.value.trim().length > 0;
  suggestedQuestions.classList.toggle("is-hidden", hasText);

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

window.addEventListener("load", () => {
  autoGrow();
  updateCharCount();
});