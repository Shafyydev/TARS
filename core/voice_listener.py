"""Voice ingestion, microphone capture, and speech-to-text listener for TARS."""
import time
from typing import Optional, Callable


class VoiceListener:
    """Captures microphone input and transcribes audio to text."""

    def __init__(self, energy_threshold: int = 300, pause_threshold: float = 0.8):
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        self._recognizer = None
        self._microphone = None
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

    def listen_once(self, timeout: int = 5, phrase_time_limit: int = 10) -> Optional[str]:
        """
        Listens to the microphone for a single phrase and returns transcribed text.
        
        Args:
            timeout: Maximum seconds to wait for speech to start.
            phrase_time_limit: Maximum duration of spoken phrase.
            
        Returns:
            Transcribed string or None if nothing detected or error occurred.
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

            # Transcribe via Google Speech Recognition API (built into speech_recognition, zero config)
            text = self._recognizer.recognize_google(audio)
            return text.strip() if text else None

        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as e:
            return None
