"""Floating sidebar chat widget for CRISPI plan review notebooks."""

import anywidget
import traitlets


class ChatWidget(anywidget.AnyWidget):
    """Floating sidebar chat widget with streaming markdown support.

    Renders as a collapsible panel fixed to the right edge of the viewport.
    Supports streaming assistant responses with inline markdown rendering
    (no CDN — regex-based, safe for marimo iframe CSP).

    Usage::

        widget = ChatWidget()

        @widget.observe("pending_message", names=["value"])
        def on_message(change):
            user_text = change["new"]
            if not user_text:
                return
            widget.is_streaming = True
            for chunk in my_llm_stream(user_text):
                widget.response_stream = widget.response_stream + chunk
            widget.messages = widget.messages + [
                {"role": "assistant", "content": widget.response_stream}
            ]
            widget.response_stream = ""
            widget.is_streaming = False
    """

    messages = traitlets.List([]).tag(sync=True)
    pending_message = traitlets.Unicode("").tag(sync=True)
    response_stream = traitlets.Unicode("").tag(sync=True)
    is_streaming = traitlets.Bool(False).tag(sync=True)
    is_sidebar = traitlets.Bool(True).tag(sync=True)

    _esm = """
    function render({ model, el }) {

      // ── Theme detection (same pattern as dagre_widget.py) ─────────────────
      function getTheme() {
        const root = document.documentElement;
        const mode = root.getAttribute("data-color-mode")
                  || root.getAttribute("data-theme")
                  || root.className;
        if (mode && (mode.includes("light") || mode === "light")) return "light";
        if (mode && (mode.includes("dark")  || mode === "dark"))  return "dark";
        const bg = getComputedStyle(document.body).backgroundColor;
        const m  = bg.match(/\\d+/g);
        if (m && m.length >= 3) {
          const lum = (parseInt(m[0]) * 299 + parseInt(m[1]) * 587 + parseInt(m[2]) * 114) / 1000;
          return lum > 128 ? "light" : "dark";
        }
        return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
      }

      // ── Inline markdown renderer (no CDN) ────────────────────────────────
      function renderMarkdown(text) {
        // Escape HTML first so injected content is safe.
        function esc(s) {
          return s.replace(/&/g,"&amp;")
                  .replace(/</g,"&lt;")
                  .replace(/>/g,"&gt;");
        }

        // Fenced code blocks  ```lang\\n...\\n```
        text = text.replace(/```[\\w]*\\n([\\s\\S]*?)```/g, (_, code) =>
          `<pre><code>${esc(code.trimEnd())}</code></pre>`
        );

        // Inline code  `code`
        text = text.replace(/`([^`]+)`/g, (_, code) =>
          `<code>${esc(code)}</code>`
        );

        // Bold  **text**
        text = text.replace(/\\*\\*([^*]+)\\*\\*/g, "<strong>$1</strong>");

        // Italic  *text*
        text = text.replace(/\\*([^*]+)\\*/g, "<em>$1</em>");

        // Unordered list items  - item  (convert to <li> wrapped in <ul>)
        text = text.replace(/((?:^- .+\\n?)+)/gm, (block) => {
          const items = block.trim().split("\\n")
            .map(line => `<li>${line.replace(/^- /, "")}</li>`)
            .join("");
          return `<ul>${items}</ul>`;
        });

        // Line breaks
        text = text.replace(/\\n/g, "<br>");

        return text;
      }

      // ── DOM structure ─────────────────────────────────────────────────────
      const sidebar = document.createElement("div");
      sidebar.className = "chat-sidebar";

      const header = document.createElement("div");
      header.className = "chat-header";

      const title = document.createElement("span");
      title.className = "chat-title";
      title.textContent = "Plan Chat";

      const toggleBtn = document.createElement("button");
      toggleBtn.className = "chat-toggle";
      toggleBtn.title = "Collapse";
      toggleBtn.innerHTML = "&#x276F;"; // ❯

      header.appendChild(title);
      header.appendChild(toggleBtn);

      const body = document.createElement("div");
      body.className = "chat-body";

      const messagesEl = document.createElement("div");
      messagesEl.className = "chat-messages";

      const typingEl = document.createElement("div");
      typingEl.className = "chat-typing";
      typingEl.innerHTML = "<span></span><span></span><span></span>";
      typingEl.style.display = "none";

      const inputArea = document.createElement("div");
      inputArea.className = "chat-input-area";

      const inputEl = document.createElement("textarea");
      inputEl.className = "chat-input";
      inputEl.placeholder = "Ask about this plan\\u2026";
      inputEl.rows = 2;

      const sendBtn = document.createElement("button");
      sendBtn.className = "chat-send";
      sendBtn.textContent = "Send";

      inputArea.appendChild(inputEl);
      inputArea.appendChild(sendBtn);

      body.appendChild(messagesEl);
      body.appendChild(typingEl);
      body.appendChild(inputArea);

      sidebar.appendChild(header);
      sidebar.appendChild(body);
      el.appendChild(sidebar);

      // ── State ──────────────────────────────────────────────────────────────
      let collapsed = false;
      let streamingBubble = null;

      // ── Helpers ───────────────────────────────────────────────────────────
      function scrollBottom() {
        messagesEl.scrollTop = messagesEl.scrollHeight;
      }

      function createBubble(role, htmlContent) {
        const wrap = document.createElement("div");
        wrap.className = `chat-msg chat-msg-${role}`;
        const bubble = document.createElement("div");
        bubble.className = "chat-bubble";
        bubble.innerHTML = htmlContent;
        wrap.appendChild(bubble);
        return { wrap, bubble };
      }

      function appendMessage(role, content) {
        const { wrap } = createBubble(role, renderMarkdown(content));
        messagesEl.appendChild(wrap);
        scrollBottom();
      }

      function applyTheme() {
        const dark = getTheme() === "dark";
        sidebar.setAttribute("data-theme", dark ? "dark" : "light");
      }

      function redrawMessages() {
        messagesEl.innerHTML = "";
        streamingBubble = null;
        const msgs = model.get("messages") || [];
        msgs.forEach(m => appendMessage(m.role, m.content));
      }

      // ── Initial render ────────────────────────────────────────────────────
      applyTheme();
      redrawMessages();

      // ── Model observers ───────────────────────────────────────────────────
      model.on("change:messages", () => {
        redrawMessages();
      });

      model.on("change:response_stream", () => {
        const chunk = model.get("response_stream") || "";
        if (!chunk) {
          // Stream reset — streaming bubble stays until messages update
          streamingBubble = null;
          return;
        }
        if (!streamingBubble) {
          // First chunk: create a new assistant bubble
          const { wrap, bubble } = createBubble("assistant", "");
          messagesEl.appendChild(wrap);
          streamingBubble = bubble;
        }
        // response_stream is cumulative; replace full bubble content each time
        streamingBubble.innerHTML = renderMarkdown(chunk);
        scrollBottom();
      });

      model.on("change:is_streaming", () => {
        const streaming = model.get("is_streaming");
        typingEl.style.display = streaming ? "flex" : "none";
        sendBtn.disabled = streaming;
        inputEl.disabled = streaming;
        if (streaming) scrollBottom();
      });

      // ── User interactions ─────────────────────────────────────────────────
      function sendMessage() {
        const text = inputEl.value.trim();
        if (!text) return;
        // Optimistically add user bubble
        appendMessage("user", text);
        inputEl.value = "";
        // Signal Python
        model.set("pending_message", text);
        model.save_changes();
      }

      sendBtn.addEventListener("click", sendMessage);

      inputEl.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          sendMessage();
        }
      });

      toggleBtn.addEventListener("click", () => {
        collapsed = !collapsed;
        body.style.display = collapsed ? "none" : "flex";
        toggleBtn.innerHTML = collapsed ? "&#x276E;" : "&#x276F;"; // \\u276e / \\u276f
        toggleBtn.title = collapsed ? "Expand" : "Collapse";
        sidebar.classList.toggle("collapsed", collapsed);
      });

      // ── Theme change observer ─────────────────────────────────────────────
      new MutationObserver(applyTheme).observe(document.documentElement,
        { attributes: true, attributeFilter: ["class", "data-theme", "data-color-mode", "style"] });
      new MutationObserver(applyTheme).observe(document.body,
        { attributes: true, attributeFilter: ["class", "style"] });
    }

    export default { render };
    """

    _css = """
    /* ── Host ──────────────────────────────────────────────────────────── */
    :host { display: block; }

    /* ── Sidebar container ─────────────────────────────────────────────── */
    .chat-sidebar {
      position: fixed;
      top: 0;
      right: 0;
      width: 360px;
      height: 100vh;
      display: flex;
      flex-direction: column;
      z-index: 1000;
      font-family: system-ui, -apple-system, sans-serif;
      font-size: 14px;
      box-shadow: -2px 0 12px rgba(0,0,0,0.15);
      transition: width 0.2s ease;
    }

    .chat-sidebar.collapsed {
      width: 44px;
    }

    /* ── Theme: light ──────────────────────────────────────────────────── */
    .chat-sidebar[data-theme="light"] {
      background: #ffffff;
      border-left: 1px solid #e0e0d8;
      color: #1a1a1a;
    }
    .chat-sidebar[data-theme="light"] .chat-header {
      background: #f5f5f0;
      border-bottom: 1px solid #e0e0d8;
    }
    .chat-sidebar[data-theme="light"] .chat-bubble {
      background: #f0f0ea;
      color: #1a1a1a;
    }
    .chat-sidebar[data-theme="light"] .chat-msg-user .chat-bubble {
      background: #3b82f6;
      color: #ffffff;
    }
    .chat-sidebar[data-theme="light"] .chat-input {
      background: #f5f5f0;
      border: 1px solid #d0d0c8;
      color: #1a1a1a;
    }
    .chat-sidebar[data-theme="light"] .chat-send {
      background: #3b82f6;
      color: #ffffff;
    }
    .chat-sidebar[data-theme="light"] .chat-send:hover { background: #2563eb; }
    .chat-sidebar[data-theme="light"] .chat-toggle {
      color: #555;
      background: transparent;
      border: none;
    }

    /* ── Theme: dark ───────────────────────────────────────────────────── */
    .chat-sidebar[data-theme="dark"] {
      background: #1e1e24;
      border-left: 1px solid #3a3a48;
      color: #e0ded8;
    }
    .chat-sidebar[data-theme="dark"] .chat-header {
      background: #16161c;
      border-bottom: 1px solid #3a3a48;
    }
    .chat-sidebar[data-theme="dark"] .chat-bubble {
      background: #2a2a35;
      color: #e0ded8;
    }
    .chat-sidebar[data-theme="dark"] .chat-msg-user .chat-bubble {
      background: #2563eb;
      color: #ffffff;
    }
    .chat-sidebar[data-theme="dark"] .chat-input {
      background: #2a2a35;
      border: 1px solid #3a3a48;
      color: #e0ded8;
    }
    .chat-sidebar[data-theme="dark"] .chat-send {
      background: #2563eb;
      color: #ffffff;
    }
    .chat-sidebar[data-theme="dark"] .chat-send:hover { background: #1d4ed8; }
    .chat-sidebar[data-theme="dark"] .chat-toggle {
      color: #aaa;
      background: transparent;
      border: none;
    }

    /* ── Header ────────────────────────────────────────────────────────── */
    .chat-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 12px;
      flex-shrink: 0;
    }

    .chat-title {
      font-weight: 600;
      font-size: 13px;
      letter-spacing: 0.02em;
      white-space: nowrap;
      overflow: hidden;
    }

    .collapsed .chat-title { display: none; }

    .chat-toggle {
      cursor: pointer;
      font-size: 16px;
      padding: 2px 4px;
      line-height: 1;
      border-radius: 3px;
      flex-shrink: 0;
    }
    .chat-toggle:hover { opacity: 0.7; }

    /* ── Body ──────────────────────────────────────────────────────────── */
    .chat-body {
      display: flex;
      flex-direction: column;
      flex: 1;
      overflow: hidden;
    }

    .collapsed .chat-body { display: none; }

    /* ── Messages ──────────────────────────────────────────────────────── */
    .chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .chat-msg {
      display: flex;
    }

    .chat-msg-user {
      justify-content: flex-end;
    }

    .chat-msg-assistant {
      justify-content: flex-start;
    }

    .chat-bubble {
      max-width: 85%;
      padding: 8px 12px;
      border-radius: 12px;
      line-height: 1.5;
      word-break: break-word;
    }

    .chat-msg-user .chat-bubble {
      border-bottom-right-radius: 3px;
    }

    .chat-msg-assistant .chat-bubble {
      border-bottom-left-radius: 3px;
    }

    .chat-bubble code {
      font-family: ui-monospace, "Cascadia Code", monospace;
      font-size: 12px;
      background: rgba(0,0,0,0.15);
      padding: 1px 4px;
      border-radius: 3px;
    }

    .chat-bubble pre {
      margin: 6px 0;
      padding: 8px;
      border-radius: 6px;
      background: rgba(0,0,0,0.2);
      overflow-x: auto;
    }

    .chat-bubble pre code {
      background: none;
      padding: 0;
    }

    .chat-bubble ul {
      margin: 4px 0;
      padding-left: 18px;
    }

    /* ── Typing indicator ──────────────────────────────────────────────── */
    .chat-typing {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 6px 16px;
      flex-shrink: 0;
    }

    .chat-typing span {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: currentColor;
      opacity: 0.4;
      animation: chat-bounce 1.2s infinite ease-in-out;
    }

    .chat-typing span:nth-child(2) { animation-delay: 0.2s; }
    .chat-typing span:nth-child(3) { animation-delay: 0.4s; }

    @keyframes chat-bounce {
      0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
      40%            { transform: translateY(-4px); opacity: 1; }
    }

    /* ── Input area ────────────────────────────────────────────────────── */
    .chat-input-area {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: 10px 12px;
      flex-shrink: 0;
    }

    .chat-input {
      width: 100%;
      resize: none;
      border-radius: 8px;
      padding: 8px 10px;
      font-family: inherit;
      font-size: 13px;
      line-height: 1.4;
      outline: none;
      box-sizing: border-box;
    }

    .chat-input:focus {
      box-shadow: 0 0 0 2px rgba(59,130,246,0.4);
    }

    .chat-send {
      align-self: flex-end;
      padding: 7px 18px;
      border: none;
      border-radius: 7px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s ease;
    }

    .chat-send:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    /* ── Scrollbar (webkit) ────────────────────────────────────────────── */
    .chat-messages::-webkit-scrollbar { width: 5px; }
    .chat-messages::-webkit-scrollbar-thumb {
      background: rgba(128,128,128,0.3);
      border-radius: 3px;
    }

    /* ── Narrow viewport: collapse automatically ───────────────────────── */
    @media (max-width: 480px) {
      .chat-sidebar { width: 100vw; height: 50vh; top: auto; bottom: 0; }
    }
    """
