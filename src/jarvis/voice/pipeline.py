"""Voice pipeline for JARVIS - Wake word, STT, TTS."""

import asyncio
import struct
import sys
from pathlib import Path

import structlog

from jarvis.config.settings import settings

logger = structlog.get_logger()

# Optional imports for voice features
try:
    import pvporcupine

    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False
    logger.warning("Porcupine not available. Install with: uv sync --extra voice")

try:
    import pyaudio

    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("PyAudio not available. Install with: uv sync --extra voice")

try:
    from faster_whisper import WhisperModel

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper not available. Install with: uv sync --extra voice")


class VoicePipeline:
    """Complete voice interaction pipeline.

    Flow:
    1. Listen for wake word ("Hey JARVIS")
    2. Record user speech
    3. Transcribe with Whisper
    4. Process command
    5. Generate response
    6. Speak via TTS
    """

    def __init__(self) -> None:
        self.porcupine = None
        self.audio = None
        self.whisper = None
        self.running = False

    async def initialize(self) -> bool:
        """Initialize all voice components."""
        if not PORCUPINE_AVAILABLE or not PYAUDIO_AVAILABLE:
            logger.error("Voice dependencies not available")
            return False

        try:
            # Initialize Porcupine wake word
            access_key = settings.voice.picovoice_access_key.get_secret_value()
            if not access_key:
                logger.error("Picovoice access key not configured")
                return False

            # Use built-in "jarvis" wake word or custom
            wake_word = settings.voice.wake_word
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keywords=[wake_word] if wake_word in pvporcupine.KEYWORDS else None,
                keyword_paths=[wake_word] if wake_word not in pvporcupine.KEYWORDS else None,
            )

            # Initialize PyAudio
            self.audio = pyaudio.PyAudio()

            # Initialize Whisper
            if WHISPER_AVAILABLE:
                model_size = settings.voice.whisper_model
                self.whisper = WhisperModel(model_size, device="cpu", compute_type="int8")

            logger.info("Voice pipeline initialized")
            return True

        except Exception as e:
            logger.error("Failed to initialize voice pipeline", error=str(e))
            return False

    async def start(self) -> None:
        """Start the voice pipeline."""
        if not await self.initialize():
            logger.error("Cannot start voice pipeline - initialization failed")
            return

        self.running = True
        logger.info("Voice pipeline started. Say 'Hey JARVIS' to wake.")

        try:
            await self._listen_loop()
        except KeyboardInterrupt:
            logger.info("Voice pipeline interrupted")
        finally:
            await self.stop()

    async def stop(self) -> None:
        """Stop the voice pipeline."""
        self.running = False

        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None

        if self.audio:
            self.audio.terminate()
            self.audio = None

        logger.info("Voice pipeline stopped")

    async def _listen_loop(self) -> None:
        """Main listening loop for wake word detection."""
        if not self.porcupine or not self.audio:
            return

        stream = self.audio.open(
            rate=self.porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.porcupine.frame_length,
        )

        logger.info("Listening for wake word...")

        try:
            while self.running:
                # Read audio frame
                pcm = stream.read(self.porcupine.frame_length)
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)

                # Check for wake word
                keyword_index = self.porcupine.process(pcm)

                if keyword_index >= 0:
                    logger.info("Wake word detected!")
                    await self._handle_wake()

                # Small delay to prevent CPU spin
                await asyncio.sleep(0.01)

        finally:
            stream.close()

    async def _handle_wake(self) -> None:
        """Handle wake word detection."""
        # Play acknowledgment sound
        await self._play_chime()

        # Record user speech
        audio_data = await self._record_speech()

        if not audio_data:
            return

        # Transcribe
        text = await self._transcribe(audio_data)

        if not text:
            await self._speak("I didn't catch that. Could you repeat?")
            return

        logger.info("Transcribed", text=text)

        # Process command and generate response
        response = await self._process_command(text)

        # Speak response
        await self._speak(response)

    async def _play_chime(self) -> None:
        """Play acknowledgment chime."""
        # In production, play an actual audio file
        logger.info("*chime*")

    async def _record_speech(self, timeout: float = 5.0) -> bytes | None:
        """Record speech until silence detected."""
        if not self.audio:
            return None

        logger.info("Recording speech...")

        frames = []
        stream = self.audio.open(
            rate=16000,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=1024,
        )

        try:
            # Simple recording for timeout duration
            # In production, use VAD (Voice Activity Detection) for silence detection
            import time

            start = time.time()
            while time.time() - start < timeout:
                data = stream.read(1024)
                frames.append(data)

            return b"".join(frames)

        finally:
            stream.close()

    async def _transcribe(self, audio_data: bytes) -> str | None:
        """Transcribe audio using Whisper."""
        if not self.whisper:
            logger.warning("Whisper not available")
            return None

        try:
            # Save to temp file (faster-whisper requires file path)
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                # Write WAV header + data
                import wave

                with wave.open(f.name, "wb") as wav:
                    wav.setnchannels(1)
                    wav.setsampwidth(2)
                    wav.setframerate(16000)
                    wav.writeframes(audio_data)

                # Transcribe
                segments, _ = self.whisper.transcribe(f.name)
                text = " ".join(segment.text for segment in segments)

                return text.strip()

        except Exception as e:
            logger.error("Transcription failed", error=str(e))
            return None

    async def _process_command(self, text: str) -> str:
        """Process command and generate response."""
        text_lower = text.lower()

        # Simple keyword matching for demo
        # In production, use Claude via Clawdbot for natural language understanding

        if "sleep" in text_lower:
            from jarvis.aggregators.health import get_health_summary

            health = await get_health_summary()
            sleep = health.get("sleep", {})
            hours = sleep.get("total_hours", 0)
            return f"You slept {hours:.1f} hours last night."

        elif "recovery" in text_lower:
            from jarvis.aggregators.health import get_health_summary

            health = await get_health_summary()
            recovery = health.get("recovery", {})
            score = recovery.get("score", "unknown")
            return f"Your recovery score is {score} percent."

        elif "schedule" in text_lower or "calendar" in text_lower:
            from jarvis.aggregators.calendar import get_merged_calendar

            cal = await get_merged_calendar()
            events = cal.get("events", [])
            if events:
                first = events[0]
                return f"Your next event is {first.get('title')} at {first.get('start', '')[:16]}."
            return "You have no events scheduled."

        elif "briefing" in text_lower:
            from jarvis.aggregators.daily import get_daily_briefing

            briefing = await get_daily_briefing()
            return briefing.get("summary", "Unable to generate briefing.")

        elif "light" in text_lower:
            from jarvis.adapters.home_assistant import HomeAssistantAdapter

            async with HomeAssistantAdapter() as ha:
                if "on" in text_lower:
                    await ha.turn_on("light.living_room")
                    return "Turning on the living room lights."
                elif "off" in text_lower:
                    await ha.turn_off("light.living_room")
                    return "Turning off the living room lights."

        else:
            return f"I heard: {text}. I'm not sure how to help with that yet."

    async def _speak(self, text: str) -> None:
        """Speak text via TTS."""
        logger.info("Speaking", text=text[:50])

        # Use Home Assistant TTS
        try:
            from jarvis.adapters.home_assistant import speak_message

            await speak_message(text)
        except Exception as e:
            logger.error("TTS failed", error=str(e))
            # Fallback: just print
            print(f"JARVIS: {text}")


def main() -> None:
    """Entry point for voice service."""
    import signal

    pipeline = VoicePipeline()

    def shutdown(sig: int, frame: object) -> None:
        logger.info("Shutting down voice pipeline...")
        asyncio.get_event_loop().run_until_complete(pipeline.stop())
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    asyncio.run(pipeline.start())


if __name__ == "__main__":
    main()
