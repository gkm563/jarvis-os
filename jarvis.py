"""
JARVIS - Simple AI Assistant
Run: python jarvis.py   OR   double-click START.bat

Boliye — JARVIS sunega, samjhega, aur jo kahenge wo karega.
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
# VOICE
# ─────────────────────────────────────────────
def speak(text: str, block: bool = False):
    clean = re.sub(r"[✅❌⚠️🔊🔉🔇📸🤖🧑●•→✓\[\]]", "", text)
    clean = re.sub(r"\n+", ". ", clean).strip()
    if not clean:
        return
    try:
        import win32com.client
        sp = win32com.client.Dispatch("SAPI.SpVoice")
        # Try Hindi voice if available, else default
        try:
            for v in sp.GetVoices().split(";;"):
                if "hi-" in v.lower() or "hindi" in v.lower():
                    idx = int(re.search(r"Attributes.*?(\d+)", v).group(1)) if re.search(r"ID=(\{[^}]+\})", v) else None
                    break
        except Exception:
            pass
        if block:
            sp.Speak(clean[:500], 0)  # SVSFDefault = 0, wait until done
        else:
            sp.Speak(clean[:500])
    except Exception:
        pass


def listen_voice(timeout_sec: int = 10) -> str:
    ps = rf"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech
$culture = New-Object System.Globalization.CultureInfo("en-IN")
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($culture)
$engine.SetInputToDefaultAudioDevice()
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$engine.LoadGrammar($grammar)
try {{
    $r = $engine.Recognize([TimeSpan]::FromSeconds({timeout_sec}))
    if ($r -and $r.Text) {{ Write-Output $r.Text.Trim() }}
}} catch [System.Exception] {{
    Write-Error $_.Exception.Message
}}
"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True, text=True, timeout=timeout_sec + 8,
            encoding="utf-8", errors="replace",
        )
        text = (r.stdout or "").strip()
        if text:
            return text
        err = (r.stderr or "").strip()
        if "audio" in err.lower() or "microphone" in err.lower():
            return ""
        return ""
    except subprocess.TimeoutExpired:
        return ""
    except Exception:
        return ""


# ─────────────────────────────────────────────
# ACTIONS
# ─────────────────────────────────────────────
def open_app(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r"\b(please|karo|do|mujhe|open|kholo|khol|app|application)\b", "", n).strip()

    commands = {
        "chrome": 'start "" "chrome"',
        "google chrome": 'start "" "chrome"',
        "notepad": "notepad",
        "calculator": "calc",
        "calc": "calc",
        "paint": "mspaint",
        "word": "start winword",
        "excel": "start excel",
        "vlc": 'start "" "vlc"',
        "vs code": 'start "" "code"',
        "vscode": 'start "" "code"',
        "visual studio code": 'start "" "code"',
        "task manager": "taskmgr",
        "file explorer": "explorer",
        "explorer": "explorer",
        "spotify": 'start "" "spotify"',
        "settings": "start ms-settings:",
        "camera": "start microsoft.windows.camera:",
        "whatsapp": 'start "" "WhatsApp"',
        "discord": 'start "" "discord"',
    }

    if "ms-" in n or "microsoft." in n:
        webbrowser.open(n)
        return f"{name} khol diya."

    cmd = commands.get(n)
    if cmd:
        subprocess.Popen(cmd, shell=True)
    else:
        subprocess.Popen(f'start "" "{name}"', shell=True)
    return f"{name.title()} khol diya."


def close_app(name: str) -> str:
    n = name.lower().strip()
    exe_map = {
        "chrome": "chrome.exe", "notepad": "notepad.exe",
        "calc": "CalculatorApp.exe", "calculator": "CalculatorApp.exe",
        "paint": "mspaint.exe", "word": "winword.exe",
        "excel": "excel.exe", "vlc": "vlc.exe", "code": "code.exe",
        "spotify": "spotify.exe",
    }
    exe = exe_map.get(n, n if n.endswith(".exe") else n + ".exe")
    r = subprocess.run(f"taskkill /f /im {exe} 2>nul", shell=True, capture_output=True)
    return f"{name.title()} band kar diya." if r.returncode == 0 else f"{name.title()} chal nahi raha tha."


def search_web(query: str) -> str:
    webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
    return f"Google pe search kiya: {query}"


def open_youtube(query: str = None) -> str:
    if query:
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
        return f"YouTube pe dhundha: {query}"
    webbrowser.open("https://www.youtube.com")
    return "YouTube khol diya."


def open_site(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Website khol di: {url}"


def take_screenshot() -> str:
    try:
        from PIL import ImageGrab
        path = os.path.join(os.path.expanduser("~"), "Desktop", f"ss_{int(time.time())}.png")
        ImageGrab.grab().save(path)
        return f"Screenshot save ho gaya Desktop pe."
    except Exception as e:
        return f"Screenshot fail: {e}"


def volume_action(action: str) -> str:
    codes = {"up": 175, "down": 174, "mute": 173}
    code = codes.get(action, 175)
    subprocess.run(
        f'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]{code})"',
        shell=True,
    )
    return {"up": "Volume badha diya.", "down": "Volume kam ki.", "mute": "Mute kar diya."}.get(action, "Done.")


def get_datetime() -> str:
    now = datetime.now()
    hour = now.hour
    if hour < 12:
        greet = "Good morning"
    elif hour < 17:
        greet = "Good afternoon"
    else:
        greet = "Good evening"
    return (
        f"{greet}! Abhi {now.strftime('%I:%M %p')} baj rahe hain. "
        f"Aaj {now.strftime('%A, %d %B %Y')} hai."
    )


def lock_pc() -> str:
    subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
    return "Screen lock ho gayi."


def shutdown_pc(cancel: bool = False) -> str:
    if cancel:
        subprocess.run("shutdown /a", shell=True)
        return "Shutdown cancel."
    subprocess.run("shutdown /s /t 30", shell=True)
    return "PC 30 second mein band hoga. Rokne ke liye bolo cancel shutdown."


def run_terminal(cmd: str) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        out = (r.stdout or r.stderr or "").strip()
        return out[:500] if out else "Command chal gayi."
    except subprocess.TimeoutExpired:
        return "Command timeout."
    except Exception as e:
        return f"Error: {e}"


def execute_tool(name: str, args: dict) -> str:
    try:
        actions = {
            "open_app": lambda: open_app(args.get("name", "")),
            "close_app": lambda: close_app(args.get("name", "")),
            "search_web": lambda: search_web(args.get("query", "")),
            "open_youtube": lambda: open_youtube(args.get("query")),
            "open_website": lambda: open_site(args.get("url", "")),
            "screenshot": take_screenshot,
            "volume": lambda: volume_action(args.get("action", "up")),
            "get_time": get_datetime,
            "lock_screen": lock_pc,
            "shutdown_pc": lambda: shutdown_pc(args.get("cancel", False)),
            "run_command": lambda: run_terminal(args.get("command", "")),
        }
        fn = actions.get(name)
        return fn() if fn else f"Unknown: {name}"
    except Exception as e:
        return f"Fail: {e}"


TOOL_DEFINITIONS = [
    {"type": "function", "function": {
        "name": "open_app",
        "description": "Open any app: Chrome, Notepad, Calculator, VS Code, WhatsApp, etc.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    }},
    {"type": "function", "function": {
        "name": "close_app",
        "description": "Close a running app.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    }},
    {"type": "function", "function": {
        "name": "search_web",
        "description": "Google search in browser.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "open_youtube",
        "description": "Open YouTube or search on YouTube.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "open_website",
        "description": "Open a website URL.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    }},
    {"type": "function", "function": {
        "name": "screenshot", "description": "Take screenshot.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "volume", "description": "Volume up/down/mute.",
        "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["up", "down", "mute"]}}, "required": ["action"]},
    }},
    {"type": "function", "function": {
        "name": "get_time", "description": "Tell current time and date.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "lock_screen", "description": "Lock PC screen.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "shutdown_pc", "description": "Shutdown PC or cancel shutdown.",
        "parameters": {"type": "object", "properties": {"cancel": {"type": "boolean"}}},
    }},
    {"type": "function", "function": {
        "name": "run_command", "description": "Run terminal command.",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
    }},
]

SYSTEM_PROMPT = """You are JARVIS — a personal AI assistant on Windows.

LANGUAGE RULES (IMPORTANT):
- Always reply in Hinglish — mix Hindi and English naturally like Indians talk daily.
- Example: "Theek hai sir, Chrome khol deta hoon." or "Haan bilkul, main samajh gaya."
- Greet warmly in both Hindi and English when user says hello.
- Keep replies short: 1-3 sentences max. User hears this spoken aloud.

BEHAVIOR:
- Listen carefully. Do EXACTLY what user asks.
- Use tools immediately when user wants an action (open app, search, youtube, screenshot, etc.)
- For questions only — answer directly, no tools needed.
- Think logically. Be helpful, obedient, smart.
- Never refuse simple tasks. Just do them.

When user says open/kholo/start something → use open_app tool immediately.
When user asks a question → answer in Hinglish directly."""


class Brain:
    def __init__(self):
        self.env = load_env()
        self.history: list[dict] = []
        self.api_key = self.env.get("GROQ_API_KEY", "")
        if self.api_key and not self.api_key.startswith("gsk_"):
            self.api_key = ""

    def set_key(self, key: str):
        self.api_key = key.strip()
        save_api_key(self.api_key)

    def has_ai(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("gsk_"))

    def verify_ai(self) -> tuple[bool, str]:
        if not self.has_ai():
            return False, "Groq API key missing. Settings se daalo."
        data = self._groq_request(
            [{"role": "user", "content": "Reply only: OK"}],
            tools=None,
        )
        if not data:
            return False, "Internet connection check karo."
        if "error" in data:
            return False, data["error"]
        return True, "Connected"

    def _groq_request(self, messages: list, tools=None) -> dict | None:
        if not self.api_key:
            return None
        body = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "max_tokens": 400,
            "temperature": 0.6,
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
                "User-Agent": "JARVIS/2.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            err = e.read().decode() if e.fp else str(e)
            if e.code in (401, 403):
                return {"error": "API key galat hai. Settings se sahi Groq key daalo."}
            return {"error": f"AI error ({e.code}): {err[:150]}"}
        except Exception as e:
            return {"error": f"Connection error: {e}"}

    def think(self, user_text: str) -> str:
        t = user_text.lower().strip()
        if re.search(r"\b(bye|goodbye|alvida|exit|quit|close jarvis|band karo jarvis)\b", t):
            return "GOODBYE_SIGNAL"

        if self.has_ai():
            result = self._ai_think(user_text)
            if result:
                return result

        return self._rule_think(user_text)

    def _ai_think(self, user_text: str) -> str | None:
        self.history.append({"role": "user", "content": user_text})
        if len(self.history) > 16:
            self.history = self.history[-16:]

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history

        for _ in range(4):
            data = self._groq_request(messages, tools=TOOL_DEFINITIONS)
            if not data:
                self.history.pop()
                return None
            if "error" in data:
                self.history.pop()
                return data["error"]

            msg = data["choices"][0]["message"]

            if msg.get("tool_calls"):
                messages.append(msg)
                results = []
                for tc in msg["tool_calls"]:
                    fn = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"].get("arguments") or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = execute_tool(fn, args)
                    results.append(result)
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

                data2 = self._groq_request(messages)
                if data2 and "choices" in data2:
                    reply = data2["choices"][0]["message"].get("content", "")
                    if reply:
                        self.history.append({"role": "assistant", "content": reply})
                        return reply
                combined = ". ".join(results)
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
            dt = get_datetime()
            return f"Walaikum Assalam! Hello! Main JARVIS hoon. {dt} Kya karna hai? Boliye!"
        if re.search(r"\b(time|baje|kitne baj|date)\b", t):
            return get_datetime()
        m = re.search(r"(?:open|kholo|khol|start|launch|chalo)\s+(.+)", t)
        if m:
            target = re.sub(r"\b(please|karo|do|mujhe)\b", "", m.group(1)).strip()
            if re.search(r"\.(com|in|org|net)\b", target):
                return open_site(target)
            return open_app(target)
        if "youtube" in t:
            m = re.search(r"youtube\s*(?:pe|par|mein|search|open|play)?\s*(.+)?", t)
            return open_youtube(m.group(1).strip() if m and m.group(1) else None)
        m = re.search(r"(?:search|google|dhundho|find)\s+(.+)", t)
        if m:
            return search_web(m.group(1).strip())
        if re.search(r"\b(screenshot)\b", t):
            return take_screenshot()
        return "AI connect nahi hai. Settings se Groq API key daalo, phir main sab karunga."


def get_greeting() -> str:
    now = datetime.now()
    h = now.hour
    if h < 12:
        en, hi = "Good morning", "Suprabhat"
    elif h < 17:
        en, hi = "Good afternoon", "Namaste"
    else:
        en, hi = "Good evening", "Shubh sandhya"
    return (
        f"Assalamu Alaikum! {en}! {hi}! "
        f"Main JARVIS hoon, aapka personal assistant. "
        f"Boliye kya karna hai — main sun raha hoon aur karunga."
    )


class JarvisApp:
    def __init__(self):
        self.brain = Brain()
        self.listening = False
        self.auto_listen = True
        self.speaking = False
        self.running = True

        self.root = tk.Tk()
        self.root.title("JARVIS — AI Assistant")
        self.root.geometry("740x640")
        self.root.configure(bg="#0D1117")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self.root.after(300, self._startup)
        self.root.mainloop()

    def _startup(self):
        ok, msg = self.brain.verify_ai()
        if ok:
            self.status_label.configure(text="● AI Connected", fg="#3FB950")
        else:
            self.status_label.configure(text="● " + msg[:40], fg="#F85149")
            if not self.brain.has_ai():
                self.root.after(800, self._settings)

        greeting = get_greeting()
        self._add("JARVIS", greeting)
        threading.Thread(target=self._speak_and_listen, args=(greeting,), daemon=True).start()

    def _speak_and_listen(self, text: str):
        self.speaking = True
        speak(text, block=True)
        self.speaking = False
        if self.auto_listen and self.running:
            self.root.after(500, self._auto_mic)

    def _auto_mic(self):
        if not self.listening and self.running and self.auto_listen:
            self._toggle_mic(auto=True)

    def _on_close(self):
        self.running = False
        self.root.destroy()

    def _settings(self):
        key = simpledialog.askstring(
            "Groq API Key (FREE)",
            "Groq API key paste karo:\nconsole.groq.com → free account → API Keys",
            show="*",
        )
        if key and key.strip():
            self.brain.set_key(key.strip())
            ok, msg = self.brain.verify_ai()
            if ok:
                self._add("JARVIS", "Perfect! AI brain connected. Ab kuch bolo!")
                self.status_label.configure(text="● AI Connected", fg="#3FB950")
                speak("Perfect! Ab main ready hoon. Boliye!", block=True)
            else:
                self._add("JARVIS", f"Key save hui lekin error: {msg}")
                messagebox.showerror("Error", msg)

    def _build_ui(self):
        bar = tk.Frame(self.root, bg="#161B22")
        bar.pack(fill="x")

        tk.Label(bar, text="JARVIS AI Assistant", font=("Segoe UI", 14, "bold"),
                 bg="#161B22", fg="#58A6FF").pack(side="left", padx=15, pady=12)

        self.auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            bar, text="Auto Listen", variable=self.auto_var,
            bg="#161B22", fg="#8B949E", selectcolor="#21262D",
            activebackground="#161B22", font=("Segoe UI", 9),
            command=lambda: setattr(self, "auto_listen", self.auto_var.get()),
        ).pack(side="right", padx=8)

        self.status_label = tk.Label(bar, text="● Starting...", font=("Segoe UI", 10),
                                      bg="#161B22", fg="#D29922")
        self.status_label.pack(side="right", padx=8)

        tk.Button(bar, text="Settings", font=("Segoe UI", 9), bg="#21262D", fg="#8B949E",
                  relief="flat", padx=8, command=self._settings).pack(side="right", padx=4)

        chat_frame = tk.Frame(self.root, bg="#0D1117")
        chat_frame.pack(fill="both", expand=True, padx=10, pady=8)

        self.chat = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, font=("Segoe UI", 12),
            bg="#0D1117", fg="#E6EDF3", relief="flat", padx=12, pady=10, state="disabled",
        )
        self.chat.pack(fill="both", expand=True)
        self.chat.tag_config("jarvis", foreground="#58A6FF")
        self.chat.tag_config("user", foreground="#3FB950")
        self.chat.tag_config("time", foreground="#484F58")

        bottom = tk.Frame(self.root, bg="#161B22", pady=10)
        bottom.pack(fill="x", padx=10, pady=8)

        self.mic_btn = tk.Button(
            bottom, text="🎤 Bolo", font=("Segoe UI", 13, "bold"),
            bg="#8957E5", fg="white", relief="flat", padx=14, pady=8,
            cursor="hand2", command=lambda: self._toggle_mic(auto=False),
        )
        self.mic_btn.pack(side="left", padx=(8, 4))

        self.entry = tk.Entry(bottom, font=("Segoe UI", 13), bg="#21262D", fg="#E6EDF3",
                               insertbackground="white", relief="flat")
        self.entry.pack(side="left", fill="x", expand=True, ipady=10, padx=8)
        self.entry.bind("<Return>", lambda e: self._send())
        self.entry.focus()

        tk.Button(bottom, text="Send ➤", font=("Segoe UI", 12, "bold"), bg="#238636", fg="white",
                  relief="flat", padx=16, pady=8, cursor="hand2", command=self._send).pack(side="right", padx=8)

        chips = tk.Frame(self.root, bg="#0D1117")
        chips.pack(fill="x", padx=10, pady=(0, 8))
        for label, cmd in [("Chrome", "Chrome kholo"), ("YouTube", "YouTube kholo"),
                           ("Time", "time batao"), ("Notepad", "Notepad kholo")]:
            tk.Button(chips, text=label, font=("Segoe UI", 10), bg="#21262D", fg="#8B949E",
                      relief="flat", padx=10, pady=4, cursor="hand2",
                      command=lambda c=cmd: self._quick(c)).pack(side="left", padx=3)

    def _toggle_mic(self, auto=False):
        if self.listening or self.speaking:
            return
        self.listening = True
        self.mic_btn.configure(text="🔴 Sun raha...", bg="#DA3633")
        self.status_label.configure(text="● Listening...", fg="#8957E5")
        if not auto:
            self._add("JARVIS", "Haan, sun raha hoon. Boliye!")
        threading.Thread(target=self._listen_and_send, daemon=True).start()

    def _listen_and_send(self):
        text = listen_voice(12)
        self.listening = False
        self.root.after(0, lambda: self.mic_btn.configure(text="🎤 Bolo", bg="#8957E5"))
        if text:
            self.root.after(0, lambda t=text: self._process(t))
        else:
            self.root.after(0, lambda: self._add("JARVIS", "Sunai nahi diya. Dobara bolo ya type karo."))
            self.root.after(0, lambda: self.status_label.configure(text="● AI Connected", fg="#3FB950"))
            if self.auto_listen:
                self.root.after(2000, self._auto_mic)

    def _quick(self, cmd):
        self.entry.delete(0, "end")
        self.entry.insert(0, cmd)
        self._send()

    def _send(self):
        text = self.entry.get().strip()
        if text:
            self.entry.delete(0, "end")
            self._process(text)

    def _process(self, text):
        self._add("Aap", text, user=True)
        self.status_label.configure(text="● Soch raha hoon...", fg="#D29922")
        threading.Thread(target=self._reply, args=(text,), daemon=True).start()

    def _reply(self, text):
        try:
            response = self.brain.think(text)
        except Exception as e:
            response = f"Error: {e}"

        if response == "GOODBYE_SIGNAL":
            bye = "Khuda Hafiz! Goodbye! Phir milenge."
            self.root.after(0, lambda: self._add("JARVIS", bye))
            speak(bye, block=True)
            self.root.after(500, self.root.destroy)
            return

        self.root.after(0, lambda r=response: self._add("JARVIS", r))
        self.root.after(0, lambda: self.status_label.configure(text="● AI Connected", fg="#3FB950"))
        threading.Thread(target=self._speak_and_listen, args=(response,), daemon=True).start()

    def _add(self, sender, msg, user=False):
        self.chat.configure(state="normal")
        t = datetime.now().strftime("%I:%M %p")
        tag = "user" if user else "jarvis"
        who = "Aap" if user else "JARVIS"
        self.chat.insert("end", f"\n{who} [{t}]\n", tag)
        self.chat.insert("end", f"  {msg}\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")


if __name__ == "__main__":
    JarvisApp()
