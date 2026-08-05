"""
JARVIS Voice Engine — Natural Hindi + English speech.

TTS: Microsoft Edge Neural voices (edge-tts) — FREE, no API key, best quality.
STT: Groq Whisper API — FREE with your Groq key, excellent Hindi + English.

Install: pip install edge-tts sounddevice numpy
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.request
from pathlib import Path

# ── Best free neural voices (Microsoft Edge TTS) ──
VOICES = {
    "hindi": "hi-IN-MadhurNeural",       # Natural Hindi male voice
    "english": "en-IN-NeerjaNeural",     # Natural Indian English female
    "english_us": "en-US-JennyNeural",   # US English fallback
}

_speaking_lock = threading.Lock()


def ensure_voice_deps() -> bool:
    """Auto-install edge-tts if missing."""
    try:
        import edge_tts  # noqa: F401
        return True
    except ImportError:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "edge-tts", "-q"],
                check=True, timeout=120,
            )
            return True
        except Exception:
            return False


def _play_mp3(path: str):
    """Play MP3 on Windows using built-in MediaPlayer — no extra install."""
    uri = Path(path).resolve().as_uri()
    ps = f"""
Add-Type -AssemblyName presentationCore
$p = New-Object System.Windows.Media.MediaPlayer
$p.Open("{uri}")
$p.Play()
Start-Sleep -Milliseconds 600
while (-not $p.NaturalDuration.HasTimeSpan) {{ Start-Sleep -Milliseconds 80 }}
Start-Sleep -Seconds ($p.NaturalDuration.TimeSpan.TotalSeconds + 0.5)
$p.Stop()
$p.Close()
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        timeout=90, capture_output=True,
    )


async def _edge_save(text: str, voice: str, path: str, rate: str = "+8%"):
    import edge_tts
    comm = edge_tts.Communicate(text, voice, rate=rate)
    await comm.save(path)


def speak_neural(text: str, lang: str = "hindi", block: bool = True) -> bool:
    """
    Speak with natural neural voice.
    lang: 'hindi' or 'english'
    Returns True if neural TTS worked, False if failed.
    """
    text = text.strip()
    if not text or len(text) < 2:
        return False

    if not ensure_voice_deps():
        return False

    voice = VOICES.get(lang, VOICES["english"])
    # Long text — split into chunks
    chunks = _split_text(text, 280)
    path = tempfile.mktemp(suffix=".mp3")

    try:
        with _speaking_lock:
            for chunk in chunks:
                asyncio.run(_edge_save(chunk, voice, path))
                if block:
                    _play_mp3(path)
                try:
                    os.remove(path)
                except Exception:
                    pass
                path = tempfile.mktemp(suffix=".mp3")
        return True
    except Exception:
        return False


def speak_sapi_fallback(text: str, block: bool = True):
    """Old Windows robotic voice — fallback only."""
    import re
    clean = re.sub(r"[✅❌⚠️🔊📸🤖●•→✓\[\]]", "", text)
    clean = re.sub(r"\n+", ". ", clean).strip()[:400]
    if not clean:
        return
    try:
        import win32com.client
        sp = win32com.client.Dispatch("SAPI.SpVoice")
        sp.Speak(clean, 0 if block else 1)
    except Exception:
        pass


def speak(text: str, lang: str = "hindi", block: bool = True):
    """Main speak function — neural first, SAPI fallback."""
    if not speak_neural(text, lang=lang, block=block):
        speak_sapi_fallback(text, block=block)


def _split_text(text: str, max_len: int) -> list[str]:
    if len(text) <= max_len:
        return [text]
    parts = []
    for sentence in text.replace("!", ".").replace("?", ".").split("."):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) <= max_len:
            parts.append(sentence + ".")
        else:
            words = sentence.split()
            chunk = ""
            for w in words:
                if len(chunk) + len(w) + 1 <= max_len:
                    chunk += w + " "
                else:
                    if chunk:
                        parts.append(chunk.strip() + ".")
                    chunk = w + " "
            if chunk:
                parts.append(chunk.strip() + ".")
    return parts or [text[:max_len]]


# ── STT: Groq Whisper (much better Hindi than Windows SAPI) ──

def listen_whisper(api_key: str, duration: int = 10, lang_hint: str = "auto") -> str:
    """
    Record mic + transcribe with Groq Whisper (free, very accurate Hindi/English).
    """
    if not api_key or not api_key.startswith("gsk_"):
        return ""

    wav_path = tempfile.mktemp(suffix=".wav")
    try:
        if not _record_wav(wav_path, duration):
            return ""
        return _groq_transcribe(api_key, wav_path, lang_hint)
    finally:
        try:
            os.remove(wav_path)
        except Exception:
            pass


def _record_wav(path: str, duration: int) -> bool:
    try:
        import numpy as np
        import sounddevice as sd
        import wave

        fs = 16000
        audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="int16")
        sd.wait()
        if np.max(np.abs(audio)) < 100:
            return False
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(fs)
            wf.writeframes(audio.tobytes())
        return os.path.getsize(path) > 1000
    except Exception:
        return False


def _groq_transcribe(api_key: str, wav_path: str, lang_hint: str) -> str:
    boundary = "----JarvisBoundary7MA4YWxk"
    with open(wav_path, "rb") as f:
        audio_data = f.read()

    lang_param = ""
    if lang_hint == "hindi":
        lang_param = b'\r\nContent-Disposition: form-data; name="language"\r\n\r\nhi'
    elif lang_hint == "english":
        lang_param = b'\r\nContent-Disposition: form-data; name="language"\r\n\r\nen'

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode() + audio_data + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="model"\r\n\r\nwhisper-large-v3-turbo'
    ).encode() + lang_param + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="response_format"\r\n\r\njson'
        f"\r\n--{boundary}--\r\n"
    ).encode()

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "JARVIS/3.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            return (data.get("text") or "").strip()
    except Exception:
        return ""


def list_voices() -> dict:
    """Available voice names for reference."""
    return dict(VOICES)
