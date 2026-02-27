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
import base64
import numpy as np
import cv2
from pymongo import MongoClient

# -------------------- PROJECT PATH SETUP --------------------

root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from resume_jd_analyser.text_extract import extract_text
from resume_jd_analyser.resume_prasing import prase_resume
from resume_jd_analyser.jd_prasing import jd_prase
from resume_jd_analyser.question_gen import generate_questions
from resume_jd_analyser.db_utils import db_helper
from face_monitoring import face_monitor

load_dotenv(root_path / ".env")

# -------------------- FLASK APP INIT --------------------

app = Flask(__name__, template_folder=str(root_path / "templates"))
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key')

LIVEKIT_API_KEY = os.environ.get('LIVEKIT_API_KEY')
LIVEKIT_API_SECRET = os.environ.get('LIVEKIT_API_SECRET')
LIVEKIT_API_URL = os.environ.get('LIVEKIT_API_URL')

# -------------------- GLOBAL REQUEST LOGGER --------------------

@app.before_request
def log_request():
    print(f"[{datetime.datetime.utcnow()}] {request.method} {request.path}")

# -------------------- MONGODB CONNECTION --------------------

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'livekit_chat')

try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client[MONGO_DB_NAME]
    messages_collection = db['messages']
    users_collection = db['users']
    print(f"✅ Connected to MongoDB: {MONGO_DB_NAME}")
except Exception as e:
    users_collection = None
    messages_collection = None
    print(f"❌ Failed to connect MongoDB: {e}")

# -------------------- AUTH ROUTES --------------------

@app.route('/')
def home():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html',
                           username=session['user'],
                           role=session.get('role', 'candidate'))

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
    role = data.get('role', 'candidate')

    if not username or not password:
        return jsonify({'error': "username and password required"}), 400

    if users_collection.find_one({"username": username}):
        return jsonify({'error': "username already exists"}), 400

    hashed_password = generate_password_hash(password)
    users_collection.insert_one({
        "username": username,
        "password": hashed_password,
        "role": role
    })

    return jsonify({'status': "created"}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = users_collection.find_one({"username": username})

    if user and check_password_hash(user['password'], password):
        session['user'] = username
        session['role'] = user.get('role', 'candidate')
        return jsonify({"status": "logged_in"})

    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# -------------------- LIVEKIT TOKEN --------------------

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

# -------------------- CHAT HISTORY --------------------

@app.route('/api/history/<room_name>')
def get_chat_history(room_name):
    messages = list(messages_collection.find(
        {"room": room_name},
        {"_id": 0}
    ).sort("timestamp", 1))

    return jsonify(messages)

@app.route('/api/save-message', methods=['POST'])
def save_message():
    data = request.json

    doc = {
        "room": data.get("room"),
        "sender": data.get("sender"),
        "text": data.get("text"),
        "timestamp": datetime.datetime.utcnow(),
        "is_transcript": False
    }

    messages_collection.insert_one(doc)
    return jsonify({"status": "saved"})

# -------------------- RESUME + JD ANALYSIS --------------------

@app.route('/api/upload-resume', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files or 'jd' not in request.form:
        return jsonify({"error": "missing resume or JD"}), 400

    resume_file = request.files['resume']
    jd_text = request.form['jd']

    temp_path = f"temp_{uuid.uuid4()}.pdf"
    resume_file.save(temp_path)

    try:
        raw_resume_text = extract_text(temp_path)
        resume_json = prase_resume(raw_resume_text)
        questions = generate_questions(resume_json, jd_text)

        room_id = str(uuid.uuid4())[:8]

        db_helper.create_session(
            room_id=room_id,
            candidate_name=resume_json.get("Name", "Candidate"),
            resume_data=resume_json,
            questions=questions,
            jd_data=jd_text
        )

        return jsonify({
            "room_id": room_id,
            "status": "success",
            "message": "Resume analyzed and questions generated successfully!"
        })

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# -------------------- TAB SWITCH MONITORING --------------------

@app.route("/api/log-tab-switch", methods=["POST"])
def log_tab_switch():
    try:
        data = request.json
        room_id = data.get("room_id")

        if not room_id:
            return jsonify({"error": "room_id required"}), 400

        event = {
            "start_time": data.get("start_time"),
            "end_time": data.get("end_time"),
            "duration_seconds": data.get("duration_seconds"),
            "timestamp": datetime.datetime.utcnow()
        }

        db_helper.collection.update_one(
            {"room_id": room_id},
            {"$push": {"tab_switch_events": event}},
            upsert=True
        )

        return jsonify({"status": "logged"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------- FACE MONITORING --------------------

@app.route("/api/check-face", methods=["POST"])
def check_face():
    try:
        data = request.json
        image_data = data.get("image")
        room_id = data.get("room_id")

        if not image_data:
            return jsonify({"error": "No image"}), 400

        image_data = image_data.split(",")[1]
        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        result = face_monitor.analyze_frame(frame)

        if result.get("violation") and room_id:
            event = {
                "type": "face_violation",
                "details": result,
                "timestamp": datetime.datetime.utcnow()
            }

            db_helper.collection.update_one(
                {"room_id": room_id},
                {"$push": {"face_violations": event}},
                upsert=True
            )
        
        print(f"Face Check Result for {room_id}: {result}")
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------- DASHBOARD & EVALUATIONS --------------------

@app.route('/api/evaluations', methods=['GET'])
def get_evaluations():
    """Returns all interview sessions that have an AI evaluation."""
    try:
        # Find all sessions with evaluations, newest first
        sessions = list(db_helper.collection.find(
            {"evaluation": {"$exists": True}},
            {"_id": 0}
        ).sort("_id", -1))
        
        # Format for frontend
        formatted = []
        for s in sessions:
            eval_data = s.get("evaluation", {})
            formatted.append({
                "room_id": s.get("room_id"),
                "candidate_name": s.get("candidate_name", eval_data.get("candidate_name", "Unknown")),
                "overall_score": eval_data.get("overall_score", 0),
                "technical_score": eval_data.get("technical_score", 0),
                "communication_score": eval_data.get("communication_score", 0),
                "recommendation": eval_data.get("recommendation", "N/A"),
                "summary": eval_data.get("summary", ""),
                "detailed_feedback": eval_data.get("detailed_feedback", []),
                "transcript": s.get("transcript", []),
                "timestamp": s.get("timestamp", datetime.datetime.utcnow()) # Fallback if missing
            })
        
        return jsonify(formatted)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    """Returns analytics data for the dashboard."""
    try:
        # 1. Total & Breakdown
        pipeline = [
            {"$match": {"evaluation": {"$exists": True}}},
            {"$group": {
                "_id": "$evaluation.recommendation",
                "count": {"$sum": 1},
                "names": {"$push": "$candidate_name"}
            }}
        ]
        results = list(db_helper.collection.aggregate(pipeline))
        
        # Match frontend structure: { recommendation: { count: X, names: [...] } }
        breakdown = {r["_id"]: {"count": r["count"], "names": r.get("names", [])} for r in results}
        
        # 2. Recent Candidates
        recent = list(db_helper.collection.find(
            {"evaluation": {"$exists": True}},
            {"_id": 0, "candidate_name": 1, "evaluation.overall_score": 1, "evaluation.recommendation": 1}
        ).sort("_id", -1).limit(5))
        
        recent_formatted = [{
            "candidate_name": r.get("candidate_name", r.get("evaluation", {}).get("candidate_name", "Unknown")),
            "score": r.get("evaluation", {}).get("overall_score", 0),
            "recommendation": r.get("evaluation", {}).get("recommendation", "N/A")
        } for r in recent]

        stats = {
            "total_interviews": sum(r["count"] for r in results),
            "breakdown": breakdown,
            "recent_candidates": recent_formatted
        }

        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------- MAIN --------------------

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
