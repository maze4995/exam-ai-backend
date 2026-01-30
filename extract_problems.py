
import fitz  # PyMuPDF
import cv2
import numpy as np
import os
import google.generativeai as genai
from PIL import Image

# --- Configuration ---
INPUT_FILE = r"C:\Users\rlgus\Desktop\Hyun&Hyun\문제집 - 과학\내신\시험지 모음\1학기 기말고사\2025 고1 통합과학 1학기 기말고사 계남고.pdf"
OUTPUT_DIR = "output_extraction"
API_KEY = "AIzaSyALdvzQFlAU9L11iEX9bA6VPK3ovHKh8Xg"

# Configure Gemini
genai.configure(api_key=API_KEY)

def setup_directories():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

def pdf_to_images(pdf_path):
    print(f"Opening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    images = []
    
    # Process first 3 pages for prototype
    for page_num in range(min(3, len(doc))):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=300) # High DPI for better OCR
        img_path = os.path.join(OUTPUT_DIR, f"page_{page_num+1}.png")
        pix.save(img_path)
        images.append(img_path)
        print(f"Saved page {page_num+1} to {img_path}")
        
    return images

def remove_red_handwriting(image_path):
    print(f"Processing image for red handwriting removal: {image_path}")
    # Read image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error reading image: {image_path}")
        return None
    
    # Convert to HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Define range for red color
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])
    
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = mask1 + mask2
    
    # Inpaint
    clean_img = cv2.inpaint(img, mask, 3, cv2.INPAINT_NS)
    
    base_name = os.path.basename(image_path)
    clean_path = os.path.join(OUTPUT_DIR, f"clean_{base_name}")
    cv2.imwrite(clean_path, clean_img)
    return clean_path

def extract_content_with_vlm(image_path):
    print(f"Sending {image_path} to Gemini VLM...")
    
    try:
        pil_img = Image.open(image_path)
        # Using gemini-1.5-pro or similar might be better for coordinate accuracy, 
        # but let's try flash-latest first as requested.
        model = genai.GenerativeModel('gemini-1.5-flash') 
        # Note: 1.5-flash is generally good at spatial reasoning. 
        # Let's use the model that worked: gemini-flash-latest or gemini-2.0-flash (if quota allows).
        # User had success with gemini-flash-latest.
        model = genai.GenerativeModel('gemini-flash-latest')

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

from utils import strict_json_parse

def crop_and_save_problems(image_path, extraction_result):
    problems = strict_json_parse(extraction_result)
        
    if not problems:
        print(f"Failed to parse JSON for {image_path}")
        return

    img = Image.open(image_path)
    width, height = img.size
    
    base_name = os.path.basename(image_path).replace(".png", "")
    crop_dir = os.path.join(OUTPUT_DIR, f"crops_{base_name}")
    if not os.path.exists(crop_dir):
        os.makedirs(crop_dir)
        
    for prob in problems:
        if "box_2d" not in prob:
            continue
            
        q_num = prob.get("question_number", "unknown")
        ymin, xmin, ymax, xmax = prob["box_2d"]
        
        # Convert 1000-scale coordinates to pixels
        left = (xmin / 1000) * width
        top = (ymin / 1000) * height
        right = (xmax / 1000) * width
        bottom = (ymax / 1000) * height
        
        # Add padding (optional)
        padding = 10
        left = max(0, left - padding)
        top = max(0, top - padding)
        right = min(width, right + padding)
        bottom = min(height, bottom + padding)
        
        crop = img.crop((left, top, right, bottom))
        crop_path = os.path.join(crop_dir, f"q_{q_num}.png")
        crop.save(crop_path)
        print(f"Saved crop: {crop_path}")

def main():
    setup_directories()
    
    # Step 1: Check if images exist
    image_paths = [os.path.join(OUTPUT_DIR, f"page_{i+1}.png") for i in range(3)]
    if not all(os.path.exists(p) for p in image_paths):
         image_paths = pdf_to_images(INPUT_FILE)
    else:
        print("Using existing images from output_extraction/")

    # Step 2: VLM Extraction & Cropping
    import time
    print("\n--- Starting AI Extraction with Cropping ---")
    
    # Only process Page 2 and 3 because Page 1 is cover
    target_pages = image_paths[1:] 
    
    for img_path in target_pages:
        result = extract_content_with_vlm(img_path)
        
        # Save raw text result
        base_name = os.path.basename(img_path)
        txt_path = os.path.join(OUTPUT_DIR, f"extracted_v2_{base_name}.json")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Saved extraction result to {txt_path}")
        
        # Crop images
        crop_and_save_problems(img_path, result)
        
        print("Waiting 35 seconds to respect API rate limits...")
        time.sleep(35)
        
    print("\n--- Phase 2 Complete ---")

if __name__ == "__main__":
    main()
