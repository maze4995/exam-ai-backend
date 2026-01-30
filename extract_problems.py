
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
API_KEY = "AIzaSyALdvzQFlAU9L11iEX9bA6VPK3ovHKh8Xg"

# Configure Gemini
genai.configure(api_key=API_KEY)

def setup_directories():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

def extract_content_with_vlm(image_path):
    # print(f"Sending {image_path} to Gemini VLM...")
    try:
        pil_img = Image.open(image_path)
        model = genai.GenerativeModel('gemini-flash-latest') 
        # Using gemini-flash-latest might be more stable in some regions
        # model = genai.GenerativeModel('gemini-flash-latest')

        prompt = """
        이 이미지에서 각 '시험 문제'의 영역을 찾아서 텍스트와 좌표를 추출해줘.
        
        [지시사항]
        1. 이미지 내의 모든 문제를 감지해. 문제 번호, 지문, 보기, 그림을 모두 포함하는 전체 영역(Bounding Box)을 잡아야 해.
        2. 좌표는 [ymin, xmin, ymax, xmax] 형식으로, 0 에서 1000 사이의 정수 값(normalized coordinates * 1000)으로 반환해.
        3. 필기(손글씨, 채점 마크)는 무시하고 인쇄된 텍스트만 추출해.
        4. 수식은 LaTeX로 변환해.
        5. 출력은 다음 JSON 형식 배열이어야 해:
        [
          {
            "question_number": "1",
            "box_2d": [ymin, xmin, ymax, xmax],
            "question_text": "...",
            "choices": ["1. ...", "2. ..."]
          }
        ]
        """
        
        response = model.generate_content([prompt, pil_img])
        return response.text
    except Exception as e:
        return f"Error during VLM extraction: {e}"

def crop_and_save_exam_problems(image_path, extraction_result, output_base):
    problems = strict_json_parse(extraction_result)
    if not problems:
        print(f"No problems parsed for {image_path}")
        return

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
            
        q_num = prob.get("question_number", "unknown")
        ymin, xmin, ymax, xmax = prob["box_2d"]
        
        # Convert 1000-scale to pixels with some padding
        left = max(0, (xmin / 1000) * width - 10)
        top = max(0, (ymin / 1000) * height - 10)
        right = min(width, (xmax / 1000) * width + 10)
        bottom = min(height, (ymax / 1000) * height + 10)
        
        try:
            crop = img.crop((left, top, right, bottom))
            crop_path = os.path.join(crop_dir, f"q_{q_num}.png")
            crop.save(crop_path)
        except Exception as e:
            print(f"Crop error for Q{q_num}: {e}")

def process_pdf(pdf_path):
    print(f"\n--- Processing: {os.path.basename(pdf_path)} ---")
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    exam_output_dir = os.path.join(OUTPUT_DIR, pdf_name)
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
    
    import time
    # Skip cover page if it has many pages
    start_index = 1 if len(image_paths) > 2 else 0
    
    for i in range(start_index, len(image_paths)):
        img_path = image_paths[i]
        json_filename = f"extracted_{os.path.basename(img_path)}.json"
        json_path = os.path.join(exam_output_dir, json_filename)
        
        if os.path.exists(json_path):
            # Check if crops also exist? Assume yes for now or re-run if json exists
            # To be thorough, we could re-run cropping if the crops folder is missing.
            print(f"Skipping extraction for {os.path.basename(img_path)} (JSON exists)")
            continue
            
        print(f"Processing Page {i+1}/{len(image_paths)}...")
        result = extract_content_with_vlm(img_path)
        
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(result)
            
        crop_and_save_exam_problems(img_path, result, exam_output_dir)
        
        # Rate limit handling (free tier usually has small RPM)
        print("Waiting 35s for rate limit...")
        time.sleep(35)
        
    doc.close()

def main():
    setup_directories()
    
    if not os.path.exists(TARGET_DIR):
        print(f"Target directory not found: {TARGET_DIR}")
        return
        
    pdf_files = [f for f in os.listdir(TARGET_DIR) if f.lower().endswith('.pdf')]
    print(f"Found {len(pdf_files)} PDF files in {TARGET_DIR}")
    
    for i, pdf_file in enumerate(pdf_files):
        pdf_path = os.path.join(TARGET_DIR, pdf_file)
        print(f"\n[Exam {i+1}/{len(pdf_files)}]")
        process_pdf(pdf_path)

if __name__ == "__main__":
    main()
