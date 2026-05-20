import asyncio
import numpy as np
from livekit.agents import tts
from piper.voice import PiperVoice

class LocalPiper(tts.TTS):
    def __init__(self, model_path: str, config_path: str = None):
        self._voice = PiperVoice.load(model_path, config_path=config_path)
        
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=self._voice.config.sample_rate,
            num_channels=1
        )

    def synthesize(self, text: str, *, conn_options=None) -> tts.ChunkedStream:
        return PiperChunkedStream(tts=self, input_text=text, conn_options=conn_options)

class PiperChunkedStream(tts.ChunkedStream):
    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        # 1. Initialize Emitter
        output_emitter.initialize(
            request_id="local_piper",
            sample_rate=self._tts.sample_rate,
            num_channels=1,
            mime_type="audio/pcm"
        )

        def get_all_audio():
            audio_data = b""
            # Piper yields raw bytes (int16)
            for chunk in self._tts._voice.synthesize(self.input_text):
                audio_data += chunk.audio_int16_bytes
            return audio_data


        # 2. Generate all audio in a thread
        try:
            print(f"--- [PIPER] Synthesizing: {self.input_text[:30]}... ---")
            audio_bytes = await asyncio.to_thread(get_all_audio)
            
            if not audio_bytes:
                print("--- [ERROR] Piper returned EMPTY audio! ---")
                return

            print(f"--- [PIPER] Generated {len(audio_bytes)} bytes ---")

            # 3. Push to LiveKit in chunks
            chunk_size = int(self._tts.sample_rate * 0.1) * 2 # 100ms
            for i in range(0, len(audio_bytes), chunk_size):
                output_emitter.push(audio_bytes[i:i + chunk_size])
                await asyncio.sleep(0) # Let loop breathe

        except Exception as e:
            print(f"--- [ERROR] Piper Synthesis Failed: {e} ---")
        
        output_emitter.flush()
