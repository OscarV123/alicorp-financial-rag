const sendBtn = document.getElementById("send-btn");
const chatArea = document.querySelector(".chat-area");
const evidenciasMap = new Map();
let evidenciaCounter = 0;
let isSending = false;

function scrollToBottom() {
  requestAnimationFrame(() => {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  });
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
    const esMobileOTablet = window.innerWidth <= 1700;

    if (esMobileOTablet && btnLeft && leftPanel && !leftPanel.classList.contains("is-open")) {
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

sendBtn.addEventListener("click", (e) => {
  e.preventDefault();
  handleSend();
});

window.addEventListener("load", () => {
  scrollToBottom(0);
});