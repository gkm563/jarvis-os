"""
JARVIS - Simple AI Assistant
Run: python jarvis.py   OR   double-click START.bat

Boliye — jo bologe type hoga, Hindi/English auto switch, aur jo kahenge wo hoga.
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
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
NOTES_DIR = Path.home() / "Desktop" / "JARVIS Notes"


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
# LANGUAGE DETECTION
# ─────────────────────────────────────────────
HINDI_WORDS = re.compile(
    r"\b(kholo|khol|karo|kar|batao|bata|kaise|kya|hai|hain|mujhe|tumhe|chalo|band|"
    r"suno|bol|bolo|nahi|haan|han|theek|thik|samjhao|samjha|likho|likh|"
    r"dhundho|dhundh|baje|aaj|kal|pe|par|mein|mera|meri|"
    r"aur|yeh|ye|woh|wo|karna|chahiye|krdo|kr|krna|banao|bana|"
    r"bandkaro|awaaz|awaz|notepad|kholo|karo|batao|samjhao)\b",
    re.I,
)


def detect_language(text: str) -> str:
    if re.search(r"[\u0900-\u097F]", text):
        return "hindi"
    hindi_hits = len(HINDI_WORDS.findall(text))
    eng_hits = len(re.findall(r"\b[a-zA-Z]{3,}\b", text))
    if hindi_hits >= 1 and hindi_hits >= eng_hits // 2:
        return "hindi"
    if eng_hits >= 2 and hindi_hits == 0:
        return "english"
    if hindi_hits > 0:
        return "hindi"
    return "english"


def get_system_prompt(lang: str) -> str:
    base = """You are JARVIS — personal AI assistant on Windows PC.

BEHAVIOR:
- Do EXACTLY what user asks. Never refuse simple tasks.
- Use tools immediately for actions (open app, camera, search, create file, type text, etc.)
- For questions only — answer directly without tools.
- Keep replies short: 1-3 sentences. User hears this spoken aloud.
- Greet with Namaste."""

    if lang == "hindi":
        return base + """

LANGUAGE (CRITICAL):
- User is speaking HINDI. Reply ONLY in Hindi (Roman Hindi is fine).
- Examples: "Theek hai, camera khol deta hoon." / "Haan bilkul, file bana di."
- Do NOT reply in English unless user switches to English."""

    return base + """

LANGUAGE (CRITICAL):
- User is speaking ENGLISH. Reply ONLY in English.
- Examples: "Sure, opening camera now." / "Done, file created on Desktop."
- Do NOT reply in Hindi unless user switches to Hindi."""


from voice_engine import speak, listen_whisper, ensure_voice_deps, list_voices, VOICES

# Auto-install voice packages on first run
ensure_voice_deps()


def listen_voice(timeout_sec: int = 12, lang: str = "auto", api_key: str = "") -> str:
    """Groq Whisper (best Hindi/English) → Windows SAPI fallback."""
    lang_hint = "hindi" if lang in ("auto", "hindi") else "english"
    if api_key and api_key.startswith("gsk_"):
        text = listen_whisper(api_key, duration=timeout_sec, lang_hint=lang_hint)
        if text:
            return text

    culture = "hi-IN" if lang in ("auto", "hindi") else "en-IN"
    ps = rf"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech
$culture = New-Object System.Globalization.CultureInfo("{culture}")
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($culture)
$engine.SetInputToDefaultAudioDevice()
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$engine.LoadGrammar($grammar)
try {{
    $r = $engine.Recognize([TimeSpan]::FromSeconds({timeout_sec}))
    if ($r -and $r.Text) {{ Write-Output $r.Text.Trim() }}
}} catch {{ }}
"""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True, text=True, timeout=timeout_sec + 10,
            encoding="utf-8", errors="replace",
        )
        return (r.stdout or "").strip()
    except Exception:
        return ""


def listen_and_type_live(entry_widget, root, timeout_sec: int = 15, lang: str = "auto", api_key: str = "") -> str:
    """Whisper STT with live typing in entry box."""
    lang_hint = "hindi" if lang in ("auto", "hindi") else "english"

    # Show listening animation in entry
    root.after(0, lambda: _update_entry(entry_widget, "🎤 Sun raha hoon..."))

    if api_key and api_key.startswith("gsk_"):
        # Poll entry while recording
        import threading as _th
        result_box = [""]

        def _record():
            result_box[0] = listen_whisper(api_key, duration=timeout_sec, lang_hint=lang_hint)

        t = _th.Thread(target=_record, daemon=True)
        t.start()
        dots = 0
        deadline = time.time() + timeout_sec + 2
        while t.is_alive() and time.time() < deadline:
            dots = (dots + 1) % 4
            root.after(0, lambda d="." * dots: _update_entry(entry_widget, f"🎤 Boliye{(' ' + d) if d else '...'}"))
            time.sleep(0.4)
        t.join(timeout=3)
        if result_box[0]:
            root.after(0, lambda t=result_box[0]: _update_entry(entry_widget, t))
            return result_box[0]

    # Fallback: Windows SAPI live dictation
    culture = "hi-IN" if lang in ("auto", "hindi") else "en-IN"
    out_file = tempfile.mktemp(suffix=".txt")
    done_file = tempfile.mktemp(suffix=".done")

    ps = rf"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech
$culture = New-Object System.Globalization.CultureInfo("{culture}")
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($culture)
$engine.SetInputToDefaultAudioDevice()
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$engine.LoadGrammar($grammar)

$outFile = "{out_file.replace(chr(92), '/')}"
$doneFile = "{done_file.replace(chr(92), '/')}"

$hyp = Register-ObjectEvent -InputObject $engine -EventName SpeechHypothesized -Action {{
    if ($EventArgs.Result.Text) {{
        Set-Content -Path $outFile -Value $EventArgs.Result.Text -Encoding UTF8 -Force
    }}
}}
$rec = Register-ObjectEvent -InputObject $engine -EventName SpeechRecognized -Action {{
    if ($EventArgs.Result.Text) {{
        Set-Content -Path $outFile -Value $EventArgs.Result.Text -Encoding UTF8 -Force
        Set-Content -Path $doneFile -Value "done" -Encoding UTF8 -Force
    }}
}}

$engine.RecognizeAsync()
$deadline = (Get-Date).AddSeconds({timeout_sec})
while ((Get-Date) -lt $deadline) {{
    if (Test-Path $doneFile) {{ break }}
    Start-Sleep -Milliseconds 150
}}
try {{ $engine.RecognizeAsyncStop() }} catch {{ }}
Unregister-Event -SourceIdentifier $hyp.Name -ErrorAction SilentlyContinue
Unregister-Event -SourceIdentifier $rec.Name -ErrorAction SilentlyContinue
if (-not (Test-Path $doneFile)) {{
    Set-Content -Path $doneFile -Value "timeout" -Encoding UTF8 -Force
}}
"""
    proc = subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    result = ""
    deadline = time.time() + timeout_sec + 2
    while time.time() < deadline:
        if os.path.exists(out_file):
            try:
                text = Path(out_file).read_text(encoding="utf-8").strip()
                if text and text != result:
                    result = text
                    root.after(0, lambda t=text: _update_entry(entry_widget, t))
            except Exception:
                pass
        if os.path.exists(done_file):
            break
        time.sleep(0.15)

    proc.wait(timeout=5)
    if os.path.exists(out_file):
        try:
            result = Path(out_file).read_text(encoding="utf-8").strip() or result
        except Exception:
            pass
    for f in (out_file, done_file):
        try:
            os.remove(f)
        except Exception:
            pass
    return result


def _update_entry(entry, text: str):
    entry.delete(0, tk.END)
    entry.insert(0, text)


def typewriter_effect(entry, root, text: str, delay: float = 0.025):
    entry.delete(0, tk.END)
    for i, ch in enumerate(text):
        entry.insert(tk.END, ch)
        root.update_idletasks()
        time.sleep(delay)


# ─────────────────────────────────────────────
# ACTIONS
# ─────────────────────────────────────────────
def open_app(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r"\b(please|karo|do|mujhe|open|kholo|khol|app|application|camera)\b", "", n).strip()
    if "camera" in name.lower():
        n = "camera"

    commands = {
        "chrome": 'start "" "chrome"',
        "google chrome": 'start "" "chrome"',
        "notepad": "notepad",
        "calculator": "calc", "calc": "calc",
        "paint": "mspaint",
        "word": "start winword", "excel": "start excel",
        "vlc": 'start "" "vlc"',
        "vs code": 'start "" "code"', "vscode": 'start "" "code"',
        "task manager": "taskmgr",
        "file explorer": "explorer", "explorer": "explorer",
        "spotify": 'start "" "spotify"',
        "settings": "start ms-settings:",
        "camera": "start microsoft.windows.camera:",
        "whatsapp": 'start "" "WhatsApp"',
        "discord": 'start "" "discord"',
        "photos": "start ms-photos:",
        "mail": "start outlookmail:",
    }

    cmd = commands.get(n)
    if cmd:
        subprocess.Popen(cmd, shell=True)
        return f"{name.title()} khol diya." if detect_language(name) == "hindi" else f"Opened {name.title()}."
    subprocess.Popen(f'start "" "{name}"', shell=True)
    return f"{name.title()} khol diya."


def close_app(name: str) -> str:
    n = name.lower().strip()
    exe_map = {
        "chrome": "chrome.exe", "notepad": "notepad.exe",
        "calc": "CalculatorApp.exe", "calculator": "CalculatorApp.exe",
        "paint": "mspaint.exe", "camera": "WindowsCamera.exe",
        "code": "code.exe", "spotify": "spotify.exe",
    }
    exe = exe_map.get(n, n if n.endswith(".exe") else n + ".exe")
    r = subprocess.run(f"taskkill /f /im {exe} 2>nul", shell=True, capture_output=True)
    return f"{name.title()} band kar diya." if r.returncode == 0 else f"{name.title()} nahi chal raha tha."


def search_web(query: str) -> str:
    webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
    return f"Search kiya: {query}"


def open_youtube(query: str = None) -> str:
    if query:
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
        return f"YouTube search: {query}"
    webbrowser.open("https://www.youtube.com")
    return "YouTube khol diya."


def open_site(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"Website kholi: {url}"


def take_screenshot() -> str:
    try:
        from PIL import ImageGrab
        path = Path.home() / "Desktop" / f"ss_{int(time.time())}.png"
        ImageGrab.grab().save(path)
        return "Screenshot Desktop pe save ho gaya."
    except Exception as e:
        return f"Screenshot fail: {e}"


def create_file(filename: str, content: str, location: str = "desktop") -> str:
    loc_map = {
        "desktop": Path.home() / "Desktop",
        "documents": Path.home() / "Documents",
        "downloads": Path.home() / "Downloads",
        "notes": NOTES_DIR,
    }
    folder = loc_map.get(location.lower(), Path(location))
    folder.mkdir(parents=True, exist_ok=True)
    if not filename.endswith((".txt", ".md", ".note")):
        filename += ".txt"
    path = folder / filename
    header = f"--- JARVIS Note | {datetime.now().strftime('%d %b %Y, %I:%M %p')} ---\n\n"
    path.write_text(header + content, encoding="utf-8")
    os.startfile(str(path))
    return f"File ban gayi: {path.name} ({folder.name} pe)"


def write_note(content: str, title: str = None) -> str:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    title = title or f"note_{int(time.time())}"
    if not title.endswith(".txt"):
        title += ".txt"
    return create_file(title, content, "notes")


def type_on_screen(text: str) -> str:
    """Active window mein jo bola wo type karo (clipboard paste)."""
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        time.sleep(0.15)
        subprocess.run(
            'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys(\'^v\')"',
            shell=True,
        )
        return f"Screen pe type kar diya: {text[:50]}..."
    except Exception as e:
        return f"Type nahi ho paya: {e}"


def volume_action(action: str) -> str:
    codes = {"up": 175, "down": 174, "mute": 173}
    subprocess.run(
        f'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]{codes.get(action, 175)})"',
        shell=True,
    )
    return {"up": "Volume badha diya.", "down": "Volume kam ki.", "mute": "Mute."}.get(action, "Done.")


def get_datetime(lang: str = "hindi") -> str:
    now = datetime.now()
    if lang == "english":
        period = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
        return f"Good {period}! It's {now.strftime('%I:%M %p')}. Today is {now.strftime('%A, %d %B %Y')}."
    period = "subah" if now.hour < 12 else "dopahar" if now.hour < 17 else "shaam"
    return f"Namaste! {period.capitalize()} ke {now.strftime('%I:%M %p')} baj rahe hain. Aaj {now.strftime('%d %B %Y')} hai."


def lock_pc() -> str:
    subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
    return "Screen lock ho gayi."


def shutdown_pc(cancel: bool = False) -> str:
    if cancel:
        subprocess.run("shutdown /a", shell=True)
        return "Shutdown cancel."
    subprocess.run("shutdown /s /t 30", shell=True)
    return "PC 30 sec mein band hoga."


def run_terminal(cmd: str) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        out = (r.stdout or r.stderr or "").strip()
        return out[:500] if out else "Command chal gayi."
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
            "get_time": lambda: get_datetime(args.get("lang", "hindi")),
            "lock_screen": lock_pc,
            "shutdown_pc": lambda: shutdown_pc(args.get("cancel", False)),
            "run_command": lambda: run_terminal(args.get("command", "")),
            "create_file": lambda: create_file(
                args.get("filename", "note.txt"),
                args.get("content", ""),
                args.get("location", "desktop"),
            ),
            "write_note": lambda: write_note(args.get("content", ""), args.get("title")),
            "type_text": lambda: type_on_screen(args.get("text", "")),
        }
        fn = actions.get(name)
        return fn() if fn else f"Unknown: {name}"
    except Exception as e:
        return f"Fail: {e}"


TOOL_DEFINITIONS = [
    {"type": "function", "function": {
        "name": "open_app",
        "description": "Open app: Chrome, Notepad, Calculator, Camera, VS Code, WhatsApp, Settings, etc.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    }},
    {"type": "function", "function": {
        "name": "close_app", "description": "Close running app.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    }},
    {"type": "function", "function": {
        "name": "search_web", "description": "Google search.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "open_youtube", "description": "Open YouTube or search.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "open_website", "description": "Open website URL.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
    }},
    {"type": "function", "function": {
        "name": "screenshot", "description": "Take screenshot.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "create_file",
        "description": "Create new file with content/notes on Desktop, Documents, or JARVIS Notes folder.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "File name e.g. mynote.txt"},
                "content": {"type": "string", "description": "Text content to write in file"},
                "location": {"type": "string", "description": "desktop, documents, downloads, or notes"},
            },
            "required": ["filename", "content"],
        },
    }},
    {"type": "function", "function": {
        "name": "write_note",
        "description": "Quick note save in JARVIS Notes folder on Desktop.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "title": {"type": "string", "description": "Optional note title/filename"},
            },
            "required": ["content"],
        },
    }},
    {"type": "function", "function": {
        "name": "type_text",
        "description": "Type text into the currently active window/app (like keyboard typing what user said).",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    }},
    {"type": "function", "function": {
        "name": "volume", "description": "Volume up/down/mute.",
        "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["up", "down", "mute"]}}, "required": ["action"]},
    }},
    {"type": "function", "function": {
        "name": "get_time", "description": "Current time and date.",
        "parameters": {"type": "object", "properties": {"lang": {"type": "string"}}},
    }},
    {"type": "function", "function": {
        "name": "lock_screen", "description": "Lock PC.",
        "parameters": {"type": "object", "properties": {}},
    }},
    {"type": "function", "function": {
        "name": "shutdown_pc", "description": "Shutdown or cancel.",
        "parameters": {"type": "object", "properties": {"cancel": {"type": "boolean"}}},
    }},
    {"type": "function", "function": {
        "name": "run_command", "description": "Run terminal command.",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
    }},
]


class Brain:
    def __init__(self):
        self.env = load_env()
        self.history: list[dict] = []
        self.api_key = self.env.get("GROQ_API_KEY", "")
        if self.api_key and not self.api_key.startswith("gsk_"):
            self.api_key = ""
        self.current_lang = "hindi"

    def set_key(self, key: str):
        self.api_key = key.strip()
        save_api_key(self.api_key)

    def has_ai(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("gsk_"))

    def verify_ai(self) -> tuple[bool, str]:
        if not self.has_ai():
            return False, "Groq API key missing"
        data = self._groq_request([{"role": "user", "content": "OK"}], tools=None)
        if not data:
            return False, "Internet check karo"
        if "error" in data:
            return False, data["error"]
        return True, "Connected"

    def _groq_request(self, messages: list, tools=None) -> dict | None:
        if not self.api_key:
            return None
        body = {"model": "llama-3.3-70b-versatile", "messages": messages, "max_tokens": 400, "temperature": 0.6}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json", "User-Agent": "JARVIS/3.0"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            err = e.read().decode() if e.fp else str(e)
            return {"error": f"AI error ({e.code}): {err[:120]}"}
        except Exception as e:
            return {"error": str(e)}

    def think(self, user_text: str) -> tuple[str, str]:
        """Returns (response, language)."""
        self.current_lang = detect_language(user_text)
        t = user_text.lower().strip()

        if re.search(r"\b(bye|goodbye|alvida|exit|quit|close jarvis|band karo jarvis)\b", t):
            return "GOODBYE_SIGNAL", self.current_lang

        if self.has_ai():
            result = self._ai_think(user_text)
            if result:
                return result, self.current_lang

        return self._rule_think(user_text), self.current_lang

    def _ai_think(self, user_text: str) -> str | None:
        self.history.append({"role": "user", "content": user_text})
        if len(self.history) > 16:
            self.history = self.history[-16:]

        messages = [{"role": "system", "content": get_system_prompt(self.current_lang)}] + self.history

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
                    results.append(execute_tool(fn, args))
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": results[-1]})

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
        lang = self.current_lang
        t = text.lower()
        if re.search(r"\b(hello|hi|hey|namaste|kaise ho)\b", t):
            return f"Namaste! Main JARVIS hoon. {get_datetime(lang)} Kya karna hai?"
        if re.search(r"\b(time|baje|date|kitne baj)\b", t):
            return get_datetime(lang)
        if re.search(r"\b(camera|camera kholo|open camera)\b", t):
            return open_app("camera")
        m = re.search(r"(?:file|note)\s+(?:banao|create|likho|save)\s*(.+)?", t, re.I)
        if m:
            content = m.group(1).strip() if m.group(1) else text
            return write_note(content)
        m = re.search(r"(?:type|likho|likh)\s+(.+)", t)
        if m:
            return type_on_screen(m.group(1).strip())
        m = re.search(r"(?:open|kholo|khol|start|launch)\s+(.+)", t)
        if m:
            target = re.sub(r"\b(please|karo|do|mujhe)\b", "", m.group(1)).strip()
            if re.search(r"\.(com|in|org)\b", target):
                return open_site(target)
            return open_app(target)
        if "youtube" in t:
            m = re.search(r"youtube\s*(?:pe|par|search|open)?\s*(.+)?", t)
            return open_youtube(m.group(1).strip() if m and m.group(1) else None)
        m = re.search(r"(?:search|google|dhundho|find)\s+(.+)", t)
        if m:
            return search_web(m.group(1).strip())
        if re.search(r"\b(screenshot)\b", t):
            return take_screenshot()
        return "AI connect nahi hai. Settings se Groq key daalo." if lang == "hindi" else "AI not connected. Add Groq key in Settings."


def get_greeting(lang: str = "hindi") -> str:
    now = datetime.now()
    if lang == "english":
        period = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
        return f"Namaste! Good {period}! I'm JARVIS, your assistant. Speak in Hindi or English — I'll switch automatically. What should I do?"
    return (
        "Namaste! Main JARVIS hoon, aapka personal assistant. "
        "Hindi ya English mein bolo — main usi language mein jawab dunga. "
        "Jo bologe type hoga aur main karunga — camera, search, file, sab kuch!"
    )


class JarvisApp:
    def __init__(self):
        self.brain = Brain()
        self.listening = False
        self.auto_listen = True
        self.speaking = False
        self.running = True
        self.dictate_mode = False  # True = sirf type karo, command mat chalao
        self.current_lang = "hindi"

        self.root = tk.Tk()
        self.root.title("JARVIS — AI Assistant")
        self.root.geometry("760x680")
        self.root.configure(bg="#0D1117")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self.root.after(300, self._startup)
        self.root.mainloop()

    def _startup(self):
        ok, msg = self.brain.verify_ai()
        voice_info = f" | 🎙 {VOICES['hindi'].split('-')[-1]}" if ensure_voice_deps() else ""
        self.status_label.configure(
            text=("● AI + Neural Voice" + voice_info) if ok else f"● {msg[:30]}",
            fg="#3FB950" if ok else "#F85149",
        )
        if not self.brain.has_ai():
            self.root.after(800, self._settings)

        greeting = get_greeting("hindi")
        self._add("JARVIS", greeting)
        threading.Thread(target=self._speak_and_listen, args=(greeting, "hindi"), daemon=True).start()

    def _speak_and_listen(self, text: str, lang: str):
        self.speaking = True
        speak(text, lang=lang, block=True)
        self.speaking = False
        if self.auto_listen and self.running:
            self.root.after(600, self._auto_mic)

    def _auto_mic(self):
        if not self.listening and self.running and self.auto_listen:
            self._toggle_mic(auto=True)

    def _on_close(self):
        self.running = False
        self.root.destroy()

    def _settings(self):
        key = simpledialog.askstring("Groq API Key", "Groq key (free): console.groq.com", show="*")
        if key and key.strip():
            self.brain.set_key(key.strip())
            ok, msg = self.brain.verify_ai()
            if ok:
                self._add("JARVIS", "AI connected! Ab bolo!")
                self.status_label.configure(text="● AI Connected", fg="#3FB950")

    def _build_ui(self):
        bar = tk.Frame(self.root, bg="#161B22")
        bar.pack(fill="x")

        tk.Label(bar, text="JARVIS AI", font=("Segoe UI", 14, "bold"),
                 bg="#161B22", fg="#58A6FF").pack(side="left", padx=15, pady=12)

        self.lang_label = tk.Label(bar, text="🌐 Auto Lang", font=("Segoe UI", 9),
                                    bg="#161B22", fg="#8B949E")
        self.lang_label.pack(side="right", padx=6)

        self.auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(bar, text="Auto Listen", variable=self.auto_var, bg="#161B22", fg="#8B949E",
                       selectcolor="#21262D", font=("Segoe UI", 9),
                       command=lambda: setattr(self, "auto_listen", self.auto_var.get())).pack(side="right", padx=4)

        self.dictate_var = tk.BooleanVar(value=False)
        tk.Checkbutton(bar, text="Dictate Only", variable=self.dictate_var, bg="#161B22", fg="#8B949E",
                       selectcolor="#21262D", font=("Segoe UI", 9),
                       command=self._toggle_dictate).pack(side="right", padx=4)

        self.status_label = tk.Label(bar, text="● Starting...", font=("Segoe UI", 10),
                                      bg="#161B22", fg="#D29922")
        self.status_label.pack(side="right", padx=8)

        tk.Button(bar, text="⚙", font=("Segoe UI", 11), bg="#21262D", fg="#8B949E",
                  relief="flat", command=self._settings).pack(side="right", padx=4)

        chat_frame = tk.Frame(self.root, bg="#0D1117")
        chat_frame.pack(fill="both", expand=True, padx=10, pady=8)

        self.chat = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, font=("Segoe UI", 12),
            bg="#0D1117", fg="#E6EDF3", relief="flat", padx=12, pady=10, state="disabled",
        )
        self.chat.pack(fill="both", expand=True)
        self.chat.tag_config("jarvis", foreground="#58A6FF")
        self.chat.tag_config("user", foreground="#3FB950")

        # Smart typing box — jo bologe yahan dikhega
        type_frame = tk.Frame(self.root, bg="#161B22")
        type_frame.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(type_frame, text="Smart Type:", font=("Segoe UI", 9), bg="#161B22", fg="#8B949E").pack(side="left", padx=8)

        bottom = tk.Frame(self.root, bg="#161B22", pady=10)
        bottom.pack(fill="x", padx=10, pady=8)

        self.mic_btn = tk.Button(
            bottom, text="🎤 Bolo", font=("Segoe UI", 13, "bold"),
            bg="#8957E5", fg="white", relief="flat", padx=14, pady=8,
            cursor="hand2", command=lambda: self._toggle_mic(auto=False),
        )
        self.mic_btn.pack(side="left", padx=(8, 4))

        self.entry = tk.Entry(
            bottom, font=("Segoe UI", 13), bg="#21262D", fg="#E6EDF3",
            insertbackground="#58A6FF", relief="flat",
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=12, padx=8)
        self.entry.bind("<Return>", lambda e: self._send())
        self.entry.focus()

        tk.Button(bottom, text="Send ➤", font=("Segoe UI", 12, "bold"), bg="#238636", fg="white",
                  relief="flat", padx=16, pady=8, cursor="hand2", command=self._send).pack(side="right", padx=8)

        tk.Button(bottom, text="⌨ Type Screen", font=("Segoe UI", 10), bg="#21262D", fg="#8B949E",
                  relief="flat", padx=10, pady=8, cursor="hand2",
                  command=self._type_entry_to_screen).pack(side="right", padx=2)

        chips = tk.Frame(self.root, bg="#0D1117")
        chips.pack(fill="x", padx=10, pady=(0, 8))
        for label, cmd in [
            ("📷 Camera", "camera kholo"), ("🔍 Search", "Python search karo"),
            ("📝 Note", "note banao JARVIS test"), ("⏰ Time", "time batao"),
        ]:
            tk.Button(chips, text=label, font=("Segoe UI", 10), bg="#21262D", fg="#8B949E",
                      relief="flat", padx=10, pady=4, cursor="hand2",
                      command=lambda c=cmd: self._quick(c)).pack(side="left", padx=3)

    def _toggle_dictate(self):
        self.dictate_mode = self.dictate_var.get()

    def _type_entry_to_screen(self):
        text = self.entry.get().strip()
        if text:
            msg = type_on_screen(text)
            self._add("JARVIS", msg)

    def _toggle_mic(self, auto=False):
        if self.listening or self.speaking:
            return
        self.listening = True
        self.mic_btn.configure(text="🔴 Sun raha...", bg="#DA3633")
        self.status_label.configure(text="● Smart Typing...", fg="#8957E5")
        self.entry.delete(0, tk.END)
        self.entry.insert(0, "🎤 Boliye...")
        self.entry.configure(fg="#8957E5")
        threading.Thread(target=self._listen_and_send, args=(auto,), daemon=True).start()

    def _listen_and_send(self, auto=False):
        lang_guess = self.current_lang
        api_key = self.brain.api_key
        text = listen_and_type_live(self.entry, self.root, timeout_sec=14, lang=lang_guess, api_key=api_key)

        if not text:
            text = listen_voice(10, lang=lang_guess, api_key=api_key)

        self.listening = False
        self.root.after(0, lambda: self.mic_btn.configure(text="🎤 Bolo", bg="#8957E5"))
        self.root.after(0, lambda: self.entry.configure(fg="#E6EDF3"))

        if text:
            self.root.after(0, lambda t=text: self._on_voice_result(t))
        else:
            self.root.after(0, lambda: self.entry.delete(0, tk.END))
            msg = "Sunai nahi diya. Dobara bolo." if self.current_lang == "hindi" else "Couldn't hear you. Try again."
            self.root.after(0, lambda: self._add("JARVIS", msg))
            self.root.after(0, lambda: self.status_label.configure(text="● AI Connected", fg="#3FB950"))
            if self.auto_listen:
                self.root.after(2500, self._auto_mic)

    def _on_voice_result(self, text: str):
        self.current_lang = detect_language(text)
        lang_tag = "🇮🇳 Hindi" if self.current_lang == "hindi" else "🇬🇧 English"
        self.lang_label.configure(text=f"🌐 {lang_tag}")

        # Smart typing — typewriter effect in entry box
        self.entry.delete(0, tk.END)
        threading.Thread(target=typewriter_effect, args=(self.entry, self.root, text, 0.015), daemon=True).start()
        time.sleep(min(len(text) * 0.015, 1.5))

        if self.dictate_mode:
            self._add("JARVIS", f"Typed: {text}" if self.current_lang == "english" else f"Type ho gaya: {text}")
            self.status_label.configure(text="● Dictate Mode", fg="#58A6FF")
            return

        self._process(text)

    def _quick(self, cmd):
        self.entry.delete(0, "end")
        self.entry.insert(0, cmd)
        self._send()

    def _send(self):
        text = self.entry.get().strip()
        if text and not text.startswith("🎤"):
            self.entry.delete(0, "end")
            self._process(text)

    def _process(self, text: str):
        self.current_lang = detect_language(text)
        lang_tag = "🇮🇳 Hindi" if self.current_lang == "hindi" else "🇬🇧 English"
        self.lang_label.configure(text=f"🌐 {lang_tag}")
        self._add("Aap", text, user=True)
        self.status_label.configure(text="● Soch raha hoon...", fg="#D29922")
        threading.Thread(target=self._reply, args=(text,), daemon=True).start()

    def _reply(self, text):
        try:
            response, lang = self.brain.think(text)
            self.current_lang = lang
        except Exception as e:
            response, lang = f"Error: {e}", self.current_lang

        if response == "GOODBYE_SIGNAL":
            bye = "Namaste! Alvida! Phir milenge." if lang == "hindi" else "Namaste! Goodbye! See you again."
            self.root.after(0, lambda: self._add("JARVIS", bye))
            speak(bye, lang=lang, block=True)
            self.root.after(500, self.root.destroy)
            return

        self.root.after(0, lambda r=response: self._add("JARVIS", r))
        self.root.after(0, lambda: self.status_label.configure(text="● AI Connected", fg="#3FB950"))
        threading.Thread(target=self._speak_and_listen, args=(response, lang), daemon=True).start()

    def _add(self, sender, msg, user=False):
        self.chat.configure(state="normal")
        t = datetime.now().strftime("%I:%M %p")
        who = "Aap" if user else "JARVIS"
        tag = "user" if user else "jarvis"
        self.chat.insert("end", f"\n{who} [{t}]\n", tag)
        self.chat.insert("end", f"  {msg}\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")


if __name__ == "__main__":
    JarvisApp()
