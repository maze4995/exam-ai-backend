
import os
import sys
import time
from pyngrok import ngrok, conf
import subprocess

def start_sharing():
    print("--- AI Exam Viewer Sharing Tool ---")
    
    # 1. Ensure app.py is running
    # We won't restart it here to avoid conflicts, but we assume it's running on 8000.
    # If not, the user should run app.py first. 
    # But for convenience, let's check port 8000? 
    # Actually, simpler to just tunnel.
    
    # 2. Setup ngrok
    # If user has an auth token, they can set it via command line: ngrok config add-authtoken <token>
    # But for anonymous use (limited duration), it works out of the box usually.
    
    try:
        # Open a HTTP tunnel on the default port 8000
        # The 'http' protocol is what we need for web viewing
        public_url = ngrok.connect(8000).public_url
        
        print("\n" + "="*60)
        print(f" ONLINE! Your viewer is available at:")
        print(f" {public_url}")
        print("="*60 + "\n")
        print("Share this URL with anyone you want to show the viewer to.")
        print("Press Ctrl+C to stop sharing.")
        
        # Keep the script running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down tunnel...")
        ngrok.kill()
    except Exception as e:
        print(f"\nError: {e}")
        print("Note: If you haven't authenticated ngrok, sessions are limited to 2 hours.")

if __name__ == "__main__":
    start_sharing()
