import pdfplumber
import re
import os
import json
from typing import List, Dict, Optional

# Import our schema and parser
try:
    from .schema import ScienceProblem, ProblemStructure
    from .parser import StructureParser
except ImportError:
    from schema import ScienceProblem, ProblemStructure
    from parser import StructureParser

PDF_PATH = r"C:\Users\rlgus\.gemini\antigravity\scratch\science-problem-recommender\완자 기출픽_통합과학_본책.pdf"
OUTPUT_DIR = r"C:\Users\rlgus\.gemini\antigravity\scratch\science-problem-dataset-builder\output"
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
JSON_PATH = os.path.join(OUTPUT_DIR, "dataset.json")

# Regex to find problem start (Number at start of line)
PROBLEM_START_RE = re.compile(r'^(\d{1,4})\s+')

class PDFConverter:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.parser = StructureParser()
        os.makedirs(IMAGE_DIR, exist_ok=True)

    def run(self, start_page: int = 1, end_page: int = None):
        problems = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            total_pages = len(pdf.pages)
            if end_page is None: end_page = total_pages
            
            print(f"Processing pages {start_page} to {end_page}...")
            
            # Carry over problem if it spans across pages? 
            # (Simplification: Assuming problems don't break across pages/columns for MVP)
            
            for i in range(start_page - 1, end_page):
                page = pdf.pages[i]
                page_num = i + 1
                
                # Split Columns
                width = page.width
                height = page.height
                x0, top, x1, bottom = page.bbox
                mid_x = (x0 + x1) / 2
                
                # Define column bboxes
                cols = [
                    {"bbox": (x0, top, mid_x, bottom), "name": "left"},
                    {"bbox": (mid_x, top, x1, bottom), "name": "right"}
                ]
                
                for col in cols:
                    crop = page.crop(col["bbox"])
                    extracted = self.process_column(crop, page, page_num, col["bbox"])
                    problems.extend(extracted)
                    
        # Save Metadata
        with open(JSON_PATH, 'w', encoding='utf-8') as f:
            # Pydantic dump
            data = [p.model_dump() for p in problems]
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"Conversion Complete. Saved {len(problems)} problems to {JSON_PATH}")

    def process_column(self, crop, original_page, page_num, col_bbox) -> List[ScienceProblem]:
        # 1. Extract Text Lines (Same as before)
        words = crop.extract_words(keep_blank_chars=True, x_tolerance=3, y_tolerance=3)
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
                    text = " ".join([word['text'] for word in current_line_words])
                    l_bottom = max([word['bottom'] for word in current_line_words])
                    lines.append({"text": text, "top": current_top, "bottom": l_bottom})
                    current_top = w['top']
                    current_line_words = [w]
        if current_line_words:
             text = " ".join([word['text'] for word in current_line_words])
             l_bottom = max([word['bottom'] for word in current_line_words])
             lines.append({"text": text, "top": current_top, "bottom": l_bottom})
        
        lines.sort(key=lambda x: x['top'])

        # 2. Get All Graphical Objects from Original Page
        # We need absolute coordinates to match with text
        # (Note: crop.extract_words returns absolute coords relative to original page top-left if using pdfplumber correctly on crop? 
        # Actually pdfplumber crop resets coords. But let's assume valid flow. 
        # Wait, if crop resets coords, then lines['top'] are relative to crop.
        # col_bbox[1] is crop top. So Absolute Top = line['top'] + col_bbox[1].
        
        # Let's re-verify coordinate system. 
        # In previous attempts, we added col_bbox[1] to y_start. This implies lines['top'] is relative.
        # So we must convert all text lines to Absolute Page Coordinates.
        
        abs_lines = []
        col_x_offset = col_bbox[0]
        col_y_offset = col_bbox[1]
        
        for l in lines:
            abs_lines.append({
                "text": l["text"],
                "top": l["top"] + col_y_offset,
                "bottom": l["bottom"] + col_y_offset
            })
            
        # Get Page Graphics
        page_graphics = []
        for obj in original_page.rects + original_page.lines + original_page.curves + original_page.images:
            # Standardize keys
            g_top = obj.get('top') or obj.get('y0') # y0 might be bottom in PDF raw, but pdfplumber normalizes usually? 
            # pdfplumber objects usually have 'top', 'bottom', 'x0', 'x1'
            if 'top' not in obj: continue
            
            page_graphics.append(obj)

        # 3. Identify Problems
        problem_indices = []
        for idx, line in enumerate(abs_lines):
            match = PROBLEM_START_RE.match(line["text"])
            if match:
                problem_indices.append(idx)
        
        extracted_problems = []
        
        col_mid_x = (col_bbox[0] + col_bbox[2]) / 2
        
        for i, start_idx in enumerate(problem_indices):
            # Define Text Y-Range
            y_start_text = abs_lines[start_idx]['top']
            
            if i + 1 < len(problem_indices):
                y_end_text = abs_lines[problem_indices[i+1]]['top'] - 5
            else:
                y_end_text = abs_lines[-1]['bottom'] + 50 # padding for footer
            
            # Determine Full Bounding Box (Text + Graphics)
            # Find graphics that vertically overlap [y_start_text, y_end_text]
            # AND belong to this column side (Center X relative to mid_x)
            
            associated_graphics = []
            for g in page_graphics:
                g_cy = (g['top'] + g['bottom']) / 2
                g_cx = (g['x0'] + g['x1']) / 2
                
                # Vertical Overlap or Proximity
                # Relaxed condition: If graphic is within the Y-range
                if y_start_text - 10 < g['bottom'] and g['top'] < y_end_text + 10:
                    # Horizontal ownership: Left or Right column?
                    # If processing Left Column, g_cx should be < col_mid_x
                    is_left_col = col_bbox[0] <= col_bbox[2] <= col_mid_x + 50 # check bbox logic?
                    # col_bbox is passed for the specific column we are processing.
                    # Left Col: x0=0, x1=333. Right Col: x0=333, x1=666.
                    
                    my_col_center = (col_bbox[0] + col_bbox[2]) / 2
                    
                    # Heuristic: Graphic belongs to this column if its center is closer to this column's center?
                    # Or simply containment.
                    if col_bbox[0] - 20 < g_cx < col_bbox[2] + 20:
                        associated_graphics.append(g)
            
            # Calculate Union BBox
            # Start with Text Boundaries
            # We assume text width is roughly the column width for safety, 
            # but visual crop should depend on content.
            
            min_x = col_bbox[0]
            max_x = col_bbox[2]
            # Refine max_x/min_x based on graphics?
            # Actually, standardizing on column width is safer for text, but for IMAGE we want full graphic.
            
            img_x0 = col_bbox[0]
            img_x1 = col_bbox[2]
            img_y0 = y_start_text
            img_y1 = y_end_text
            
            if associated_graphics:
                g_x0 = min([g['x0'] for g in associated_graphics])
                g_x1 = max([g['x1'] for g in associated_graphics])
                g_y0 = min([g['top'] for g in associated_graphics])
                g_y1 = max([g['bottom'] for g in associated_graphics])
                
                # Expand crop to include graphics
                img_x0 = min(img_x0, g_x0)
                img_x1 = max(img_x1, g_x1)
                img_y0 = min(img_y0, g_y0)
                img_y1 = max(img_y1, g_y1)

            # Safety Clamps (Don't go off page)
            page_bbox = original_page.bbox # (x0, top, x1, bottom)
            img_x0 = max(page_bbox[0], img_x0)
            img_x1 = min(page_bbox[2], img_x1)
            img_y0 = max(page_bbox[1], img_y0)
            img_y1 = min(page_bbox[3], img_y1)
            
            # Extract Text Info
            prob_lines = abs_lines[start_idx : problem_indices[i+1] if i+1 < len(problem_indices) else len(abs_lines)]
            full_text = "\n".join([l["text"] for l in prob_lines])
            p_id_match = PROBLEM_START_RE.match(prob_lines[0]['text'])
            p_id = p_id_match.group(1) if p_id_match else "unk"

            # Crop & Save
            img_filename = f"p{page_num}_{p_id}.png"
            img_path = os.path.join(IMAGE_DIR, img_filename)
            
            try:
                # Crop Union Box
                p_crop = original_page.crop((img_x0, img_y0, img_x1, img_y1))
                im = p_crop.to_image(resolution=300)
                im.save(img_path)
            except Exception as e:
                print(f"Image Error {p_id}: {e}")
                img_path = None
            
            # Parse
            parsed_prob = self.parser.parse(p_id, page_num, full_text)
            if img_path: parsed_prob.content.visuals.append(img_filename)
            extracted_problems.append(parsed_prob)
            
        return extracted_problems

if __name__ == "__main__":
    # Test on pages 10-15
    converter = PDFConverter(PDF_PATH)
    converter.run(start_page=50, end_page=55)
