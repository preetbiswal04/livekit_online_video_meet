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
                # 2. If the last entry has the same role, append the text to it
                # We target the last element using the positional $ operator is tricky with arrays
                # So we simply pop the last one and push the merged one, or update by index.
                # However, since we don't know the index easily without fetching all, 
                # a safe way is to find by room_id and update the specifically last item.
                # But MongoDB doesn't support updating "last element" easily without knowing index.
                # Alternative: Use a pipeline update (MongoDB 4.2+)
                
                # Let's try to update using the array index if we can get the length, 
                # but getting length is an extra query.
                
                # Robust Approach: 
                # Fetch full transcript is bad for size. 
                # Fetch last item, if matches, we want to append.
                
                # Let's use a simpler logic:
                # We will just append the text. The UI can merge them if needed?
                # The user SPECIFICALLY asked for them to be stored in one object.
                
                # So we MUST merge in DB.
                # Let's read the full transcript length or use a pipeline.
                pass
                
                # Pipeline update to append to string of last element if role matches
                # But pipeline updates are complex.
                
                # Let's stick to the "Fetch -> Modify Last -> Save" if concurrency isn't massive.
                # Or "Pop Last -> Push Merged".
                # Pop is not atomic with Push.
                
                # Let's just use Python logic:
                # We need to know the index of the last element.
                # We can't know it without querying.
                
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
