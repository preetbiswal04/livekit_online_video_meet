# import asyncio
# from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, stt
# from livekit.plugins import deepgram, silero
# from livekit.rtc import AudioStream, DataPacketKind, TrackKind
# from dotenv import load_dotenv
# import os

# load_dotenv()

# async def entrypoint(ctx: JobContext):
#     print(f"--- Room {ctx.room.name}: Deepgram Transcription agent started ---")

#     # Get API key from environment
#     api_key = os.getenv("DEEPGRAM_API_KEY")
#     if not api_key:
#         print("ERROR: DEEPGRAM_API_KEY is missing from .env!")
#         return

#     # Initialize Deepgram STT - optimized for ultra-low latency
#     stt_instance = deepgram.STT(
#         api_key=api_key,
#         interim_results=True,  # Enable for real-time updates
#         model="nova-2",
#         #model = "nova-3", 
#         language="en-IN" ,
#         endpointing_ms=1000# Fast model
#     )
#     vad=silero.VAD.load(),  
    
    
#     await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
#     print(f"Connected as {ctx.room.local_participant.identity}")

#     async def process_track(track, participant):
#         print(f"DEBUG: Starting Deepgram stream for: {participant.identity}")
#         stt_stream = stt_instance.stream()
#         is_stream_active = True

#         async def push_audio():
#             nonlocal is_stream_active
#             try:
#                 audio_stream = AudioStream(track)
#                 async for event in audio_stream:
#                     if not is_stream_active:
#                         break
#                     stt_stream.push_frame(event.frame)
#                 stt_stream.end_input()
#             except Exception as e:
#                 if is_stream_active:
#                     print(f"DEBUG: Audio push task ending for {participant.identity}: {e}")
#             finally:
#                 is_stream_active = False

#         push_task = asyncio.create_task(push_audio())

#         try:
#             async for event in stt_stream:
#                 text = ""
#                 try:
#                     if hasattr(event, 'transcript') and event.transcript:
#                         text = event.transcript.text
#                     elif hasattr(event, 'alternatives') and event.alternatives and len(event.alternatives) > 0:
#                         text = event.alternatives[0].text
#                 except Exception:
#                     pass

#                 if text and text.strip():
#                     is_final = (event.type == stt.SpeechEventType.FINAL_TRANSCRIPT)
                    
#                     # Show real-time updates in chat
#                     print(f"{'[FINAL]' if is_final else '[LIVE]'} [{participant.identity}]: {text}")
                    
#                     # Publish to chat (both interim and final for low latency)
#                     try:
#                         # Simple format: just user and their text
#                         publish_msg = f"{participant.identity}: {text}"
#                         await ctx.room.local_participant.publish_data(
#                             publish_msg.encode("utf-8")
#                         )
#                     except Exception as e:
#                         print(f"ERROR: Chat publication FAILED: {e}")
                    
#                     # Only save final transcripts to file
#                     if is_final:
#                         with open("transcripts.log", "a", encoding="utf-8") as f:
#                             f.write(f"{participant.identity}: {text}\n")
                
#                 if event.type == stt.SpeechEventType.RECOGNITION_USAGE:
#                    print("DEBUG: Deepgram processed utterance.")
        
#         except Exception as e:
#             print(f"DEBUG: STT Stream ended for {participant.identity}: {e}")
#         finally:
#             is_stream_active = False
#             await push_task

#     @ctx.room.on("track_subscribed")
#     def on_track(track, publication, participant):
#         print(f"EVENT: Track subscribed! Kind: {track.kind}, Sender: {participant.identity}")
#         if track.kind == TrackKind.KIND_AUDIO:
#             asyncio.create_task(process_track(track, participant))
#         else:
#             print(f"Ignoring non-audio track: {track.kind}")

#     print("Agent is ready and listening for Deepgram events...")

# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

###################################deepgram##################################################
############################aws##############################################################
# import boto3
# from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli
# from livekit.rtc import DataPacketKind

# lex = boto3.client(
#     "lexv2-runtime",
#     region_name="ap-south-1"
# )

# BOT_ID = "YOUR_BOT_ID"
# BOT_ALIAS_ID = "YOUR_ALIAS_ID"
# LOCALE = "en_US"

# async def entrypoint(ctx: JobContext):
#     await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

#     @ctx.room.on("track_subscribed")
#     async def on_track(track, *_):
#         if track.kind != "audio":
#             return

#         async for frame in track:
#             # frame.data = PCM audio bytes
#             response = lex.recognize_utterance(
#                 botId=BOT_ID,
#                 botAliasId=BOT_ALIAS_ID,
#                 localeId=LOCALE,
#                 sessionId=ctx.room.name,
#                 inputStream=frame.data,
#                 contentType="audio/lpcm; sample-rate=16000; sample-size-bits=16; channel-count=1"
#             )

#             if "inputTranscript" in response:
#                 text = response["inputTranscript"]

#                 await ctx.room.local_participant.publish_data(
#                     text.encode(),
#                     kind=DataPacketKind.RELIABLE
#                 )
#################################elevenlabs#################################
# import logging
# from dotenv import load_dotenv
# from livekit.agents import (
#     AutoSubscribe,
#     JobContext,
#     WorkerOptions,
#     cli,
#     llm,
# )
# from livekit.agents.pipeline import VoicePipelineAgent
# from livekit.plugins import elevenlabs, openai

# load_dotenv()

# logger = logging.getLogger("voice-agent")
# logger.setLevel(logging.INFO)

# async def entrypoint(ctx: JobContext):
#     initial_ctx = llm.ChatContext().append(
#         role="system",
#         text=(
#             "You are a helpful assistant. Your interface with the user will be voice. "
#             "You should provide concise and polite responses."
#         ),
#     )

#     await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

#     agent = VoicePipelineAgent(
#         stt=elevenlabs.STT(model="scribe_v2_realtime"),
#         llm=openai.LLM(),
#         tts=openai.TTS(),
#         chat_ctx=initial_ctx,
#     )

#     agent.start(ctx.room)
    
#     # Listen for transcripts and print them (optional, for logging)
#     @agent.on("user_transcript_finished")
#     def on_user_transcript(transcript: str):
#         print(f"User: {transcript}")
#         with open("transcripts.log", "a", encoding="utf-8") as f:
#             f.write(f"User: {transcript}\n")

#     @agent.on("agent_transcript_finished")
#     def on_agent_transcript(transcript: str):
#         print(f"Agent: {transcript}")
#         with open("transcripts.log", "a", encoding="utf-8") as f:
#             f.write(f"Agent: {transcript}\n")

#     await agent.say("Hello! How can I help you today?", allow_interruptions=True)

# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
# ################################elevenlabs without openai#################################

# import logging
# import asyncio
# from dotenv import load_dotenv
# from livekit.agents import (
#     AutoSubscribe,
#     JobContext,
#     WorkerOptions,
#     cli,
# )
# from livekit.plugins import elevenlabs
# from livekit.rtc import DataPacketKind, TrackKind

# load_dotenv()

# async def entrypoint(ctx: JobContext):
#     print(f"--- Room {ctx.room.name}: Transcription agent started ---")

#     import os
#     # Get API key - try both common names
#     api_key = os.getenv("ELEVEN_API_KEY") or os.getenv("ELEVENLABS_API_KEY")
#     if not api_key:
#         print("ERROR: ELEVEN_API_KEY is missing from .env!")
#         return

#     # Use ElevenLabs Scribe
#     # (use_realtime=True and language_code="en" often help with connection stability)
#     stt = elevenlabs.STT(
#         api_key=api_key,
#         use_realtime=True,
#         language_code="en",
#         tag_audio_events=False
#     )
    
#     print(f"Connecting to room {ctx.room.name}...")
#     # Using SUBSCRIBE_ALL often helps with initial discovery
#     await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    
#     # Wait a moment for room state to synchronize
#     await asyncio.sleep(1)
#     print(f"Connected as {ctx.room.local_participant.identity}")

#     async def transcribe_track(track, participant):
#         print(f"DEBUG: Starting transcription stream for: {participant.identity}")
#         try:
#             # ElevenLabs STT.stream() does not take a track argument.
#             # We create a stream and manually push audio frames into it.
#             stt_stream = stt.stream()
            
#             async def push_audio():
#                 async for frame in track:
#                     stt_stream.push_frame(frame)
#                 stt_stream.end_input()

#             # Run push_audio in the background
#             push_task = asyncio.create_task(push_audio())

#             async for event in stt_stream:
#                 if event.type == "transcript":
#                     text = event.transcript.text
#                     sender = participant.identity

#                     if not text.strip():
#                         continue

#                     print(f"TRANSCRIPTION [{sender}]: {text}")

#                     # 1. Store in local file
#                     with open("transcripts.log", "a", encoding="utf-8") as f:
#                         f.write(f"{sender}: {text}\n")

#                     # 2. Send to the Web UI chat
#                     message = f"Transcript ({sender}): {text}"
#                     await ctx.room.local_participant.publish_data(
#                         message.encode("utf-8"),
#                         kind=DataPacketKind.RELIABLE
#                     )
            
#             await push_task
#         except Exception as e:
#             print(f"ERROR in transcription stream: {e}")
#             import traceback
#             traceback.print_exc()

#     @ctx.room.on("track_subscribed")
#     def on_track(track, publication, participant):
#         print(f"DEBUG: Track subscribed! Kind: {track.kind}, Sender: {participant.identity}")
#         if track.kind == TrackKind.KIND_AUDIO:
#             asyncio.create_task(transcribe_track(track, participant))

#     print("Agent is ready and waiting for audio...")

# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

################################### whisper open ai ###############################################
# import asyncio
# from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, stt
# from livekit.plugins import deepgram
# from openai import OpenAI
# from livekit.rtc import AudioStream, DataPacketKind, TrackKind
# from dotenv import load_dotenv
# import os

# load_dotenv()

# async def entrypoint(ctx: JobContext):
#     print(f"--- Room {ctx.room.name}: openai Transcription agent started ---")

#     # Get API key from environment
#     api_key = os.getenv("OPENAI_API_KEY")
#     if not api_key:
#         print("ERROR: OPENAI_API_KEY is missing from .env!")
#         return

#     # Initialize openai STT - optimized for ultra-low latency
#     stt_instance = OpenAI.STT(
#         api_key=api_key,
#         #interim_results=True,  # Enable for real-time updates
#         model="whisper-1"  # Fast model
#     )
    
#     await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
#     print(f"Connected as {ctx.room.local_participant.identity}")

#     async def process_track(track, participant):
#         print(f"DEBUG: Starting openai stream for: {participant.identity}")
#         stt_stream = stt_instance.stream()
#         is_stream_active = True

#         async def push_audio():
#             nonlocal is_stream_active
#             try:
#                 audio_stream = AudioStream(track)
#                 async for event in audio_stream:
#                     if not is_stream_active:
#                         break
#                     stt_stream.push_frame(event.frame)
#                 stt_stream.end_input()
#             except Exception as e:
#                 if is_stream_active:
#                     print(f"DEBUG: Audio push task ending for {participant.identity}: {e}")
#             finally:
#                 is_stream_active = False

#         push_task = asyncio.create_task(push_audio())

#         try:
#             async for event in stt_stream:
#                 text = ""
#                 try:
#                     if hasattr(event, 'transcript') and event.transcript:
#                         text = event.transcript.text
#                     elif hasattr(event, 'alternatives') and event.alternatives and len(event.alternatives) > 0:
#                         text = event.alternatives[0].text
#                 except Exception:
#                     pass

#                 if text and text.strip():
#                     is_final = (event.type == stt.SpeechEventType.FINAL_TRANSCRIPT)
                    
#                     # Show real-time updates in chat
#                     print(f"{'[FINAL]' if is_final else '[LIVE]'} [{participant.identity}]: {text}")
                    
#                     # Publish to chat (both interim and final for low latency)
#                     try:
#                         # Simple format: just user and their text
#                         publish_msg = f"{participant.identity}: {text}"
#                         await ctx.room.local_participant.publish_data(
#                             publish_msg.encode("utf-8")
#                         )
#                     except Exception as e:
#                         print(f"ERROR: Chat publication FAILED: {e}")
                    
#                     # Only save final transcripts to file
#                     # if is_final:
#                     #     with open("transcripts.log", "a", encoding="utf-8") as f:
#                     #         f.write(f"{participant.identity}: {text}\n")
                
#                 if event.type == stt.SpeechEventType.RECOGNITION_USAGE:
#                    print("DEBUG: openai processed utterance.")
        
#         except Exception as e:
#             print(f"DEBUG: STT Stream ended for {participant.identity}: {e}")
#         finally:
#             is_stream_active = False
#             await push_task

#     @ctx.room.on("track_subscribed")
#     def on_track(track, publication, participant):
#         print(f"EVENT: Track subscribed! Kind: {track.kind}, Sender: {participant.identity}")
#         if track.kind == TrackKind.KIND_AUDIO:
#             asyncio.create_task(process_track(track, participant))
#         else:
#             print(f"Ignoring non-audio track: {track.kind}")

#     print("Agent is ready and listening for Deepgram events...")

# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
# ######################################### cartesia #######################################################
# import asyncio
# from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, stt
# from livekit.plugins import deepgram
# from livekit.rtc import AudioStream, DataPacketKind, TrackKind
# from livekit.agents import AgentSession, inference
# from dotenv import load_dotenv
# import os

# load_dotenv()

# async def entrypoint(ctx: JobContext):
#     print(f"--- Room {ctx.room.name}: cartesia Transcription agent started ---")

#     # Get API key from environment
#     api_key = os.getenv("cartesia_api_key")
#     if not api_key:
#         print("ERROR: cartesia_api_key is missing from .env!")
#         return

#     # Initialize Deepgram STT - optimized for ultra-low latency
#     session = AgentSession(
#     stt=inference.STT(
#         model="cartesia/ink-whisper", 
#         #language="hi",
#         language="en"
#         #language="mr"
#     ),
#     # ... tts, stt, vad, turn_detection, etc.
# )

#     await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
#     print(f"Connected as {ctx.room.local_participant.identity}")

#     async def process_track(track, participant):
#         print(f"DEBUG: Starting cartesia stream for: {participant.identity}")
#         stt_stream = session.stt.stream()
#         is_stream_active = True

#         async def push_audio():
#             nonlocal is_stream_active
#             try:
#                 audio_stream = AudioStream(track)
#                 async for event in audio_stream:
#                     if not is_stream_active:
#                         break
#                     stt_stream.push_frame(event.frame)
#                 stt_stream.end_input()
#             except Exception as e:
#                 if is_stream_active:
#                     print(f"DEBUG: Audio push task ending for {participant.identity}: {e}")
#             finally:
#                 is_stream_active = False

#         push_task = asyncio.create_task(push_audio())

#         try:
#             async for event in stt_stream:
#                 text = ""
#                 try:
#                     if hasattr(event, 'transcript') and event.transcript:
#                         text = event.transcript.text
#                     elif hasattr(event, 'alternatives') and event.alternatives and len(event.alternatives) > 0:
#                         text = event.alternatives[0].text
#                 except Exception:
#                     pass

#                 if text and text.strip():
#                     is_final = (event.type == stt.SpeechEventType.FINAL_TRANSCRIPT)
                    
#                     # Show real-time updates in chat
#                     print(f"{'[FINAL]' if is_final else '[LIVE]'} [{participant.identity}]: {text}")
                    
#                     # Publish to chat (both interim and final for low latency)
#                     try:
#                         # Simple format: just user and their text
#                         publish_msg = f"{participant.identity}: {text}"
#                         await ctx.room.local_participant.publish_data(
#                             publish_msg.encode("utf-8")
#                         )
#                     except Exception as e:
#                         print(f"ERROR: Chat publication FAILED: {e}")
                    
#                     # Only save final transcripts to file
#                     # if is_final:
#                     #     with open("transcripts.log", "a", encoding="utf-8") as f:
#                     #         f.write(f"{participant.identity}: {text}\n")
                
#                 if event.type == stt.SpeechEventType.RECOGNITION_USAGE:
#                    print("DEBUG: cartesia processed utterance.")
        
#         except Exception as e:
#             print(f"DEBUG: STT Stream ended for {participant.identity}: {e}")
#         finally:
#             is_stream_active = False
#             await push_task

#     @ctx.room.on("track_subscribed")
#     def on_track(track, publication, participant):
#         print(f"EVENT: Track subscribed! Kind: {track.kind}, Sender: {participant.identity}")
#         if track.kind == TrackKind.KIND_AUDIO:
#             asyncio.create_task(process_track(track, participant))
#         else:
#             print(f"Ignoring non-audio track: {track.kind}")

#     print("Agent is ready and listening for cartesia events...")

# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
