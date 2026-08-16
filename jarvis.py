"""
JARVIS - English AI Assistant
Run: python jarvis.py   OR   double-click START.bat

Speak in English — JARVIS listens, talks back, and does what you ask.
(Hindi support will be added later.)
"""

# English-first mode — set to "hindi" later when integrating Hindi
APP_LANG = "english"


def L(en: str, hi: str = "") -> str:
    """Localized string — English now, Hindi later."""
    return en if APP_LANG == "english" else (hi or en)

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
import asyncio
from datetime import datetime
from pathlib import Path

# JARVIS OS Modular imports
from jarvis.brain.planner import TaskPlanner
from jarvis.orchestration.executor import ExecutionManager, AgentRegistry
from jarvis.core.models import Plan, Step, AgentAction, PlanStatus, StepStatus
from jarvis.agents.desktop_agent import DesktopControlAgent
from jarvis.agents.browser_agent import BrowserAutomationAgent
from jarvis.agents.file_agent import FileSystemAgent
from jarvis.agents.office_agent import OfficeAgent
from jarvis.agents.research_agent import InternetResearchAgent

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
NOTES_DIR = Path.home() / "Desktop" / "JARVIS Notes"


def set_startup(enable: bool = True) -> str:
    startup_dir = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    shortcut_path = startup_dir / "JARVIS.bat"
    
    if enable:
        bat_content = f'@echo off\ncd /d "{ROOT}"\nstart START.bat\n'
        shortcut_path.write_text(bat_content, encoding="utf-8")
        return "JARVIS registered in Windows startup."
    else:
        if shortcut_path.exists():
            shortcut_path.unlink()
        return "JARVIS removed from Windows startup."


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
    if APP_LANG == "english":
        return "english"
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
    return """You are JARVIS — a personal AI assistant on a Windows PC.

BEHAVIOR:
- Do EXACTLY what the user asks. Never refuse simple tasks.
- Answer questions directly in 1-3 short sentences.
- Keep replies short — the user hears this spoken aloud.
- You CANNOT run apps yourself — the system executes actions separately. Reply naturally and confirm what was done.

LANGUAGE (CRITICAL):
- Reply ONLY in clear English.
- Examples: "Sure, opening Chrome now." / "Done, your note is saved on the Desktop."
- Be friendly and professional."""


from voice_engine import speak, listen_best, ensure_voice_deps, stop_speaking, VOICES

ensure_voice_deps()

_cancel_event = threading.Event()


def request_cancel():
    _cancel_event.set()


def clear_cancel():
    _cancel_event.clear()


def is_cancelled() -> bool:
    return _cancel_event.is_set()


def interruptible_sleep(seconds: float, step: float = 0.15) -> bool:
    """Sleep in chunks; return False if cancelled."""
    elapsed = 0.0
    while elapsed < seconds:
        if is_cancelled():
            return False
        wait = min(step, seconds - elapsed)
        time.sleep(wait)
        elapsed += wait
    return True


def listen_voice(timeout_sec: int = 8, lang: str = "auto", api_key: str = "", on_status=None, on_partial=None, should_stop=None) -> tuple[str, str]:
    return listen_best(api_key, timeout_sec, lang, on_status=on_status, on_partial=on_partial, should_stop=should_stop)


def listen_voice_only(
    api_key: str,
    timeout_sec: int = 10,
    lang: str = "english",
    on_status=None,
    should_stop=None,
) -> tuple[str, str]:
    """Listen only — no typing anywhere. Returns (text, error)."""
    def on_status_safe(msg: str):
        if on_status:
            on_status(msg)

    text, err = listen_best(
        api_key, timeout_sec, lang,
        on_status=on_status_safe,
        on_partial=None,
        should_stop=should_stop,
    )
    if text:
        return text.strip(), ""
    return "", err or L("Didn't hear anything", "Sunai nahi diya")


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
        return L(f"Opened {name.title()}.", f"{name.title()} khol diya.")
    subprocess.Popen(f'start "" "{name}"', shell=True)
    return L(f"Opened {name.title()}.", f"{name.title()} khol diya.")


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
    return L(f"Closed {name.title()}.", f"{name.title()} band kar diya.") if r.returncode == 0 else L(f"{name.title()} wasn't running.", f"{name.title()} nahi chal raha tha.")


def search_web(query: str) -> str:
    webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
    return L(f"Searched Google for: {query}", f"Search kiya: {query}")


def open_youtube(query: str = None) -> str:
    if query:
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
        return f"YouTube search: {query}"
    webbrowser.open("https://www.youtube.com")
    return L("Opened YouTube.", "YouTube khol diya.")


def open_site(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return L(f"Opened website: {url}", f"Website kholi: {url}")


def take_screenshot() -> str:
    try:
        from PIL import ImageGrab
        path = Path.home() / "Desktop" / f"ss_{int(time.time())}.png"
        ImageGrab.grab().save(path)
        return L("Screenshot saved to Desktop.", "Screenshot Desktop pe save ho gaya.")
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
    return L(f"File created: {path.name} on {folder.name}", f"File ban gayi: {path.name} ({folder.name} pe)")


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
        return L(f"Typed on screen: {text[:50]}...", f"Screen pe type kar diya: {text[:50]}...")
    except Exception as e:
        return f"Type nahi ho paya: {e}"


def volume_action(action: str) -> str:
    codes = {"up": 175, "down": 174, "mute": 173}
    subprocess.run(
        f'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]{codes.get(action, 175)})"',
        shell=True,
    )
    return {
        "up": L("Volume increased.", "Volume badha diya."),
        "down": L("Volume decreased.", "Volume kam ki."),
        "mute": L("Muted.", "Mute."),
    }.get(action, "Done.")


def get_datetime(lang: str = "hindi") -> str:
    now = datetime.now()
    if lang == "english":
        period = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
        return f"Good {period}! It's {now.strftime('%I:%M %p')}. Today is {now.strftime('%A, %d %B %Y')}."
    period = "subah" if now.hour < 12 else "dopahar" if now.hour < 17 else "shaam"
    return f"Namaste! {period.capitalize()} ke {now.strftime('%I:%M %p')} baj rahe hain. Aaj {now.strftime('%d %B %Y')} hai."


def lock_pc() -> str:
    subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
    return L("Screen locked.", "Screen lock ho gayi.")


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
        return out[:500] if out else L("Command executed.", "Command chal gayi.")
    except Exception as e:
        return f"Error: {e}"


# Devanagari → Roman (Whisper Hindi output ke liye)
DEVANAGARI_MAP = {
    "कैमरा": "camera", "कैमरे": "camera", "खोलो": "kholo", "खोल": "khol",
    "ओपन": "open", "करो": "karo", "कर": "kar", "बंद": "band", "नोट": "note",
    "बनाओ": "banao", "फोटो": "photo", "फ़ोटो": "photo", "क्लिक": "click",
    "सर्च": "search", "टाइम": "time", "समय": "time", "और": "aur",
    "गूगल": "google", "यूट्यूब": "youtube",
    "नमस्ते": "namaste", "चलो": "chalo", "बताओ": "batao", "लिखो": "likho",
    "स्क्रीनशॉट": "screenshot", "वॉल्यूम": "volume", "म्यूट": "mute",
    "क्रोम": "chrome", "नोटपैड": "notepad", "कैलकुलेटर": "calculator",
}


def normalize_command(text: str) -> str:
    t = text.strip()
    for dev, roman in DEVANAGARI_MAP.items():
        t = t.replace(dev, roman)
    t = t.lower()
    t = re.sub(r"\bkro\b", "karo", t)
    t = re.sub(r"\bkr\b", "kar", t)
    t = re.sub(r"\bkhul\b", "kholo", t)
    t = re.sub(r"\bkrna\b", "karna", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _find_camera_roll() -> Path | None:
    for p in [
        Path.home() / "Pictures" / "Camera Roll",
        Path.home() / "OneDrive" / "Pictures" / "Camera Roll",
        Path.home() / "Pictures",
    ]:
        if p.exists():
            return p
    return None


def show_camera_photos() -> str:
    folder = _find_camera_roll()
    if folder:
        os.startfile(str(folder))
        return L(
            f"Opened your photos folder: {folder}",
            f"Photo yahan save hoti hai — folder khol diya: {folder}",
        )
    return L("Photos are usually in Pictures > Camera Roll.", "Photos usually Pictures > Camera Roll mein milti hain.")


def camera_take_photo() -> str:
    """Open camera, take photo, open photos folder."""
    if is_cancelled():
        return L("Cancelled.", "Cancel ho gaya.")
    subprocess.Popen("start microsoft.windows.camera:", shell=True)
    if not interruptible_sleep(4.0):
        return L("Cancelled.", "Cancel ho gaya.")
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "Start-Sleep -Milliseconds 800; "
        '[System.Windows.Forms.SendKeys]::SendWait(" "); '
        "Start-Sleep -Milliseconds 600; "
        '[System.Windows.Forms.SendKeys]::SendWait(" ")'
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], shell=True, capture_output=True)
    if not interruptible_sleep(1.5):
        return L("Cancelled.", "Cancel ho gaya.")
    folder = _find_camera_roll()
    if folder:
        subprocess.Popen(f'explorer "{folder}"')
        return L(
            "Done! Camera opened, photo taken. Your photos folder is open — check there!",
            "Ho gaya! Camera khuli, photo click ki. Photos folder ab khul gaya — wahan apni photo dekho!",
        )
    return L(
        "Camera opened and photo taken! Check Pictures > Camera Roll.",
        "Camera khuli aur photo click ki! Pictures > Camera Roll mein check karo.",
    )


def _single_action(t: str, lang: str, raw: str) -> str | None:
    if re.search(r"\b(what time|what's the time|what is the time|time is it|what date|today's date|what day)\b", t):
        return get_datetime(lang)
    if re.search(r"\b(time|date|baje|kitne baj|samay)\b", t) and re.search(r"\b(what|tell|show|batao|bata)\b", t):
        return get_datetime(lang)
    if re.search(r"\b(take screenshot|screenshot|screen shot|capture screen|ss)\b", t):
        return take_screenshot()
    if re.search(r"\b(volume up|turn up volume|increase volume|awaaz badhao)\b", t):
        return volume_action("up")
    if re.search(r"\b(volume down|turn down volume|decrease volume|awaaz kam)\b", t):
        return volume_action("down")
    if re.search(r"\b(mute|unmute|silence|chup|awaaz band)\b", t):
        return volume_action("mute")
    if re.search(r"\b(lock|lock screen|lock pc|lock computer)\b", t):
        return lock_pc()

    # Camera + photo
    if re.search(r"\b(take a photo|take photo|take picture|take a picture|capture photo|snap a photo|click photo|click a photo|take selfie|capture picture)\b", t):
        return camera_take_photo()
    if "camera" in t and re.search(r"\b(photo|click|pic|selfie|capture|snap|picture)\b", t):
        return camera_take_photo()
    if re.search(r"\b(open camera|launch camera|start camera|camera open|camera kholo|camera karo|camera chalu)\b", t):
        return open_app("camera")
    if t.strip() in ("camera", "camera app"):
        return open_app("camera")

    m = re.search(r"(?:create|make|write|save)\s+(?:a\s+)?(?:note|file)\s*(?:about|saying|with|:)?\s*(.+)?", t)
    if not m:
        m = re.search(r"(?:note|file|notepad)\s+(?:banao|create|likho|save|mein likho|banana)\s*(.+)?", t)
    if m:
        content = re.sub(r"^(note|file)\s+", "", (m.group(1) or raw).strip(), flags=re.I).strip()
        return write_note(content or raw)

    m = re.search(r"(?:type on screen|type this|type|write on screen|likho screen pe)\s+(.+)", t)
    if m:
        return type_on_screen(m.group(1).strip())

    if "youtube" in t:
        m = re.search(r"youtube\s*(?:pe|par|mein|search|open|play|for|kholo)?\s*(.+)?", t)
        q = m.group(1).strip() if m and m.group(1) else None
        if q:
            q = re.sub(r"\b(kholo|open|search|karo|pe|par|for|on)\b", "", q).strip()
        return open_youtube(q if q else None)

    m = re.search(r"(?:search for|search|google|find|look up|dhundho|google pe)\s+(.+)", t)
    if not m:
        m = re.search(r"(.+?)\s+search\s*(?:karo|kar|kro|please)?\s*$", t)
    if m:
        q = re.sub(r"\b(karo|kar|please|pe|par|for|on)\b", "", m.group(1)).strip()
        if q:
            return search_web(q)

    m = re.search(r"(?:close|quit|exit|kill|band karo|band)\s+(.+)", t)
    if m:
        return close_app(m.group(1).strip())

    m = re.search(r"(?:open|launch|start|run|kholo|khol|chalo|chalao)\s+(.+)", t)
    if m:
        target = re.sub(r"\b(please|plz|karo|do|mujhe|app|application|the|my)\b", "", m.group(1)).strip()
        if re.search(r"\.(com|in|org|net)\b", target):
            return open_site(target)
        return open_app(target)

    for app in ("chrome", "notepad", "calculator", "calc", "paint", "whatsapp", "vscode", "settings", "camera"):
        if t == app or t.endswith(f" {app}") or f"open {app}" in t or f"{app} kholo" in t:
            return open_app(app)
    return None


def try_local_action(text: str) -> str | None:
    """Parse and run local actions immediately."""
    lang = detect_language(text)
    norm = normalize_command(text)

    # Where is my photo?
    if re.search(r"(where|location|find|show|saved|folder).*(photo|picture|pic|selfie)", norm):
        return show_camera_photos()
    if re.search(r"(photo|pic|picture|selfie).*(where|location|saved|folder|find)", norm):
        return show_camera_photos()
    if re.search(r"(photo|pic|picture|selfie)", norm) and re.search(
        r"(kaha|kidhar|where|location|dikhao|show|milegi|mili|save|folder)", norm
    ):
        return show_camera_photos()

    # Camera + photo — permissive
    if "camera" in norm or "camra" in norm or "kamera" in norm:
        if re.search(r"(photo|click|pic|selfie|capture|snap|foto|picture)", norm):
            return camera_take_photo()
        if re.search(r"(open|kholo|khol|karo|chalu|start|launch)", norm):
            return open_app("camera")

    if re.search(r"(take a photo|take photo|photo click|click photo|photo lo|photo le|selfie lo|take picture)", norm):
        return camera_take_photo()

    results = []
    parts = re.split(r"\s+(?:aur|and|then|also|phir)\s+", norm)
    for part in parts:
        if is_cancelled():
            return L("Cancelled.", "Cancel ho gaya.")
        part = part.strip()
        if not part:
            continue
        r = _single_action(part, lang, text)
        if r:
            results.append(r)

    if results:
        return " | ".join(results)
    return _single_action(norm, lang, text)


class Brain:
    def __init__(self):
        self.env = load_env()
        self.history: list[dict] = []
        self.api_key = self.env.get("GROQ_API_KEY", "")
        if self.api_key and not self.api_key.startswith("gsk_"):
            self.api_key = ""
        self.current_lang = APP_LANG
        self.app = None

        # Register agents in registry
        self.registry = AgentRegistry()
        self.registry.register(DesktopControlAgent())
        self.registry.register(BrowserAutomationAgent())
        self.registry.register(FileSystemAgent())
        self.registry.register(OfficeAgent())
        self.registry.register(InternetResearchAgent())

        self.planner = TaskPlanner()
        self.executor = ExecutionManager(registry=self.registry)

    def set_key(self, key: str):
        self.api_key = key.strip()
        save_api_key(self.api_key)

    def has_ai(self) -> bool:
        return bool(self.api_key and self.api_key.startswith("gsk_")) or bool(self.env.get("GEMINI_API_KEY"))

    def verify_ai(self) -> tuple[bool, str]:
        if self.env.get("GEMINI_API_KEY"):
            return True, "Gemini Connected"
        if not self.has_ai():
            return False, "Groq API key missing"
        data = self._groq_request([{"role": "user", "content": "OK"}], tools=None)
        if not data:
            return False, "Check your internet connection"
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

        # Run async think_async
        try:
            return asyncio.run(self.think_async(user_text))
        except Exception as e:
            logger.error(f"Error in think_async: {e}")
            return f"I ran into an issue: {e}", self.current_lang

    async def think_async(self, user_text: str) -> tuple[str, str]:
        self.current_lang = detect_language(user_text)
        t = user_text.lower().strip()

        # Special check: custom shutdown
        if any(w in t for w in ["switch off", "shutdown", "shut down", "turn off computer"]) and any(w in t for w in ["laptop", "pc", "computer"]):
            if self.app:
                self.app.root.after(0, self.app._graceful_shutdown)
                await asyncio.sleep(8.0)
                return "GOODBYE_SIGNAL", self.current_lang

        from jarvis.brain.llm_provider import UniversalLLMProvider
        llm = UniversalLLMProvider()

        classification_prompt = f"""Classify the user prompt into one of these categories:
- "knowledge": The user is asking a general information question, educational topic, history, explanation, coding question (e.g. "who is CEO of Microsoft", "explain Dijkstra", "how World War happened", "what is this code", "hello", "hi").
- "automation": The user wants to perform action(s) on the computer (e.g. "open chrome", "create a file", "take a photo", "close notepad", "save work", "send whatsapp").

User Prompt: "{user_text}"
Output ONLY the category name ("knowledge" or "automation")."""

        category = "knowledge"
        try:
            category = await llm.generate_response(classification_prompt)
            category = category.lower().strip().replace('"', '').replace("'", "")
            logger.info(f"Classified prompt category as: '{category}'")
        except Exception as e:
            logger.error(f"Classification failed: {e}. Defaulting to knowledge.")

        if "automation" in category:
            try:
                plan = await self.planner.create_plan(user_text)
            except Exception as e:
                logger.error(f"Plan creation failed: {e}")
                return f"I had trouble planning that: {e}", self.current_lang

            logger.info(f"Generated plan with {len(plan.steps)} steps")
            if not plan.steps:
                return "I couldn't identify any steps to execute.", self.current_lang

            # Speak plan created
            if self.app:
                msg = f"I've created a plan with {len(plan.steps)} steps to execute. Starting now."
                self.app._speak_sync(msg)

            for step in plan.steps:
                if self.app:
                    msg = f"Executing step: {step.description}"
                    self.app._speak_sync(msg)

                # Check if sensitive
                if step.action.is_sensitive or any(w in step.action.action_type for w in ["delete", "send_whatsapp", "system_state"]):
                    if self.app:
                        self.app._speak_sync("This step requires your approval.")
                        approved = self.app._ask_confirmation(step.description)
                        if not approved:
                            self.app._speak_sync("Action cancelled by user.")
                            return "I cancelled the remaining actions as requested.", self.current_lang

                # Camera guide
                if step.action.agent_name == "desktop_agent" and step.action.action_type == "camera_take_photo":
                    if self.app:
                        self.app._speak_sync("Please position yourself in front of the webcam. Capturing photo in 4 seconds.")

                # Execute step
                result = await self.executor._execute_step(step)
                if not result.success:
                    err_msg = f"I got stuck at step: {step.description} due to: {result.error_message}"
                    if self.app:
                        self.app._speak_sync(f"Step failed: {result.error_message}")
                    return err_msg, self.current_lang

                # Parameter propagation
                if result.data and "response_content" in result.data:
                    content = result.data["response_content"]
                    for next_step in plan.steps:
                        if next_step.step_id != step.step_id:
                            params = next_step.action.parameters
                            for k, v in list(params.items()):
                                if isinstance(v, str) and "{response_content}" in v:
                                    params[k] = v.replace("{response_content}", content)
                                if k == "content" and (not v or v == "JARVIS OS Generated Document"):
                                    params[k] = content

                if result.data and "output_pdf" in result.data:
                    pdf_path = result.data["output_pdf"]
                    for next_step in plan.steps:
                        if next_step.step_id != step.step_id:
                            params = next_step.action.parameters
                            for k, v in list(params.items()):
                                if isinstance(v, str) and "{output_pdf}" in v:
                                    params[k] = v.replace("{output_pdf}", pdf_path)
                                if k == "filepath" and ("attachment" in k or "file" in k or not v):
                                    params[k] = pdf_path

            success_msg = "Completed successfully, boss."
            return success_msg, self.current_lang

        else:
            try:
                system_prompt = get_system_prompt(self.current_lang)
                response = await llm.generate_response(user_text, system_prompt=system_prompt)
                self.history.append({"role": "user", "content": user_text})
                self.history.append({"role": "assistant", "content": response})
                if len(self.history) > 16:
                    self.history = self.history[-16:]
                return response, self.current_lang
            except Exception as e:
                logger.error(f"Knowledge query failed: {e}")
                return self._rule_think(user_text), self.current_lang

    def _rule_think(self, text: str) -> str:
        if re.search(r"\b(hello|hi|hey|good morning|good evening)\b", text.lower()):
            return L(
                f"Hello! I'm JARVIS. {get_datetime('english')} What can I do for you?",
                f"Namaste! Main JARVIS hoon. {get_datetime('hindi')} Kya karna hai?",
            )
        return L(
            "I didn't understand. Try: 'open Chrome', 'open camera and take a photo', 'what time is it', 'search Python'",
            "Samajh nahi aaya. Try: 'Chrome kholo', 'camera kholo', 'time batao', 'note banao...'",
        )


def get_greeting(lang: str = "english") -> str:
    now = datetime.now()
    period = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
    return (
        f"Hello! Good {period}! I'm JARVIS. "
        "Just speak — tell me what to do. Open apps, take photos, search, anything."
    )


# UI Theme — clean voice-first
C = {
    "bg": "#0B0F19",       # Deep slate black
    "card": "#161D30",     # Dark card background
    "card2": "#1F2942",    # Medium card background
    "card_border": "#24324F", # Subtle border/divider line
    "accent": "#6366F1",   # Indigo-500
    "accent_light": "#818CF8", # Indigo-400
    "cyan": "#06B6D4",     # Cyan-500
    "green": "#10B981",    # Emerald-500
    "red": "#EF4444",      # Red-500
    "orange": "#F59E0B",   # Amber-500
    "text": "#F8FAFC",     # Slate-50
    "muted": "#64748B",    # Slate-500
    "user": "#A5B4FC",     # Indigo light
    "jarvis": "#22D3EE",   # Cyan light
}


class JarvisApp:
    def __init__(self):
        self.brain = Brain()
        self.brain.app = self
        self.listening = False
        self.auto_listen = True
        self.speaking = False
        self.running = True
        self.dictate_mode = False
        self.current_lang = APP_LANG
        self._pulse_id = None
        self._auto_mic_after_id = None
        self._task_gen = 0
        self._working = False
        self._last_spoken = ""
        self._mic_ready_at = 0.0

        self.root = tk.Tk()
        self.root.title("JARVIS — Voice Assistant")
        self.root.geometry("720x820")
        self.root.configure(bg=C["bg"])
        self.root.minsize(700, 650)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self.root.after(300, self._startup)
        self.root.mainloop()

    def _startup(self):
        ok, msg = self.brain.verify_ai()
        self._set_status("AI Connected" if ok else msg[:20], C["green"] if ok else C["red"])
        if not self.brain.has_ai():
            self.root.after(800, self._settings)

        greeting = get_greeting("english")
        self._add("JARVIS", greeting)
        threading.Thread(target=self._speak_and_listen, args=(greeting, "english", 0), daemon=True).start()

    def _cancel_timers(self):
        if self._auto_mic_after_id:
            try:
                self.root.after_cancel(self._auto_mic_after_id)
            except Exception:
                pass
            self._auto_mic_after_id = None
        if self._pulse_id:
            try:
                self.root.after_cancel(self._pulse_id)
            except Exception:
                pass
            self._pulse_id = None

    def _interrupt(self):
        """Stop speech, cancel in-progress task, prepare for new input."""
        self._task_gen += 1
        request_cancel()
        stop_speaking()
        self._cancel_timers()
        self.speaking = False
        self._working = False

    def _speak_and_listen(self, text: str, lang: str, task_gen: int):
        if task_gen != self._task_gen:
            return
        self._last_spoken = text
        self.speaking = True
        self.root.after(0, lambda: self._set_orb_state("speaking"))
        speak(text, lang=lang, block=True)
        self.speaking = False
        self.root.after(0, lambda: self._set_orb_state("idle"))
        if task_gen != self._task_gen:
            return
        # Wait so mic does NOT hear JARVIS own voice from speakers
        self._mic_ready_at = time.time() + 3.0
        if self.auto_listen and self.running:
            self._auto_mic_after_id = self.root.after(3000, self._auto_mic)

    def _auto_mic(self):
        if not self.running or not self.auto_listen:
            return
        if time.time() < self._mic_ready_at:
            wait_ms = int((self._mic_ready_at - time.time()) * 1000) + 200
            self._auto_mic_after_id = self.root.after(max(wait_ms, 200), self._auto_mic)
            return
        if self.speaking or self._working or self.listening:
            self._auto_mic_after_id = self.root.after(400, self._auto_mic)
            return
        self._toggle_mic(auto=True)

    def _on_close(self):
        self.running = False
        self._interrupt()
        self.root.destroy()

    def _settings(self):
        key = simpledialog.askstring("Groq API Key", "Groq key (free): console.groq.com", show="*")
        if key and key.strip():
            self.brain.set_key(key.strip())
            ok, msg = self.brain.verify_ai()
            if ok:
                self._add("JARVIS", "AI connected!")
                self._set_status("AI Connected", C["green"])

    def _build_ui(self):
        # Header
        header = tk.Frame(self.root, bg=C["card"], height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Draw a line border under header
        border = tk.Frame(self.root, bg=C["card_border"], height=1)
        border.pack(fill="x")

        tk.Label(header, text="JARVIS OS", font=("Segoe UI", 18, "bold"),
                 bg=C["card"], fg=C["cyan"]).pack(side="left", padx=18, pady=10)
        tk.Label(header, text="v3.0.0 Pro", font=("Segoe UI", 9, "bold"),
                 bg=C["card2"], fg=C["text"], padx=6, pady=2).pack(side="left", padx=4, pady=16)

        self.status_dot = tk.Label(header, text="● Ready", font=("Segoe UI", 10, "bold"),
                                   bg=C["card"], fg=C["green"])
        self.status_dot.pack(side="right", padx=16)

        tk.Button(header, text="⚙ Settings", font=("Segoe UI", 9), bg=C["card2"], fg=C["text"],
                  relief="flat", bd=0, padx=10, command=self._settings, cursor="hand2",
                  activebackground=C["accent"]).pack(side="right", padx=8, pady=12)

        # Chat
        chat_wrap = tk.Frame(self.root, bg=C["bg"])
        chat_wrap.pack(fill="both", expand=True, padx=16, pady=(12, 8))

        self.chat = scrolledtext.ScrolledText(
            chat_wrap, wrap=tk.WORD, font=("Segoe UI", 12),
            bg=C["card"], fg=C["text"], relief="flat", padx=18, pady=16,
            state="disabled", insertbackground=C["cyan"],
            selectbackground=C["accent"], borderwidth=0,
            highlightbackground=C["card_border"], highlightthickness=1
        )
        self.chat.pack(fill="both", expand=True)

        # Align text bubbles: user text bubble is shifted right, jarvis bubble is shifted left
        self.chat.tag_config("user", foreground="#FFFFFF", lmargin1=80, lmargin2=80, rmargin=10, font=("Segoe UI", 12, "bold"))
        self.chat.tag_config("jarvis", foreground=C["cyan"], lmargin1=10, lmargin2=10, rmargin=80)
        self.chat.tag_config("action", foreground=C["green"], font=("Segoe UI", 11, "italic"))
        self.chat.tag_config("sys", foreground=C["muted"], font=("Segoe UI", 10, "italic"))

        # Live status
        status_frame = tk.Frame(self.root, bg=C["card2"], padx=20, pady=14, 
                                highlightbackground=C["card_border"], highlightthickness=1)
        status_frame.pack(fill="x", padx=16, pady=(0, 8))

        self.live_label = tk.Label(
            status_frame,
            text="Speak your command or check setting options",
            font=("Segoe UI", 12, "bold"), bg=C["card2"], fg=C["text"],
            anchor="center", wraplength=400,
        )
        self.live_label.pack(fill="x")

        self.heard_label = tk.Label(
            status_frame, text="", font=("Segoe UI", 11, "italic"),
            bg=C["card2"], fg=C["accent_light"], anchor="center", wraplength=400,
        )
        self.heard_label.pack(fill="x", pady=(6, 0))

        self.progress = tk.Canvas(status_frame, height=3, bg=C["card2"], highlightthickness=0)
        self.progress.pack(fill="x", pady=(10, 0))
        self._progress_bar = self.progress.create_rectangle(0, 0, 0, 3, fill=C["cyan"], width=0)

        # Big mic area — Siri-like glowing Voice Orb
        mic_area = tk.Frame(self.root, bg=C["bg"], pady=8)
        mic_area.pack(fill="x", padx=16, pady=(0, 10))

        self.mic_canvas = tk.Canvas(mic_area, width=110, height=110, bg=C["bg"], highlightthickness=0)
        self.mic_canvas.pack(pady=4)

        # Draw a beautiful pulsing interactive voice orb
        self.mic_ring = self.mic_canvas.create_oval(10, 10, 100, 100, fill=C["card"], outline=C["accent"], width=3)
        self.mic_orb = self.mic_canvas.create_oval(22, 22, 88, 88, fill=C["accent"], outline="", width=0)
        self.mic_icon = self.mic_canvas.create_text(55, 55, text="🎤", font=("Segoe UI", 26), fill="white")

        # Bind hover and click events
        for item in (self.mic_ring, self.mic_orb, self.mic_icon):
            self.mic_canvas.tag_bind(item, "<Button-1>", lambda e: self._toggle_mic(auto=False))
            self.mic_canvas.tag_bind(item, "<Enter>", lambda e: self.mic_canvas.itemconfig(self.mic_ring, outline=C["accent_light"], width=4))
            self.mic_canvas.tag_bind(item, "<Leave>", lambda e: self.mic_canvas.itemconfig(self.mic_ring, outline=C["accent"], width=3))

        tk.Label(mic_area, text="Tap Voice Orb to talk to JARVIS",
                 font=("Segoe UI", 9), bg=C["bg"], fg=C["muted"]).pack()

        # Footer Checkbuttons
        footer = tk.Frame(self.root, bg=C["bg"])
        footer.pack(fill="x", padx=16, pady=(0, 12))

        self.auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(footer, text="Auto listen after I speak", variable=self.auto_var,
                       bg=C["bg"], fg=C["muted"], selectcolor=C["card2"],
                       activebackground=C["bg"], font=("Segoe UI", 9),
                       command=lambda: setattr(self, "auto_listen", self.auto_var.get())).pack()

        startup_file = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "JARVIS.bat"
        self.startup_var = tk.BooleanVar(value=startup_file.exists())
        tk.Checkbutton(footer, text="Launch JARVIS on Windows Startup", variable=self.startup_var,
                       bg=C["bg"], fg=C["muted"], selectcolor=C["card2"],
                       activebackground=C["bg"], font=("Segoe UI", 9),
                       command=self._toggle_startup).pack(pady=(4, 0))

    def _set_status(self, text: str, color: str):
        self.status_dot.configure(text=f"● {text}", fg=color)

    def _set_orb_state(self, state: str):
        if not hasattr(self, "mic_canvas"):
            return
        if state == "idle":
            self.mic_canvas.itemconfig(self.mic_orb, fill=C["accent"])
            self.mic_canvas.itemconfig(self.mic_ring, outline=C["accent"], width=3)
            self.mic_canvas.itemconfig(self.mic_icon, text="🎤")
        elif state == "listening":
            self.mic_canvas.itemconfig(self.mic_orb, fill=C["red"])
            self.mic_canvas.itemconfig(self.mic_ring, outline=C["red"], width=4)
            self.mic_canvas.itemconfig(self.mic_icon, text="🔴")
        elif state == "thinking":
            self.mic_canvas.itemconfig(self.mic_orb, fill=C["orange"])
            self.mic_canvas.itemconfig(self.mic_ring, outline=C["orange"], width=3)
            self.mic_canvas.itemconfig(self.mic_icon, text="⏳")
        elif state == "speaking":
            self.mic_canvas.itemconfig(self.mic_orb, fill=C["cyan"])
            self.mic_canvas.itemconfig(self.mic_ring, outline=C["cyan"], width=3)
            self.mic_canvas.itemconfig(self.mic_icon, text="🔊")

    def _animate_progress(self, active: bool):
        if not active:
            self.progress.coords(self._progress_bar, 0, 0, 0, 4)
            return
        w = self.progress.winfo_width() or 700

        def step(p=0):
            if p > w + 50:
                self._animate_progress(True)
                return
            self.progress.coords(self._progress_bar, 0, 0, min(p, w), 4)
            self.root.after(18, lambda: step(p + 12))

        step()

    def _pulse_mic(self, on=True, step=0):
        if not on or not self.listening:
            self._set_orb_state("idle")
            return
        colors_orb = [C["red"], "#fb7185", C["red"], "#dc2626"]
        colors_ring = ["#fca5a5", C["red"], "#fca5a5", "#b91c1c"]
        self.mic_canvas.itemconfig(self.mic_orb, fill=colors_orb[step % len(colors_orb)])
        self.mic_canvas.itemconfig(self.mic_ring, outline=colors_ring[step % len(colors_ring)], width=3 + (step % 2) * 2)
        self._pulse_id = self.root.after(250, lambda: self._pulse_mic(True, step + 1))

    def _is_echo_or_junk(self, text: str) -> bool:
        """Ignore speaker echo / junk — not real user commands."""
        t = re.sub(r"[^\w\s']", "", text.lower()).strip()
        if len(t) < 4:
            return True
        junk = (
            "thank you", "thanks for watching", "subscribe", "hello good",
            "im jarvis", "just speak", "voice only", "tap mic",
            "good morning", "good afternoon", "good evening",
        )
        if any(j in t for j in junk):
            return True
        if self._last_spoken:
            spoken = re.sub(r"[^\w\s']", "", self._last_spoken.lower())
            if t in spoken or (len(t) > 10 and spoken in t):
                return True
            tw, sw = set(t.split()), set(spoken.split())
            if len(tw) >= 3 and len(tw & sw) / max(len(tw), 1) > 0.55:
                return True
        return False

    def _toggle_mic(self, auto=False):
        if self.listening:
            return
        if auto and time.time() < self._mic_ready_at:
            wait_ms = int((self._mic_ready_at - time.time()) * 1000) + 200
            self._auto_mic_after_id = self.root.after(max(wait_ms, 200), self._auto_mic)
            return
        if self.speaking or self._working:
            self._interrupt()
            self.live_label.configure(text="Stopped — listening now...", fg=C["orange"])
        clear_cancel()
        self.listening = True
        self._set_orb_state("listening")
        self._set_status("LISTENING", C["red"])
        self.live_label.configure(text="🎤 LISTENING — speak now!", fg=C["accent2"])
        self.heard_label.configure(text="")
        self._animate_progress(True)
        self._pulse_mic(True)
        listen_gen = self._task_gen
        threading.Thread(target=self._listen_and_send, args=(auto, listen_gen), daemon=True).start()

    def _listen_and_send(self, auto=False, listen_gen=0):
        api_key = self.brain.api_key
        text, err = "", ""

        def on_status(msg: str):
            if "Heard:" in msg or "✅" in msg:
                heard = msg.replace("✅ Heard:", "").replace("✅ Suna:", "").strip()
                self.root.after(0, lambda h=heard: self.heard_label.configure(text=f'"{h}"'))
            elif "Listening" in msg or "Recording" in msg or "█" in msg:
                self.root.after(0, lambda m=msg: self.live_label.configure(text=m, fg=C["accent2"]))
            elif "Processing" in msg:
                self.root.after(0, lambda m=msg: self.live_label.configure(text=m, fg=C["orange"]))
            else:
                self.root.after(0, lambda m=msg: self.live_label.configure(text=m, fg=C["muted"]))

        def should_stop():
            return listen_gen != self._task_gen or not self.running

        try:
            text, err = listen_voice_only(
                api_key, timeout_sec=12, lang=APP_LANG,
                on_status=on_status, should_stop=should_stop,
            )
        finally:
            if listen_gen == self._task_gen:
                self.listening = False
                self._pulse_mic(False)
                self._animate_progress(False)
                self.root.after(0, lambda: self._set_orb_state("idle"))

        if listen_gen != self._task_gen:
            return

        if text and not self._is_echo_or_junk(text):
            self.root.after(0, lambda t=text: self._on_voice_result(t))
        elif text and self._is_echo_or_junk(text):
            self.root.after(0, lambda: self.live_label.configure(
                text="Heard echo — speak again clearly", fg=C["orange"]))
            self.root.after(0, lambda: self.heard_label.configure(text=""))
            if self.auto_listen:
                self._auto_mic_after_id = self.root.after(2000, self._auto_mic)
        elif err == "Interrupted":
            pass
        else:
            fail = err or L("Didn't hear you — tap mic and speak louder", "Sunai nahi diya")
            self.root.after(0, lambda: self.live_label.configure(text=fail, fg=C["red"]))
            self.root.after(0, lambda: self.heard_label.configure(text=""))
            self.root.after(0, lambda: self._set_status("Tap mic", C["orange"]))
            if self.auto_listen:
                self._auto_mic_after_id = self.root.after(2000, self._auto_mic)

    def _on_voice_result(self, text: str):
        self.heard_label.configure(text=f'"{text}"')
        self.live_label.configure(text="Got it — doing it now...", fg=C["green"])
        self._add("user_heard", text)
        self._process(text)

    def _process(self, text: str):
        self._interrupt()
        clear_cancel()
        task_gen = self._task_gen
        self.current_lang = APP_LANG
        self._add("You", text, user=True)
        self.live_label.configure(text=f"Working: {text[:60]}...", fg=C["orange"])
        self._set_status("Working", C["orange"])
        self._working = True
        self._animate_progress(True)
        threading.Thread(target=self._reply, args=(text, task_gen), daemon=True).start()

    def _reply(self, text, task_gen):
        if task_gen != self._task_gen:
            return
        self.root.after(0, lambda: self._set_orb_state("thinking"))
        try:
            response, lang = self.brain.think(text)
            self.current_lang = lang
        except Exception as e:
            response, lang = f"Error: {e}", self.current_lang

        if task_gen != self._task_gen:
            self.root.after(0, lambda: self._set_orb_state("idle"))
            return

        if not response or not str(response).strip():
            response = L("I heard you but couldn't respond. Try again.", "Sunai diya lekin jawab nahi mila. Dubara bolo.")

        self._working = False
        self.root.after(0, lambda: self._animate_progress(False))
        self.root.after(0, lambda: self._set_orb_state("idle"))

        if response == "GOODBYE_SIGNAL":
            bye = L("Goodbye!", "Namaste! Alvida!")
            self.root.after(0, lambda: self._add("JARVIS", bye))
            speak(bye, lang=lang, block=True)
            self.root.after(500, self.root.destroy)
            return

        is_action = any(w in response.lower() for w in ("opened", "open", "search", "created", "click", "saved", "closed", "done", "typed", "screenshot", "camera", "cancelled"))
        self.root.after(0, lambda r=response: self._add("JARVIS", r, action=is_action))
        self.root.after(0, lambda r=response: self.live_label.configure(
            text=f"✅ Done: {r[:70]}", fg=C["green"]))
        self.root.after(0, lambda: self._set_status("Ready", C["green"]))
        threading.Thread(target=self._speak_and_listen, args=(response, lang, task_gen), daemon=True).start()

    def _add(self, sender, msg, user=False, action=False):
        self.chat.configure(state="normal")
        t = datetime.now().strftime("%I:%M %p")

        if sender == "user_heard":
            self.chat.insert("end", f"\n", "sys")
            self.chat.insert("end", f"  🎤 Heard: ", "sys")
            self.chat.insert("end", f"{msg}\n", "user")
        elif user:
            self.chat.insert("end", f"\n┌─ You [{t}]\n", "user")
            self.chat.insert("end", f"│  {msg}\n", "user")
            self.chat.insert("end", f"└─\n", "user")
        else:
            tag = "action" if action else "jarvis"
            icon = "⚡" if action else "🤖"
            self.chat.insert("end", f"\n{icon} JARVIS [{t}]\n", tag)
            self.chat.insert("end", f"  {msg}\n", tag)

        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _speak_sync(self, text: str, lang: str = "english"):
        self.root.after(0, lambda: self._add("JARVIS", text))
        self.root.after(0, lambda: self._set_orb_state("speaking"))
        speak(text, lang=lang, block=True)
        self.root.after(0, lambda: self._set_orb_state("idle"))

    def _ask_confirmation(self, description: str) -> bool:
        result = []
        event = threading.Event()

        def show_dialog():
            res = messagebox.askyesno(
                "JARVIS Confirmation Gate",
                f"JARVIS is about to perform a sensitive action:\n\n{description}\n\nDo you approve?"
            )
            result.append(res)
            event.set()

        self.root.after(0, show_dialog)
        event.wait()
        return result[0]

    def _toggle_startup(self):
        enable = self.startup_var.get()
        msg = set_startup(enable)
        self.root.after(0, lambda: self._add("sys", msg))

    def _graceful_shutdown(self):
        self._speak_sync("Closing open applications and saving your work, boss.")
        
        # Send Alt+F4 to gracefully close applications and Enter to auto-save default dialogs
        for _ in range(5):
            send_keys(0x12, 0x73) # Alt+F4
            time.sleep(0.5)
            send_keys(0x0D) # Enter
            time.sleep(0.3)
            
        self._speak_sync("done boss everything i am going by bye")
        time.sleep(1.5)
        subprocess.run("shutdown /s /t 10", shell=True)
        self.root.after(0, self._on_close)


if __name__ == "__main__":
    JarvisApp()
