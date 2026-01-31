import google.generativeai as genai
import os
import PIL.Image

# Attempt to access key from environment
api_key = os.getenv("GEMINI_API_KEY")
print(f"API Key present in Env: {bool(api_key)}")

if api_key:
    # Save to .env file to ensure persistence for app.py
    with open(".env", "w", encoding="utf-8") as f:
        f.write(f"GEMINI_API_KEY={api_key}\n")
    print("Saved GEMINI_API_KEY to .env file.")
    
    # Verify model
    genai.configure(api_key=api_key)
    try:
        model = genai.GenerativeModel('models/gemini-3-pro-image-preview')
        print("Model initialized.")
        img = PIL.Image.new('RGB', (100, 100), color = 'red')
        response = model.generate_content(["Describe this image", img])
        print(f"Response: {response.text}")
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("CRITICAL: API Key MISSING from environment.")
