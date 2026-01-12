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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
