import os
import vertexai
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
from google.oauth2 import service_account

_gemini_fast_model = None

from vertexai.generative_models import SafetySetting

# Export standard safety settings for Vertex AI
SAFETY_SETTINGS = [
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
]

def get_gemini_fast_model():
    global _gemini_fast_model
    if _gemini_fast_model is None:
        key_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),"service_account_key.json")

        if not os.path.exists(key_path):
            raise FileNotFoundError(f"service account key not found at {key_path}")

        print(f"loading credentials from {key_path}")
        credentials = service_account.Credentials.from_service_account_file(key_path)
        vertexai.init(
            project = "balmy-amp-481707-p6",
            location = "us-central1",
            credentials = credentials
        )
        _gemini_fast_model = GenerativeModel(
            "gemini-2.5-flash",
            generation_config={
                "temperature":0,
                "max_output_tokens":8192,
                "top_p":0.95,
                "top_k":40,
                "response_mime_type":"text/plain"
            }
        )
    return _gemini_fast_model
