class CapsuleBrainGUI {
  constructor(options = {}) {
    this.ws = null;
    this.isConnected = false;
    this.currentTheme = localStorage.getItem('theme') || 'dark';
    const stored = localStorage.getItem('autoScroll');
    this.autoScroll = stored === null ? true : stored === 'true';
    this.showTimestamps = localStorage.getItem('showTimestamps') === 'true' || false;
    this.fontSize = parseInt(localStorage.getItem('fontSize')) || 14;
    this.recognition = null;
    this.isRecording = false;
    this.uploadedFiles = [];

    // WebSocket reconnection settings with configurable defaults
    const defaultConfig = {
      reconnectAttempt: 0,
      maxReconnectAttempts: 10,
      baseDelayMs: 1000,
      maxDelayMs: 30000
    };

    // Merge provided options with defaults
    const wsConfig = { ...defaultConfig, ...options };
    this.reconnectAttempt = wsConfig.reconnectAttempt;
    this.maxReconnectAttempts = Math.max(1, parseInt(wsConfig.maxReconnectAttempts) || 10);
    this.baseDelayMs = Math.max(100, parseInt(wsConfig.baseDelayMs) || 1000);
    this.maxDelayMs = Math.max(this.baseDelayMs, parseInt(wsConfig.maxDelayMs) || 30000);

    this.init();
  }

  init() {
    this.setupWebSocket();
    this.setupEventListeners();
    this.setupTheme();
    this.setupVoiceRecognition();
    this.loadSettings();
    this.setupMarked();
  }

  setupWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    this.ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

    this.ws.onopen = () => {
      this.updateStatus("Connected", "online");
      this.isConnected = true;
      this.reconnectAttempt = 0; // Reset reconnection attempts on successful connection
      this.showNotification("Connected to Capsule Brain", "success");
    };

    this.ws.onclose = () => {
      this.updateStatus("Disconnected", "offline");
      this.isConnected = false;
      this.showNotification("Disconnected from server", "error");
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.updateStatus("Error", "offline");
      this.isConnected = false;
      this.scheduleReconnect();
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        this.handleMessage(msg);
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };
  }

  scheduleReconnect() {
    if (this.reconnectAttempt >= this.maxReconnectAttempts) {
      this.showNotification("Max reconnection attempts reached", "error");
      return;
    }

    // Calculate delay with exponential backoff and jitter
    const delay = Math.min(
      this.baseDelayMs * Math.pow(2, this.reconnectAttempt),
      this.maxDelayMs
    );
    const jitter = Math.random() * 1000; // Add up to 1 second of jitter
    const totalDelay = delay + jitter;

    this.reconnectAttempt++;

    setTimeout(() => {
      this.setupWebSocket();
    }, totalDelay);
  }

  handleMessage(msg) {
    switch (msg.type) {
      case "phi_update":
        this.updateHud(msg.payload);
        break;
      case "wiring_proposal":
        this.appendMessage("New self-wiring proposal received.", "assistant");
        break;
      case "agi_response":
        this.appendMessage(msg.payload.answer, "assistant");
        break;
      case "system_status":
        this.updateSystemStatus(msg.payload);
        break;
      case "tool_status":
        this.updateToolStatus(msg.payload);
        break;
      default:
        console.log('Unknown message type:', msg.type);
    }
  }

  setupEventListeners() {
    // Navigation tabs
    document.querySelectorAll(".nav-tab").forEach((tab) => {
      tab.addEventListener("click", () => this.switchTab(tab.dataset.panel));
    });

    // Chat input
    const chatInput = document.getElementById("chatInput");
    const sendButton = document.getElementById("sendButton");

    sendButton.addEventListener("click", () => this.sendChatMessage());

    chatInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.sendChatMessage();
      }
    });

    // Auto-resize textarea
    chatInput.addEventListener("input", () => {
      chatInput.style.height = "auto";
      chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + "px";
    });

    // File upload
    const fileEl = document.getElementById("fileUpload");
    fileEl.addEventListener("change", (e) => this.handleFileUpload(e));

    // Voice input
    const voiceBtn = document.getElementById("voiceInputBtn");
    voiceBtn.addEventListener("click", () => this.toggleVoiceRecording());

    // Clear chat
    const clearBtn = document.getElementById("clearChatBtn");
    clearBtn.addEventListener("click", () => this.clearChat());

    // Theme toggle
    const themeToggle = document.getElementById("themeToggle");
    themeToggle.addEventListener("click", () => this.toggleTheme());

    // Fullscreen toggle
    const fullscreenToggle = document.getElementById("fullscreenToggle");
    fullscreenToggle.addEventListener("click", () => this.toggleFullscreen());

    // Settings
    this.setupSettingsListeners();

    // Refresh system
    const refreshBtn = document.getElementById("refreshSystemBtn");
    refreshBtn.addEventListener("click", () => this.loadSystem());

    // Event delegation for remove file buttons
    document.addEventListener("click", (e) => {
      if (e.target.closest('.remove-file')) {
        const button = e.target.closest('.remove-file');
        const index = parseInt(button.dataset.index);
        this.removeFile(index);
      }
    });

    // Event delegation for approval buttons
    document.addEventListener("click", (e) => {
      if (e.target.closest('.approve, .deny')) {
        const button = e.target.closest('.approve, .deny');
        const action = button.dataset.action;
        const id = button.dataset.id;

        if (action === 'approve') {
          this.approveItem(id);
        } else if (action === 'deny') {
          this.denyItem(id);
        }
      }
    });
  }

  setupSettingsListeners() {
    const themeSelect = document.getElementById("themeSelect");
    const fontSize = document.getElementById("fontSize");
    const autoScroll = document.getElementById("autoScroll");
    const showTimestamps = document.getElementById("showTimestamps");

    if (themeSelect) {
      themeSelect.value = this.currentTheme;
      themeSelect.addEventListener("change", (e) => {
        this.currentTheme = e.target.value;
        this.setupTheme();
        localStorage.setItem('theme', this.currentTheme);
      });
    }

    if (fontSize) {
      fontSize.value = this.fontSize;
      fontSize.addEventListener("input", (e) => {
        this.fontSize = parseInt(e.target.value);
        document.documentElement.style.fontSize = this.fontSize + "px";
        document.getElementById("fontSizeValue").textContent = this.fontSize + "px";
        localStorage.setItem('fontSize', this.fontSize);
      });
    }

    if (autoScroll) {
      autoScroll.checked = this.autoScroll;
      autoScroll.addEventListener("change", (e) => {
        this.autoScroll = e.target.checked;
        localStorage.setItem('autoScroll', this.autoScroll);
      });
    }

    if (showTimestamps) {
      showTimestamps.checked = this.showTimestamps;
      showTimestamps.addEventListener("change", (e) => {
        this.showTimestamps = e.target.checked;
        localStorage.setItem('showTimestamps', this.showTimestamps);
      });
    }
  }

  setupTheme() {
    document.documentElement.setAttribute('data-theme', this.currentTheme);
    const themeIcon = document.querySelector("#themeToggle i");
    if (themeIcon) {
      themeIcon.className = this.currentTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
  }

  setupVoiceRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = false;
      this.recognition.interimResults = false;
      this.recognition.lang = 'en-US';

      this.recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        document.getElementById("chatInput").value = transcript;
        this.sendChatMessage();
      };

      this.recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        this.showNotification('Voice recognition error: ' + event.error, 'error');
        this.isRecording = false;
        this.updateVoiceButton();
      };

      this.recognition.onend = () => {
        this.isRecording = false;
        this.updateVoiceButton();
      };
    }
  }

  setupMarked() {
    if (window.marked) {
      window.marked.setOptions({
        highlight: function(code, lang) {
          if (window.hljs && lang && window.hljs.getLanguage(lang)) {
            try {
              return window.hljs.highlight(code, { language: lang }).value;
            } catch (err) {}
          }
          return code;
        },
        breaks: true,
        gfm: true
      });
    }
  }

  switchTab(panelName) {
    // Update active tab
    document.querySelector(".nav-tab.active").classList.remove("active");
    document.querySelector(`[data-panel="${panelName}"]`).classList.add("active");

    // Update active panel
    document.querySelector(".panel.active").classList.remove("active");
    document.getElementById(`${panelName}Panel`).classList.add("active");

    // Load panel-specific data
    switch (panelName) {
      case "system":
        this.loadSystem();
        this.loadApprovals();
        break;
      case "tools":
        this.loadTools();
        break;
      case "settings":
        this.loadSettings();
        break;
    }
  }

  async sendChatMessage() {
    const message = document.getElementById("chatInput").value.trim();
    const files = this.uploadedFiles;

    if (!message && files.length === 0) return;

    this.appendMessage(message || `[Attached: ${files.map(f => f.name).join(', ')}]`, "user");
    document.getElementById("chatInput").value = "";
    this.uploadedFiles = [];
    this.updateFilePreview();

    // Show typing indicator
    this.showTypingIndicator();

    try {
      if (files.length > 0) {
        const form = new FormData();
        form.append("q", message || "Document question");
        files.forEach(file => form.append("files", file));

        const resp = await fetch("/ask_with_document", {
          method: "POST",
          body: form,
        });

        if (!resp.ok) throw new Error('Document upload failed');
        await resp.json();
      } else {
        const response = await fetch("/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ q: message }),
        });

        if (!response.ok) throw new Error('Request failed');
        await response.json();
      }
    } catch (e) {
      this.hideTypingIndicator();
      this.appendMessage("Error: " + e.message, "system");
    }
  }

  handleFileUpload(event) {
    const files = Array.from(event.target.files);
    this.uploadedFiles = [...this.uploadedFiles, ...files];
    this.updateFilePreview();
  }

  updateFilePreview() {
    const preview = document.getElementById("filePreview");
    preview.innerHTML = "";

    this.uploadedFiles.forEach((file, index) => {
      const item = document.createElement("div");
      item.className = "file-preview-item";
      item.innerHTML = `
        <i class="fas fa-file"></i>
        <span>${file.name}</span>
        <button class="remove-file" data-index="${index}">
          <i class="fas fa-times"></i>
        </button>
      `;
      preview.appendChild(item);
    });
  }

  removeFile(index) {
    this.uploadedFiles.splice(index, 1);
    this.updateFilePreview();
  }

  toggleVoiceRecording() {
    if (!this.recognition) {
      this.showNotification('Voice recognition not supported', 'error');
      return;
    }

    if (this.isRecording) {
      this.recognition.stop();
    } else {
      this.recognition.start();
      this.isRecording = true;
      this.updateVoiceButton();
    }
  }

  updateVoiceButton() {
    const btn = document.getElementById("voiceInputBtn");
    const icon = btn.querySelector("i");

    if (this.isRecording) {
      btn.classList.add("recording");
      icon.className = "fas fa-stop";
    } else {
      btn.classList.remove("recording");
      icon.className = "fas fa-microphone";
    }
  }

  clearChat() {
    if (confirm("Are you sure you want to clear the chat?")) {
      document.getElementById("chatMessages").innerHTML =
        '<div class="system-message">Chat cleared. Welcome to Capsule Brain Supreme AGI.</div>';
    }
  }

  toggleTheme() {
    this.currentTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
    this.setupTheme();
    localStorage.setItem('theme', this.currentTheme);
  }

  toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  }

  showTypingIndicator() {
    const messages = document.getElementById("chatMessages");
    const indicator = document.createElement("div");
    indicator.className = "message assistant typing-indicator";
    indicator.id = "typingIndicator";
    indicator.innerHTML = '<div class="loading"></div> <span>AGI is thinking...</span>';
    messages.appendChild(indicator);
    this.scrollToBottom();
  }

  hideTypingIndicator() {
    const indicator = document.getElementById("typingIndicator");
    if (indicator) {
      indicator.remove();
    }
  }

  appendMessage(content, sender) {
    this.hideTypingIndicator();

    const messages = document.getElementById("chatMessages");
    const msg = document.createElement("div");
    msg.className = `message ${sender}`;

    const timestamp = this.showTimestamps ?
      `<div class="message-timestamp">${new Date().toLocaleTimeString()}</div>` : '';

    const contentToRender = content || "...";
    let renderedContent;

    if (window.marked) {
      const parsed = window.marked.parse(contentToRender);
      // Sanitize the HTML if DOMPurify is available, otherwise use textContent for safety
      if (window.DOMPurify) {
        renderedContent = window.DOMPurify.sanitize(parsed);
      } else {
        // Fallback: create a temporary element and use textContent to avoid XSS
        const temp = document.createElement('div');
        temp.textContent = contentToRender;
        renderedContent = temp.innerHTML;
      }
    } else {
      // Fallback: use textContent to avoid XSS
      const temp = document.createElement('div');
      temp.textContent = contentToRender;
      renderedContent = temp.innerHTML;
    }

    msg.innerHTML = timestamp + renderedContent;

    messages.appendChild(msg);

    if (this.autoScroll) {
      this.scrollToBottom();
    }
  }

  scrollToBottom() {
    const messages = document.getElementById("chatMessages");
    messages.scrollTop = messages.scrollHeight;
  }

  updateStatus(text, klass) {
    document.getElementById("statusText").textContent = text;
    const dot = document.querySelector(".status-dot");
    dot.className = `status-dot ${klass}`;
  }

  updateHud(metrics) {
    if (!metrics) return;

    const phi = document.getElementById("phiValue");
    const glyphs = document.getElementById("glyphsValue");
    const memory = document.getElementById("memoryValue");
    const cpu = document.getElementById("cpuValue");

    if (phi && metrics.phi !== undefined) {
      phi.textContent = (+metrics.phi).toFixed(4);
      phi.style.animation = "pulse 0.5s ease";
    }

    if (glyphs && metrics.glyphs) {
      glyphs.textContent = (metrics.glyphs || []).join(" ") || "∅";
    }

    if (memory && metrics.memory !== undefined) {
      memory.textContent = (+metrics.memory).toFixed(1) + "%";
    }

    if (cpu && metrics.cpu !== undefined) {
      cpu.textContent = (+metrics.cpu).toFixed(1) + "%";
    }
  }

  updateSystemStatus(data) {
    this.updateHud(data);
  }

  updateToolStatus(data) {
    // Update tool status indicators
    console.log('Tool status update:', data);
  }

  async loadSystem() {
    try {
      const resp = await fetch("/state/summary");
      const data = await resp.json();
      this.updateHud(data.self_awareness_metrics);
    } catch (e) {
      console.error('Failed to load system data:', e);
    }
  }

  async loadApprovals() {
    try {
      const resp = await fetch("/approvals");
      const approvals = await resp.json();
      const container = document.getElementById("approvalQueue");
      const count = document.getElementById("queueCount");

      if (!container) return;

      container.innerHTML = "";
      count.textContent = `${approvals.length} items`;

      approvals.forEach((item) => {
        const div = document.createElement("div");
        div.className = "approval-item";

        // Create content span safely
        const contentSpan = document.createElement("span");
        contentSpan.textContent = item.content;

        // Create actions container
        const actionsDiv = document.createElement("div");
        actionsDiv.className = "approval-actions";

        // Create approve button
        const approveBtn = document.createElement("button");
        approveBtn.className = "approve";
        approveBtn.textContent = "Approve";
        approveBtn.setAttribute("data-action", "approve");
        approveBtn.setAttribute("data-id", item.id);

        // Create deny button
        const denyBtn = document.createElement("button");
        denyBtn.className = "deny";
        denyBtn.textContent = "Deny";
        denyBtn.setAttribute("data-action", "deny");
        denyBtn.setAttribute("data-id", item.id);

        // Assemble the elements
        actionsDiv.appendChild(approveBtn);
        actionsDiv.appendChild(denyBtn);
        div.appendChild(contentSpan);
        div.appendChild(actionsDiv);

        container.appendChild(div);
      });
    } catch (e) {
      console.error('Failed to load approvals:', e);
    }
  }

  async approveItem(id) {
    try {
      await fetch(`/approvals/${id}/approve`, { method: "POST" });
      this.loadApprovals();
      this.showNotification("Item approved", "success");
    } catch (e) {
      this.showNotification("Failed to approve item", "error");
    }
  }

  async denyItem(id) {
    try {
      await fetch(`/approvals/${id}/deny`, { method: "POST" });
      this.loadApprovals();
      this.showNotification("Item denied", "success");
    } catch (e) {
      this.showNotification("Failed to deny item", "error");
    }
  }

  async loadTools() {
    // Load available tools
    console.log('Loading tools...');
  }

  loadSettings() {
    // Load current settings
    console.log('Loading settings...');
  }

  showNotification(message, type = 'info') {
    const notification = document.createElement("div");
    notification.className = `notification ${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
      notification.remove();
    }, 3000);
  }
}

// Initialize the GUI when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  // Get configuration from window.APP_CONFIG or data attributes
  let config = {};

  if (window.APP_CONFIG && window.APP_CONFIG.websocket) {
    config = window.APP_CONFIG.websocket;
  } else {
    // Fallback to data attributes on the body element
    const body = document.body;
    if (body) {
      config = {
        reconnectAttempt: parseInt(body.dataset.reconnectAttempt) || 0,
        maxReconnectAttempts: parseInt(body.dataset.maxReconnectAttempts) || 10,
        baseDelayMs: parseInt(body.dataset.baseDelayMs) || 1000,
        maxDelayMs: parseInt(body.dataset.maxDelayMs) || 30000
      };
    }
  }

  window.gui = new CapsuleBrainGUI(config);
});

// Handle page visibility changes
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    // Page is hidden, pause updates
    console.log('Page hidden, pausing updates');
  } else {
    // Page is visible, resume updates
    console.log('Page visible, resuming updates');
    if (window.gui) {
      window.gui.loadSystem();
    }
  }
});

// Handle beforeunload
window.addEventListener("beforeunload", () => {
  if (window.gui && window.gui.ws) {
    window.gui.ws.close();
  }
});
