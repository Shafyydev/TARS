"""Ultra-low latency voice ingestion, microphone capture, and speech-to-text listener for TARS."""
import time
import re
from typing import Optional, Tuple, Callable


class VoiceListener:
    """
    Captures microphone input with ultra-responsive VAD thresholds,
    detects wake words (including phonetic STT approximations),
    and transcribes speech with minimal end-of-phrase lag.
    """

    # Extended list of wake words including common phonetic STT transcriptions
    WAKE_WORDS = [
        "tars", "hey tars", "yo tars", "ok tars", "okay tars", "robot",
        "tar", "stars", "cars", "taurus", "torres", "tas", "dars", "taz",
        "torch", "hello torch", "tarts", "target", "lotus"
    ]

    def __init__(self, energy_threshold: int = 120, pause_threshold: float = 0.35):
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self._recognizer = None
        self._microphone = None
        self.last_active_time = 0.0
        self.active_dialogue_window_sec = 30.0
        self._init_audio()

    def _init_audio(self) -> None:
        """Initializes speech_recognition components with tuned low-latency thresholds."""
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = self.energy_threshold
            # Rapid end-of-phrase detection (cuts out 1.0+ second of trailing silence)
            self._recognizer.pause_threshold = self.pause_threshold
            self._recognizer.non_speaking_duration = 0.2
            self._recognizer.phrase_threshold = 0.15
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.dynamic_energy_adjustment_damping = 0.15
            self._recognizer.dynamic_energy_ratio = 1.4

            self._microphone = sr.Microphone()
        except Exception as e:
            print(f"[Listener] Warning: Microphone init failed: {e}")
            self._recognizer = None
            self._microphone = None

    def calibrate(self, duration: float = 0.5) -> float:
        """Calibrates microphone for ambient acoustics and clamps energy threshold."""
        if self._recognizer and self._microphone:
            try:
                with self._microphone as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=duration)
                # Keep threshold responsive: not too deaf, not hyper-sensitive
                self._recognizer.energy_threshold = max(70, min(350, self._recognizer.energy_threshold))
                # Lock threshold post-calibration to eliminate per-chunk dynamic adjustment latency
                self._recognizer.dynamic_energy_threshold = False
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
        timeout: int = 5,
        phrase_time_limit: int = 8,
        on_listening_start: Optional[Callable[[], None]] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Listens to the microphone with minimal delay and returns transcribed text.
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

            # Transcribe via Google Speech Recognition with explicit US English
            text = self._recognizer.recognize_google(audio, language="en-US")
            if text and text.strip():
                return text.strip(), "ok"
            return None, "unrecognized"

        except sr.WaitTimeoutError:
            return None, "timeout"
        except sr.UnknownValueError:
            return None, "unrecognized"
        except Exception as e:
            return None, f"error: {str(e)}"
