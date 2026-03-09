from livekit.agents import stt
from livekit.agents.utils import AudioBuffer
from faster_whisper import WhisperModel
import numpy as np
import asyncio

class LocalWhisper(stt.STT):
    def __init__(self):
        super().__init__(capabilities=stt.STTCapabilities(streaming=False, interim_results=False, diarization=False))
        # Switch to base model for better real-time performance on CPU
        self._model = WhisperModel("base", device="cpu", compute_type="int8")

    async def _recognize_impl(self, buffer: AudioBuffer, *, language=None, conn_options=None):
        if not isinstance(buffer, (list, tuple)):
            buffer = [buffer]
            
        if not buffer:
            return stt.SpeechEvent(type=stt.SpeechEventType.FINAL_TRANSCRIPT, alternatives=[])

        # Get sample rate from the first frame
        sample_rate = buffer[0].sample_rate
        if sample_rate != 16000:
            print(f"--- [STT WARNING] Received audio at {sample_rate}Hz, but Whisper expects 16000Hz. This may cause gibberish. ---")

        # Merge frames and convert to float32 (Whisper requirement)
        audio_data = np.concatenate([np.frombuffer(f.data, dtype=np.int16) for f in buffer])
        audio_data = audio_data.astype(np.float32) / 32768.0

        # Run transcription in a thread pool to avoid blocking the event loop
        # Forcing language="en" to prevent hallucinations in other languages (like Welsh)
        segments, info = await asyncio.to_thread(
            self._model.transcribe, 
            audio_data, 
            beam_size=5, 
            language="en",
            condition_on_previous_text=False
        )
        text = " ".join(seg.text for seg in segments).strip()
        
        if text:
            print(f"--- [STT DEBUG] Transcribed ({info.language}): {text} ---")
        
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(text=text, language=info.language)]
        )
