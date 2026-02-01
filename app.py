from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from typing import List, Dict, Union, Any
import uvicorn
from utils import strict_json_parse
from extract_problems import process_pdf # Import extraction logic
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

app = FastAPI(title="AI Exam Dataset Viewer")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = "output_extraction"

# Check if output directory exists
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

@app.get("/api/exams")
async def list_exams():
    """List all processed exams in the output directory."""
    if not os.path.exists(OUTPUT_DIR):
        return []
    
    exams = []
    for entry in os.scandir(OUTPUT_DIR):
        if entry.is_dir() and not entry.name.startswith("crops_"):
            exams.append(entry.name)
    return sorted(exams)

@app.get("/api/exams/{exam_name}/problems")
async def get_exam_problems(exam_name: str):
    """Retrieve all problems and metadata for a specific exam."""
    exam_path = os.path.join(OUTPUT_DIR, exam_name)
    if not os.path.exists(exam_path):
        raise HTTPException(status_code=404, detail="Exam not found")
    
    all_problems = []
    
    # 1. Look for all extracted_*.png.json files
    json_files = [f for f in os.listdir(exam_path) if f.startswith("extracted_") and f.endswith(".json")]
    
    # Sort by page number using a helper
    def get_page_num(fname):
        try:
            # extracted_page_2.png.json -> 2
            return int(fname.split("_")[2].split(".")[0])
        except:
            return 999
    
    json_files.sort(key=get_page_num)
    
    print(f"Loading exam {exam_name}: Found {len(json_files)} JSON files")

    for jf in json_files:
        # Correspond to page name: extracted_page_2.png.json -> page_2
        page_name = jf.replace("extracted_", "").replace(".png.json", "")
        
        json_full_path = os.path.join(exam_path, jf)
        try:
            with open(json_full_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            problems = strict_json_parse(content)
            if not problems:
                print(f"  Warning: No problems returned from {jf}")
                continue
                
            for prob in problems:
                content = prob.get("content", {})
                q_header = content.get("header") or prob.get("question_number") or "unknown"
                
                # Construct crop image path
                page_name = jf.replace("extracted_", "").replace(".png.json", "")
                crop_rel_dir = f"crops_{page_name}"
                # Extract numbers for matching filename
                import re
                q_num_clean = re.sub(r'[^0-9]', '', str(q_header)) or "None"
                crop_filename = f"q_{q_num_clean}.png"
                crop_path = f"/images/{exam_name}/{crop_rel_dir}/{crop_filename}"
                
                # Add to list with detailed metadata
                all_problems.append({
                    "id": f"{exam_name}_{page_name}_{q_header}",
                    "page": page_name,
                    "header": q_header,
                    "scenario": content.get("scenario"),
                    "charts": content.get("charts", []),
                    "visual_elements": content.get("visual_elements", []),
                    "visuals": content.get("visuals", []), # Legacy
                    "directive": content.get("directive", ""),
                    "propositions": content.get("propositions"),
                    "options": content.get("options", []),
                    "image_url": crop_path,
                    "box_2d": prob.get("box_2d", [])
                })
        except Exception as e:
            print(f"  Error loading {jf}: {e}")
            
    # Sort all problems by page number then header number
    def sort_key(p):
        try:
            pg = int(p["page"].replace("page_", ""))
            hd = int(re.sub(r'[^0-9]', '', str(p["header"])))
            return (pg, hd)
        except:
            return (999, 999)
            
    all_problems.sort(key=sort_key)
    return all_problems

# Mount the output directory to serve images
app.mount("/images", StaticFiles(directory=OUTPUT_DIR), name="images")

import google.generativeai as genai
from PIL import Image

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
print(f"DEBUG: Startup - API Key Status: {'SET' if api_key else 'MISSING'}")

if api_key:
    genai.configure(api_key=api_key)

class VariationRequest(BaseModel):
    header: Union[str, int, float] = None
    scenario: Union[str, List[Any], None] = None
    directive: Union[str, List[Any], None] = None
    propositions: Union[str, List[Any], Dict[str, Any], None] = None
    options: Union[List[str], List[Any]] = []
    image_url: str = None 
    visual_elements: List[Dict[str, Any]] = []

    class Config:
        extra = "ignore"

@app.post("/api/generate-variation")
async def generate_variation(req: VariationRequest):
    """
    Generate a similar problem and clean SVG using Gemini 3 Pro.
    """
    try:
        if not api_key:
             raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")
    
        # Safe access to lists
        visuals_safe = req.visual_elements or []
        has_visuals = len(visuals_safe) > 0
        
        prompt_parts = []
        
        if has_visuals:
            # --- MODE A: RECONSTRUCTION + VARIATION (Visuals Present) ---
            instruction = """
            You are an expert scientific illustrator and educator in Korea.
            Your task is to:
            1. ANALYZE the provided problem image(s).
            2. RECONSTRUCT the main diagram/graph as high-quality **SVG CODE**.
               - Output RAW <svg> code. Do NOT use markdown code blocks.
               - Ensure specific numbers/labels from the original are preserved or logically adapted.
               - Make it look PROFESSIONAL (text-book quality).
               - Do NOT generate Python code. ONLY SVG.
            3. CREATE A SIMILAR PROBLEM based on the logic of the original.
               - **LANGUAGE: KOREAN (한국어).** The problem text, scenario, and directives MUST be in natural, academic Korean.
               - **TABLES (표):** If the problem contains a data table, provide it in the 'table' field using Markdown format.
               - **PROPOSITIONS (보기):** If the problem involves matching statements (e.g., ㄱ, ㄴ, ㄷ), you MUST provide these in the 'propositions' field as a single formatted string.
               - **OPTIONS (선지):** You MUST provide 5 distinct choices (text) for the answer. Do NOT leave 'options' empty.
            
            OUTPUT FORMAT (JSON):
            {
                "reconstruction_type": "svg",
                "reconstruction_code": "<svg>...</svg>",
                "variation_problem": {
                    "header": "유사 문제",
                    "scenario": "New scenario in Korean...",
                    "table": "| Header 1 | Header 2 |\\n|---|---|\\n| Val 1 | Val 2 |",
                    "directive": "New directive in Korean...",
                    "propositions": "ㄱ. Statement A...\\nㄴ. Statement B...\\nㄷ. Statement C...",
                    "options": ["1번 보기", "2번 보기", "3번 보기", "4번 보기", "5번 보기"]
                }
            }
            """
            prompt_parts.append(instruction)
            
            # Load Images (Robustly)
            try:
                # 1. Main Context Image
                if req.image_url:
                    rel_path = req.image_url.replace("/images/", "")
                    full_path = os.path.join(OUTPUT_DIR, rel_path)
                    if os.path.exists(full_path):
                        img = Image.open(full_path)
                        prompt_parts.append(img)
                        prompt_parts.append("Main Context Image")
                
                # 2. Visual Elements
                for vis in visuals_safe:
                     if 'image_path' in vis and req.image_url:
                         # We need req.image_url to know the base directory
                         base_dir = os.path.dirname(req.image_url.replace("/images/", ""))
                         vis_full_path = os.path.join(OUTPUT_DIR, base_dir, vis['image_path'])
                         if os.path.exists(vis_full_path):
                             v_img = Image.open(vis_full_path)
                             prompt_parts.append(v_img)
                             prompt_parts.append("Visual Element to Reconstruct")
            except Exception as e:
                print(f"Error loading images: {e}")
    
        else:
            # --- MODE B: TEXT VARIATION ONLY ---
            instruction = """
            You are an expert scientific educator in Korea.
            Your task is to CREATE A SIMILAR PROBLEM based on the provided text.
            
            CRITICAL RULES:
            1. **LANGUAGE: KOREAN (한국어).** All text must be in fluent, academic Korean.
            2. **TABLES (표):** If necessary, provide tables in Markdown in the 'table' field.
            3. **PROPOSITIONS (보기):** If applicable (e.g., ㄱ, ㄴ, ㄷ statements), provide them in 'propositions'.
            4. **OPTIONS (선지):** If the original problem is multiple choice, you MUST provide 5 distinct choices.
            
            OUTPUT FORMAT (JSON):
            {
                "reconstruction_type": "none",
                "reconstruction_code": "",
                "variation_problem": {
                    "header": "유사 문제",
                    "scenario": "New scenario in Korean...",
                    "table": "| column | column |\\n|---|---|",
                    "directive": "New directive in Korean...",
                    "propositions": "ㄱ. Statement A...\\nㄴ. Statement B...\\nㄷ. Statement C...",
                    "options": ["1번 보기", "2번 보기", "3번 보기", "4번 보기", "5번 보기"]
                }
            }
            """
            prompt_parts.append(instruction)
    
        # Add Text Context (Always)
        context = f"""
        Original Problem:
        Header: {req.header}
        Scenario: {req.scenario}
        Directive: {req.directive}
        Propositions: {req.propositions}
        Options: {req.options}
        """
        prompt_parts.append(context)
    
        # 4. Call Generation Model
        # Use the specific model requested
        model = genai.GenerativeModel('models/gemini-3-pro-image-preview')
        
        response = model.generate_content(prompt_parts)
        
        # DEBUG LOGGING (Safe Print)
        try:
            print(f"\n[Gemini Raw Output]:\n{response.text}\n")
        except:
            print(f"[Gemini Log Error]: Could not print response text.")
        
        # Parse result
        json_str = response.text.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:-3].strip()
        elif json_str.startswith("```"):
             json_str = json_str[3:-3].strip()
            
        # Robust JSON Cleaning: Escape backslashes that aren't already escaped
        try:
            import re
            json_str = re.sub(r'\\(?![/u"bfnrt\\])', r'\\\\', json_str)
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[JSON Error] Failed to parse: {e}")
            return {
                "reconstruction_type": "error",
                "reconstruction_code": f"JSON Parsing Failed: {str(e)}",
                "variation_problem": None
            }
        
        # Validate structure
        if "variation_problem" not in result:
            result["variation_problem"] = {
                "header": "Variation Generation Failed",
                "directive": "The model did not return a valid variation problem.",
                "options": []
            }
        if "reconstruction_type" not in result:
            result["reconstruction_type"] = "error"
            result["reconstruction_code"] = "Model did not return reconstruction type."
            
        return result

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Generation Critical Error: {e}")
        return {
            "reconstruction_type": "error",
            "reconstruction_code": f"Server Error: {str(e)}",
            "variation_problem": {
                "header": "System Error",
                "directive": "An tracking error occurred. Please check server logs.",
            }
        }

# --- PDF Upload & Progress ---
from fastapi import UploadFile, File, BackgroundTasks

# Simple in-memory progress store: { "filename": { "status": "msg", "percent": 0, "done": False } }
processing_status = {}

@app.get("/api/progress/{filename}")
async def get_progress(filename: str):
    """Get the current processing status of a file."""
    # Try exact match first
    if filename in processing_status:
        return processing_status[filename]
        
    # Try matching without extension if needed
    for k, v in processing_status.items():
        if filename in k or k in filename:
            return v
            
    return {"status": "Not found", "percent": 0, "done": False}

@app.post("/api/upload")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Handle PDF upload and trigger background processing.
    """
    try:
        # 1. Validate
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
            
        # 2. Save to input directory
        input_dir = "input_pdfs"
        if not os.path.exists(input_dir):
            os.makedirs(input_dir)
            
        # Sanitize filename
        import re
        safe_filename = re.sub(r'[^a-zA-Z0-9_\-\.가-힣]', '_', file.filename)
        file_path = os.path.join(input_dir, safe_filename)
        
        with open(file_path, "wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)
            
        print(f"File uploaded: {file_path}")
        
        # 3. Trigger Background Processing
        # Initialize progress
        processing_status[safe_filename] = {"status": "Starting...", "percent": 0, "done": False}

        # We wrap process_pdf to catch errors without crashing app
        def safe_process(path, fname):
            def update_progress(msg, pct):
                processing_status[fname] = {"status": msg, "percent": pct, "done": False}
                
            try:
                print(f"Starting background processing for {path}")
                process_pdf(path, progress_callback=update_progress)
                print(f"Finished background processing for {path}")
                processing_status[fname] = {"status": "Complete!", "percent": 100, "done": True}
            except Exception as e:
                print(f"Background processing failed for {path}: {e}")
                processing_status[fname] = {"status": f"Error: {str(e)}", "percent": 0, "done": True}
                
        background_tasks.add_task(safe_process, file_path, safe_filename)
        
        return {"filename": safe_filename, "message": "Upload successful. Processing started in background."}
        
    except Exception as e:
        print(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# Serve the frontend as a single file for now
@app.get("/")
async def get_index():
    from fastapi.responses import HTMLResponse
    with open("viewer.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/manifest.json")
async def get_manifest():
    from fastapi.responses import FileResponse
    return FileResponse("manifest.json", media_type="application/manifest+json")

@app.get("/icon.png")
async def get_icon():
    from fastapi.responses import FileResponse
    return FileResponse("icon.png", media_type="image/png")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
