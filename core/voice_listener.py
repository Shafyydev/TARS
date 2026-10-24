"""Voice ingestion, microphone capture, wake-word detection, and speech-to-text listener for TARS."""
import time
import re
from typing import Optional, Tuple, Callable


class VoiceListener:
    """
    Captures microphone input, handles wake words and direct speech,
    maintains conversational state, and transcribes speech to text.
    """

    # Extended list of wake words including common phonetic STT transcriptions of 'TARS'
    WAKE_WORDS = [
        "tars", "hey tars", "yo tars", "ok tars", "okay tars", "robot",
        "tar", "stars", "cars", "taurus", "torres", "tas", "dars", "taz"
    ]

    def __init__(self, energy_threshold: int = 150, pause_threshold: float = 0.6):
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self._recognizer = None
        self._microphone = None
        self.last_active_time = 0.0
        self.active_dialogue_window_sec = 30.0  # Seconds TARS stays attentive after hearing wake word
        self._init_audio()

    def _init_audio(self) -> None:
        """Initializes speech_recognition components."""
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = self.energy_threshold
            self._recognizer.pause_threshold = self.pause_threshold
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.dynamic_energy_adjustment_damping = 0.15
            self._recognizer.dynamic_energy_ratio = 1.5

            # Find best working input device
            # Prefer Realtek or default device
            self._microphone = sr.Microphone()
        except Exception as e:
            print(f"[Listener] Warning: Microphone init failed: {e}")
            self._recognizer = None
            self._microphone = None

    def calibrate(self, duration: float = 0.5) -> float:
        """Calibrates microphone for ambient room noise, keeping energy threshold balanced."""
        if self._recognizer and self._microphone:
            try:
                with self._microphone as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=duration)
                # Ensure threshold doesn't get set excessively high or low
                self._recognizer.energy_threshold = max(80, min(500, self._recognizer.energy_threshold))
                return self._recognizer.energy_threshold
            except Exception:
                pass
        return float(self.energy_threshold)

    def check_wake_word(self, text: str) -> Tuple[bool, str]:
        """
        Checks if text contains a wake word.
        Returns:
            (has_wake_word, cleaned_command)
        """
        if not text:
            return False, ""

        clean = text.strip()
        lower = clean.lower()
        now = time.time()

        # Check explicit wake words
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
        phrase_time_limit: int = 10,
        on_listening_start: Optional[Callable[[], None]] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Listens to the microphone for a phrase.
        
        Returns:
            (transcribed_text, status_message)
            status_message can be 'ok', 'timeout', 'unrecognized', or 'error: ...'
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

            # Transcribe via Google Speech Recognition API
            text = self._recognizer.recognize_google(audio)
            if text and text.strip():
                return text.strip(), "ok"
            return None, "unrecognized"

        except sr.WaitTimeoutError:
            return None, "timeout"
        except sr.UnknownValueError:
            return None, "unrecognized"
        except Exception as e:
            return None, f"error: {str(e)}"
