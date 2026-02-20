import multiprocessing
import os 
import sys
from backend import app
from livekit.agents import cli, WorkerOptions
from transcription_agent_deepgram import entrypoint
from interviewer_agent_2 import entrypoint as interviewer_entry
#from manual_interviewer_agent import entrypoint as interviewer_entry
#from interviewer_agent import entrypoint as interviewer_entry
from transcription_agent_deepgram import entrypoint as transcriber_entry

def run_flask() :
    print(">>>>>>>>Starting Flask app<<<<<<<<<<")
    app.run(host='0.0.0.0', port=5000, debug = False, use_reloader=False)

def run_interviewer_agent():
    print(">>>>>>>>Starting Interviewer agent<<<<<<<<<<")
    sys.argv = ["agent", "dev"]
    cli.run_app(WorkerOptions(entrypoint_fnc=interviewer_entry))

# def run_transcriber_agent():
#     print(">>>>>>>>Starting Transcriber agent<<<<<<<<<<")
#     sys.argv = ["agent", "dev"]
#     cli.run_app(WorkerOptions(entrypoint_fnc=transcriber_entry,port=8051))

# def run_agent():
#     print(">>>>>>>>Starting LiveKit agent<<<<<<<<<<")
#     sys.argv = ["agent", "dev"]
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

if __name__ == "__main__":
    flask_process = multiprocessing.Process(target=run_flask)
    interviewer_process = multiprocessing.Process(target=run_interviewer_agent)
    # transcriber_process = multiprocessing.Process(target=run_transcriber_agent)
    print("strating agents")
    flask_process.start()
    interviewer_process.start()
    # transcriber_process.start()
    try:
        flask_process.join()
        interviewer_process.join()
        # transcriber_process.join()
    except KeyboardInterrupt:
        print("Shutting down agents...")
        flask_process.terminate()
        interviewer_process.terminate()
        # transcriber_process.terminate()

        flask_process.join(timeout=2)
        interviewer_process.join(timeout=2)
        # transcriber_process.join(timeout=2)
        print("Shutdown complete.")
        sys.exit(0)
