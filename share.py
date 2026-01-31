import subprocess
import time
import sys

def start_sharing():
    print("--- AI Exam Viewer Sharing Tool (via localtunnel) ---")
    print("Starting localtunnel on port 8000...")
    
    try:
        # Run npx localtunnel
        # We use shell=True to find npx in path
        process = subprocess.Popen(["npx", "localtunnel", "--port", "8000"], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE, 
                                   text=True,
                                   shell=True)
        
        print("Waiting for tunnel URL...")
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                if "your url is:" in output.lower():
                    print("\n" + "="*60)
                    print(f" SHARE THIS URL: {output.strip().split('is: ')[-1]}")
                    print(f" Password (if asked): {get_password()}")
                    print("="*60 + "\n")
                    
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nStopping sharing...")
        process.terminate()
    except Exception as e:
        print(f"Error: {e}")

def get_password():
    try:
        # Retrieve the tunnel password (public IP)
        import urllib.request
        with urllib.request.urlopen('https://loca.lt/mytunnelpassword') as response:
            return response.read().decode('utf-8').strip()
    except:
        return "Check https://loca.lt/mytunnelpassword"

if __name__ == "__main__":
    start_sharing()
