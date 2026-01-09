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
LIVEKIT_API_URL = os.environ.get('LIVEKIT_API_URL', 'http://localhost:7880')

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
