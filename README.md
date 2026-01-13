# LiveKit Real-Time Transcription System

A real-time video meeting platform with live speech-to-text transcription powered by Deepgram.

## Features

- 🎥 Video conferencing with LiveKit
- 🎤 Real-time speech transcription using Deepgram STT
- 💬 Live chat with transcript display
- 📝 Automatic transcript logging
- 🎨 Modern Microsoft Teams-inspired UI

## Prerequisites

- Python 3.11+
- LiveKit Cloud account (or self-hosted LiveKit server)
- Deepgram API key

## Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd live_kit
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_API_URL=wss://your-server.livekit.cloud
DEEPGRAM_API_KEY=your_deepgram_api_key
```

## Usage

### 1. Start the Web Server
```bash
python app.py
```
Access the UI at `http://localhost:5000`

### 2. Start the Transcription Agent
In a separate terminal:
```bash
python transcription_agent.py dev
```

### 3. Join a Meeting
- Open `http://localhost:5000` in your browser
- Create or join a room
- Click the chat icon to view live transcripts

## Project Structure

```
live_kit/
├── app.py                    # Flask web server
├── transcription_agent.py    # Deepgram STT agent
├── templates/
│   └── index.html           # Frontend UI
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
└── transcripts.log         # Saved transcripts
```

## Deployment

See [AWS Deployment Guide](aws_deployment_guide.md) for production deployment instructions.

## Configuration

### Transcription Settings
Edit `transcription_agent.py`:
- `interim_results=True` - Show live updates (lower latency, more messages)
- `interim_results=False` - Show only final transcripts (cleaner, slight delay)
- `model="nova-2"` - Fast model for low latency

## Logs

All final transcripts are saved to `transcripts.log`:
```
user-123: Hello everyone
user-456: How are you doing today
```

## Troubleshooting

### Agent not connecting
- Verify `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` in `.env`
- Check LiveKit server URL is correct

### No transcriptions appearing
- Verify `DEEPGRAM_API_KEY` is valid
- Check agent terminal for errors
- Ensure microphone permissions are granted in browser

### Chat not showing transcripts
- Click the chat icon (message bubble) in the meeting UI
- Check browser console for errors

## License

MIT

## Credits

Built with:
- [LiveKit](https://livekit.io/) - Real-time video infrastructure
- [Deepgram](https://deepgram.com/) - Speech-to-text API
- [Flask](https://flask.palletsprojects.com/) - Web framework
