
import fitz  # PyMuPDF
import cv2
import numpy as np
import os
import google.generativeai as genai
from PIL import Image
from utils import strict_json_parse

# --- Configuration ---
TARGET_DIR = r"C:\Users\rlgus\Desktop\Hyun&Hyun\문제집 - 과학\내신\시험지 모음\1학기 기말고사"
OUTPUT_DIR = "output_extraction"
# DO NOT hardcode your API key here. Set an environment variable like:
# $env:GEMINI_API_KEY = "your_key_here" in PowerShell
API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_NEW_API_KEY_HERE")

# Configure Gemini
genai.configure(api_key=API_KEY)

def setup_directories():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

def extract_content_with_vlm(image_path):
    import time
    max_retries = 5
    for attempt in range(max_retries):
        try:
            pil_img = Image.open(image_path)
            model = genai.GenerativeModel('gemini-3-flash-preview') 

            prompt = """
            이 이미지에서 각 '시험 문제'를 찾아 구조화된 JSON 데이터로 추출해줘.
            
            [핵심 지시사항]
            1. **줄 바꿈 및 띄어쓰기 엄수**: 문제에 표기된 줄 바꿈(`\\n`)과 띄어쓰기를 원본과 최대한 동일하게 유지해.
            2. **수식/기호/화학식 처리**: 수식, 화학식, 기호 등은 모두 `$` 기호로 감싸는 LaTeX 형식을 사용해. 
            3. **표(Table) 처리**: 지문에 포함된 표는 `scenario`에서 제외하고, `charts` 필드에 Markdown Table 형식으로 따로 추출해.
            4. **시각 자료(Visuals) 상세 추출**: 문제 내부에 포함된 그림, 그래프, 도표 등은 전체 문제 영역과 별도로 `visual_elements`에 좌표와 함께 식별해 줘.
            
            [표준 스키마]
            {
              "content": {
                "header": "문제 번호 (예: '1.')",
                "scenario": "배경 상황/지문 (표 제외, 원본 줄바꿈 유지)",
                "charts": ["Markdown 형식의 표 내용"], 
                "visual_elements": [
                  { "type": "graph/diagram", "box_2d": [ymin, xmin, ymax, xmax] } 
                ], // 문제 내의 시각 자료 위치 (없으면 빈 배열)
                "directive": "질문 지시문 (원본 줄바꿈 유지)",
                "propositions": "ㄱ, ㄴ, ㄷ 보기 내용 (원본 줄바꿈 유지, 없으면 null)",
                "options": ["① ...", "② ...", "③ ..."] // 선지
              },
              "box_2d": [ymin, xmin, ymax, xmax] // 문제 전체 영역
            }
            """
            
            response = model.generate_content([prompt, pil_img])
            return response.text
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "quota" in err_msg.lower():
                print(f"Quota exceeded (429). Waiting 70s before retry {attempt+1}/{max_retries}...")
                time.sleep(70)
                continue
            return f"Error during VLM extraction: {e}"
    
    return "Error during VLM extraction: Maximum retries exceeded for quota issue."

def crop_and_save_exam_problems(image_path, extraction_result, output_base):
    problems = strict_json_parse(extraction_result)
    if not problems:
        print(f"No problems parsed for {image_path}")
        return []

    try:
        img = Image.open(image_path)
        width, height = img.size
    except Exception as e:
        print(f"Error opening image for cropping: {e}")
        return
    
    page_bs = os.path.splitext(os.path.basename(image_path))[0] # page_1
    crop_dir = os.path.join(output_base, f"crops_{page_bs}")
    if not os.path.exists(crop_dir):
        os.makedirs(crop_dir)
        
    for prob in problems:
        if "box_2d" not in prob:
            continue
            
        # Standardized schema uses content.header
        content = prob.get("content", {})
        q_header = content.get("header") or prob.get("question_number") or "unknown"
        
        # Sanitize for filename (extract only numbers if possible)
        import re
        q_num = re.sub(r'[^0-9]', '', str(q_header)) or "None"
        
        ymin, xmin, ymax, xmax = prob["box_2d"]
        
        # Convert 1000-scale to pixels with some padding
        left = max(0, (xmin / 1000) * width - 10)
        top = max(0, (ymin / 1000) * height - 10)
        right = min(width, (xmax / 1000) * width + 10)
        bottom = min(height, (ymax / 1000) * height + 10)
        
        try:
            # Crop main problem
            crop = img.crop((left, top, right, bottom))
            crop_path = os.path.join(crop_dir, f"q_{q_num}.png")
            crop.save(crop_path)
            
            # --- Fix: Add image_url for frontend ---
            # Path construction: /images/{username}/{exam_name}/crops_{page}/{filename}
            # output_base is .../output_extraction/{username}/{exam_name}
            exam_name = os.path.basename(output_base)
            parent_dir = os.path.basename(os.path.dirname(output_base))
            
            # Check if running in user-isolated mode (parent != output_extraction)
            # Adjust condition based on actual folder structure
            if parent_dir == "output_extraction" or parent_dir == "output":
                 url_prefix = f"/images/{exam_name}"
            else:
                 url_prefix = f"/images/{parent_dir}/{exam_name}"

            prob["image_url"] = f"{url_prefix}/crops_{page_bs}/q_{q_num}.png"
            
            # Crop visual elements (new feature)
            visuals = content.get("visual_elements", [])
            for idx, vis in enumerate(visuals):
                if "box_2d" in vis:
                    v_ymin, v_xmin, v_ymax, v_xmax = vis["box_2d"]
                    v_left = max(0, (v_xmin / 1000) * width)
                    v_top = max(0, (v_ymin / 1000) * height)
                    v_right = min(width, (v_xmax / 1000) * width)
                    v_bottom = min(height, (v_ymax / 1000) * height)
                    
                    try:
                        vis_crop = img.crop((v_left, v_top, v_right, v_bottom))
                        vis_filename = f"q_{q_num}_visual_{idx}.png"
                        vis_path = os.path.join(crop_dir, vis_filename)
                        vis_crop.save(vis_path)
                        # Add path to the visual object for frontend
                        vis["image_url"] = f"{url_prefix}/crops_{page_bs}/{vis_filename}"
                    except Exception as ve:
                        print(f"Visual crop error for Q{q_num} visual {idx}: {ve}")
                        
        except Exception as e:
            print(f"Crop error for Q{q_num}: {e}")
            
    return problems

def process_pdf(pdf_path, output_dir="output_extraction", progress_callback=None):
    if progress_callback: progress_callback("Initializing...", 0)
    print(f"\n--- Processing: {os.path.basename(pdf_path)} ---")
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    exam_output_dir = os.path.join(output_dir, pdf_name)
    if not os.path.exists(exam_output_dir):
        os.makedirs(exam_output_dir)
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return

    # Convert PDF to images
    image_paths = []
    for page_num in range(len(doc)):
        img_filename = f"page_{page_num+1}.png"
        img_path = os.path.join(exam_output_dir, img_filename)
        
        if not os.path.exists(img_path):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=300)
            pix.save(img_path)
        
        image_paths.append(img_path)
    
    print(f"Total pages: {len(image_paths)}")
    if progress_callback: progress_callback(f"Converted PDF to {len(image_paths)} images.", 10)
    
    import time
    # Skip cover page if it has many pages
    start_index = 1 if len(image_paths) > 2 else 0
    
    for i in range(start_index, len(image_paths)):
        img_path = image_paths[i]
        json_filename = f"extracted_{os.path.basename(img_path)}.json"
        json_path = os.path.join(exam_output_dir, json_filename)
        
        if progress_callback:
            percent = 10 + int((i / len(image_paths)) * 90)
            progress_callback(f"Analyzing Page {i+1}/{len(image_paths)} (AI Extraction)...", percent)

        # User requested to start fresh, so we remove skip logic
        print(f"Processing Page {i+1}/{len(image_paths)}...")
        result = extract_content_with_vlm(img_path)
        
        # Crop and get updated data with image paths
        updated_problems = crop_and_save_exam_problems(img_path, result, exam_output_dir)
        
        # Save the updated structured data
        import json
        with open(json_path, "w", encoding="utf-8") as f:
            if updated_problems:
                json.dump(updated_problems, f, ensure_ascii=False, indent=2)
            else:
                 # Fallback to saving raw result if parsing failed
                f.write(result)
            
        # Rate limit handling (free tier usually has small RPM)
        print("Waiting 35s for rate limit...")
        if progress_callback: progress_callback(f"Waiting 35s for Gemini API quota...", percent)
        time.sleep(35)
        
    doc.close()

def main():
    setup_directories()
    
    if not os.path.exists(TARGET_DIR):
        print(f"Target directory not found: {TARGET_DIR}")
        return
        
    pdf_files = [f for f in os.listdir(TARGET_DIR) if f.lower().endswith('.pdf')]
    print(f"Found {len(pdf_files)} PDF files in {TARGET_DIR}")
    
    # Limit to 10 exams as requested
    pdf_files = pdf_files[:10]
    print(f"Limiting processing to 10 PDF files as requested.")
    
    for i, pdf_file in enumerate(pdf_files):
        pdf_path = os.path.join(TARGET_DIR, pdf_file)
        print(f"\n[Exam {i+1}/{len(pdf_files)}]")
        process_pdf(pdf_path)

if __name__ == "__main__":
    main()
