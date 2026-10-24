"""Low-latency streaming neural TTS speaker for TARS with offline SAPI fallback."""
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
    with automatic offline fallback to Windows native SAPI.
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

    def __init__(self, voice_name: str = "en-US-GuyNeural", rate: str = "+0%", pitch: str = "+0Hz"):
        self.voice_name = os.getenv("TARS_VOICE", voice_name)
        self.rate = os.getenv("TARS_VOICE_RATE", rate)
        self.pitch = os.getenv("TARS_VOICE_PITCH", pitch)
        self._is_speaking = False
        self._pygame_initialized = False
        self._lock = threading.Lock()

    @property
    def is_speaking(self) -> bool:
        """Returns True if audio is currently playing."""
        return self._is_speaking

    def _init_pygame(self) -> bool:
        """Lazily initializes pygame mixer for audio playback."""
        if not self._pygame_initialized:
            try:
                import pygame
                pygame.mixer.init()
                self._pygame_initialized = True
                return True
            except Exception as e:
                print(f"[Speaker] Warning: Pygame mixer init failed: {e}")
                return False
        return True

    def _clean_text_for_speech(self, text: str) -> str:
        """Strips markdown, emojis, codeblocks, and raw URLs for crisp speech delivery."""
        # Remove markdown code blocks
        clean = re.sub(r"```[\s\S]*?```", "", text)
        # Remove inline code backticks
        clean = re.sub(r"`([^`]+)`", r"\1", clean)
        # Remove markdown links [text](url) -> text
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)
        # Remove bare URLs
        clean = re.sub(r"https?://\S+", "a web link", clean)
        # Remove bold/italic markers
        clean = re.sub(r"[*_~#>]", "", clean)
        # Remove excessive whitespace
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
                pygame.time.Clock().tick(15)
            return True
        except Exception:
            return False

    def _speak_sapi_fallback(self, text: str) -> bool:
        """Zero-latency offline speech using Windows SAPI."""
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Speak(text)
            pythoncom.CoUninitialize()
            return True
        except Exception:
            # Last-ditch: PowerShell speech synthesis
            try:
                import subprocess
                escaped = text.replace("'", "''").replace('"', '`"')
                cmd = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{escaped}')"
                subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=10)
                return True
            except Exception:
                return False

    def speak_ack(self) -> None:
        """Speaks a brief, instantaneous acknowledgment phrase."""
        ack = random.choice(self.ACKNOWLEDGMENTS)
        self.speak(ack, blocking=False)

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

        def _worker():
            with self._lock:
                self._is_speaking = True
                temp_audio = None
                try:
                    # 1. Attempt edge-tts neural voice
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                        temp_audio = tf.name

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    edge_success = loop.run_until_complete(self._synthesize_edge_tts(speech_text, temp_audio))
                    loop.close()

                    if edge_success and os.path.exists(temp_audio) and os.path.getsize(temp_audio) > 0:
                        played = self._play_audio_pygame(temp_audio)
                        if not played:
                            self._speak_sapi_fallback(speech_text)
                    else:
                        # 2. Fall back to native Windows SAPI voice
                        self._speak_sapi_fallback(speech_text)

                except Exception as e:
                    self._speak_sapi_fallback(speech_text)
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
