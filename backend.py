from flask import Flask, jsonify, render_template, request, session, url_for, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from livekit import api
from dotenv import load_dotenv
from flask_cors import CORS
import uuid
import os
import sys
from pathlib import Path

# Add project root to sys.path to find resume_jd_analyser
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from resume_jd_analyser.text_extract import extract_text
from resume_jd_analyser.resume_prasing import prase_resume
from resume_jd_analyser.jd_prasing import jd_prase
from resume_jd_analyser.question_gen import generate_questions
from resume_jd_analyser.db_utils import db_helper

load_dotenv()

app = Flask(__name__, template_folder=str(root_path / "templates"))
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

LIVEKIT_API_KEY = os.environ.get('LIVEKIT_API_KEY')
LIVEKIT_API_SECRET = os.environ.get('LIVEKIT_API_SECRET')
LIVEKIT_API_URL = os.environ.get('LIVEKIT_API_URL', 'wss://appvideocall-4e91dis5.livekit.cloud')

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html', username = session['user'])

#login route
@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error':"username and password are required"}), 400
    if users_collection.find_one({"username": username}):
        return jsonify({'error':"username already exists"}), 400
    hashed_password = generate_password_hash(password)
    users_collection.insert_one({"username": username, "password": hashed_password})
    return jsonify({'status': "created"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    user = users_collection.find_one({"username": username})
    if user and check_password_hash(user['password'], password):
        session['user'] = username
        return jsonify({"status": "logged_in"})
    
    return jsonify({"error": "Invalid credentials"}), 401
@app.route('/api/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login_page'))


@app.route('/get-token/<room_name>/<user_identity>')
def get_token(room_name, user_identity):
    identity = session.get('user', user_identity)
    token = api.AccessToken(
        LIVEKIT_API_KEY,
        LIVEKIT_API_SECRET,
    ).with_identity(identity).with_grants(
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
    users_collection = db['users']
    print(f"Connected to MongoDB: {MONGO_DB_NAME}")
except Exception as e:
    users_collection = None
    messages_collection = None
    print(f"Failed to connect to MongoDB: {e}")

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

# # --- Register Blueprints ---
# from agent_routes import agent_bp
# app.register_blueprint(agent_bp)
#interview session route 
@app.route('/api/upload-resume', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files or 'jd' not in request.form:
        return jsonify({"error":"missing resume or JD"}),400
    
    resume_file = request.files['resume']
    jd_text = request.form['jd']

    temp_path = f"temp_{uuid.uuid4()}.pdf"
    resume_file.save(temp_path)

    try:
        raw_resume_text = extract_text(temp_path)
        resume_json = prase_resume(raw_resume_text)

        questions = generate_questions(resume_json,jd_text)

        room_id = str(uuid.uuid4())[:8]
        db_helper.create_session(room_id=room_id,candidate_name=resume_json.get("Name","Candidate"),resume_data=resume_json,questions=questions)
        return jsonify({"room_id":room_id,"status":"success","message":"analysis completed redirecting to interview..."})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
