# JARVIS OS 🤖💻
### Enterprise-Grade AI Desktop Operating Layer for Windows

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/jarvis-os/jarvis-os)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

**JARVIS OS** is a full-stack, multi-agent AI operating system layer that sits on top of Microsoft Windows. It allows users to control applications, files, browsers, codebases, and enterprise workflows using natural spoken or typed instructions.

---

## 🌟 Key Features

- 🧠 **Multi-Agent Orchestration**: Intent decomposition into Directed Acyclic Graphs (DAGs) executed by 20 specialized domain agents.
- 🔒 **Zero-Trust Security**: AES-256-GCM encrypted secret vault, granular permission scopes, and mandatory human confirmation gates for sensitive actions.
- 👁️ **Vision & Self-Healing**: Screen capture, OCR text extraction, semantic UI classification, and automatic locator self-healing when application UIs change.
- 🎙️ **Offline Voice Assistant**: Speech-to-text via Whisper, Edge-TTS audio synthesis, and wake-word spotting ("Hey Jarvis").
- 📁 **Safe File System Agent**: Safe CRUD, SHA-256 duplicate scanning, versioned backups, and safety threshold guardrails.
- 🌐 **Browser Automation**: Playwright-powered navigation, form filling, file downloads, and tab/cookie management.
- 💻 **AI Coding Agent**: Refactoring, docstring generation, test runner execution, and Git/GitHub automation.
- ⚡ **FastAPI Local Microservice**: REST API and WebSocket real-time telemetry streaming for UI overlays and companion apps.

---

## 🚀 Quick Start

### 1. Installation
```bash
# Clone repository
git clone https://github.com/jarvis-os/jarvis-os.git
cd jarvis-os

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
```bash
cp .env.example .env
```

### 3. Run Application
```bash
python -m jarvis.main
```

### 4. Run Test Suite
```bash
python -m pytest tests/ -v
```

---

## 🏛️ Project Architecture & Documentation

- [Architecture Blueprint](docs/architecture.md)
- [Developer & Plugin Guide](docs/developer_guide.md)
- [Implementation Plan](file:///C:/Users/Lenovo/.gemini/antigravity-ide/brain/8b87797d-7f4e-4e7f-a62c-538df7457ead/implementation_plan.md)

---

## 📄 License
Released under the MIT License.
