import os
import google.generativeai as genai
from legacyhelper.model.base import BaseModel

class GeminiModel(BaseModel):
    def __init__(self, api_key: str = None):
        if api_key is None:
            api_key = os.environ.get("GEMINI_API_KEY")
        if api_key is None:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('models/gemini-pro-latest')

    def get_response(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        return response.text
