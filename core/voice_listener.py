"""Voice ingestion, microphone capture, wake-word detection, and speech-to-text listener for TARS."""
import time
import re
from typing import Optional, Tuple, Callable


class VoiceListener:
    """
    Captures microphone input, detects wake words ('TARS', 'Hey TARS'),
    maintains conversational state, and transcribes speech to text.
    """

    WAKE_WORDS = ["tars", "hey tars", "yo tars", "ok tars", "okay tars", "robot"]

    def __init__(self, energy_threshold: int = 300, pause_threshold: float = 0.8):
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self._recognizer = None
        self._microphone = None
        self.last_active_time = 0.0
        self.active_dialogue_window_sec = 25.0  # Seconds TARS stays attentive after hearing wake word
        self._init_audio()

    def _init_audio(self) -> None:
        """Initializes speech_recognition components."""
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = self.energy_threshold
            self._recognizer.pause_threshold = self.pause_threshold
            self._recognizer.dynamic_energy_threshold = True
            self._microphone = sr.Microphone()
        except Exception as e:
            print(f"[Listener] Warning: Microphone init failed: {e}")
            self._recognizer = None
            self._microphone = None

    def calibrate(self, duration: int = 1) -> None:
        """Calibrates microphone for ambient room noise."""
        if self._recognizer and self._microphone:
            try:
                with self._microphone as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=duration)
            except Exception:
                pass

    def check_wake_word(self, text: str) -> Tuple[bool, str]:
        """
        Checks if text contains a wake word or if within active dialogue window.
        
        Returns:
            (is_activated, cleaned_command)
        """
        if not text:
            return False, ""

        clean = text.strip()
        lower = clean.lower()
        now = time.time()

        # Check explicit wake words
        for ww in self.WAKE_WORDS:
            # Matches "tars, open chrome" or "hey tars what time is it" or just "tars"
            pattern = rf"^{re.escape(ww)}[\s,:\-]*(.*)$"
            match = re.match(pattern, lower, re.IGNORECASE)
            if match:
                self.last_active_time = now
                remainder = clean[match.start(1):].strip() if match.group(1) else ""
                return True, remainder

            # Or wake word at the end: "open chrome tars"
            if lower.endswith(ww):
                self.last_active_time = now
                remainder = clean[:len(clean) - len(ww)].strip(" ,:-")
                return True, remainder

        # If already in an active conversational window, accept command without repeating "TARS"
        if (now - self.last_active_time) <= self.active_dialogue_window_sec:
            self.last_active_time = now
            return True, clean

        return False, clean

    def listen_once(self, timeout: int = 5, phrase_time_limit: int = 12) -> Optional[str]:
        """
        Listens to the microphone for a single phrase and returns transcribed text.
        """
        if not self._recognizer or not self._microphone:
            return None

        import speech_recognition as sr

        try:
            with self._microphone as source:
                audio = self._recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

            # Transcribe via Google Speech Recognition API (zero config, low latency)
            text = self._recognizer.recognize_google(audio)
            return text.strip() if text else None

        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return None
        except Exception:
            return None
