# 🐺 Wolfclaw — AI Command Center

<p align="center">
  <img src="static/img/wolfclaw-logo.png" alt="Wolfclaw" width="120">
</p>

<p align="center">
  <strong>Your desktop AI assistant with full system control.</strong><br>
  Multi-model chat · Desktop automation · Remote SSH · Tool Console · Bot Army
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20Linux-blue" alt="Platform">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/version-2.0-blueviolet" alt="Version">
</p>

---

## ✨ Features

### 🤖 Multi-Model AI Chat
Chat with any LLM through a unified interface. Supported providers:
- **Nvidia NIM** — Llama 3.1 70B (Free!)
- **OpenAI** — GPT-4o
- **Anthropic** — Claude 3.5 Sonnet
- **DeepSeek** — Chat
- **Ollama** — Local models

### 🛠️ Tool Console
Execute 7 powerful tools directly from a visual GUI — no AI needed:

| Tool | Description |
|------|-------------|
| 🖥️ Terminal Command | Run PowerShell/Bash on your machine |
| 🔍 Web Search | DuckDuckGo search with top 5 results |
| 📸 Screenshot | One-click screen capture |
| 📄 Read Document | Extract text from PDF/TXT files |
| 🔗 SSH Command | Execute commands on remote servers |
| 🖱️ GUI Automation | Simulate keyboard typing, hotkeys, and mouse clicks |
| 🌍 Web Browser | Extract text content from any URL |

### 🪖 Bot Army — Telegram Deployment
Deploy your bots as Telegram workers. Start/stop individual bots, monitor live status with animated indicators, and manage your entire bot fleet from one dashboard.

### 🧠 Bot Profiles
Each bot has three customizable files:
- **SOUL.md** — Personality and system prompt
- **USER.md** — Your profile and context
- **MEMORY.md** — Auto-updated long-term memory

### 🔐 Remote Server Management
Full SSH client with password and PEM key authentication. Run commands on remote Linux servers directly from the dashboard.

### 📋 Activity Log
Live scrolling feed of all tool executions with success/error filtering.

### 🎨 Premium UI
Dark glassmorphism theme with gradient accents, animated status indicators, Inter font, and responsive card layouts.

---

## 🚀 Quick Start

```bash
git clone https://github.com/pravinamathew/wolfclaw.git
cd wolfclaw
pip install -r requirements.txt
python desktop_launcher.py
```

## 📦 Architecture

```
wolfclaw/
├── api/              # FastAPI backend
│   ├── main.py       # App entry + router registration
│   └── routes/       # Auth, Bots, Chat, Settings, Tools, Channels
├── core/             # Engine
│   ├── llm_engine.py # Multi-provider LLM router
│   ├── tools.py      # 7 tool implementations
│   └── bot_manager.py
├── static/           # Frontend SPA
│   ├── index.html    # Single-page app
│   ├── css/styles.css
│   ├── js/app.js
│   └── img/          # Generated branding assets
├── desktop_launcher.py  # PyWebView native window launcher
└── SOUL.md           # Default bot personality
```

## ⚠️ Legal Disclaimer

1. **For Educational & Personal Use**: This software is provided for educational and personal research purposes only.
2. **API Key Security**: API keys are stored locally in a SQLite database. Never share your `wolfclaw_local.db` or `.env` file.
3. **Third-Party ToS**: Users are responsible for complying with the Terms of Service of all third-party providers (OpenAI, Anthropic, Nvidia, Telegram, etc.).
4. **SSH Security**: The SSH client provides direct access to remote systems. Use with caution.
5. **No Warranty**: This software is provided "as is" under the MIT License, without warranty of any kind.

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  <sub>Crafted with 🐺 by <strong>Pravin A Mathew</strong></sub>
</p>
