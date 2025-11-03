import google.generativeai as genai
import os

# For demonstration purposes, we'll set the API key here.
# In a real application, you would use a more secure method.
gemini_api_key = os.environ.get("GEMINI_API_KEY")
if gemini_api_key is None:
    print("Please set the GEMINI_API_KEY environment variable.")
else:
    genai.configure(api_key=gemini_api_key)

    for m in genai.list_models():
      if 'generateContent' in m.supported_generation_methods:
        print(m.name)
