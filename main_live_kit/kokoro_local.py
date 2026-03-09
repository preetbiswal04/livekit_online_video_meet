from livekit.agents import tts
from kokoro_onnx import Kokoro
import numpy as np 
import os
import asyncio
from livekit import rtc

class LocalKokoro(tts.TTS):
    def __init__(self, model_path: str = "livekit_online_video_meet/main_live_kit/kokoro-v1.0.fp16-gpu.onnx", voice_path: str = "livekit_online_video_meet/main_live_kit/voices-v1.0.bin"):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=24000,
            num_channels=1
        )
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"kokoro model not found at {model_path}")
        self._kokoro = Kokoro(model_path, voice_path)

    def synthesize(self, text: str, *, conn_options=None) -> tts.ChunkedStream:
        return LocalChunkedStream(tts=self, input_text=text, conn_options=conn_options)

class LocalChunkedStream(tts.ChunkedStream):
    def __init__(self, *, tts: LocalKokoro, input_text: str, conn_options):
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._tts = tts

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        # af_heart is a common voice, but verify it exists in voices.bin
        # Run synthesis in a thread pool to avoid blocking the event loop
        samples, sample_rate = await asyncio.to_thread(
            self._tts._kokoro.create, 
            self.input_text, 
            voice="af_heart", 
            speed=1.0
        )
        audio_data = (samples * 32767).astype(np.int16).tobytes()
        
        output_emitter.initialize(
            request_id="local_kokoro",
            sample_rate=sample_rate,
            num_channels=1,
            mime_type="audio/pcm"
        )
        
        # Chunking: Push audio in smaller pieces (e.g., 100ms = 2400 samples * 2 bytes)
        chunk_size = int(sample_rate * 0.1) * 2 # 100ms chunk
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            output_emitter.push(chunk)
            # Subtle sleep to allow the event loop to breathe if needed, 
            # though usually not required for a single non-streaming synthesis.
            await asyncio.sleep(0) 

        output_emitter.flush()

