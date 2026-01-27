import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

class InterviewSession:
    def __init__(self):
        self.client = MongoClient(os.getenv("MONGO_URI"))
        self.db = self.client[os.getenv("MONGO_DB_NAME", "interview_session")]
        self.collection = self.db.sessions

    def create_session(self, room_id, candidate_name, resume_data, questions):
        data = {
            "room_id": room_id,
            "candidate_name": candidate_name,
            "resume_context": resume_data,
            "questions": questions,
            "status": "pending",
            "transcript": []
        }
        return self.collection.update_one({"room_id": room_id}, {"$set": data}, upsert=True)

    def get_session(self, room_id):
        return self.collection.find_one({"room_id": room_id})

    def log_message(self, room_id, role, text):
        return self.collection.update_one(
            {"room_id": room_id},
            {"$push": {"transcript": {"text": text, "role": role}}}
        )

db_helper = InterviewSession()