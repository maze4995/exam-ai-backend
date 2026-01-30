import pdfplumber
import os
import cv2
import numpy as np
from src.converter import PDFConverter
from src.parser import StructureParser
import shutil

# Configuration
PDF_PATH = r"C:\Users\rlgus\.gemini\antigravity\scratch\science-problem-recommender\완자 기출픽_통합과학_본책.pdf"
DATASET_DIR = r"C:\Users\rlgus\.gemini\antigravity\scratch\science-problem-dataset-builder\training_data"
IMAGES_DIR = os.path.join(DATASET_DIR, "images")
LABELS_DIR = os.path.join(DATASET_DIR, "labels")

# Classes
CLASS_MAPPING = {
    "problem": 0
}

def setup_dirs():
    if os.path.exists(DATASET_DIR):
        shutil.rmtree(DATASET_DIR)
    os.makedirs(IMAGES_DIR)
    os.makedirs(LABELS_DIR)
    
    # Create classes.txt
    with open(os.path.join(DATASET_DIR, "classes.txt"), "w") as f:
        for k in CLASS_MAPPING:
            f.write(f"{k}\n")

def convert_bbox_to_yolo(size, box):
    # box: (xmin, ymin, xmax, ymax)
    dw = 1. / size[0]
    dh = 1. / size[1]
    x = (box[0] + box[2]) / 2.0
    y = (box[1] + box[3]) / 2.0
    w = box[2] - box[0]
    h = box[3] - box[1]
    x = x * dw
    w = w * dw
    y = y * dh
    h = h * dh
    return (x, y, w, h)

class DataGenerator(PDFConverter):
    def __init__(self):
        super().__init__(PDF_PATH)
        # We don't need parser actually, just bbox logic
        
    def generate_yolo_data(self, start_page=50, end_page=60):
        setup_dirs()
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for i in range(start_page - 1, end_page):
                page = pdf.pages[i]
                page_num = i + 1
                print(f"Processing Page {page_num}...")
                
                # 1. Save Page Image
                img_filename = f"page_{page_num}.jpg"
                img_path = os.path.join(IMAGES_DIR, img_filename)
                
                # High res rendering
                im_obj = page.to_image(resolution=300)
                im = im_obj.original.convert('RGB')
                im.save(img_path, format="JPEG")
                
                # Page Dimensions
                w_page = page.width
                h_page = page.height
                
                # Heuristic Problem Detection
                p_bbox = page.bbox
                mid_x = (p_bbox[0] + p_bbox[2]) / 2
                
                cols = [
                    (p_bbox[0], p_bbox[1], mid_x, p_bbox[3]),      # Left
                    (mid_x, p_bbox[1], p_bbox[2], p_bbox[3])       # Right
                ]
                
                all_bboxes = []
                
                for col_idx, col_bbox in enumerate(cols):
                    # Clamp just in case
                    c_x0 = max(p_bbox[0], col_bbox[0])
                    c_top = max(p_bbox[1], col_bbox[1])
                    c_x1 = min(p_bbox[2], col_bbox[2])
                    c_bottom = min(p_bbox[3], col_bbox[3])
                    
                    if c_x1 <= c_x0 or c_bottom <= c_top: continue
                    
                    crop_box = (c_x0, c_top, c_x1, c_bottom)
                    crop = page.crop(crop_box)
                    words = crop.extract_words(keep_blank_chars=True, x_tolerance=3, y_tolerance=3)
                    
                    # Group Lines
                    lines = []
                    current_line_words = []
                    current_top = -1
                    for w in words:
                        if current_top == -1:
                            current_top = w['top']
                            current_line_words = [w]
                        else:
                            if abs(w['top'] - current_top) < 5:
                                current_line_words.append(w)
                            else:
                                text = " ".join([wd['text'] for wd in current_line_words])
                                l_bottom = max([wd['bottom'] for wd in current_line_words])
                                lines.append({"text": text, "top": current_top, "bottom": l_bottom})
                                current_top = w['top']
                                current_line_words = [w]
                    if current_line_words:
                         text = " ".join([wd['text'] for wd in current_line_words])
                         l_bottom = max([wd['bottom'] for wd in current_line_words])
                         lines.append({"text": text, "top": current_top, "bottom": l_bottom})
                    
                    lines.sort(key=lambda x: x['top'])
                    
                    # Absolute Lines
                    abs_lines = []
                    col_y_offset = col_bbox[1]
                    for l in lines:
                        abs_lines.append({
                            "text": l["text"],
                            "top": l["top"] + col_y_offset,
                            "bottom": l["bottom"] + col_y_offset
                        })
                        
                    # Find Starts
                    import re
                    PROBLEM_START_RE = re.compile(r'^(\d{1,4})')
                    
                    problem_indices = []
                    for idx, line in enumerate(abs_lines):
                        if PROBLEM_START_RE.match(line["text"]):
                            problem_indices.append(idx)
                            
                    # Calc BBoxes
                    for k, start_idx in enumerate(problem_indices):
                        y_start = abs_lines[start_idx]['top']
                        if k + 1 < len(problem_indices):
                            y_end = abs_lines[problem_indices[k+1]]['top'] - 5
                        else:
                            y_end = abs_lines[-1]['bottom'] + 50
                            
                        # Box (Left/Right Col)
                        # Expand slightly for creating Label
                        b_x0 = col_bbox[0]
                        b_x1 = col_bbox[2]
                        b_y0 = y_start
                        b_y1 = y_end
                        
                        # Clamp
                        b_x0 = max(0, b_x0)
                        b_x1 = min(w_page, b_x1)
                        b_y0 = max(0, b_y0)
                        b_y1 = min(h_page, b_y1)
                        
                        if b_y1 > b_y0:
                            all_bboxes.append((b_x0, b_y0, b_x1, b_y1))

                # 3. Write Label File
                label_filename = f"page_{page_num}.txt"
                label_path = os.path.join(LABELS_DIR, label_filename)
                
                with open(label_path, "w") as f:
                    for box in all_bboxes:
                        # Convert to YOLO
                        yolo_box = convert_bbox_to_yolo((w_page, h_page), box)
                        # Class 0 = Problem
                        f.write(f"0 {yolo_box[0]:.6f} {yolo_box[1]:.6f} {yolo_box[2]:.6f} {yolo_box[3]:.6f}\n")

if __name__ == "__main__":
    gen = DataGenerator()
    # Generate for pages 50-60 (10 pages for init)
    print("Generating training data for pages 50-60...")
    gen.generate_yolo_data(50, 60)
    print(f"Data generation complete. Check {DATASET_DIR}")
