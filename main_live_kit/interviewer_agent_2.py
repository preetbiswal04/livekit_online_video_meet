import asyncio
import os
import sys
import traceback
from pathlib import Path
from dotenv import load_dotenv
import json 

root_path = Path(__file__).parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from livekit.agents import JobContext, Agent, AgentSession, llm, WorkerOptions, cli, UserInputTranscribedEvent, ConversationItemAddedEvent, AutoSubscribe
from livekit.plugins import deepgram, aws, cartesia, silero


try:
    from .evaluation_gen import evaluate_candidate
except ImportError:
    try:
        from main_live_kit.evaluation_gen import evaluate_candidate
    except ImportError:
        try:
             from evaluation_gen import evaluate_candidate
        except ImportError:
             print("--- [WARNING] Could not import evaluate_candidate.")
             evaluate_candidate = None

load_dotenv()

if not os.getenv("AWS_ACCESS_KEY_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
    print("--- [WARNING] AWS Credentials missing for Bedrock LLM!")

try:
    from resume_jd_analyser.db_utils import db_helper
except ImportError:
    try:
        from main_live_kit.resume_jd_analyser.db_utils import db_helper
    except ImportError:
        print("--- [WARNING] Could not import db_helper globally.")
        db_helper = None

async def entrypoint(ctx: JobContext):
    print(f"--- [DEBUG] Room {ctx.room.name}: STARTING ENTRYPOINT (AWS/Gemma) ---")
    
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
    
    # 1. System Prompt & Chat Context Initialization
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

    # 2. Plugin Initialization
    try:
        print("--- [DEBUG] Initializing Plugins...")
        stt_plugin = deepgram.STT()
        
        # GEMMA via AWS Bedrock
        # Note: If this fails with ValidationException, it means the plugin doesn't yet support Gemma 3's format.
        aws_region = (os.environ.get("AWS_REGION") or "ap-south-1").strip("'\"")
        aws_ak = (os.environ.get("AWS_ACCESS_KEY_ID") or "").strip("'\"")
        aws_sk = (os.environ.get("AWS_SECRET_ACCESS_KEY") or "").strip("'\"")
        
        print(f"--- [DEBUG] Initializing LLM: google.gemma-3-12b-it in {aws_region} (AK={aws_ak[:5]}...) ---")
        llm_plugin = aws.LLM(
            model="google.gemma-3-12b-it",
            region=aws_region
        )
        
        # Use specific voice if requested
        print("--- [DEBUG] Initializing TTS (Cartesia) ---")
        tts_plugin = cartesia.TTS(voice="e07c00bc-4134-4eae-9ea4-1a55fb45746b")
        
        print("--- [DEBUG] Initializing VAD (Silero) ---")
        try:
            vad_plugin = silero.VAD.load(min_silence_duration=0.3, min_speech_duration=0.3)
        except Exception as e:
            print(f"--- [ERROR] VAD Init Failed: {e}")
            vad_plugin = None

        print("--- [DEBUG] Creating AgentSession ---")
        session = AgentSession(
            stt=stt_plugin,
            llm=llm_plugin,
            tts=tts_plugin,
            vad=vad_plugin,
        )
    except Exception as e:
        print(f"--- [ERROR] Plugin Init Failed: {e}")
        traceback.print_exc()
        return

    # 3. Agent & Handlers
    print("--- [DEBUG] Setting up Agent Handlers ---")
    agent = Agent(instructions=system_prompt, chat_ctx=chat_ctx)

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
            if isinstance(content, list):
                content = " ".join([str(c) for c in content])
            
            print(f"[{role.upper()}] {content}")
            
            # Log to DB
            if db_helper:
                try:
                    if role == "user":
                        db_helper.log_message(room_name, "candidate", content)
                    elif role == "assistant":
                        db_helper.log_message(room_name, "interviewer", content)
                except Exception as e:
                    print(f"--- [ERROR] DB Logging Failed: {e}")

    # 4. Starting the Session
    print("--- [DEBUG] Starting Session logic...")
    try:
        await session.start(agent, room=ctx.room)
        print("--- [DEBUG] SESSION STARTED SUCCESSFULLY!")
    except Exception as e:
        print(f"--- [ERROR] Session Start Failed: {e}")
        traceback.print_exc()
        return
    
    # 5. Greeting
    print("--- [DEBUG] Preparing Greeting ---")
    name = interviewer_data.get('candidate_name', 'there') if interviewer_data else 'there'
    greeting = f"Hello {name}, I am your AI interviewer today. Let me load your context. Let's begin!"
    try:
        print(f"--- [DEBUG] Agent saying: {greeting}")
        await session.say(greeting, allow_interruptions=True)
        print("--- [DEBUG] Greeting track sent. Generating first reply...")
        session.generate_reply()
    except Exception as e:
        print(f"--- [ERROR] Initial Speech/Reply Failed: {e}")
        traceback.print_exc()

    # Keep alive until disconnect
    print("--- [DEBUG] Agent now waiting for room disconnect... ---")
    try:
        await ctx.room.disconnect_future
    except Exception as e:
        print(f"--- [DEBUG] Break in disconnect_future: {e}")
    finally:
        print(f"--- [SHUTDOWN] Room {room_name} disconnected. Starting Evaluation...")
        await run_evaluation(room_name, db_helper)

async def run_evaluation(room_name, db_helper):
    print(f"--- [EVAL] Fetching data for room {room_name}...")
    try:
        if not db_helper: return
        session_data = db_helper.get_session(room_name)
        if not session_data or 'transcript' not in session_data:
            print("--- [ERROR] No transcript found for evaluation.")
            return

        transcript_text = "\n".join([f"{entry.get('role', 'unknown').upper()}: {entry.get('text','')}" for entry in session_data['transcript']])
        jd_text = str(session_data.get('jd_data', 'Not provided'))
        resume_text = str(session_data.get('resume_context', 'Not provided'))

        print("--- [EVAL] generating evaluation with LLM...")
        if evaluate_candidate:
            eval_json_str = evaluate_candidate(transcript_text, jd_text, resume_text)
            eval_data = json.loads(eval_json_str)
            db_helper.save_evaluation(room_name, eval_data)
            print(f"--- [EVAL] Evaluation saved! Score: {eval_data.get('overall_score')}/10")
        else:
            print("--- [ERROR] evaluate_candidate function not available.")
    except Exception as e:
        print(f"--- [ERROR] Evaluation Failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, port=8050))
