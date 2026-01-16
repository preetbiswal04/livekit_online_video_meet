import asyncio
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, stt
from livekit.plugins import deepgram, silero
from livekit.rtc import AudioStream, DataPacketKind, TrackKind
from dotenv import load_dotenv
import os
import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import datetime
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

async def entrypoint(ctx: JobContext):
    print(f"--- Room {ctx.room.name}: Deepgram Transcription agent started ---")

    # Get API key from environment
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("ERROR: DEEPGRAM_API_KEY is missing from .env!")
        return

    # Initialize Deepgram STT - optimized for ultra-low latency
    stt_instance = deepgram.STT(
        api_key=api_key,
        interim_results=True,  # Enable for real-time updates
        model="nova-2",
        #model = "nova-3", 
        language="en-IN" ,
        #endpointing_ms=1000# Fast model
    )
    # vad=silero.VAD.load(),  

    # --- MongoDB Setup (Async) ---
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    mongo_db_name = os.getenv("MONGO_DB_NAME", "livekit_chat")
    try:
        mongo_client = AsyncIOMotorClient(mongo_uri)
        db = mongo_client[mongo_db_name]
        messages_collection = db['messages']
        print(f"Connected to MongoDB: {mongo_db_name}")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")
        messages_collection = None
    
    
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    print(f"Connected as {ctx.room.local_participant.identity}")

    async def process_track(track, participant):
        print(f"DEBUG: Starting Deepgram stream for: {participant.identity}")
        stt_stream = stt_instance.stream()
        is_stream_active = True

        async def push_audio():
            nonlocal is_stream_active
            try:
                audio_stream = AudioStream(track)
                async for event in audio_stream:
                    if not is_stream_active:
                        break
                    stt_stream.push_frame(event.frame)
                stt_stream.end_input()
            except Exception as e:
                if is_stream_active:
                    print(f"DEBUG: Audio push task ending for {participant.identity}: {e}")
            finally:
                is_stream_active = False

        push_task = asyncio.create_task(push_audio())

        try:
            async for event in stt_stream:
                text = ""
                try:
                    if hasattr(event, 'transcript') and event.transcript:
                        text = event.transcript.text
                    elif hasattr(event, 'alternatives') and event.alternatives and len(event.alternatives) > 0:
                        text = event.alternatives[0].text
                except Exception:
                    pass

                if text and text.strip():
                    is_final = (event.type == stt.SpeechEventType.FINAL_TRANSCRIPT)
                    
                    # Show real-time updates in chat
                    print(f"{'[FINAL]' if is_final else '[LIVE]'} [{participant.identity}]: {text}")
                    
                    # Publish to chat (both interim and final for low latency)
                    try:
                        # Simple format: just user and their text
                        publish_msg = f"{participant.identity}: {text}"
                        await ctx.room.local_participant.publish_data(
                            publish_msg.encode("utf-8")
                        )
                    except Exception as e:
                        print(f"ERROR: Chat publication FAILED: {e}")
                    
                    # # Only save final transcripts to file
                    if is_final:
                        with open("transcripts.log", "a", encoding="utf-8") as f:
                            f.write(f"{participant.identity}: {text}\n")
                        
                        # Save to MongoDB
                        if messages_collection is not None:
                            try:
                                await messages_collection.update_one(
                                    {
                                        "room": ctx.room.name,
                                        "type": "transcript_aggregation"
                                    },
                                    {
                                        "$setOnInsert": {
                                            "created_at": datetime.datetime.utcnow(),
                                            "is_transcript": True
                                        },
                                        "$push": {
                                            "segments": {
                                                "sender": participant.identity,
                                                "text": text,
                                                "timestamp": datetime.datetime.utcnow()
                                            }
                                        }
                                    },
                                    upsert=True
                                )
                            except Exception as e:
                                print(f"ERROR: Failed to save to MongoDB: {e}")
                
                if event.type == stt.SpeechEventType.RECOGNITION_USAGE:
                   print("DEBUG: Deepgram processed utterance.")
        
        except Exception as e:
            print(f"DEBUG: STT Stream ended for {participant.identity}: {e}")
        finally:
            is_stream_active = False
            await push_task

    @ctx.room.on("track_subscribed")
    def on_track(track, publication, participant):
        print(f"EVENT: Track subscribed! Kind: {track.kind}, Sender: {participant.identity}")
        if track.kind == TrackKind.KIND_AUDIO:
            asyncio.create_task(process_track(track, participant))
        else:
            print(f"Ignoring non-audio track: {track.kind}")

    print("Agent is ready and listening for Deepgram events...")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
