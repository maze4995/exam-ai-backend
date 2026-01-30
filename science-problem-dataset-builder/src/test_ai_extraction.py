import pdfplumber
import os
import json
import re
from ultralytics import YOLO
import numpy as np

# Reuse existing schema/parser
try:
    from src.schema import ScienceProblem, ProblemStructure
    from src.parser import StructureParser
except ImportError:
    from schema import ScienceProblem, ProblemStructure
    from parser import StructureParser

# Config
PDF_PATH = os.path.join(BASE_DIR, "input", "완자 기출픽_통합과학_본책.pdf")
BASE_DIR = r"C:\Users\rlgus\.gemini\antigravity\scratch\science-problem-dataset-builder"
MODEL_PATH = os.path.join(BASE_DIR, "models/best.pt")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images_ai_test")
JSON_PATH = os.path.join(OUTPUT_DIR, "dataset_ai_test.json")
PROBLEM_START_RE = re.compile(r'^(\d{1,4})\s+')

class AIProblemExtractor:
    def __init__(self, pdf_path, model_path):
        self.pdf_path = pdf_path
        self.model = YOLO(model_path)
        self.parser = StructureParser()
        os.makedirs(IMAGE_DIR, exist_ok=True)
        
    def run(self, start_page=61, end_page=70):
        print(f"Starting AI Extraction on pages {start_page}-{end_page}...")
        results = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for i in range(start_page - 1, end_page):
                page = pdf.pages[i]
                page_num = i + 1
                # 0. Check Page Type (Filter Concept Pages)
                text_preview = page.extract_text()
                if not text_preview: text_preview = ""
                
                # Normalize (remove spaces)
                text_norm = text_preview.replace(" ", "")
                # if page_num == 56:
                #      print(f"DEBUG P56 Text: {text_norm[:200]}")
                
                # Keywords for Concept Pages (to exclude)
                # Specific keywords found on Concept text
                skip_keywords = ["핵심정리", "빈출자료", "기출Tip", "자료1"] 
                
                if any(k in text_norm for k in skip_keywords):
                    print(f"Skipping Page {page_num} (Concept Page detected)")
                    continue
                
                print(f"Processing Page {page_num}...")
                
                # 1. AI Inference
                # Convert to image for YOLO
                im_obj = page.to_image(resolution=300)
                im_pil = im_obj.original.convert("RGB")
                
                # Predict
                yolo_results = self.model.predict(im_pil, verbose=False)[0]
                
                # Calculate Scale Factor (Image Pixels -> PDF Points)
                # PDF Page is in points (e.g. 595x842)
                # Image is in pixels (e.g. 2480x3508 at 300dpi)
                scale_x = page.width / im_pil.width
                scale_y = page.height / im_pil.height
                
                # 2. Process Boxes
                boxes = []
                for box in yolo_results.boxes:
                    x1_px, y1_px, x2_px, y2_px = box.xyxy[0].tolist()
                    
                    # Convert to PDF Coords
                    x1 = x1_px * scale_x
                    y1 = y1_px * scale_y
                    x2 = x2_px * scale_x
                    y2 = y2_px * scale_y
                    
                    conf = box.conf[0].item()
                    # Filter low confidence?
                    if conf < 0.5: continue
                    boxes.append((x1, y1, x2, y2, conf))
                    
                # 3. Sort Boxes (Left Col vs Right Col, then Top-Down)
                width = page.width
                mid_x = width / 2
                
                left_col = []
                right_col = []
                
                for b in boxes:
                    bx1, by1, bx2, by2, _ = b
                    center_x = (bx1 + bx2) / 2
                    if center_x < mid_x:
                        left_col.append(b)
                    else:
                        right_col.append(b)
                        
                # Sort by Y1
                left_col.sort(key=lambda x: x[1])
                right_col.sort(key=lambda x: x[1])
                
                sorted_boxes = left_col + right_col
                
                # 4. Extract Content per Box
                for b_idx, box in enumerate(sorted_boxes):
                    x1, y1, x2, y2, conf = box
                    
                    # Crop PDF
                    # pdfplumber uses (x0, top, x1, bottom)
                    # We might need to clamp to page bbox
                    pg_bbox = page.bbox
                    x1 = max(pg_bbox[0], x1)
                    y1 = max(pg_bbox[1], y1)
                    x2 = min(pg_bbox[2], x2)
                    y2 = min(pg_bbox[3], y2)
                    
                    crop = page.crop((x1, y1, x2, y2))
                    
                    # Extract Text
                    text_content = crop.extract_text()
                    if not text_content: text_content = ""
                    
                    # Parse ID
                    # Try to find ID in the first few characters
                    p_id = "unk"
                    match = PROBLEM_START_RE.match(text_content.strip())
                    if match:
                        p_id = match.group(1)
                    else:
                        # Fallback: sometimes ID is above? or OCR issue. 
                        # For now, unique ID based on page
                        p_id = f"{page_num}_{b_idx+1}"
                        
                    # Save Image
                    img_filename = f"ai_p{page_num}_{p_id}.png"
                    img_path = os.path.join(IMAGE_DIR, img_filename)
                    try:
                        im_crop = crop.to_image(resolution=300)
                        im_crop.save(img_path)
                    except Exception as e:
                        print(f"Err saving img {p_id}: {e}")
                        img_filename = None
                        
                    # Structure Parse
                    parsed = self.parser.parse(p_id, page_num, text_content)
                    if img_filename:
                        parsed.content.visuals.append(img_filename)
                        
                    results.append(parsed)
                    
        # Save JSON
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            data = [p.model_dump() for p in results]
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"Done. Extracted {len(results)} problems to {JSON_PATH}")

if __name__ == "__main__":
    extractor = AIProblemExtractor(PDF_PATH, MODEL_PATH)
    extractor.run(56, 65)
