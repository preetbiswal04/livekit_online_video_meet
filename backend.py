from flask import Flask, jsonify, render_template
from livekit import api
import os
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)

LIVEKIT_API_KEY = os.environ.get('LIVEKIT_API_KEY')
LIVEKIT_API_SECRET = os.environ.get('LIVEKIT_API_SECRET')
LIVEKIT_API_URL = os.environ.get('LIVEKIT_API_URL', 'wss://appvideocall-4e91dis5.livekit.cloud')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/get-token/<room_name>/<user>')
def get_token(room_name, user):
    token = api.AccessToken(
        LIVEKIT_API_KEY,
        LIVEKIT_API_SECRET,
    ).with_identity(user).with_grants(
        api.VideoGrants(
            room_join=True,
            room=room_name
        )
    )
    return jsonify({
        "token": token.to_jwt(),
        "url": LIVEKIT_API_URL
    })

# --- Expanded API for Teams UI ---

@app.route('/api/rooms')
def list_rooms():
    # In a real app, you'd fetch this from LiveKit API or a database
    # For now, we'll return some mock active rooms
    rooms = [
        {"name": "General", "participants": 3, "id": "general"},
        {"name": "Project Alpha", "participants": 5, "id": "alpha"},
        {"name": "Weekly Sync", "participants": 2, "id": "sync"}
    ]
    return jsonify(rooms)

@app.route('/api/create-room', methods=['POST'])
def create_room():
    # Mock room creation
    new_room_id = f"room-{os.urandom(4).hex()}"
    return jsonify({"room_name": new_room_id, "status": "created"})

@app.route('/api/user')
def get_user_info():
    # Mock user info
    return jsonify({
        "id": "user-" + os.urandom(2).hex(),
        "name": "Jane Doe",
        "role": "Moderator"
    })

# --- MongoDB Integration ---
from pymongo import MongoClient

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'livekit_chat')

try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[MONGO_DB_NAME]
    messages_collection = db['messages']
    print(f"Connected to MongoDB: {MONGO_DB_NAME}")
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")
    messages_collection = None

@app.route('/api/history/<room_name>')
def get_chat_history(room_name):
    if messages_collection is None:
        return jsonify([])
    
    # Fetch messages, sorted by timestamp (oldest first)
    # Exclude _id field for cleaner JSON
    messages = list(messages_collection.find(
        {"room": room_name},
        {"_id": 0}
    ).sort("timestamp", 1))
    
    return jsonify(messages)

@app.route('/api/save-message', methods=['POST'])
def save_message():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
    
    if messages_collection is not None:
        try:
            doc = {
                "room": data.get("room"),
                "sender": data.get("sender"),
                "text": data.get("text"),
                "timestamp": datetime.datetime.utcnow(),
                "is_transcript": False
            }
            messages_collection.insert_one(doc)
            return jsonify({"status": "saved"})
        except Exception as e:
            print(f"Error saving message: {e}")
            return jsonify({"error": str(e)}), 500
            
    return jsonify({"error": "DB not connected"}), 500

# --- Register Blueprints ---
from agent_routes import agent_bp
app.register_blueprint(agent_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
