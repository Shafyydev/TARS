"""High-accuracy, locale-aware voice capture and speech recognition listener for TARS."""
import os
import time
import re
import locale
import threading
import struct
import math
from typing import Optional, Tuple, Callable, Any


def detect_system_stt_language() -> str:
    """Detects system locale to choose the best Google STT acoustic model (e.g. en-IN, en-US, en-GB)."""
    lang_env = os.getenv("TARS_STT_LANGUAGE")
    if lang_env:
        return lang_env

    try:
        loc, _ = locale.getlocale()
        if loc:
            loc = loc.replace("_", "-")
            if loc.startswith("en-IN") or loc.startswith("en_IN"):
                return "en-IN"
            elif loc.startswith("en-GB") or loc.startswith("en_GB"):
                return "en-GB"
            elif loc.startswith("en-AU") or loc.startswith("en_AU"):
                return "en-AU"
            elif loc.startswith("en-CA") or loc.startswith("en_CA"):
                return "en-CA"
    except Exception:
        pass

    try:
        # Check timezone offset for India (+5:30 -> -19800)
        if time.timezone == -19800 or "India" in str(time.tzname):
            return "en-IN"
    except Exception:
        pass

    return "en-US"


def normalize_voice_command(text: str) -> str:
    """Corrects common speech-to-text phonetic confusions and acoustic artifacts."""
    if not text:
        return ""

    t = text.strip()

    # Browser tab confusions: "tap" / "top" / "table" -> "tab"
    t = re.sub(
        r"\b(new|close|next|previous|prev|switch|open|reopen|shut)\s+(?:this\s+)?(?:the\s+)?(?:tap|top|table)\b",
        r"\1 tab",
        t,
        flags=re.IGNORECASE
    )
    # Homophones: "clothes" -> "close"
    t = re.sub(r"\bclothes\s+(tab|window|app|this)\b", r"close \1", t, flags=re.IGNORECASE)
    # "write/ride click" -> "right click"
    t = re.sub(r"\b(?:write|ride|rite)\s+click\b", "right click", t, flags=re.IGNORECASE)
    # "double-click" -> "double click"
    t = re.sub(r"\bdouble-click\b", "double click", t, flags=re.IGNORECASE)
    # "call down / stroll down" -> "scroll down"
    t = re.sub(r"\b(?:call|stroll|score|crawled)\s+down\b", "scroll down", t, flags=re.IGNORECASE)
    # "stroll up / score up" -> "scroll up"
    t = re.sub(r"\b(?:call|stroll|score)\s+up\b", "scroll up", t, flags=re.IGNORECASE)
    # "screen shot" -> "screenshot"
    t = re.sub(r"\bscreen\s+shot\b", "screenshot", t, flags=re.IGNORECASE)
    # "mood / meet" -> "mute"
    if t.lower() in ["mood", "meet", "newt"]:
        t = "mute"
    # Single-word "ex", "ax it", "eggs it" -> "exit"
    if t.lower() in ["ex", "ax it", "eggs it", "exit out", "ex it"]:
        t = "exit"

    return t


class VoiceListener:
    """
    Captures microphone input with tuned VAD thresholds,
    locale-aware acoustic recognition, and phonetic command normalization.
    """

    WAKE_WORDS = [
        "tars", "hey tars", "yo tars", "ok tars", "okay tars", "robot",
        "tar", "stars", "cars", "taurus", "torres", "tas", "dars", "taz",
        "torch", "hello torch", "tarts", "target", "lotus"
    ]

    def __init__(
        self,
        energy_threshold: int = 250,
        pause_threshold: float = 0.35,
        language: Optional[str] = None,
        mic_index: Optional[int] = None
    ):
        self.energy_threshold = int(os.getenv("TARS_STT_ENERGY", str(energy_threshold)))
        self.pause_threshold = float(os.getenv("TARS_STT_PAUSE", str(pause_threshold)))
        self.language = language or os.getenv("TARS_STT_LANGUAGE") or detect_system_stt_language()
        
        env_mic = os.getenv("TARS_MIC_INDEX")
        self.mic_index = mic_index if mic_index is not None else (int(env_mic) if env_mic else None)

        self._recognizer = None
        self._microphone = None
        self.last_active_time = 0.0
        self.active_dialogue_window_sec = 30.0
        self._init_audio()

    def _init_audio(self) -> None:
        """Initializes speech_recognition with tuned low-latency acoustic VAD parameters."""
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = self.energy_threshold
            # Rapid 0.35s end-of-phrase detection (snappy without clipping words)
            self._recognizer.pause_threshold = self.pause_threshold
            self._recognizer.non_speaking_duration = 0.15
            self._recognizer.phrase_threshold = 0.15
            # Set strict network operation timeout to prevent socket hangs
            self._recognizer.operation_timeout = 3.5
            # Smooth dynamic adaptation to ambient room sound
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.dynamic_energy_adjustment_damping = 0.20
            self._recognizer.dynamic_energy_ratio = 1.4

            self._microphone = sr.Microphone(device_index=self.mic_index)
        except Exception as e:
            print(f"[Listener] Warning: Microphone init failed: {e}")
            self._recognizer = None
            self._microphone = None

    def calibrate(self, duration: float = 0.8) -> float:
        """Calibrates microphone for ambient acoustics with a safe noise floor."""
        if self._recognizer and self._microphone:
            try:
                with self._microphone as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=duration)
                # Keep energy floor safe: never drop below 200 (prevents fan noise from triggering)
                self._recognizer.energy_threshold = max(200, min(1500, self._recognizer.energy_threshold * 1.25))
                # Keep dynamic adaptation enabled so background noise doesn't corrupt speech
                self._recognizer.dynamic_energy_threshold = True
                return self._recognizer.energy_threshold
            except Exception:
                pass
        return float(self.energy_threshold)

    def check_wake_word(self, text: str) -> Tuple[bool, str]:
        """
        Checks if text contains a wake word or phonetic approximation.
        Returns:
            (has_wake_word, cleaned_command)
        """
        if not text:
            return False, ""

        clean = text.strip()
        lower = clean.lower()
        now = time.time()

        for ww in self.WAKE_WORDS:
            pattern = rf"^{re.escape(ww)}[\s,:\-]*(.*)$"
            match = re.match(pattern, lower, re.IGNORECASE)
            if match:
                self.last_active_time = now
                remainder = clean[match.start(1):].strip() if match.group(1) else ""
                return True, remainder

            if lower.endswith(ww):
                self.last_active_time = now
                remainder = clean[:len(clean) - len(ww)].strip(" ,:-")
                return True, remainder

        # If already in an active conversational window, accept command
        if (now - self.last_active_time) <= self.active_dialogue_window_sec:
            self.last_active_time = now
            return True, clean

        return False, clean

    def listen_once(
        self,
        timeout: int = 4,
        phrase_time_limit: int = 4,
        on_listening_start: Optional[Callable[[], None]] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Listens to the microphone with locale-aware STT and phonetic normalization.
        """
        if not self._recognizer or not self._microphone:
            return None, "Microphone not initialized"

        import speech_recognition as sr

        try:
            if on_listening_start:
                on_listening_start()

            with self._microphone as source:
                audio = self._recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

            # Fast single STT network call with user's locale (e.g. en-IN)
            try:
                text = self._recognizer.recognize_google(audio, language=self.language)
            except sr.UnknownValueError:
                return None, "unrecognized"

            if text and text.strip():
                normalized = normalize_voice_command(text.strip())
                return normalized, "ok"
            return None, "unrecognized"

        except sr.WaitTimeoutError:
            return None, "timeout"
        except sr.UnknownValueError:
            return None, "unrecognized"
        except Exception as e:
            return None, f"error: {str(e)}"

    def create_barge_in_monitor(self) -> Optional["VoiceBargeInMonitor"]:
        """Creates a barge-in audio energy monitor calibrated to current room acoustics."""
        if not self._recognizer or not self._microphone:
            return None
        # Safe threshold: at least 500 and 2.0x current energy threshold to reject speaker bleed
        thresh = max(500, int(self._recognizer.energy_threshold * 2.0))
        return VoiceBargeInMonitor(self._recognizer, self._microphone, energy_threshold=thresh)


class VoiceBargeInMonitor:
    """
    Lightweight audio energy monitor that listens to the microphone
    during TTS speech playback to trigger instant voice barge-in.
    """

    def __init__(self, recognizer: Any, microphone: Any, energy_threshold: int = 500):
        self.recognizer = recognizer
        self.microphone = microphone
        self.energy_threshold = energy_threshold
        self._stop_event = threading.Event()
        self._triggered = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Starts background monitoring."""
        if not self.microphone or not self.recognizer:
            return
        self._stop_event.clear()
        self._triggered.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stops background monitoring."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.15)

    def is_triggered(self) -> bool:
        """Returns True if user voice energy exceeded threshold."""
        return self._triggered.is_set()

    def _run(self) -> None:
        try:
            with self.microphone as source:
                consecutive = 0
                while not self._stop_event.is_set():
                    try:
                        raw = source.stream.read(source.CHUNK)
                        if not raw:
                            continue
                        count = len(raw) // 2
                        shorts = struct.unpack(f"{count}h", raw)
                        sum_squares = sum(s * s for s in shorts)
                        rms = int(math.sqrt(sum_squares / max(1, count)))
                        if rms >= self.energy_threshold:
                            consecutive += 1
                            # 2 consecutive frames (~80ms) above threshold confirms speech
                            if consecutive >= 2:
                                self._triggered.set()
                                break
                        else:
                            consecutive = max(0, consecutive - 1)
                    except Exception:
                        break
        except Exception:
            pass
