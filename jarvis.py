"""
JARVIS - Simple AI Chat Agent
Run: python jarvis.py
Bas type karo ya bolo, JARVIS samjhega aur kaam karega.
"""

import tkinter as tk
from tkinter import scrolledtext
import threading
import subprocess
import webbrowser
import os
import time
import re
import json
import urllib.request
import urllib.parse
from datetime import datetime


# ─────────────────────────────────────────────
# VOICE: Windows built-in SAPI
# ─────────────────────────────────────────────
def speak(text: str):
    clean = re.sub(r"[✅❌⚠️🔊🔉🔇📸🤖🧑●•→]", "", text)
    try:
        import win32com.client
        sp = win32com.client.Dispatch("SAPI.SpVoice")
        sp.Speak(clean[:300])
    except Exception:
        pass


# ─────────────────────────────────────────────
# ACTIONS: What JARVIS can actually DO
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
    return f"{name.title()} khol diya ✓"


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
    return f"{name.title()} band kar diya ✓" if r.returncode == 0 else f"{name.title()} chal nahi raha tha."


def search_web(query: str) -> str:
    webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(query)}")
    return f"Google pe search kiya: '{query}' ✓"


def open_youtube(query: str = None) -> str:
    if query:
        webbrowser.open(f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}")
        return f"YouTube pe search kiya: '{query}' ✓"
    webbrowser.open("https://www.youtube.com")
    return "YouTube khol diya ✓"


def open_site(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"{url} khol diya ✓"


def take_screenshot() -> str:
    try:
        from PIL import ImageGrab
        path = os.path.join(os.path.expanduser("~"), "Desktop", f"ss_{int(time.time())}.png")
        ImageGrab.grab().save(path)
        return f"Screenshot le liya → Desktop/{os.path.basename(path)} ✓"
    except Exception as e:
        return f"Screenshot nahi le paya: {e}"


def volume_action(action: str) -> str:
    codes = {"up": 175, "down": 174, "mute": 173}
    code = codes.get(action, 175)
    subprocess.run(f'powershell -c "(New-Object -ComObject WScript.Shell).SendKeys([char]{code})"', shell=True)
    msgs = {"up": "Volume badha diya ✓", "down": "Volume ghata diya ✓", "mute": "Mute kar diya ✓"}
    return msgs.get(action, "Done ✓")


def get_datetime() -> str:
    now = datetime.now()
    return f"Abhi {now.strftime('%I:%M %p')} baj rahe hain. Aaj {now.strftime('%A, %d %B %Y')} hai."


def lock_pc() -> str:
    subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
    return "Screen lock kar diya ✓"


def shutdown_pc(cancel=False) -> str:
    if cancel:
        subprocess.run("shutdown /a", shell=True)
        return "Shutdown cancel kar diya ✓"
    subprocess.run("shutdown /s /t 30", shell=True)
    return "30 seconds mein PC band hoga. Rokne ke liye bolo 'shutdown cancel'."


def run_terminal(cmd: str) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        out = (r.stdout or r.stderr or "").strip()
        return out[:500] if out else "Command run ho gaya ✓"
    except subprocess.TimeoutExpired:
        return "Command timeout ho gaya."
    except Exception as e:
        return f"Error: {e}"


# ─────────────────────────────────────────────
# BRAIN: Understand what user wants
# ─────────────────────────────────────────────
def understand_and_act(text: str) -> str:
    t = text.lower().strip()

    # Greetings
    if re.search(r"\b(hello|hi|hey|hii|salam|namaste|kya hal|kaise ho|sup|wassup)\b", t):
        return ("Walaikum Assalam! Main JARVIS hoon — aapka personal AI assistant.\n"
                "Kya karna hai? Apps kholne hain, kuch search karna hai, ya koi aur kaam? 😊")

    # Farewells
    if re.search(r"\b(bye|goodbye|alvida|band karo|exit|quit|close jarvis)\b", t):
        return "GOODBYE_SIGNAL"

    # Time/Date
    if re.search(r"\b(time|baje|time kya|kitne baj|date|aaj kya|din|weekday)\b", t):
        return get_datetime()

    # Help
    if re.search(r"\b(help|madad|kya kar|features|kya karna|kya aata)\b", t):
        return (
            "Main yeh kar sakta hoon:\n\n"
            "• Apps kholo → 'Chrome kholo', 'Notepad open karo'\n"
            "• Apps band karo → 'Notepad band karo'\n"
            "• Web search → 'AI kya hai search karo'\n"
            "• YouTube → 'YouTube pe Arijit Singh'\n"
            "• Website → 'instagram.com kholo'\n"
            "• Screenshot → 'screenshot lo'\n"
            "• Volume → 'volume up', 'mute karo'\n"
            "• Time → 'time kya hai'\n"
            "• Lock → 'screen lock karo'\n"
            "• Command → 'run: ipconfig'\n\n"
            "Bas seedha bolo jaise WhatsApp pe karte ho! 😊"
        )

    # YouTube
    if "youtube" in t:
        m = re.search(r"youtube\s*(?:pe|par|mein|me|search|open|kholna|play)?\s*(.+)?", t)
        q = m.group(1).strip() if m and m.group(1) else None
        return open_youtube(q)

    # Run terminal command
    m = re.search(r"(?:run:|terminal:|cmd:|execute:|chala)\s*(.+)", t)
    if m:
        return run_terminal(m.group(1).strip())

    # Close app
    m = re.search(r"(?:close|band karo|band kro|bnd kro|band|shut)\s+(.+)", t)
    if m:
        return close_app(m.group(1).strip())

    # Open app / website
    m = re.search(r"(?:open|kholo|khol do|khol|chalo|chalao|start|launch|chhalo|open karo)\s+(.+)", t)
    if m:
        target = m.group(1).strip()
        target = re.sub(r"\b(please|plz|bhai|yaar|jaldi|abhi|karo|do|mujhe|for me)\b", "", target).strip()
        # Check if it's a URL
        if re.search(r"\.(com|in|org|net|io|co|pk|uk|edu)\b", target) or target.startswith("http"):
            return open_site(target)
        return open_app(target)

    # Web search
    m = re.search(r"(?:search|google|dhundho|dhundo|khojo|find|batao)\s+(.+)", t)
    if m:
        q = m.group(1).strip()
        q = re.sub(r"\b(karo|kar|please|plz)\b", "", q).strip()
        return search_web(q)

    # Screenshot
    if re.search(r"\b(screenshot|screen capture|screen photo|capture)\b", t):
        return take_screenshot()

    # Volume
    if re.search(r"\b(volume|awaaz|awaz|sound)\b", t):
        if re.search(r"\b(up|barhao|zyada|high|increase|tez)\b", t):
            return volume_action("up")
        if re.search(r"\b(down|ghata|kam|low|decrease|dheema)\b", t):
            return volume_action("down")
        if re.search(r"\b(mute|chup|silent|band)\b", t):
            return volume_action("mute")

    # Lock
    if re.search(r"\b(lock|lock screen|screen lock)\b", t):
        return lock_pc()

    # Shutdown
    if re.search(r"\b(cancel.*shutdown|shutdown.*cancel|shutdown roko|roko shutdown)\b", t):
        return shutdown_pc(cancel=True)
    if re.search(r"\b(shutdown|band karo pc|pc band|computer band|turn off)\b", t):
        return shutdown_pc()

    # URL detected in text
    url_m = re.search(r"((?:https?://|www\.)\S+|\S+\.(?:com|in|org|net|io|co)\S*)", t)
    if url_m:
        return open_site(url_m.group(1))

    # "Kya hai" / "explain" — answer intelligently
    if re.search(r"\b(kya hai|kya hota|explain|samjhao|bata|batao|matlab|meaning|define)\b", t):
        topic = re.sub(r"\b(kya hai|kya hota|explain|samjhao|bata|batao|matlab|meaning|define|mujhe|please|yaar)\b", "", t).strip()
        webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(topic)}")
        return f"'{topic}' ke baare mein Google pe search kar diya. Padh lo! ✓"

    # Anything else → Google it
    return search_web(text)


# ─────────────────────────────────────────────
# GUI: Simple Clean Chat Window
# ─────────────────────────────────────────────
class JarvisApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("JARVIS — AI Assistant")
        self.root.geometry("700x580")
        self.root.configure(bg="#0D1117")
        self.root.resizable(True, True)

        self._build_ui()
        self._add("JARVIS", "Assalamu Alaikum! Main JARVIS hoon — aapka AI assistant.\n\nBas seedha bolo jaise kisi dost se baat karte ho:\n→ 'Chrome kholo'\n→ 'YouTube pe koi song'\n→ 'AI kya hai'\n→ 'time kya hai'\n\nMain samjhunga aur kar dunga! 😊")
        self.root.mainloop()

    def _build_ui(self):
        # Title bar
        title_bar = tk.Frame(self.root, bg="#161B22", height=50)
        title_bar.pack(fill="x")
        tk.Label(title_bar, text="🤖  JARVIS  —  Your AI Assistant",
                 font=("Segoe UI", 14, "bold"), bg="#161B22", fg="#58A6FF").pack(side="left", padx=15, pady=12)
        tk.Label(title_bar, text="● Online", font=("Segoe UI", 10),
                 bg="#161B22", fg="#3FB950").pack(side="right", padx=15)

        # Chat window
        chat_frame = tk.Frame(self.root, bg="#0D1117")
        chat_frame.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        self.chat = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, font=("Segoe UI", 12),
            bg="#0D1117", fg="#E6EDF3", insertbackground="white",
            relief="flat", padx=12, pady=10, state="disabled",
            selectbackground="#264F78"
        )
        self.chat.pack(fill="both", expand=True)
        self.chat.tag_config("jarvis", foreground="#58A6FF")
        self.chat.tag_config("user", foreground="#3FB950")
        self.chat.tag_config("time", foreground="#484F58")
        self.chat.tag_config("divider", foreground="#21262D")

        # Input area
        bottom = tk.Frame(self.root, bg="#161B22", pady=10)
        bottom.pack(fill="x", padx=10, pady=8)

        self.entry = tk.Entry(
            bottom, font=("Segoe UI", 13), bg="#21262D", fg="#E6EDF3",
            insertbackground="white", relief="flat", bd=0
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=10, padx=(8, 8))
        self.entry.bind("<Return>", lambda e: self._send())
        self.entry.focus()

        send_btn = tk.Button(
            bottom, text="Send ➤", font=("Segoe UI", 12, "bold"),
            bg="#238636", fg="white", relief="flat", padx=16, pady=8,
            cursor="hand2", activebackground="#2EA043",
            command=self._send
        )
        send_btn.pack(side="right", padx=(0, 8))

        # Quick chips
        chips = tk.Frame(self.root, bg="#0D1117")
        chips.pack(fill="x", padx=10, pady=(0, 8))

        for label, cmd in [
            ("Chrome", "Chrome kholo"), ("YouTube", "YouTube kholo"),
            ("Notepad", "Notepad kholo"), ("Time", "time kya hai"),
            ("Screenshot", "screenshot lo"), ("Help", "help"),
        ]:
            btn = tk.Button(
                chips, text=label, font=("Segoe UI", 10),
                bg="#21262D", fg="#8B949E", relief="flat", padx=10, pady=4,
                cursor="hand2", activebackground="#30363D",
                command=lambda c=cmd: self._quick(c)
            )
            btn.pack(side="left", padx=3)

    def _quick(self, cmd):
        self.entry.delete(0, "end")
        self.entry.insert(0, cmd)
        self._send()

    def _send(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self._add("Aap", text, user=True)
        threading.Thread(target=self._reply, args=(text,), daemon=True).start()

    def _reply(self, text):
        try:
            response = understand_and_act(text)
        except Exception as e:
            response = f"Kuch gadbad ho gayi: {e}"

        if response == "GOODBYE_SIGNAL":
            self._add("JARVIS", "Khuda Hafiz! Dobara aana 😊")
            self.root.after(1500, self.root.destroy)
            return

        self.root.after(0, self._add, "JARVIS", response)
        threading.Thread(target=speak, args=(response,), daemon=True).start()

    def _add(self, sender, msg, user=False):
        self.chat.configure(state="normal")
        t = datetime.now().strftime("%I:%M %p")

        # Divider
        if self.chat.get("1.0", "end").strip():
            self.chat.insert("end", "\n" + "─" * 60 + "\n", "divider")

        tag = "user" if user else "jarvis"
        icon = "🧑" if user else "🤖"
        self.chat.insert("end", f"{icon} {sender} ", tag)
        self.chat.insert("end", f"[{t}]\n", "time")
        self.chat.insert("end", f"  {msg}\n")

        self.chat.configure(state="disabled")
        self.chat.see("end")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    JarvisApp()
