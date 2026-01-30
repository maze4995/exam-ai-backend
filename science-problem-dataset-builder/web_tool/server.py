from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os

app = FastAPI()

# Mount the web tool directory to serve index.html
TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
# Data dir is parallel to web_tool: ../output
DATA_DIR = os.path.join(os.path.dirname(TOOL_DIR), "output")

print(f"Serving Data form: {DATA_DIR}")

app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(TOOL_DIR, "viewer.html"))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
