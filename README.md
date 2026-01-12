Application Startup Guide (LiveKit Cloud)
This document outlines the steps to run the application using LiveKit Cloud. Docker is no longer required.

1. System Requirements
Software
Python 3.7+: Required for the Flask backend.
Web Browser: A modern browser (Chrome, Edge, or Firefox).
Security (CRITICAL)
Secure Context: Browsers only allow camera/microphone access in a "Secure Context".
Recommended: Use http://localhost:5000.
2. Environment Configuration
Your 
.env
 file should contain your LiveKit Cloud credentials:

LIVEKIT_API_KEY=your_cloud_api_key
LIVEKIT_API_SECRET=your_cloud_api_secret
LIVEKIT_API_URL=wss://your-project.livekit.cloud
3. Backend Setup
Install dependencies:
pip install flask flask-cors python-dotenv livekit
Start the backend:
python backend.py
4. Accessing the App
Open your browser to: http://localhost:5000
Click Join Meeting.
5. Verification Plan
Verify 
backend.py
 log shows it's running on http://127.0.0.1:5000.
Verify the "CONNECTED to room" message appears in the browser console/log after joining.
