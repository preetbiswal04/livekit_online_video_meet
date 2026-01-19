import multiprocessing
import os 
import sys
from backend import app
from livekit.agents import cli, WorkerOptions
from transcription_agent_deepgram import entrypoint

def run_flask() :
    print(">>>>>>>>Starting Flask app<<<<<<<<<<")
    app.run(host='0.0.0.0', port=5000, debug = False, use_reloader=False)
def run_agent():
    print(">>>>>>>>Starting LiveKit agent<<<<<<<<<<")
    sys.argv = ["agent", "dev"]
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

if __name__ == "__main__":
    flask_process = multiprocessing.Process(target=run_flask)
    agent_process = multiprocessing.Process(target=run_agent)
    flask_process.start()
    agent_process.start()
    try:
        flask_process.join()
        agent_process.join()
    except KeyboardInterrupt:
        flask_process.terminate()
        agent_process.terminate()