"""
JARVIS - Simple AI Assistant
Run: python jarvis.py   OR   double-click START.bat

Type karo ya mic dabao — JARVIS samjhega, sochega, aur jo kahe wo karega.
"""

import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox
import threading
import subprocess
import webbrowser
import os
import time
import re
import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
def load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("GROQ_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"):
        if k not in env and os.environ.get(k):
            env[k] = os.environ[k]
    return env


def save_api_key(key: str):
    lines = []
    found = False
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("GROQ_API_KEY="):
                lines.append(f"GROQ_API_KEY={key}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"GROQ_API_KEY={key}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ─────────────────────────────────────────────
# VOICE: Windows SAPI (speak + listen)
# ─────────────────────────────────────────────
def speak(text: str):
    clean = re.sub(r"[✅❌⚠️🔊🔉🔇📸🤖🧑●•→✓]", "", text)
    clean = re.sub(r"\n+", ". ", clean).strip()
    if not clean:
        return
    try:
        import win32com.client
        sp = win32com.client.Dispatch("SAPI.SpVoice")
        sp.Speak(clean[:400])
    except Exception:
        pass


def listen_voice(timeout_sec: int = 8) -> str:
    """Windows built-in speech recognition — koi extra install nahi."""
    ps = f"""
Add-Type -AssemblyName System.Speech
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
$engine.SetInputToDefaultAudioDevice()
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$engine.LoadGrammar($grammar)
try {{
    $r = $engine.Recognize([TimeSpan]::FromSeconds({timeout_sec}))
    if ($r) {{ Write-Output $r.Text }}
}} catch {{ }}
"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=timeout_sec + 5,
        )
        return (r.stdout or "").strip()
    except Exception:
        return ""


# ─────────────────────────────────────────────
# ACTIONS: Jo JARVIS actually kar sakta hai
# ─────────────────────────────────────────────
def open_app(name: str) -> str:
    n = name.lower().strip()
    app_map = {
        "chrome": "chrome", "google chrome": "chrome",
        "notepad": "notepad", "calculator": "calc", "calc": "calc",
        "paint": "mspaint", "word": "winword", "excel": "excel",
        "powerpoint": "powerpnt", "vlc": "vlc",
        "whatsapp": "WhatsApp", "telegram": "telegram",
        "vs code": "code", "vscode": "code", "visual studio code": "code",
        "task manager": "taskmgr", "file explorer": "explorer",
        "explorer": "explorer", "spotify": "spotify",
        "settings": "ms-settings:", "camera": "microsoft.windows.camera:",
        "discord": "discord", "zoom": "zoom",
    }
    exe = app_map.get(n, n)
    if "ms-" in exe or "microsoft." in exe:
        webbrowser.open(exe)
    else:
        subprocess.Popen(exe, shell=True)
    return f"{name.title()} khol diya."


def close_app(name: str) -> str:
    n = name.lower().strip()
    exe_map = {
        "chrome": "chrome.exe", "notepad": "notepad.exe",
        "calc": "calculator.exe", "calculator": "calculator.exe",
        "paint": "mspaint.exe", "word": "winword.exe",
        "excel": "excel.exe", "vlc": "vlc.exe", "code": "code.exe",
        "vs code": "code.exe", "spotify": "spotify.exe",
    }
    exe = exe_map.get(n, n + ".exe")
    r = subprocess.run(f"taskkill /f /im {exe}", shell=True, capture_output=True)
    return f"{name.title()} band kar diya." if r.returncode == 0 else f"{name.title()} chal nahi raha tha."


def search_web(query: str) -> str:
    webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
    return f"Google pe search kiya: '{query}'"


def open_youtube(query: str = None) -> str:
    if query:
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
        return f"YouTube pe search kiya: '{query}'"
    webbrowser.open("https://www.youtube.com")
    return "YouTube khol diya."


def open_site(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"{url} khol diya."


def take_screenshot() -> str:
    try:
        from PIL import ImageGrab
        path = os.path.join(os.path.expanduser("~"), "Desktop", f"ss_{int(time.time())}.png")
        ImageGrab.grab().save(path)
        return f"Screenshot Desktop pe save: {os.path.basename(path)}"
    except Exception as e:
        return f"Screenshot nahi le paya: {e}"


def volume_action(action: str) -> str:
    codes = {"up": 175, "down": 174, "mute": 173}
    code = codes.get(action, 175)
    subprocess.run(
        f'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]{code})"',
        shell=True,
    )
    msgs = {"up": "Volume badha diya.", "down": "Volume ghata diya.", "mute": "Mute kar diya."}
    return msgs.get(action, "Done.")


def get_datetime() -> str:
    now = datetime.now()
    return f"Abhi {now.strftime('%I:%M %p')} baj rahe hain. Aaj {now.strftime('%A, %d %B %Y')} hai."


def lock_pc() -> str:
    subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
    return "Screen lock kar diya."


def shutdown_pc(cancel: bool = False) -> str:
    if cancel:
        subprocess.run("shutdown /a", shell=True)
        return "Shutdown cancel kar diya."
    subprocess.run("shutdown /s /t 30", shell=True)
    return "30 seconds mein PC band hoga. Rokne ke liye bolo 'shutdown cancel'."


def run_terminal(cmd: str) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        out = (r.stdout or r.stderr or "").strip()
        return out[:500] if out else "Command run ho gaya."
    except subprocess.TimeoutExpired:
        return "Command timeout ho gaya."
    except Exception as e:
        return f"Error: {e}"


def execute_tool(name: str, args: dict) -> str:
    try:
        if name == "open_app":
            return open_app(args.get("name", ""))
        if name == "close_app":
            return close_app(args.get("name", ""))
        if name == "search_web":
            return search_web(args.get("query", ""))
        if name == "open_youtube":
            return open_youtube(args.get("query"))
        if name == "open_website":
            return open_site(args.get("url", ""))
        if name == "screenshot":
            return take_screenshot()
        if name == "volume":
            return volume_action(args.get("action", "up"))
        if name == "get_time":
            return get_datetime()
        if name == "lock_screen":
            return lock_pc()
        if name == "shutdown_pc":
            return shutdown_pc(args.get("cancel", False))
        if name == "run_command":
            return run_terminal(args.get("command", ""))
        return f"Unknown action: {name}"
    except Exception as e:
        return f"Action fail: {e}"


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Koi application kholo — Chrome, Notepad, Calculator, VS Code, etc.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "App ka naam"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_app",
            "description": "Koi chal rahi application band karo.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Google pe kuch search karo aur browser mein kholo.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_youtube",
            "description": "YouTube kholo ya kuch search karo.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Optional search query"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_website",
            "description": "Koi website URL kholo.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description": "Screen ka screenshot lo.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "volume",
            "description": "Volume control — up, down, ya mute.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["up", "down", "mute"]},
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Current time aur date batao.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lock_screen",
            "description": "PC screen lock karo.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shutdown_pc",
            "description": "PC shutdown karo ya cancel karo.",
            "parameters": {
                "type": "object",
                "properties": {"cancel": {"type": "boolean", "description": "True = shutdown roko"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Terminal/CMD command chalao.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
]

SYSTEM_PROMPT = """Tu JARVIS hai — user ka personal AI assistant Windows PC pe.

Tera kaam:
1. User se Hinglish mein baat karo (Hindi + English mix, jaise dost se).
2. Logical aur critical soch — seedha, smart jawab do. Bakwas mat karo.
3. User jo kahe WO KARO — apps kholo, search karo, commands chalao. Tool use karo jab action chahiye.
4. Agar sirf sawaal hai (explain, discuss, advice) to tool mat use karo — seedha jawab do.
5. Chhota jawab prefer karo — 2-4 sentences. Lambi speech mat likho.
6. Agar user galat soch raha ho to politely sahi raasta dikhao (critical thinking).
7. Sensitive actions (shutdown, delete) pe pehle confirm karo.

Tu smart, helpful, aur obedient hai. User ki baat sun, samajh, aur karo."""


# ─────────────────────────────────────────────
# BRAIN: AI + fallback rules
# ─────────────────────────────────────────────
class Brain:
    def __init__(self):
        self.env = load_env()
        self.history: list[dict] = []
        self.api_key = self.env.get("GROQ_API_KEY") or self.env.get("OPENAI_API_KEY", "")

    def set_key(self, key: str):
        self.api_key = key.strip()
        save_api_key(self.api_key)

    def has_ai(self) -> bool:
        return bool(self.api_key)

    def _groq_request(self, messages: list, tools=None) -> dict | None:
        if not self.api_key:
            return None
        body = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "max_tokens": 600,
            "temperature": 0.7,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"

        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "JARVIS/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            err = e.read().decode() if e.fp else str(e)
            if "401" in str(e.code) or "invalid" in err.lower():
                return {"error": "API key galat hai. Settings se sahi key daalo."}
            return {"error": f"AI error: {err[:200]}"}
        except Exception as e:
            return {"error": str(e)}

    def think(self, user_text: str) -> str:
        if re.search(r"\b(bye|goodbye|alvida|exit|quit|close jarvis|band karo jarvis)\b", user_text.lower()):
            return "GOODBYE_SIGNAL"

        if self.has_ai():
            result = self._ai_think(user_text)
            if result:
                return result

        return self._rule_think(user_text)

    def _ai_think(self, user_text: str) -> str | None:
        self.history.append({"role": "user", "content": user_text})
        if len(self.history) > 20:
            self.history = self.history[-20:]

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history

        for _ in range(3):
            data = self._groq_request(messages, tools=TOOL_DEFINITIONS)
            if not data:
                return None
            if "error" in data:
                self.history.pop()
                return data["error"]

            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {})

            if msg.get("tool_calls"):
                messages.append(msg)
                action_results = []
                for tc in msg["tool_calls"]:
                    fn = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"].get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = execute_tool(fn, args)
                    action_results.append(result)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    })

                data2 = self._groq_request(messages)
                if data2 and "choices" in data2:
                    reply = data2["choices"][0]["message"].get("content", "")
                    if reply:
                        self.history.append({"role": "assistant", "content": reply})
                        return reply
                combined = " ".join(action_results)
                self.history.append({"role": "assistant", "content": combined})
                return combined

            reply = msg.get("content", "")
            if reply:
                self.history.append({"role": "assistant", "content": reply})
                return reply
            break

        self.history.pop()
        return None

    def _rule_think(self, text: str) -> str:
        t = text.lower().strip()

        if re.search(r"\b(hello|hi|hey|salam|namaste|kaise ho|kya hal)\b", t):
            extra = ""
            if not self.has_ai():
                extra = (
                    "\n\nTip: Groq API key daalo (free) taaki main aur smart ho jaaun.\n"
                    "Settings button dabao → key paste karo → console.groq.com se free lo."
                )
            return f"Walaikum Assalam! Main JARVIS hoon. Kya karna hai? Bol seedha.{extra}"

        if re.search(r"\b(time|baje|kitne baj|date|aaj kya din)\b", t):
            return get_datetime()

        if re.search(r"\b(help|madad|kya kar sakta)\b", t):
            return (
                "Main kar sakta hoon:\n"
                "• Apps kholo/band karo — 'Chrome kholo'\n"
                "• Search — 'Python kya hai search karo'\n"
                "• YouTube — 'YouTube pe Arijit Singh'\n"
                "• Screenshot, volume, time, lock screen\n"
                "• Baat-cheet — kuch bhi puchho!\n\n"
                "Mic button se bolo ya type karo."
            )

        if "youtube" in t:
            m = re.search(r"youtube\s*(?:pe|par|mein|search|open|play)?\s*(.+)?", t)
            q = m.group(1).strip() if m and m.group(1) else None
            return open_youtube(q)

        m = re.search(r"(?:run:|terminal:|cmd:|chala)\s*(.+)", t)
        if m:
            return run_terminal(m.group(1).strip())

        m = re.search(r"(?:close|band karo|band)\s+(.+)", t)
        if m:
            return close_app(m.group(1).strip())

        m = re.search(r"(?:open|kholo|khol|start|launch|chalo)\s+(.+)", t)
        if m:
            target = re.sub(r"\b(please|karo|do|mujhe)\b", "", m.group(1)).strip()
            if re.search(r"\.(com|in|org|net|io)\b", target):
                return open_site(target)
            return open_app(target)

        m = re.search(r"(?:search|google|dhundho|find)\s+(.+)", t)
        if m:
            return search_web(m.group(1).strip())

        if re.search(r"\b(screenshot|screen capture)\b", t):
            return take_screenshot()

        if re.search(r"\b(volume|awaaz|sound)\b", t):
            if re.search(r"\b(up|barhao|tez)\b", t):
                return volume_action("up")
            if re.search(r"\b(down|ghata|kam)\b", t):
                return volume_action("down")
            if re.search(r"\b(mute|chup)\b", t):
                return volume_action("mute")

        if re.search(r"\b(lock|lock screen)\b", t):
            return lock_pc()

        if re.search(r"\b(shutdown|pc band|computer band)\b", t):
            return shutdown_pc()

        return (
            "Samajh gaya, lekin AI brain abhi connect nahi hai.\n"
            "Settings → Groq API key daalo (free, 2 minute mein).\n"
            "Tab main properly baat karunga aur jo kahe wo karunga."
        )


# ─────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────
class JarvisApp:
    def __init__(self):
        self.brain = Brain()
        self.listening = False

        self.root = tk.Tk()
        self.root.title("JARVIS — AI Assistant")
        self.root.geometry("720x620")
        self.root.configure(bg="#0D1117")
        self.root.resizable(True, True)

        self._build_ui()
        self._welcome()
        if not self.brain.has_ai():
            self.root.after(500, self._prompt_api_key)
        self.root.mainloop()

    def _welcome(self):
        mode = "AI Brain ON" if self.brain.has_ai() else "Basic Mode (API key add karo)"
        self._add("JARVIS", (
            f"Assalamu Alaikum! Main JARVIS hoon. [{mode}]\n\n"
            "Seedha bolo jaise dost se:\n"
            "→ 'Chrome kholo'\n"
            "→ 'AI kya hai, samjhao'\n"
            "→ 'YouTube pe song'\n"
            "→ 'time kya hai'\n\n"
            "Mic dabao bolne ke liye. Main sununga, sochenga, aur karunga."
        ))

    def _prompt_api_key(self):
        if messagebox.askyesno(
            "JARVIS Setup",
            "Smart AI brain ke liye Groq API key chahiye (100% FREE).\n\n"
            "1. console.groq.com pe jao\n"
            "2. Free account banao\n"
            "3. API key copy karo\n\n"
            "Ab key daaloge?",
        ):
            self._settings()

    def _settings(self):
        key = simpledialog.askstring(
            "Groq API Key",
            "Apni Groq API key paste karo:\n(free — console.groq.com)",
            show="*",
        )
        if key and key.strip():
            self.brain.set_key(key.strip())
            self._add("JARVIS", "API key save ho gayi! Ab main properly smart hoon. Kuch bolo!")
            messagebox.showinfo("Done", "JARVIS AI brain connected!")

    def _build_ui(self):
        title_bar = tk.Frame(self.root, bg="#161B22", height=50)
        title_bar.pack(fill="x")

        tk.Label(
            title_bar, text="JARVIS — Your AI Assistant",
            font=("Segoe UI", 14, "bold"), bg="#161B22", fg="#58A6FF",
        ).pack(side="left", padx=15, pady=12)

        self.status_label = tk.Label(
            title_bar,
            text="● AI Ready" if self.brain.has_ai() else "● Basic Mode",
            font=("Segoe UI", 10), bg="#161B22",
            fg="#3FB950" if self.brain.has_ai() else "#D29922",
        )
        self.status_label.pack(side="right", padx=10)

        tk.Button(
            title_bar, text="Settings", font=("Segoe UI", 9),
            bg="#21262D", fg="#8B949E", relief="flat", padx=8, pady=4,
            cursor="hand2", command=self._settings,
        ).pack(side="right", padx=5)

        chat_frame = tk.Frame(self.root, bg="#0D1117")
        chat_frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        self.chat = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, font=("Segoe UI", 12),
            bg="#0D1117", fg="#E6EDF3", insertbackground="white",
            relief="flat", padx=12, pady=10, state="disabled",
            selectbackground="#264F78",
        )
        self.chat.pack(fill="both", expand=True)
        self.chat.tag_config("jarvis", foreground="#58A6FF")
        self.chat.tag_config("user", foreground="#3FB950")
        self.chat.tag_config("time", foreground="#484F58")
        self.chat.tag_config("divider", foreground="#21262D")

        bottom = tk.Frame(self.root, bg="#161B22", pady=10)
        bottom.pack(fill="x", padx=10, pady=8)

        self.mic_btn = tk.Button(
            bottom, text="Mic", font=("Segoe UI", 14),
            bg="#8957E5", fg="white", relief="flat", padx=12, pady=8,
            cursor="hand2", activebackground="#A371F7",
            command=self._toggle_mic,
        )
        self.mic_btn.pack(side="left", padx=(8, 4))

        self.entry = tk.Entry(
            bottom, font=("Segoe UI", 13), bg="#21262D", fg="#E6EDF3",
            insertbackground="white", relief="flat", bd=0,
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=10, padx=8)
        self.entry.bind("<Return>", lambda e: self._send())
        self.entry.focus()

        tk.Button(
            bottom, text="Send", font=("Segoe UI", 12, "bold"),
            bg="#238636", fg="white", relief="flat", padx=16, pady=8,
            cursor="hand2", activebackground="#2EA043",
            command=self._send,
        ).pack(side="right", padx=(0, 8))

        chips = tk.Frame(self.root, bg="#0D1117")
        chips.pack(fill="x", padx=10, pady=(0, 8))
        for label, cmd in [
            ("Chrome", "Chrome kholo"), ("YouTube", "YouTube kholo"),
            ("Time", "time kya hai"), ("Screenshot", "screenshot lo"),
            ("Help", "help"), ("AI?", "AI kya hai samjhao"),
        ]:
            tk.Button(
                chips, text=label, font=("Segoe UI", 10),
                bg="#21262D", fg="#8B949E", relief="flat", padx=10, pady=4,
                cursor="hand2", activebackground="#30363D",
                command=lambda c=cmd: self._quick(c),
            ).pack(side="left", padx=3)

    def _toggle_mic(self):
        if self.listening:
            return
        self.listening = True
        self.mic_btn.configure(text="...", bg="#DA3633")
        self._add("JARVIS", "Sun raha hoon... bolo!")
        threading.Thread(target=self._listen_and_send, daemon=True).start()

    def _listen_and_send(self):
        text = listen_voice(8)
        self.listening = False
        self.root.after(0, lambda: self.mic_btn.configure(text="Mic", bg="#8957E5"))
        if text:
            self.root.after(0, lambda: self._process(text))
        else:
            self.root.after(0, lambda: self._add("JARVIS", "Kuch sunai nahi diya. Dobara try karo."))

    def _quick(self, cmd):
        self.entry.delete(0, "end")
        self.entry.insert(0, cmd)
        self._send()

    def _send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self._process(text)

    def _process(self, text):
        self._add("Aap", text, user=True)
        self.status_label.configure(text="● Thinking...", fg="#D29922")
        threading.Thread(target=self._reply, args=(text,), daemon=True).start()

    def _reply(self, text):
        try:
            response = self.brain.think(text)
        except Exception as e:
            response = f"Kuch gadbad ho gayi: {e}"

        if response == "GOODBYE_SIGNAL":
            self.root.after(0, lambda: self._add("JARVIS", "Khuda Hafiz! Dobara aana."))
            self.root.after(1500, self.root.destroy)
            return

        self.root.after(0, lambda: self._add("JARVIS", response))
        self.root.after(0, lambda: self.status_label.configure(
            text="● AI Ready" if self.brain.has_ai() else "● Basic Mode",
            fg="#3FB950" if self.brain.has_ai() else "#D29922",
        ))
        threading.Thread(target=speak, args=(response,), daemon=True).start()

    def _add(self, sender, msg, user=False):
        self.chat.configure(state="normal")
        t = datetime.now().strftime("%I:%M %p")
        if self.chat.get("1.0", "end").strip():
            self.chat.insert("end", "\n" + "─" * 60 + "\n", "divider")
        tag = "user" if user else "jarvis"
        icon = "You" if user else "JARVIS"
        self.chat.insert("end", f"{icon} ", tag)
        self.chat.insert("end", f"[{t}]\n", "time")
        self.chat.insert("end", f"  {msg}\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")


if __name__ == "__main__":
    JarvisApp()
