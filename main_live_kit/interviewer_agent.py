import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json 
# Add project root to sys.path to find resume_jd_analyser
root_path = Path(__file__).parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))
from livekit.agents import JobContext, Agent, AgentSession, llm, WorkerOptions, cli, UserInputTranscribedEvent, ConversationItemAddedEvent, AutoSubscribe
from livekit.plugins import deepgram, google, cartesia, silero
# Fix import to point to the local file in the same directory or package
try:
    from .evaluation_gen import evaluate_candidate
except ImportError:
    try:
        from main_live_kit.evaluation_gen import evaluate_candidate
    except ImportError:
         from evaluation_gen import evaluate_candidate

load_dotenv()

key_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),"service_account_key.json")
if os.path.exists(key_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
    os.environ["GOOGLE_CLOUD_PROJECT"] = "balmy-amp-481707-p6"
    os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1" 
    print(f"--- [DEBUG] Vertex AI Credentials set: {key_path}")
else:
    print(f"--- [ERROR] Vertex AI Credentials not found at: {key_path}")


# Map lowercase env keys to uppercase as expected by plugins
if os.getenv("cartesia_api_key") and not os.getenv("CARTESIA_API_KEY"):
    os.environ["CARTESIA_API_KEY"] = os.getenv("cartesia_api_key")

# Pre-load VAD model globally to avoid loading it for every session
# print("--- [DEBUG] Pre-loading VAD model...")
# try:
#     vad_plugin = silero.VAD.load(min_silence_duration=0.5, min_speech_duration=0.3)
#     print("--- [DEBUG] VAD model pre-loaded successfully.")
# except Exception as e:
#     print(f"--- [ERROR] Failed to pre-load VAD model: {e}")
#     vad_plugin = None

# Global import for db_helper
try:
    from resume_jd_analyser.db_utils import db_helper
except ImportError:
    try:
        from main_live_kit.resume_jd_analyser.db_utils import db_helper
    except ImportError:
         print("--- [WARNING] Could not import db_helper globally.")
         db_helper = None

async def entrypoint(ctx: JobContext):
    print(f"--- [DEBUG] Room {ctx.room.name}: STARTING ENTRYPOINT ---")
    
    try:
        print("--- [DEBUG] Attempting to connect to room...")
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
        print(f"--- [DEBUG] CONNECTED! Local Identity: {ctx.room.local_participant.identity}")
    except Exception as e:
        print(f"--- [ERROR] Connection Failed: {e}")
        return
    
    room_name = ctx.room.name
    print(f"--- [DEBUG] Fetching session for room: {room_name}")
    try:
        interviewer_data = db_helper.get_session(room_name)
    except Exception as e:
        print(f"--- [ERROR] DB Helper Failed: {e}")
        interviewer_data = None
    
    if not interviewer_data:
        print(f"--- [WARNING] No session data found in DB. Using fallback prompt.")
        company_name = 'NEWEL TECHNOLOGIES'        
        system_prompt = f""" You are an expert technical interviewer for {company_name}.
Your task is to conduct a technical interview.

INPUT CONTEXT:
1. JOB DESCRIPTION (Source of all technical questions).
2. RESUME (Source for introduction and personal greeting ONLY).

RULES:
- Step 1 (Introduction): Start by introducing yourself and {company_name}. Then, greet the candidate by their name (from Resume) and mention 1-2 key highlights from their Resume summary/experience to break the ice. Ask them to introduce themselves.
- Step 2 (Technical Questions): After the intro, switch STRICTLY to the Job Description.
    - Ask questions ONLY based on the skills/tools in the JOB DESCRIPTION.
    - Do NOT ask questions based on the Resume skills if they are not in the JOB DESCRIPTION.
    - Do NOT ask generic/behavioral questions unless specified.

INTERVIEW STRUCTURE (10 Questions Total):
1. Intro: Role + Company + Personal greeting (using Resume) + Ask candidate intro.
2. 3 Questions: Core concepts from JOB DESCRIPTION.
3. 3 Questions: Tools/Skills from JOB DESCRIPTION.
4. 2 Questions: Technical deep-dive from JOB DESCRIPTION.
5. 2 Questions: Experience-based scenarios (related to JOB DESCRIPTION requirements).
"""
    else:
        print(f"--- [DEBUG] Found session data for {interviewer_data.get('candidate_name')}")
        system_prompt = f"""You are a professional AI Technical Interviewer.
        Candidate: {interviewer_data['candidate_name']}
        Resume Context: {interviewer_data['resume_context']}
        
        Ask these questions one by one:
        {interviewer_data['questions']}
        """

    chat_ctx = llm.ChatContext()
    chat_ctx.add_message(role="system", content=system_prompt)
    initialize_agent = chat_ctx
    print("--- [DEBUG] ChatContext initialized.")

    try:
        print("--- [DEBUG] Initializing STT (Deepgram)...")
        stt_plugin = deepgram.STT()
        
        print("--- [DEBUG] Initializing LLM (Gemini 2.0)...")
        
        llm_plugin = google.LLM(model="gemini-2.5-flash",vertexai=True)
        
        print("--- [DEBUG] Initializing TTS (Cartesia)...")
       
        tts_plugin = deepgram.TTS()
        
        # Pre-load VAD model globally to avoid loading it for every session
        print("--- [DEBUG] Pre-loading VAD model...")
        try:
            vad_plugin = silero.VAD.load(min_silence_duration=0.5, min_speech_duration=0.3)
            print("--- [DEBUG] VAD model pre-loaded successfully.")
        except Exception as e:
            print(f"--- [ERROR] Failed to pre-load VAD model: {e}")
            vad_plugin = None

        print("--- [DEBUG] Creating AgentSession...")
        session = AgentSession(
            stt=stt_plugin,
            llm=llm_plugin,
            tts=tts_plugin,
            vad=vad_plugin,
        )
        print("--- [DEBUG] AgentSession READY.")
    except Exception as e:
        print("--- [ERROR] Plugin Initialization Failed!")
        import traceback
        traceback.print_exc()
        return

    agent = Agent(instructions=system_prompt, chat_ctx=initialize_agent)

    @session.on("user_input_transcribed")
    def on_user_transcript(event: UserInputTranscribedEvent):
        if event.is_final:
            print(f"[TRANSCRIPT] Candidate: {event.transcript}")

    @session.on("conversation_item_added")
    def on_item_added(event: ConversationItemAddedEvent):
        if isinstance(event.item, llm.ChatMessage):
            if event.item.role == "system":
                return
            
            role = event.item.role
            content = event.item.content
            
            # Convert list content (multi-modal) to string if necessary
            if isinstance(content, list):
                content = " ".join([str(c) for c in content])
            
            print(f"[{role.upper()}] {content}")
            
            # Log both candidate (user) and interviewer (assistant) full messages
            if role == "user":
                 db_helper.log_message(room_name, "candidate", content)
            elif role == "assistant":
                 db_helper.log_message(room_name, "interviewer", content)

    print("--- [DEBUG] Starting Session logic...")
    try:
        await session.start(agent, room=ctx.room)
        print("--- [DEBUG] SESSION STARTED SUCCESSFULLY!")
    except Exception as e:
        print(f"--- [ERROR] Session Start Failed: {e}")
        return
    
    
    name = interviewer_data.get('candidate_name', 'there') if interviewer_data else 'there'
    greeting = f"Hello {name}, I am your AI interviewer today. Let's begin!"
    print(f"--- [DEBUG] Sending greeting: {greeting}")
    
    try:
        # await asyncio.sleep(1) # Removed artificial delay
        await session.say(greeting, allow_interruptions=True)
        session.generate_reply()
        print("--- [DEBUG] Greeting sent.")
    except Exception as e:
        print(f"--- [ERROR] Speech Failed: {e}")


    print("--- [DEBUG] Agent waiting for START signal...")

    print("--- [DEBUG] Agent running... waiting for shutdown/disconnect.")
    
    # Wait for the user to disconnect or the job to end
    # We use a Future that will never complete unless we cancel it, 
    # but we can wrap it in a try/finally to catch the shutdown.
    try:
        # This keeps the agent alive
        await ctx.room.disconnect_future
    except Exception:
        pass
    finally:
        print(f"--- [SHUTDOWN] Room {room_name} disconnected. Starting Evaluation...")
        await run_evaluation(room_name, db_helper)

async def run_evaluation(room_name, db_helper):
    print(f"--- [EVAL] Fetching data for room {room_name}...")
    
    # 1. Fetch latest session data (with full transcript)
    try:
        session_data = db_helper.get_session(room_name)
    except Exception as e:
         print(f"--- [ERROR] DB Error during eval fetch: {e}")
         return

    if not session_data or 'transcript' not in session_data:
        print("--- [ERROR] No transcript found for evaluation.")
        return

    # 2. Prepare data
    # Convert transcript list to a readable string
    transcript_text = "\n".join([f"{entry.get('role', 'unknown').upper()}: {entry.get('text','')}" for entry in session_data['transcript']])
    
    # CORRECT KEY: Use 'jd_data' not 'job_description'
    jd_text = str(session_data.get('jd_data', 'Not provided'))
    resume_text = str(session_data.get('resume_context', 'Not provided'))

    print("--- [EVAL] generating evaluation with LLM...")
    # 3. Call LLM
    try:
        eval_json_str = evaluate_candidate(transcript_text, jd_text, resume_text)
        
        # 4. Parse and Save
        eval_data = json.loads(eval_json_str)
        db_helper.save_evaluation(room_name, eval_data)
        print(f"--- [EVAL] Evaluation saved successfully! Score: {eval_data.get('overall_score')}/10")
    except json.JSONDecodeError:
        print(f"--- [ERROR] Failed to parse evaluation JSON: {eval_json_str}")
    except Exception as e:
        print(f"--- [ERROR] Evaluation Failed: {e}")

if __name__ == "__main__":
    print("--- Starting Diagnositc Interviewer Agent ---")
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, port=8050))
