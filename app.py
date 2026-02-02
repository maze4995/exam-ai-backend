from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from datetime import datetime
from typing import List, Dict, Union, Any
import uvicorn
from utils import strict_json_parse
from extract_problems import process_pdf
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# --- Auth Modules ---
from database import engine, init_db, get_db, User
# --- Auth Modules ---
from database import engine, init_db, get_db, User
from auth import get_current_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
# Removed get_password_hash, verify_password from auth import to use local versions
from datetime import timedelta
from passlib.context import CryptContext
import hashlib

# Load environment variables
load_dotenv(override=True)

# Initialize Database Table
# Initialize Database Table
init_db()

# --- Local Auth Helpers (Fix for caching/update issues) ---
# Switched to pbkdf2_sha256 to avoid bcrypt version mismatch issues on server
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def verify_password_local(plain_password, hashed_password):
    # Fix: Pre-hash with SHA-256 to ensure input is always 64 chars
    safe_password = hashlib.sha256(plain_password.encode('utf-8')).hexdigest()
    return pwd_context.verify(safe_password, hashed_password)

def get_password_hash_local(password):
    # Fix: Pre-hash with SHA-256
    safe_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return pwd_context.hash(safe_password)

app = FastAPI(title="AI Exam Dataset Viewer")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Check for Railway persistent volume
PERSISTENT_ROOT = "/app/persistent" if os.path.exists("/app/persistent") else "."
BASE_OUTPUT_DIR = os.path.join(PERSISTENT_ROOT, "output_extraction")

if not os.path.exists(BASE_OUTPUT_DIR):
    os.makedirs(BASE_OUTPUT_DIR)

# --- Auth Endpoints ---

class UserRegister(BaseModel):
    username: str
    password: str

@app.post("/api/register")
def register(user: UserRegister, db: Session = Depends(get_db)):
    try:
        db_user = db.query(User).filter(User.username == user.username).first()
        if db_user:
            raise HTTPException(status_code=400, detail="Username already registered")
        
        # Use LOCAL hash function
        hashed_password = get_password_hash_local(user.password)
        
        new_user = User(username=user.username, hashed_password=hashed_password)
        db.add(new_user)
        db.commit()
        return {"message": "User created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Registration Error: {e}")
        # Message to confirm new logic is running
        raise HTTPException(status_code=500, detail=f"LOCAL_AUTH_FIX Error: {str(e)}")

@app.post("/api/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    # Use LOCAL verify function
    if not user or not verify_password_local(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Protected Routes Helper ---
def get_user_output_dir(user: User):
    """Get isolated output directory for the current user."""
    user_dir = os.path.join(BASE_OUTPUT_DIR, user.username)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return user_dir

@app.get("/api/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username, "id": current_user.id}

# --- Modified Exam Endpoints (User Isolated) ---

@app.get("/api/exams")
async def list_exams(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all processed exams in the USER'S private directory."""
    user_dir = get_user_output_dir(current_user)
    
    exams = set() # Use set to avoid duplicates
    
    print(f"\n[DEBUG] list_exams called for user: {current_user.username}")
    print(f"[DEBUG] user_dir: {user_dir}")
    print(f"[DEBUG] BASE_OUTPUT_DIR: {BASE_OUTPUT_DIR}")

    # 1. User's isolated exams
    if os.path.exists(user_dir):
        print(f"[DEBUG] user_dir exists. Scanning...")
        for entry in os.scandir(user_dir):
            if entry.is_dir() and not entry.name.startswith("crops_"):
                exams.add(entry.name)
    else:
        print(f"[DEBUG] user_dir does NOT exist.")

    # 2. Legacy/Shared exams (in root output dir)
    if os.path.exists(BASE_OUTPUT_DIR):
        print(f"[DEBUG] BASE_OUTPUT_DIR exists. Legacy scanning...")
        
        # Get all usernames to exclude them from the list
        users = db.query(User).all()
        user_dirs = {u.username for u in users}
        
        for entry in os.scandir(BASE_OUTPUT_DIR):
            # Exclusion 1: Known user directories
            if not entry.is_dir() or entry.name.startswith("crops_") or entry.name in user_dirs:
                continue
                
            # Exclusion 2: Strict Content Check (Must contain 'extracted_*.json')
            # User directories usually contain exam folders, not the JSONs directly.
            # Valid exams MUST have these analysis files.
            is_exam = False
            try:
                for sub in os.scandir(entry.path):
                    if sub.is_file() and sub.name.startswith("extracted_") and sub.name.endswith(".json"):
                        is_exam = True
                        break
            except Exception:
                pass
            
            if is_exam:
                exams.add(entry.name)
            else:
                 print(f"[DEBUG] Skipping non-exam folder: {entry.name}")
                
    results = sorted(list(exams))
    print(f"[DEBUG] Found exams: {results}")
    return results

@app.delete("/api/exams/{exam_name}")
async def delete_exam(exam_name: str, current_user: User = Depends(get_current_user)):
    """Delete an exam and its associated data for the current user."""
    user_dir = get_user_output_dir(current_user)
    exam_path = os.path.join(user_dir, exam_name)
    
    # Fallback to legacy root path
    if not os.path.exists(exam_path):
        exam_path = os.path.join(BASE_OUTPUT_DIR, exam_name)
    
    if not os.path.exists(exam_path):
        raise HTTPException(status_code=404, detail="Exam not found")
        
    try:
        import shutil
        shutil.rmtree(exam_path)
        return {"message": f"Exam '{exam_name}' deleted successfully"}
    except Exception as e:
        print(f"Error deleting exam {exam_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete exam: {str(e)}")

@app.get("/api/exams/{exam_name}/problems")
async def get_exam_problems(exam_name: str, current_user: User = Depends(get_current_user)):
    """Retrieve problems for a specific exam belonging to the user."""
    user_dir = get_user_output_dir(current_user)
    exam_path = os.path.join(user_dir, exam_name)
    
    # Fallback to legacy root path
    if not os.path.exists(exam_path):
        exam_path = os.path.join(BASE_OUTPUT_DIR, exam_name)
    
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
                crop_path = f"/images/{current_user.username}/{exam_name}/{crop_rel_dir}/{crop_filename}"
                
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
app.mount("/images", StaticFiles(directory=BASE_OUTPUT_DIR), name="images")

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
            # --- STEP 1: IMAGE ANALYSIS (New Request) ---
            print("\n[Step 1] Analyzing Image Structure...")
            analysis_instruction = """
            [지시사항] 업로드한 이미지를 분석하여 다음의 구조에 따라 상세하게 설명해 줘. 모든 설명은 전문적이고 깔끔한 교과서 삽화 분석 스타일을 유지해야 해.

            1. 전체적인 구조:
            - 이미지의 레이아웃(예: 좌우 배치, 상하 배치)과 기호(예: (가), (나), 화살표)를 파악해 줘.
            - 전반적인 시각적 스타일(예: 삽화, 사진, 그래프, 인포그래픽)을 정의해 줘.

            2. 각 섹션별 상세 설명 (섹션이 나뉘어 있을 경우):
            - 주제: 해당 섹션이 나타내는 핵심 개념이나 사물.
            - 스타일: 색상 구성(흑백, 컬러), 선의 특징, 배경 처리 방식.
            - 핵심 요소:
              > * 이미지에 나타난 주요 사물, 인물, 기구 등에 대한 정밀한 묘사.
              > * 포함된 모든 텍스트, 숫자, 단위(μg/m³, %, °C 등)를 정확하게 기록.
              > * 그래프의 경우 형태(원형, 막대, 선)와 데이터의 시각적 비중(예: 게이지가 채워진 정도)을 설명.

            3. 기타 특징:
            - 배경의 흐림 정도나 강조된 부분 등 학습에 도움이 될 만한 시각적 장치들을 기술해 줘.
            """
            
            # Prepare Analysis Prompt
            analysis_parts = [analysis_instruction]
            
            # Load Images for Analysis (Reuse logic)
            if req.image_url:
                rel_path = req.image_url.replace("/images/", "")
                full_path = os.path.join(BASE_OUTPUT_DIR, rel_path)
                if os.path.exists(full_path):
                    img = Image.open(full_path)
                    analysis_parts.append(img)
            
            for vis in visuals_safe:
                 if 'image_path' in vis and req.image_url:
                     base_dir = os.path.dirname(req.image_url.replace("/images/", ""))
                     vis_full_path = os.path.join(BASE_OUTPUT_DIR, base_dir, vis['image_path'])
                     if os.path.exists(vis_full_path):
                         v_img = Image.open(vis_full_path)
                         analysis_parts.append(v_img)

            # Call Model for Analysis
            model = genai.GenerativeModel('models/gemini-3-pro-image-preview')
            try:
                analysis_response = model.generate_content(analysis_parts)
                analysis_text = analysis_response.text
                print(f"\n[Analysis Result]:\n{analysis_text[:200]}...\n")
            except Exception as e:
                print(f"[Analysis Error] Skipping analysis step: {e}")
                analysis_text = "Image analysis failed. Proceed with direct reconstruction."

            # --- STEP 2: GENERATION (Existing Logic + Injected Analysis) ---
            instruction = f"""
            당신은 전문적인 과학 교과서 삽화가이자 교육용 인포그래픽 복원 전문가입니다.
            당신의 목표는 제공된 원본 이미지(Source Image)를 기반으로, 노이즈가 제거된 깨끗하고 전문적인 **'풀 컬러 교과서 스타일 삽화'**를 재구성하는 것입니다.

            **[참고: 이미지 정밀 분석 결과]**
            아래 분석 내용을 바탕으로 이미지를 더욱 정확하게 재구성하십시오.
            ---
            {analysis_text}
            ---

            반드시 준수해야 할 핵심 지침:

            1. **노이즈 및 필기 흔적 제거 (NOISE REMOVAL):**
               - 이미지 내의 손글씨, 낙서, 임의의 동그라미, 밑줄 등 학생의 필기 흔적과 종이의 질감, 얼룩을 완벽하게 제거하십시오.
               - 오직 **'인쇄된 원본 요소'**만 남겨야 합니다.

            2. **원본 색상 및 데이터 보존 (COLOR & DATA):**
               - 색상 유지: 원본 이미지에 사용된 색상 체계를 그대로 계승하십시오. (예: 화산 내부의 붉은 마그마, 상태를 나타내는 색상 지표 등).
               - 선명도 개선: 색상은 유지하되, 출판물에 적합하도록 채도를 정돈하고 경계를 선명하게 표현하십시오. 배경은 가급적 깨끗한 흰색으로 처리하여 개체가 돋보이게 하십시오.

            3. **시각적 요소의 정교화 (VECTOR STYLE RECONSTRUCTION):**
               - **SVG CODE 생성 필수:** 모든 선은 매끄러운 벡터 스타일로 표현하고, 불필요한 픽셀 깨짐이 없어야 합니다.
               - **스타일 (FLAT DESIGN):** 복잡한 질감(예: 바위 표면, 물결)을 억지로 그리지 말고, **단순화된 '플랫 디자인(Flat Design)'** 스타일로 변환하십시오.
               - **색상:** 그라데이션 대신 **단색(Solid Color)** 위주로 사용하여 깔끔하게 표현하십시오.
               - **수식 표기 (LaTeX):** 모든 수식, 숫자, 단위(m/s², kg 등)는 반드시 LaTeX 문법을 사용하여 **`$` 기호로 감싸야 합니다.** (예: `$3\\text{{m/s}}^2$`, `$10\\text{{kg}}$`)
               - **금지 사항:** `<image>` 태그를 사용하여 비트맵 이미지를 임베딩하지 마십시오. 오직 벡터 요소(`<path>`, `<rect>`, `<circle>` 등)만 사용해야 합니다.
               - 텍스트 및 레이블: (가), (나), A, B, C와 같은 기호와 수치, 단위(μg/m³ 등)는 가독성이 뛰어난 표준 고딕 계열 폰트로 다시 작성하십시오.
               - 결과물은 반드시 **RAW <svg> 코드**로 `reconstruction_code` 필드에 제공해야 합니다.

            4. **유사 문제 생성 (GENERATE SIMILAR PROBLEM):**
               - [원본 이미지]의 시각적 형태와 논리를 바탕으로, 새로운 유사 문제를 생성하십시오. 
               - **언어:** 한국어 (Korean) - 자연스럽고 학술적인 어조.
               - **내용:** 원본 문제의 핵심 개념을 유지하되, 수치나 상황을 변형하여 새로운 문제를 만드십시오.

            OUTPUT FORMAT (JSON):
            {{
                "reconstruction_type": "svg",
                "reconstruction_code": "<svg>...</svg>",
                "variation_problem": {{
                    "header": "유사 문제",
                    "scenario": "새로운 문제 시나리오 (한국어)...",
                    "table": "| 헤더1 | 헤더2 |\\n|---|---|\\n| 값1 | 값2 |",
                    "directive": "새로운 지시문 (한국어)...",
                    "propositions": "ㄱ. 보기 A...\\nㄴ. 보기 B...\\nㄷ. 보기 C...",
                    "options": ["1번 선지", "2번 선지", "3번 선지", "4번 선지", "5번 선지"]
                }}
            }}
            """
            prompt_parts.append(instruction)
            
            # Load Images (Robustly)
            try:
                # 1. Main Context Image
                if req.image_url:
                    rel_path = req.image_url.replace("/images/", "")
                    full_path = os.path.join(BASE_OUTPUT_DIR, rel_path)
                    if os.path.exists(full_path):
                        img = Image.open(full_path)
                        prompt_parts.append(img)
                        prompt_parts.append("Main Context Image")
                
                # 2. Visual Elements
                for vis in visuals_safe:
                     if 'image_path' in vis and req.image_url:
                         # We need req.image_url to know the base directory
                         base_dir = os.path.dirname(req.image_url.replace("/images/", ""))
                         vis_full_path = os.path.join(BASE_OUTPUT_DIR, base_dir, vis['image_path'])
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
            
        # Robust JSON Cleaning
        try:
            import re
            # 1. Protect common LaTeX commands that start with JSON escape chars (t, n, r, b, f)
            # Use negative lookbehind to ensure we don't double-escape
            json_str = re.sub(r'(?<!\\)\\(t(?=ext|imes|au|heta|an)|n(?=u|eq)|r(?=ho|ight)|b(?=eta)|f(?=rac|phi))', r'\\\\\1', json_str)
            
            # 2. General escape for other chars (existing logic)
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
        error_msg = str(e)
        formatted_trace = traceback.format_exc()
        
        print(f"Generation Critical Error: {error_msg}")
        # Log to file
        with open("server_error.log", "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now()}] ERROR:\n{formatted_trace}\n")
            
        return {
            "reconstruction_type": "error",
            "reconstruction_code": f"Server Error: {error_msg}",
            "variation_problem": {
                "header": "System Error",
                "directive": f"오류가 발생했습니다: {error_msg}\n(자세한 내용은 server_error.log를 확인하세요)",
                "options": []
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
async def upload_pdf(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Handle PDF upload and trigger background processing.
    """
    try:
        # 1. Validate
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
            
        # 2. Save to user-specific upload directory
        user_input_dir = os.path.join("uploads", current_user.username)
        if not os.path.exists(user_input_dir):
            os.makedirs(user_input_dir)
            
        # Sanitize filename
        import re
        safe_filename = re.sub(r'[^a-zA-Z0-9_\-\.가-힣]', '_', file.filename)
        file_path = os.path.join(user_input_dir, safe_filename)
        
        with open(file_path, "wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)
            
        print(f"File uploaded by {current_user.username}: {file_path}")
        
        # 3. Trigger Background Processing
        # Initialize progress
        processing_status[safe_filename] = {"status": "Starting...", "percent": 0, "done": False}

        # Determine user output directory
        user_output_dir = get_user_output_dir(current_user)

        def safe_process(path, fname, output_dir):
            def update_progress(msg, pct):
                processing_status[fname] = {"status": msg, "percent": pct, "done": False}
                
            try:
                print(f"Starting background processing for {path}")
                # Pass user_output_dir to process_pdf
                process_pdf(path, output_dir=output_dir, progress_callback=update_progress)
                print(f"Finished background processing for {path}")
                processing_status[fname] = {"status": "Complete!", "percent": 100, "done": True}
            except Exception as e:
                print(f"Background processing failed for {path}: {e}")
                processing_status[fname] = {"status": f"Error: {str(e)}", "percent": 0, "done": True}
                
        background_tasks.add_task(safe_process, file_path, safe_filename, user_output_dir)
        
        return {"filename": safe_filename, "message": "Upload started"}
    except Exception as e:
         print(f"Upload Error: {e}")
         raise HTTPException(status_code=500, detail=str(e))



# Serve the frontend as a single file for now
@app.get("/manifest.json")
async def get_manifest():
    from fastapi.responses import FileResponse
    return FileResponse("manifest.json", media_type="application/manifest+json")

@app.get("/icon.png")
async def get_icon():
    from fastapi.responses import FileResponse
    return FileResponse("icon.png", media_type="image/png")

# --- Image Serving Proxy (Fix for User Isolation) ---
@app.get("/api/images/{exam_name}/{image_path:path}")
async def get_exam_image(
    exam_name: str, 
    image_path: str, 
    token: str = None
):
    """
    Serve images from Exam directory.
    Auth: Requires 'token' query parameter for access validation.
    Checks User's private directory first, then Legacy shared directory.
    """
    # 1. Manual Auth Validation (since img tags can't send headers easily)
    if not token:
         raise HTTPException(status_code=401, detail="Token required for image access")
    
    try:
        from jose import jwt
        from auth import SECRET_KEY, ALGORITHM
        from database import get_db, User
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401)
            
        # Get DB session manually (hacky but quick for this specific endpoint pattern)
        # Better: Depedency injection, but let's keep it simple.
        # Actually, let's just trust the token username for directory lookup?
        # Ideally check DB, but file isolation relies on username.
        
    except Exception:
         raise HTTPException(status_code=401, detail="Invalid Token")

    user_dir = os.path.join(BASE_OUTPUT_DIR, username)
    
    # 2. Check User Dir
    file_path = os.path.join(user_dir, exam_name, image_path)
    if not os.path.exists(file_path):
        # 3. Check Legacy Dir
        file_path = os.path.join(BASE_OUTPUT_DIR, exam_name, image_path)
        
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
        
    from fastapi.responses import FileResponse
    return FileResponse(file_path)

# Mount client directory to serve frontend (Must be last)
app.mount("/", StaticFiles(directory="client", html=True), name="frontend")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
