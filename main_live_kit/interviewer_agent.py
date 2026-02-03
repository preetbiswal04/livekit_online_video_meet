import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path to find resume_jd_analyser
root_path = Path(__file__).parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from livekit.agents import JobContext, Agent, AgentSession, llm, WorkerOptions, cli, UserInputTranscribedEvent, ConversationItemAddedEvent, AutoSubscribe
from livekit.plugins import deepgram, google, cartesia, silero

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
    from resume_jd_analyser.db_utils import db_helper
    
    print(f"--- [DEBUG] Fetching session for room: {room_name}")
    try:
        interviewer_data = db_helper.get_session(room_name)
    except Exception as e:
        print(f"--- [ERROR] DB Helper Failed: {e}")
        interviewer_data = None
    
    if not interviewer_data:
        print(f"--- [WARNING] No session data found in DB. Using fallback prompt.")
        system_prompt = """ You are an expert technical interviewer.
Your task is to generate interview questions strictly and only based on the provided Job Description.

Rules:
- Ask questions only from skills, tools, technologies, responsibilities, and qualifications explicitly mentioned in the Job Description.
- Do NOT ask generic, behavioral, HR, or personality questions.
- Do NOT ask questions outside the Job Description and Resume (no extra technologies, frameworks, or concepts).
- If a skill is mentioned briefly, ask basic and easy questions about it.
- If a skill is emphasized or repeated, ask in-depth technical questions.
- If a candidate is not able to answer a question, if he say okay or move to next question, then ask next question.

The questions should go like this :
-There should be total 10 questions.
-The start of interview should be by introduction of role and comapny and ask candidate introduces them self.
-Then ask 3 questions from mentioned in job description.
-Then ask 3 question from tools and skills mentioned in job description.
-Then ask 2 technical questions from job description.
-Then ask 2 questions from experience mentioned in job description."""
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
       
        tts_plugin = cartesia.TTS()
        
        print("--- [DEBUG] Initializing VAD (Silero)...")
        vad_plugin = silero.VAD.load()

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
        await asyncio.sleep(1)
        await session.say(greeting, allow_interruptions=True)
        session.generate_reply()
        print("--- [DEBUG] Greeting sent.")
    except Exception as e:
        print(f"--- [ERROR] Speech Failed: {e}")

    print("--- [DEBUG] Agent waiting for START signal...")

    print("--- [DEBUG] Agent running... waiting for shutdown.")
    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    print("--- Starting Diagnositc Interviewer Agent ---")
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, port=8050))
