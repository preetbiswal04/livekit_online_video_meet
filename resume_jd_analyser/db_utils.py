import os
from pymongo import MongoClient
from dotenv import load_dotenv


load_dotenv()

class InterviewSession:
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client[os.getenv("MONGO_DB_NAME", "livekit_chat")]
        self.collection = self.db.sessions
        self.users = self.db.users
        self.messages = self.db.messages

    def create_session(self, room_id, candidate_name, resume_data, questions, jd_data=None):
        data = {
            "room_id": room_id,
            "candidate_name": candidate_name,
            "resume_context": resume_data,
            "questions": questions,
            "jd_data": jd_data,
            "status": "pending",
            "transcript": []
        }
        return self.collection.update_one({"room_id": room_id}, {"$set": data}, upsert=True)

    def get_session(self, room_id):
        return self.collection.find_one({"room_id": room_id})

    def log_message(self, room_id, role, text):
        # 1. Fetch the current session document to check the last transcript entry
        session = self.collection.find_one({"room_id": room_id}, {"transcript": {"$slice": -1}})
        
        should_push = True
        
        if session and "transcript" in session and session["transcript"]:
            last_entry = session["transcript"][0]
            if last_entry.get("role") == role:
.
                pass
                
                # Simplest working solution:
                session_full = self.collection.find_one({"room_id": room_id}, {"transcript": 1})
                if session_full and "transcript" in session_full and session_full["transcript"]:
                    transcript = session_full["transcript"]
                    if transcript[-1]["role"] == role:
                         # Append text
                         new_text = transcript[-1]["text"] + " " + text
                         # Update the last element
                         return self.collection.update_one(
                             {"room_id": room_id},
                             {"$set": {f"transcript.{len(transcript)-1}.text": new_text}}
                         )
        
        # Default: Push new
        return self.collection.update_one(
            {"room_id": room_id},
            {"$push": {"transcript": {"text": text, "role": role}}}
        )

db_helper = InterviewSession()
