# LiveKit Real-Time Transcription System

A real-time video meeting platform with live speech-to-text transcription powered by Deepgram.

## Features

- 🎥 Video conferencing with LiveKit
- 🎤 Real-time speech transcription using Deepgram STT
- 💬 Live chat with transcript display
- 📝 Automatic transcript logging
- 🎨 Modern Microsoft Teams-inspired UI

# LiveKit AI Interviewer - Setup Guide

This guide explains how to set up the AI Interviewer application on a new machine (Windows/Mac/Linux).

## 1. Prerequisites / Requirements

Ensure the following are installed on the new machine:
*   **Python 3.10+**: [Download Python](https://www.python.org/downloads/)
*   **MongoDB**: Using a cloud Atlas database (no local install needed) or install MongoDB Community Server locally.
*   **Git**: [Download Git](https://git-scm.com/downloads) (Optional, for cloning)
*   **Google Cloud SDK** (Optional, for advanced auth, but we use a JSON key file here)

## 2. Project Setup

1.  **Copy the Project Files**:
    *   Copy the entire project folder to the new machine.
    *   *Critical:* Ensure the `service_account_key.json` file (Google Vertex AI credentials) is included in the project root.

2.  **Create a Virtual Environment**:
    Open a terminal/command prompt in the project folder:
    ```bash
    python -m venv venv
    ```

3.  **Activate the Virtual Environment**:
    *   **Windows:**
        ```powershell
        .\venv\Scripts\activate
        ```
    *   **Mac/Linux:**
        ```bash
        source venv/bin/activate
        ```

4.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## 3. Configuration (.env)

Create a file named `.env` in the root folder and add your API keys. You can copy the content below:

```ini
# LiveKit Configuration
LIVEKIT_API_URL=wss://your-project-url.livekit.cloud
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
LIVEKIT_URL=wss://your-project-url.livekit.cloud

# Database
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGO_DB_NAME=livekit_chat

# AI Services
DEEPGRAM_API_KEY=your_deepgram_key
CARTESIA_API_KEY=your_cartesia_key

# Google Vertex AI (Authentication handled via JSON key file, but path set here)
GOOGLE_APPLICATION_CREDENTIALS=service_account_key.json
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

## 4. Running the Application

To start the full application (Backend + AI Agent):

1.  Make sure your virtual environment is activated.
2.  Run the unified runner script:
    ```bash
    python run_app.py
    ```
3.  The Flask server will start on `http://127.0.0.1:5000`.
4.  The Agent is now waiting for a room connection.

## 5. Usage
1.  Open `http://127.0.0.1:5000` in your browser.
2.  Upload a Resume and Job Description.
3.  Click "Start Interview" to join the LiveKit room.

