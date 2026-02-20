import os
import boto3

_aws_gemma_client = None

def get_gemma_model():
    global _aws_gemma_client
    if _aws_gemma_client is None:
        session = boto3.Session(
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION"),
        )
        _aws_gemma_client = session.client(
            service_name="bedrock-runtime"
        )
    return _aws_gemma_client

class DummyContentPart:
    pass

class DummyContent:
    def __init__(self, text):
        self.parts = [DummyContentPart()]

class DummyCandidate:
    def __init__(self, text):
        self.content = DummyContent(text)

class DummyResponse:
    def __init__(self, text):
        self.text = text
        self.candidates = [DummyCandidate(text)]

class BaseFastModel:
    def generate_content(self, prompt, safety_settings=None):
        client = get_gemma_model()
        response = client.converse(
            modelId="google.gemma-3-12b-it",
            messages=[
                {"role": "user", "content": [{"text": prompt}]}
            ],
            inferenceConfig={
                "maxTokens": 8192,
                "temperature": 0.0,
                "topP": 0.95
            }
        )
        text = response["output"]["message"]["content"][0]["text"]
        return DummyResponse(text)

def get_gemini_fast_model():
    return BaseFastModel()

SAFETY_SETTINGS = []

def generate_text(prompt):
    model = get_gemini_fast_model()
    return model.generate_content(prompt).text

    