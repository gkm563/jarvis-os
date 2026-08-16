"""
JARVIS Voice Engine — Natural Hindi + English speech.

TTS: edge-tts (Microsoft Neural) — FREE
STT: Groq Whisper — FREE with Groq key
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
import urllib.error
from pathlib import Path
from typing import Callable, Optional

VOICES = {
    "hindi": "hi-IN-MadhurNeural",
    "english": "en-IN-NeerjaNeural",
    "english_us": "en-US-JennyNeural",
}

_speaking_lock = threading.Lock()
_stop_speak = threading.Event()
_play_proc: subprocess.Popen | None = None


def stop_speaking():
    """Stop any in-progress TTS immediately."""
    _stop_speak.set()
    global _play_proc
    proc = _play_proc
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=1)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    _play_proc = None
    try:
        import win32com.client
        sp = win32com.client.Dispatch("SAPI.SpVoice")
        sp.Speak("", 2)
    except Exception:
        pass


def ensure_voice_deps() -> bool:
    try:
        import edge_tts  # noqa: F401
        return True
    except ImportError:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "edge-tts", "-q"], check=True, timeout=120)
            return True
        except Exception:
            return False


def _play_mp3(path: str) -> bool:
    global _play_proc
    if _stop_speak.is_set():
        return False
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
    import time
    _play_proc = subprocess.Popen(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    while _play_proc.poll() is None:
        if _stop_speak.is_set():
            try:
                _play_proc.terminate()
            except Exception:
                pass
            _play_proc = None
            return False
        time.sleep(0.08)
    _play_proc = None
    return not _stop_speak.is_set()


async def _edge_save(text: str, voice: str, path: str, rate: str = "+8%"):
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate).save(path)


def speak_neural(text: str, lang: str = "english", block: bool = True) -> bool:
    text = text.strip()
    if not text or len(text) < 2:
        return False
    if not ensure_voice_deps():
        return False
    voice = VOICES.get(lang, VOICES["english_us"] if lang == "english" else VOICES["english"])
    try:
        _stop_speak.clear()
        with _speaking_lock:
            for chunk in _split_text(text, 280):
                if _stop_speak.is_set():
                    return False
                path = tempfile.mktemp(suffix=".mp3")
                asyncio.run(_edge_save(chunk, voice, path))
                if block:
                    if not _play_mp3(path):
                        try:
                            os.remove(path)
                        except Exception:
                            pass
                        return False
                try:
                    os.remove(path)
                except Exception:
                    pass
        return not _stop_speak.is_set()
    except Exception:
        return False


def speak_sapi_fallback(text: str, block: bool = True):
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


def speak(text: str, lang: str = "english", block: bool = True):
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
        parts.append(sentence + "." if len(sentence) <= max_len else sentence[:max_len] + ".")
    return parts or [text[:max_len]]


# ── STT ──

def _status_msg(lang: str, key: str) -> str:
    en = {
        "mic_on": "🎤 Mic on — speak now...",
        "thinking": "⏳ Processing...",
        "heard": "✅ Heard: ",
        "recording": "🎤 Recording... speak now",
        "listening": "🎤 Listening... ",
        "no_voice": "No voice detected — check mic or speak louder",
        "nothing": "Didn't hear anything",
        "win_mic": "🎤 Trying Windows mic...",
    }
    hi = {
        "mic_on": "🎤 Mic on — ab bolo...",
        "thinking": "⏳ Samajh raha hoon...",
        "heard": "✅ Suna: ",
        "recording": "🎤 Recording... bolo ab",
        "listening": "🎤 Sun raha... ",
        "no_voice": "Awaaz nahi aayi — mic check karo ya zor se bolo",
        "nothing": "Kuch sunai nahi diya",
        "win_mic": "🎤 Windows mic try kar raha...",
    }
    msgs = en if lang in ("english", "en") else hi
    return msgs.get(key, key)


def listen_whisper(
    api_key: str,
    duration: int = 8,
    lang_hint: str = "auto",
    on_status: Optional[Callable[[str], None]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> tuple[str, str]:
    """
    Record + Groq Whisper transcribe.
    Returns (text, error_message) — error empty on success.
    """
    lang_key = "english" if lang_hint in ("english", "en") else "hindi"
    if not api_key or not api_key.startswith("gsk_"):
        return "", "Groq API key missing"

    wav_path = tempfile.mktemp(suffix=".wav")
    try:
        if on_status:
            on_status(_status_msg(lang_key, "mic_on"))
        ok, rec_err = _record_wav_vad(
            wav_path, max_duration=float(duration), on_status=on_status,
            lang=lang_key, should_stop=should_stop,
        )
        if not ok:
            if should_stop and should_stop():
                return "", "Interrupted"
            return "", rec_err or _status_msg(lang_key, "no_voice")

        if should_stop and should_stop():
            return "", "Interrupted"

        if on_status:
            on_status(_status_msg(lang_key, "thinking"))

        text, err = _groq_transcribe(api_key, wav_path, lang_hint)
        if text:
            if on_status:
                on_status(f"{_status_msg(lang_key, 'heard')}{text}")
            return text, ""
        return "", err or _status_msg(lang_key, "nothing")
    finally:
        try:
            os.remove(wav_path)
        except Exception:
            pass


def _get_best_input_device() -> int:
    """Helper to detect and return the best input device (built-in Microphone Array fallback)."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        default_idx = sd.default.device[0]
        
        default_name = ""
        if default_idx is not None and default_idx >= 0:
            default_name = devices[default_idx]['name'].lower()
            
        # If default device is a bluetooth headset/hands-free, fallback to built-in Microphone Array
        if any(w in default_name for w in ["headset", "hands-free", "handsfree", "boult", "bluetooth"]):
            for idx, d in enumerate(devices):
                if d['max_input_channels'] > 0:
                    name = d['name'].lower()
                    if "microphone array" in name and "realtek" in name:
                        return idx
            for idx, d in enumerate(devices):
                if d['max_input_channels'] > 0:
                    name = d['name'].lower()
                    if "microphone array" in name:
                        return idx
        return default_idx
    except Exception:
        return None


def _record_wav_vad(
    path: str,
    max_duration: float = 12.0,
    silence_sec: float = 1.0,
    on_status=None,
    lang: str = "english",
    should_stop=None,
) -> tuple[bool, str]:
    """Record until user stops speaking (voice activity detection)."""
    try:
        import numpy as np
        import sounddevice as sd
        import wave

        fs = 16000
        chunk_ms = 0.1
        block = int(chunk_ms * fs)
        chunks = []
        heard_voice = False
        silence_chunks = 0
        silence_needed = max(3, int(silence_sec / chunk_ms))
        max_chunks = int(max_duration / chunk_ms)

        if on_status:
            on_status(_status_msg(lang, "recording"))

        device_idx = _get_best_input_device()
        with sd.InputStream(samplerate=fs, channels=1, dtype="int16", device=device_idx) as stream:
            for i in range(max_chunks):
                if should_stop and should_stop():
                    return False, "Interrupted"
                data, _ = stream.read(block)
                chunks.append(data.copy())
                level = int(np.max(np.abs(data)))
                if level > 45:
                    heard_voice = True
                    silence_chunks = 0
                elif heard_voice:
                    silence_chunks += 1
                    if silence_chunks >= silence_needed:
                        break
                if on_status and i % 4 == 0:
                    bars = "█" * min(level // 300, 12)
                    on_status(f"{_status_msg(lang, 'listening')}{bars}")

        if not chunks:
            return False, _status_msg(lang, "no_voice")

        audio = np.concatenate(chunks, axis=0)
        if not heard_voice or int(np.max(np.abs(audio))) < 35:
            return False, _status_msg(lang, "no_voice")

        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(fs)
            wf.writeframes(audio.tobytes())
        return True, ""
    except Exception as e:
        return False, f"Mic error: {e}"


def _record_wav(path: str, duration: int, on_status=None, lang: str = "english", should_stop=None) -> tuple[bool, str]:
    """Fixed-duration fallback recording."""
    try:
        import numpy as np
        import sounddevice as sd
        import wave

        fs = 16000
        block = int(0.2 * fs)
        chunks = []
        heard_voice = False

        if on_status:
            on_status(_status_msg(lang, "recording"))

        device_idx = _get_best_input_device()
        with sd.InputStream(samplerate=fs, channels=1, dtype="int16", device=device_idx) as stream:
            for i in range(int(duration / 0.2)):
                if should_stop and should_stop():
                    return False, "Interrupted"
                data, _ = stream.read(block)
                chunks.append(data.copy())
                level = int(np.max(np.abs(data)))
                if level > 45:
                    heard_voice = True
                if on_status and i % 3 == 0:
                    bars = "█" * min(level // 350, 10)
                    on_status(f"{_status_msg(lang, 'listening')}{bars}")

        audio = np.concatenate(chunks, axis=0)
        if not heard_voice and np.max(np.abs(audio)) < 35:
            return False, _status_msg(lang, "no_voice")

        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(fs)
            wf.writeframes(audio.tobytes())
        return True, ""
    except Exception as e:
        return False, f"Mic error: {e}"


def _groq_transcribe(api_key: str, wav_path: str, lang_hint: str) -> tuple[str, str]:
    boundary = "----JarvisBoundary7MA4YWxk"
    with open(wav_path, "rb") as f:
        audio_data = f.read()

    parts = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n',
        b"Content-Type: audio/wav\r\n\r\n",
        audio_data,
        f"\r\n--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="model"\r\n\r\nwhisper-large-v3-turbo',
    ]
    if lang_hint == "hindi":
        parts += [f"\r\n--{boundary}\r\n".encode(), b'Content-Disposition: form-data; name="language"\r\n\r\nhi']
    elif lang_hint == "english":
        parts += [f"\r\n--{boundary}\r\n".encode(), b'Content-Disposition: form-data; name="language"\r\n\r\nen']
    parts += [f"\r\n--{boundary}\r\n".encode(), b'Content-Disposition: form-data; name="response_format"\r\n\r\njson']
    parts += [f"\r\n--{boundary}--\r\n".encode()]
    body = b"".join(parts)

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/audio/transcriptions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "JARVIS/3.1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode())
            return (data.get("text") or "").strip(), ""
    except urllib.error.HTTPError as e:
        err = e.read().decode() if e.fp else str(e)
        return "", f"Whisper error {e.code}: {err[:100]}"
    except Exception as e:
        return "", str(e)


def listen_windows_sapi(timeout_sec: int = 10, lang: str = "auto", on_partial=None) -> str:
    """Windows built-in speech — live partial text via temp file."""
    culture = "en-US" if lang in ("english", "en") else ("hi-IN" if lang in ("auto", "hindi") else "en-US")
    out_file = tempfile.mktemp(suffix=".txt")
    done_file = tempfile.mktemp(suffix=".done")
    out_esc = out_file.replace("\\", "/")
    done_esc = done_file.replace("\\", "/")

    ps = f"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Speech
$culture = New-Object System.Globalization.CultureInfo("{culture}")
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine($culture)
$engine.SetInputToDefaultAudioDevice()
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$engine.LoadGrammar($grammar)
$outFile = "{out_esc}"
$doneFile = "{done_esc}"
$engine.Add_SpeechHypothesized({{ param($s,$e) if($e.Result.Text){{ Set-Content $outFile $e.Result.Text -Encoding UTF8 -Force }} }})
$engine.Add_SpeechRecognized({{ param($s,$e) if($e.Result.Text){{ Set-Content $outFile $e.Result.Text -Encoding UTF8 -Force; Set-Content $doneFile "done" -Encoding UTF8 -Force; $engine.RecognizeAsyncStop() }} }})
$engine.RecognizeAsync()
$deadline = (Get-Date).AddSeconds({timeout_sec})
while ((Get-Date) -lt $deadline) {{ if (Test-Path $doneFile) {{ break }}; Start-Sleep -Milliseconds 120 }}
try {{ $engine.RecognizeAsyncStop() }} catch {{ }}
"""
    import time
    proc = subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps])
    result = ""
    deadline = time.time() + timeout_sec + 3
    while time.time() < deadline:
        if os.path.exists(out_file):
            try:
                text = Path(out_file).read_text(encoding="utf-8").strip()
                if text and text != result:
                    result = text
                    if on_partial:
                        on_partial(text)
            except Exception:
                pass
        if os.path.exists(done_file):
            break
        time.sleep(0.12)
    proc.wait(timeout=5)
    for f in (out_file, done_file):
        try:
            os.remove(f)
        except Exception:
            pass
    return result


def listen_best(
    api_key: str,
    timeout_sec: int = 8,
    lang: str = "auto",
    on_status: Optional[Callable[[str], None]] = None,
    on_partial: Optional[Callable[[str], None]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
) -> tuple[str, str]:
    """Groq Whisper (VAD) first — avoids hearing JARVIS own voice via Windows SAPI."""
    lang_hint = "english" if lang in ("english", "en") else ("hindi" if lang in ("auto", "hindi") else "english")

    if api_key and api_key.startswith("gsk_"):
        text, err = listen_whisper(
            api_key, duration=timeout_sec, lang_hint=lang_hint,
            on_status=on_status, should_stop=should_stop,
        )
        if text:
            return text, ""
        if should_stop and should_stop():
            return "", "Interrupted"

    if should_stop and should_stop():
        return "", "Interrupted"

    if on_status:
        on_status(_status_msg(lang_hint, "win_mic"))
    text = listen_windows_sapi(timeout_sec, lang_hint, on_partial=on_partial)
    if text:
        if on_status:
            on_status(f"{_status_msg(lang_hint, 'heard')}{text}")
        return text, ""
    return "", _status_msg(lang_hint, "nothing") + " — speak louder or check mic"


def list_voices() -> dict:
    return dict(VOICES)
