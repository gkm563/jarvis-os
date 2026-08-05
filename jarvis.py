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


from voice_engine import speak, listen_best, ensure_voice_deps, VOICES

ensure_voice_deps()


def listen_voice(timeout_sec: int = 8, lang: str = "auto", api_key: str = "", on_status=None, on_partial=None) -> tuple[str, str]:
    return listen_best(api_key, timeout_sec, lang, on_status=on_status, on_partial=on_partial)


def listen_and_type_live(entry_widget, root, timeout_sec: int = 8, lang: str = "auto", api_key: str = "", on_chat=None) -> tuple[str, str]:
    """Listen + live type in entry box. Returns (text, error)."""
    status = {"last": ""}

    def on_status(msg: str):
        status["last"] = msg
        root.after(0, lambda m=msg: _update_entry(entry_widget, m))

    def on_partial(text: str):
        root.after(0, lambda t=text: _update_entry(entry_widget, f"📝 {t}"))

    text, err = listen_best(api_key, timeout_sec, lang, on_status=on_status, on_partial=on_partial)

    if text:
        root.after(0, lambda t=text: _update_entry(entry_widget, t))
        if on_chat:
            root.after(0, lambda t=text: on_chat(f'🎤 Heard: "{t}"'))
        return text, ""
    return "", err or status["last"] or L("Didn't hear anything", "Sunai nahi diya")


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
    """Camera kholo, photo click karo, photos folder kholo."""
    subprocess.Popen("start microsoft.windows.camera:", shell=True)
    time.sleep(4.0)
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "Start-Sleep -Milliseconds 800; "
        '[System.Windows.Forms.SendKeys]::SendWait(" "); '
        "Start-Sleep -Milliseconds 600; "
        '[System.Windows.Forms.SendKeys]::SendWait(" ")'
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], shell=True, capture_output=True)
    time.sleep(1.5)
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

        # ALWAYS try local action first — AI se pehle, taaki sirf "theek hai" na bole
        action = try_local_action(user_text)
        if action:
            reply = L(f"Done! {action}", f"Theek hai! {action}")
            self.history.append({"role": "user", "content": user_text})
            self.history.append({"role": "assistant", "content": reply})
            if len(self.history) > 16:
                self.history = self.history[-16:]
            return reply, self.current_lang

        if self.has_ai():
            result = self._ai_think(user_text)
            if result:
                return result, self.current_lang

        return self._rule_think(user_text), self.current_lang

    def _ai_think(self, user_text: str) -> str | None:
        # Local action already tried in think() — ab sirf chat
        self.history.append({"role": "user", "content": user_text})
        if len(self.history) > 16:
            self.history = self.history[-16:]

        messages = [{"role": "system", "content": get_system_prompt(self.current_lang)}] + self.history
        data = self._groq_request(messages, tools=None)

        if not data:
            self.history.pop()
            return None
        if "error" in data:
            self.history.pop()
            # Fallback on API error
            return self._rule_think(user_text)

        reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if reply:
            self.history.append({"role": "assistant", "content": reply})
            return reply

        self.history.pop()
        return self._rule_think(user_text) or L("Sorry, I didn't understand. Please try again.", "Sorry, samajh nahi aaya. Dubara bolo.")

    def _rule_think(self, text: str) -> str:
        lang = self.current_lang
        action = try_local_action(text)
        if action:
            return action
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
        f"Hello! Good {period}! I'm JARVIS, your personal assistant. "
        "Speak in English — I'll listen, talk back, and do what you ask. "
        "Try: open Chrome, take a photo, search something, or create a note!"
    )


# UI Theme
C = {
    "bg": "#0b0f19", "card": "#131a2b", "card2": "#1a2236",
    "accent": "#6366f1", "accent2": "#22d3ee", "green": "#10b981",
    "red": "#ef4444", "orange": "#f59e0b", "text": "#e2e8f0", "muted": "#64748b",
    "user": "#a78bfa", "jarvis": "#38bdf8",
}


class JarvisApp:
    def __init__(self):
        self.brain = Brain()
        self.listening = False
        self.auto_listen = True
        self.speaking = False
        self.running = True
        self.dictate_mode = False
        self.current_lang = APP_LANG
        self._pulse_id = None

        self.root = tk.Tk()
        self.root.title("JARVIS AI Assistant")
        self.root.geometry("820x780")
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
        threading.Thread(target=self._speak_and_listen, args=(greeting, "english"), daemon=True).start()

    def _speak_and_listen(self, text: str, lang: str):
        self.speaking = True
        speak(text, lang=lang, block=True)
        self.speaking = False
        # TTS ke baad thoda wait — phir mic on (echo avoid)
        if self.auto_listen and self.running:
            self.root.after(1200, self._auto_mic)

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
                self._add("JARVIS", "AI connected!")
                self._set_status("AI Connected", C["green"])

    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self.root, bg=C["card"], height=56)
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(header, text="⚡ JARVIS", font=("Segoe UI", 18, "bold"),
                 bg=C["card"], fg=C["accent2"]).pack(side="left", padx=20, pady=12)
        tk.Label(header, text="AI Assistant", font=("Segoe UI", 11),
                 bg=C["card"], fg=C["muted"]).pack(side="left", pady=14)

        self.status_dot = tk.Label(header, text="● Ready", font=("Segoe UI", 10, "bold"),
                                    bg=C["card"], fg=C["orange"])
        self.status_dot.pack(side="right", padx=16)

        self.lang_label = tk.Label(header, text="🇬🇧 English", font=("Segoe UI", 10),
                                    bg=C["card2"], fg=C["text"], padx=8, pady=2)
        self.lang_label.pack(side="right", padx=6, pady=14)

        tk.Button(header, text="⚙", font=("Segoe UI", 12), bg=C["card2"], fg=C["muted"],
                  relief="flat", padx=8, command=self._settings).pack(side="right", padx=4, pady=12)

        # ── Chat area ──
        chat_wrap = tk.Frame(self.root, bg=C["bg"])
        chat_wrap.pack(fill="both", expand=True, padx=14, pady=(10, 6))

        self.chat = scrolledtext.ScrolledText(
            chat_wrap, wrap=tk.WORD, font=("Segoe UI", 12),
            bg=C["card"], fg=C["text"], relief="flat", padx=16, pady=14,
            state="disabled", insertbackground=C["accent2"],
            selectbackground=C["accent"],
        )
        self.chat.pack(fill="both", expand=True)
        self.chat.tag_config("user", foreground=C["user"], font=("Segoe UI", 12, "bold"))
        self.chat.tag_config("jarvis", foreground=C["jarvis"])
        self.chat.tag_config("action", foreground=C["green"], font=("Segoe UI", 11, "italic"))
        self.chat.tag_config("sys", foreground=C["muted"], font=("Segoe UI", 10, "italic"))

        # ── Live status bar (interactive feedback) ──
        status_frame = tk.Frame(self.root, bg=C["card2"], padx=14, pady=10)
        status_frame.pack(fill="x", padx=14, pady=(0, 6))

        self.live_label = tk.Label(
            status_frame,
            text="👂 Press mic or type — I listen and execute your commands",
            font=("Segoe UI", 11, "bold"), bg=C["card2"], fg=C["accent2"],
            anchor="w", wraplength=760,
        )
        self.live_label.pack(fill="x")

        self.progress = tk.Canvas(status_frame, height=3, bg=C["card2"], highlightthickness=0)
        self.progress.pack(fill="x", pady=(6, 0))
        self._progress_bar = self.progress.create_rectangle(0, 0, 0, 3, fill=C["accent"], width=0)

        # ── Input bar ──
        bottom = tk.Frame(self.root, bg=C["card"], pady=12)
        bottom.pack(fill="x", padx=14, pady=(0, 8))

        self.mic_btn = tk.Button(
            bottom, text="🎤", font=("Segoe UI", 20),
            bg=C["accent"], fg="white", relief="flat", width=3, height=1,
            cursor="hand2", activebackground="#818cf8",
            command=lambda: self._toggle_mic(auto=False),
        )
        self.mic_btn.pack(side="left", padx=(10, 6))

        entry_wrap = tk.Frame(bottom, bg=C["card2"], padx=2, pady=2)
        entry_wrap.pack(side="left", fill="x", expand=True, padx=4)

        self.entry = tk.Entry(
            entry_wrap, font=("Segoe UI", 13), bg=C["card2"], fg=C["text"],
            insertbackground=C["accent2"], relief="flat",
        )
        self.entry.pack(fill="x", ipady=12, padx=10)
        self.entry.bind("<Return>", lambda e: self._send())
        self.entry.focus()

        tk.Button(bottom, text="➤ GO", font=("Segoe UI", 11, "bold"),
                  bg=C["green"], fg="white", relief="flat", padx=18, pady=10,
                  cursor="hand2", activebackground="#059669",
                  command=self._send).pack(side="right", padx=(4, 10))

        # ── Quick actions ──
        chips = tk.Frame(self.root, bg=C["bg"])
        chips.pack(fill="x", padx=14, pady=(0, 10))

        actions = [
            ("📷 Camera+Photo", "open camera and take a photo"),
            ("🔍 Search", "search Python"),
            ("📝 Note", "create note meeting tomorrow"),
            ("⏰ Time", "what time is it"),
            ("🌐 Chrome", "open chrome"),
        ]
        for label, cmd in actions:
            tk.Button(
                chips, text=label, font=("Segoe UI", 10, "bold"),
                bg=C["card2"], fg=C["text"], relief="flat",
                padx=12, pady=6, cursor="hand2", activebackground=C["accent"],
                command=lambda c=cmd: self._quick(c),
            ).pack(side="left", padx=4)

        # ── Footer toggles ──
        footer = tk.Frame(self.root, bg=C["bg"])
        footer.pack(fill="x", padx=14, pady=(0, 8))

        self.auto_var = tk.BooleanVar(value=True)
        tk.Checkbutton(footer, text="🔄 Auto Listen", variable=self.auto_var,
                       bg=C["bg"], fg=C["muted"], selectcolor=C["card2"],
                       activebackground=C["bg"], font=("Segoe UI", 9),
                       command=lambda: setattr(self, "auto_listen", self.auto_var.get())).pack(side="left")

        tk.Label(footer, text="  |  ", bg=C["bg"], fg=C["muted"]).pack(side="left")
        tk.Label(footer, text="💡 Speak clearly — commands run automatically",
                 bg=C["bg"], fg=C["green"], font=("Segoe UI", 9)).pack(side="left")

    def _set_status(self, text: str, color: str):
        self.status_dot.configure(text=f"● {text}", fg=color)

    def _animate_progress(self, active: bool):
        if not active:
            self.progress.coords(self._progress_bar, 0, 0, 0, 3)
            return
        w = self.progress.winfo_width() or 700

        def step(p=0):
            if p > w + 50:
                self._animate_progress(True)
                return
            self.progress.coords(self._progress_bar, 0, 0, min(p, w), 3)
            self.root.after(18, lambda: step(p + 12))

        step()

    def _pulse_mic(self, on=True, step=0):
        if not on or not self.listening:
            self.mic_btn.configure(bg=C["accent"])
            return
        colors = [C["red"], "#f87171", C["red"], "#dc2626"]
        self.mic_btn.configure(bg=colors[step % len(colors)])
        self._pulse_id = self.root.after(250, lambda: self._pulse_mic(True, step + 1))

    def _type_entry_to_screen(self):
        text = self.entry.get().strip()
        if text:
            msg = type_on_screen(text)
            self._add("JARVIS", msg)

    def _toggle_mic(self, auto=False):
        if self.listening:
            return
        if self.speaking:
            self.root.after(600, lambda: self._toggle_mic(auto))
            return
        self.listening = True
        self.mic_btn.configure(text="🔴")
        self._set_status("LISTENING...", C["red"])
        self.live_label.configure(text="🎤 Speak now! Watch the volume bars...", fg=C["accent2"])
        self._animate_progress(True)
        self._pulse_mic(True)
        self.entry.delete(0, tk.END)
        threading.Thread(target=self._listen_and_send, args=(auto,), daemon=True).start()

    def _listen_and_send(self, auto=False):
        api_key = self.brain.api_key

        def on_live(msg):
            self.root.after(0, lambda m=msg: self.live_label.configure(text=m, fg=C["accent2"]))
            self.root.after(0, lambda m=msg: _update_entry(self.entry, m) if "Suna:" in m or "📝" in m else None)

        text, err = listen_and_type_live(
            self.entry, self.root,
            timeout_sec=8, lang=APP_LANG, api_key=api_key,
        )

        self.listening = False
        self._pulse_mic(False)
        self._animate_progress(False)
        self.root.after(0, lambda: self.mic_btn.configure(text="🎤", bg=C["accent"]))

        if text:
            self.root.after(0, lambda t=text: self._on_voice_result(t))
        else:
            fail = err or L("Didn't hear anything", "Sunai nahi diya")
            self.root.after(0, lambda: self.live_label.configure(text=f"❌ {fail}", fg=C["red"]))
            self.root.after(0, lambda: self._set_status("Mic fail", C["red"]))
            if self.auto_listen:
                self.root.after(3000, self._auto_mic)

    def _on_voice_result(self, text: str):
        self.current_lang = APP_LANG
        self.lang_label.configure(text="🇬🇧 English")

        self.entry.delete(0, tk.END)
        self.entry.insert(0, text)
        self.live_label.configure(text=f'✅ Heard: "{text}"', fg=C["green"])
        self._add("user_heard", text)
        self._process(text)  # ALWAYS execute — no dictate block

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
        self.current_lang = APP_LANG
        self.lang_label.configure(text="🇬🇧 English")
        self._add("You", text, user=True)
        self.live_label.configure(text=f"⚡ Working on: {text[:50]}...", fg=C["orange"])
        self._set_status("Working...", C["orange"])
        self._animate_progress(True)
        threading.Thread(target=self._reply, args=(text,), daemon=True).start()

    def _reply(self, text):
        try:
            response, lang = self.brain.think(text)
            self.current_lang = lang
        except Exception as e:
            response, lang = f"Error: {e}", self.current_lang

        if not response or not str(response).strip():
            response = L("I heard you but couldn't respond. Try again.", "Sunai diya lekin jawab nahi mila. Dubara bolo.")

        self.root.after(0, lambda: self._animate_progress(False))

        if response == "GOODBYE_SIGNAL":
            bye = L("Goodbye!", "Namaste! Alvida!")
            self.root.after(0, lambda: self._add("JARVIS", bye))
            speak(bye, lang=lang, block=True)
            self.root.after(500, self.root.destroy)
            return

        is_action = any(w in response.lower() for w in ("opened", "open", "search", "created", "click", "saved", "closed", "done", "typed", "screenshot", "camera"))
        self.root.after(0, lambda r=response: self._add("JARVIS", r, action=is_action))
        self.root.after(0, lambda r=response: self.live_label.configure(
            text=f"✅ Done: {r[:70]}", fg=C["green"]))
        self.root.after(0, lambda: self._set_status("Ready", C["green"]))
        threading.Thread(target=self._speak_and_listen, args=(response, lang), daemon=True).start()

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


if __name__ == "__main__":
    JarvisApp()
