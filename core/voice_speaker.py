"""Low-latency streaming neural TTS speaker for TARS."""
import asyncio
import os
import tempfile
import threading
from pathlib import Path
from typing import Optional


class VoiceSpeaker:
    """Handles text-to-speech synthesis using Microsoft Neural voices via edge-tts."""

    def __init__(self, voice_name: str = "en-US-GuyNeural", rate: str = "+0%", pitch: str = "+0Hz"):
        self.voice_name = os.getenv("TARS_VOICE", voice_name)
        self.rate = os.getenv("TARS_VOICE_RATE", rate)
        self.pitch = os.getenv("TARS_VOICE_PITCH", pitch)
        self._is_speaking = False
        self._pygame_initialized = False

    def _init_pygame(self) -> None:
        """Lazily initializes pygame mixer for audio playback."""
        if not self._pygame_initialized:
            try:
                import pygame
                pygame.mixer.init()
                self._pygame_initialized = True
            except Exception as e:
                print(f"[Speaker] Warning: Pygame mixer init failed: {e}")

    async def _synthesize_to_file(self, text: str, output_path: str) -> bool:
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
        except Exception as e:
            print(f"[Speaker] edge-tts synthesis failed: {e}")
            return False

    def _play_audio(self, audio_file: str) -> None:
        """Plays the generated audio file."""
        self._init_pygame()
        try:
            import pygame
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and self._is_speaking:
                pygame.time.Clock().tick(10)
        except Exception as e:
            # Fallback to Windows PowerShell sound player
            try:
                import subprocess
                subprocess.run([
                    "powershell",
                    "-c",
                    f"(New-Object Media.SoundPlayer '{audio_file}').PlaySync();"
                ], capture_output=True, timeout=15)
            except Exception:
                pass
        finally:
            self._is_speaking = False
            # Clean up temp file
            try:
                if os.path.exists(audio_file):
                    os.remove(audio_file)
            except Exception:
                pass

    def speak(self, text: str, blocking: bool = False) -> None:
        """
        Synthesizes and speaks text aloud.
        
        Args:
            text: The text string to speak.
            blocking: If True, blocks until speech finishes. If False, runs in background thread.
        """
        if not text or not text.strip():
            return

        def _worker():
            self._is_speaking = True
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                temp_audio = tf.name

            try:
                # Run async edge-tts
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(self._synthesize_to_file(text, temp_audio))
                loop.close()

                if success and os.path.exists(temp_audio) and os.path.getsize(temp_audio) > 0:
                    self._play_audio(temp_audio)
            except Exception as e:
                print(f"[Speaker] Speech playback failed: {e}")
                self._is_speaking = False

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
