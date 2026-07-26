# JARVIS OS 🤖💻
### Enterprise-Grade AI Desktop Operating Layer for Windows

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/gkm563/jarvis-os)
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

### 1. Launch Master Application (GUI + Backend)
```bash
python launch.py
```

### 2. Run Automated Pytest Suite
```bash
python -m pytest tests/ -v
```

---

## 🧪 Interactive Test Suite & Scenarios

| Test ID | Natural Language Prompt / Command | Expected Agent & Behavior | Security Gate |
|:---|:---|:---|:---|
| **TEST-01** | *"Open Chrome, search AKTU results, and download marksheet"* | `browser_agent` navigates, searches, and extracts PDF result | 🟢 Standard |
| **TEST-02** | *"Create file test.txt in Downloads and scan for duplicates"* | `file_agent` writes file, creates versioned backup, runs SHA-256 scan | 🟢 Standard |
| **TEST-03** | *"Delete all files in Downloads folder"* | `file_agent` triggers `SensitiveActionGate` bulk delete policy | 🔴 **Human Confirmation Required** |
| **TEST-04** | *"Refactor main.py and run pytest suite"* | `coding_agent` parses AST, edits code, and executes test runner | 🟢 Standard |
| **TEST-05** | *"Open Notepad and Calculator side by side"* | `desktop_agent` launches apps and snaps window positions | 🟢 Standard |

---

## 🏛️ Project Architecture & Documentation

- [Architecture Blueprint](docs/architecture.md)
- [Developer & Plugin Guide](docs/developer_guide.md)
- [Implementation Plan](file:///C:/Users/Lenovo/.gemini/antigravity-ide/brain/8b87797d-7f4e-4e7f-a62c-538df7457ead/implementation_plan.md)
- [Walkthrough Report](file:///C:/Users/Lenovo/.gemini/antigravity-ide/brain/8b87797d-7f4e-4e7f-a62c-538df7457ead/walkthrough.md)

---

## 📄 License
Released under the MIT License.
