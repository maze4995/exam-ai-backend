import google.generativeai as genai
import os

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Try to find it in the environment or simple hardcoded check if environment variable is missing in this context
    # ideally it should be in env.
    print("No API Key found")
else:
    genai.configure(api_key=api_key)
    print("Listing models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
