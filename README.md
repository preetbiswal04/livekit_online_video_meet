#  LiveKit Video Meeting – Setup Guide

This guide explains how to **set up the LiveKit video meeting project locally** on your system.

---

## 🔹 Prerequisites

Before setup, make sure you have:

* **Python 3.9+**
* **Docker & Docker Compose download **
* **Git**
* LiveKit API Key and Secret (from your LiveKit account)

---


## 🔹 Step 1: Configure Environment

1. Create a `.env` file in the project root.
2. Add your LiveKit credentials:

```env
LIVEKIT_API_KEY=your_api_key_here
LIVEKIT_API_SECRET=your_api_secret_here
LIVEKIT_URL=ws://localhost:7880
```

> **Important:** `.env` file is ignored in Git. Never upload it to GitHub.

---

## 🔹 Step 2: Start LiveKit Server (Docker)

```bash
docker compose up -d
```

Check if server is running:

```bash
docker ps
```

---

## 🔹 Step 5: Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔹 Step 6: Run Flask Backend

```bash
python backend.py
```

* The backend will run at:

```
http://localhost:5000
```

---

## 🔹 Step 7: Open Frontend

* Open `templates/index.html` in a browser
* Enter your **name** and **room name**
* Share the same **room name** with others to join the call

---

## 🔹 Notes

* Make sure **all participants** are on the same network or have LiveKit server accessible.
* Use `.env.example` as reference if unsure about environment variables.

---

This README **only covers setup** — nothing about code explanation or architecture.

