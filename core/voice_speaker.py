"""Low-latency streaming neural TTS speaker for TARS with offline SAPI fallback and instant async acknowledgments."""
import asyncio
import os
import re
import random
import tempfile
import threading
from typing import Optional


class VoiceSpeaker:
    """
    Handles text-to-speech synthesis using Microsoft Neural voices via edge-tts,
    with zero-latency async acknowledgments and Windows native SAPI fast mode.
    """

    ACKNOWLEDGMENTS = [
        "Affirmative.",
        "Right away.",
        "Executing now.",
        "Understood.",
        "On it.",
        "Acknowledged.",
        "Processing.",
    ]

    def __init__(self, voice_name: str = "en-US-GuyNeural", rate: str = "+0%", pitch: str = "+0Hz", fast_voice: bool = False):
        self.voice_name = os.getenv("TARS_VOICE", voice_name)
        self.rate = os.getenv("TARS_VOICE_RATE", rate)
        self.pitch = os.getenv("TARS_VOICE_PITCH", pitch)
        self.fast_voice = fast_voice or (os.getenv("TARS_FAST_VOICE", "0") in ["1", "true", "True"])
        self._is_speaking = False
        self._pygame_initialized = False
        self._lock = threading.Lock()
        
        # Pre-warm audio subsystem at startup
        self._init_pygame()

    @property
    def is_speaking(self) -> bool:
        """Returns True if audio is currently playing."""
        return self._is_speaking

    def _init_pygame(self) -> bool:
        """Initializes pygame mixer once at startup for instant audio playback."""
        if not self._pygame_initialized:
            try:
                import pygame
                pygame.mixer.init()
                self._pygame_initialized = True
                return True
            except Exception as e:
                return False
        return True

    def _clean_text_for_speech(self, text: str) -> str:
        """Strips markdown, emojis, codeblocks, and raw URLs for crisp speech delivery."""
        clean = re.sub(r"```[\s\S]*?```", "", text)
        clean = re.sub(r"`([^`]+)`", r"\1", clean)
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)
        clean = re.sub(r"https?://\S+", "a web link", clean)
        clean = re.sub(r"[*_~#>]", "", clean)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    async def _synthesize_edge_tts(self, text: str, output_path: str) -> bool:
        """Synthesizes text into an MP3 file using edge-tts."""
        try:
            import edge_tts
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice_name,
                rate=self.rate,
                pitch=self.pitch
            )
            await communicate.save(output_path)
            return True
        except Exception:
            return False

    def _play_audio_pygame(self, audio_file: str) -> bool:
        """Plays the generated audio file using pygame."""
        if not self._init_pygame():
            return False

        try:
            import pygame
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and self._is_speaking:
                pygame.time.Clock().tick(20)
            return True
        except Exception:
            return False

    def _speak_sapi(self, text: str, async_mode: bool = False) -> bool:
        """Zero-latency offline speech using Windows native SAPI."""
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            # Flag 1 is SVSFlagsAsync (non-blocking, instant return)
            flags = 1 if async_mode else 0
            speaker.Speak(text, flags)
            pythoncom.CoUninitialize()
            return True
        except Exception:
            try:
                import subprocess
                escaped = text.replace("'", "''").replace('"', '`"')
                cmd = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{escaped}')"
                subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=10)
                return True
            except Exception:
                return False

    def speak_ack(self) -> None:
        """Speaks an instantaneous acknowledgment phrase (<20ms latency) without blocking."""
        ack = random.choice(self.ACKNOWLEDGMENTS)
        # Use async SAPI directly for zero network latency and zero lock contention
        self._speak_sapi(ack, async_mode=True)

    def speak(self, text: str, blocking: bool = False) -> None:
        """
        Synthesizes and speaks text aloud.
        
        Args:
            text: The text string to speak.
            blocking: If True, blocks until speech finishes. If False, runs in background thread.
        """
        if not text or not text.strip():
            return

        speech_text = self._clean_text_for_speech(text)
        if not speech_text:
            return

        # If fast-voice mode is requested, speak instantly with native SAPI
        if self.fast_voice:
            self._is_speaking = True
            try:
                self._speak_sapi(speech_text, async_mode=(not blocking))
            finally:
                if blocking:
                    self._is_speaking = False
            return

        def _worker():
            with self._lock:
                self._is_speaking = True
                temp_audio = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                        temp_audio = tf.name

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    edge_success = loop.run_until_complete(self._synthesize_edge_tts(speech_text, temp_audio))
                    loop.close()

                    if edge_success and os.path.exists(temp_audio) and os.path.getsize(temp_audio) > 0:
                        played = self._play_audio_pygame(temp_audio)
                        if not played:
                            self._speak_sapi(speech_text, async_mode=False)
                    else:
                        self._speak_sapi(speech_text, async_mode=False)

                except Exception:
                    self._speak_sapi(speech_text, async_mode=False)
                finally:
                    self._is_speaking = False
                    if temp_audio and os.path.exists(temp_audio):
                        try:
                            os.remove(temp_audio)
                        except Exception:
                            pass

        if blocking:
            _worker()
        else:
            t = threading.Thread(target=_worker, daemon=True)
            t.start()

    def stop(self) -> None:
        """Stops currently playing audio."""
        self._is_speaking = False
        if self._pygame_initialized:
            try:
                import pygame
                pygame.mixer.music.stop()
            except Exception:
                pass
