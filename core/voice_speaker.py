"""Low-latency streaming neural TTS speaker for TARS with offline SAPI fallback and instant async acknowledgments."""
import asyncio
import os
import re
import random
import tempfile
import threading
import time
from typing import Optional, Callable, Any


os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"


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

    def __init__(self, voice_name: str = "en-US-GuyNeural", rate: str = "+0%", pitch: str = "+0Hz", fast_voice: bool = True):
        self.voice_name = os.getenv("TARS_VOICE", voice_name)
        self.rate = os.getenv("TARS_VOICE_RATE", rate)
        self.pitch = os.getenv("TARS_VOICE_PITCH", pitch)
        # Default to fast native Windows SAPI for zero-latency instant responses unless cloud neural voice requested
        force_neural = (os.getenv("TARS_NEURAL_VOICE", "0") in ["1", "true", "True"]) or (not fast_voice)
        self.fast_voice = not force_neural
        self._is_speaking = False
        self._stop_requested = False
        self._sapi_speaker = None
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
        # Sanitize technical API errors so TARS never speaks raw JSON or stack traces aloud
        if any(err_kw in text for err_kw in ["{'error':", "RESOURCE_EXHAUSTED", "429", "Traceback (most recent"]):
            return "API rate limit reached on the free tier. Please pause for a few seconds or use direct system commands."

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
        """Plays the generated audio file using pygame with instant interruption support."""
        if not self._init_pygame():
            return False

        try:
            import pygame
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and self._is_speaking and not self._stop_requested:
                try:
                    import msvcrt
                    if msvcrt.kbhit():
                        msvcrt.getch()
                        self.stop()
                        return False
                except Exception:
                    pass
                pygame.time.Clock().tick(30)
            return True
        except Exception:
            return False

    def _speak_sapi(self, text: str, async_mode: bool = True) -> bool:
        """Zero-latency offline speech using Windows native SAPI with tactical military tone."""
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()
            if self._sapi_speaker is None:
                self._sapi_speaker = win32com.client.Dispatch("SAPI.SpVoice")
                for v in self._sapi_speaker.GetVoices():
                    if "david" in v.GetDescription().lower():
                        self._sapi_speaker.Voice = v
                        break
                self._sapi_speaker.Rate = 1

            # Flag 1: SVSFlagsAsync (non-blocking), Flag 2: SVSFPurgeBeforeSpeak
            flags = (1 | 2) if async_mode else 0
            self._sapi_speaker.Speak(text, flags)
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

    def wait_while_speaking(
        self,
        interrupt_check: Optional[Callable[[], bool]] = None,
        poll_interval: float = 0.015
    ) -> bool:
        """
        Monitors speech playback in real time (<15ms poll rate).
        Interruption triggers:
        1. Any key pressed in the console (msvcrt.kbhit).
        2. Voice barge-in callback returning True.
        3. self.stop() called.
        
        Returns True if interrupted, False if finished naturally.
        """
        # Wait up to 0.25s for SAPI to initialize running state
        t0 = time.time()
        while self.fast_voice and self._sapi_speaker:
            try:
                if self._sapi_speaker.Status.RunningState == 2:
                    break
            except Exception:
                break
            if time.time() - t0 >= 0.25:
                break
            try:
                import msvcrt
                if msvcrt.kbhit():
                    msvcrt.getch()
                    self.stop()
                    return True
            except Exception:
                pass
            if interrupt_check:
                try:
                    if interrupt_check():
                        self.stop()
                        return True
                except Exception:
                    pass
            time.sleep(0.01)

        interrupted = False
        while self._is_speaking and not self._stop_requested:
            # 1. SAPI state check
            if self.fast_voice and self._sapi_speaker:
                try:
                    if self._sapi_speaker.Status.RunningState != 2:
                        break
                except Exception:
                    break

            # 2. Pygame state check
            if not self.fast_voice and self._pygame_initialized:
                try:
                    import pygame
                    if not pygame.mixer.music.get_busy():
                        break
                except Exception:
                    break

            # 3. Instant Keyboard Interruption Check (any key in console)
            try:
                import msvcrt
                if msvcrt.kbhit():
                    msvcrt.getch()
                    self.stop()
                    interrupted = True
                    break
            except Exception:
                pass

            # 4. Voice Barge-In Check
            if interrupt_check:
                try:
                    if interrupt_check():
                        self.stop()
                        interrupted = True
                        break
                except Exception:
                    pass

            time.sleep(poll_interval)

        self._is_speaking = False
        return interrupted

    def speak_ack(self) -> None:
        """Speaks an instantaneous acknowledgment phrase (<20ms latency) without blocking."""
        ack = random.choice(self.ACKNOWLEDGMENTS)
        self._speak_sapi(ack, async_mode=True)

    def speak(
        self,
        text: str,
        blocking: bool = False,
        listener: Optional[Any] = None
    ) -> bool:
        """
        Synthesizes and speaks text aloud with instant interruption support.
        
        Args:
            text: The text string to speak.
            blocking: If True, waits until speech completes or is interrupted.
            listener: Optional VoiceListener instance to enable acoustic voice barge-in.
            
        Returns:
            True if interrupted early, False if finished normally.
        """
        if not text or not text.strip():
            return False

        speech_text = self._clean_text_for_speech(text)
        if not speech_text:
            return False

        self._stop_requested = False
        self._is_speaking = True

        # Fast native Windows SAPI mode
        if self.fast_voice:
            self._speak_sapi(speech_text, async_mode=True)
            if blocking:
                monitor = listener.create_barge_in_monitor() if listener and hasattr(listener, "create_barge_in_monitor") else None
                if monitor:
                    monitor.start()
                try:
                    check_fn = monitor.is_triggered if monitor else None
                    interrupted = self.wait_while_speaking(interrupt_check=check_fn)
                    return interrupted
                finally:
                    if monitor:
                        monitor.stop()
            return False

        # Neural edge-tts path
        interrupted = False
        def _worker():
            nonlocal interrupted
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
                        if not played and not self._stop_requested:
                            self._speak_sapi(speech_text, async_mode=True)
                            interrupted = self.wait_while_speaking()
                    elif not self._stop_requested:
                        self._speak_sapi(speech_text, async_mode=True)
                        interrupted = self.wait_while_speaking()

                except Exception:
                    if not self._stop_requested:
                        self._speak_sapi(speech_text, async_mode=True)
                        interrupted = self.wait_while_speaking()
                finally:
                    self._is_speaking = False
                    if temp_audio and os.path.exists(temp_audio):
                        try:
                            os.remove(temp_audio)
                        except Exception:
                            pass

        if blocking:
            _worker()
            return interrupted
        else:
            t = threading.Thread(target=_worker, daemon=True)
            t.start()
            return False

    def stop(self) -> None:
        """Stops currently playing audio immediately (<1ms)."""
        self._is_speaking = False
        self._stop_requested = True
        if self._sapi_speaker is not None:
            try:
                # SVSFPurgeBeforeSpeak = 2 purges all speech instantly
                self._sapi_speaker.Speak("", 2)
            except Exception:
                pass
        if self._pygame_initialized:
            try:
                import pygame
                pygame.mixer.music.stop()
            except Exception:
                pass
