import pdfplumber
import os
import re

PDF_PATH = r"C:\Users\rlgus\.gemini\antigravity\scratch\science-problem-recommender\완자 기출픽_통합과학_본책.pdf"
OUTPUT_DIR = r"C:\Users\rlgus\.gemini\antigravity\scratch\science-problem-dataset-builder\output_debug"
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
os.makedirs(IMAGE_DIR, exist_ok=True)

def debug_problem_210():
    print("--- Debugging Problem 210 Extraction ---")
    
    with pdfplumber.open(PDF_PATH) as pdf:
        page = pdf.pages[53] # Page 54
        
        # Clamp Box Logic (Switch to LEFT COLUMN)
        p_bbox = page.bbox
        mid_x = (p_bbox[0] + p_bbox[2]) / 2
        
        # Left Column
        c_x0 = p_bbox[0]
        c_top = p_bbox[1]
        c_x1 = mid_x
        c_bottom = p_bbox[3]
        col_bbox = (c_x0, c_top, c_x1, c_bottom)
        
        print(f"BBox: {col_bbox}")
        crop = page.crop(col_bbox)
        
        # Extract Words & Reconstruct Lines
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
        
        # Absolute Lines
        abs_lines = []
        col_y_offset = col_bbox[1]
        
        print("\n[Extracted Lines RE-CHECK]")
        for i, l in enumerate(lines):
            abs_text = l["text"]
            abs_top = l["top"] + col_y_offset
            print(f"[{i}] {abs_text}")
            
            abs_lines.append({
                "text": l["text"],
                "top": l["top"] + col_y_offset,
                "bottom": l["bottom"] + col_y_offset
            })

        # Locate 210
        start_idx = -1
        end_idx = -1
        
        print("\n[Scanning Lines]")
        for i, line in enumerate(abs_lines):
            # Relaxed check
            if "210" in line['text'][:5]:
                start_idx = i
                print(f"-> START 210 found at line {i}: {line['text']}")
            
            if start_idx != -1 and i > start_idx and "211" in line['text'][:5]:
                end_idx = i
                print(f"-> END 211 found at line {i}: {line['text']}")
                break
        
        if start_idx == -1:
            print("FAILED: Could not find Problem 210.")
            return
            
        if end_idx == -1: end_idx = len(abs_lines)

        y_start_text = abs_lines[start_idx]['top']
        y_end_text = abs_lines[end_idx]['top'] - 5 if end_idx < len(abs_lines) else abs_lines[-1]['bottom'] + 50
        
        print(f"Text Range: Y={y_start_text:.2f} to Y={y_end_text:.2f}")

        # Get Graphics
        page_graphics = []
        for obj in page.rects + page.lines + page.curves + page.images:
             if 'top' in obj: page_graphics.append(obj)

        # Include Graphics
        associated_graphics = []
        col_mid_x = (col_bbox[0] + col_bbox[2]) / 2 # Mid of this column
        
        # 210 is in Right Column.
        # So we should look for graphics whose centers are roughly in Right Column range.
        
        for g in page_graphics:
            g_cy = (g['top'] + g['bottom']) / 2
            g_cx = (g['x0'] + g['x1']) / 2
            
            # Vertical Overlap (Relaxed)
            if y_start_text - 10 < g['bottom'] and g['top'] < y_end_text + 10:
                 # Column Check
                 # Right column is roughly 333 to 609
                 if col_bbox[0] - 50 < g_cx < col_bbox[2] + 50:
                     associated_graphics.append(g)

        # Calculate Crop Box
        img_x0 = col_bbox[0]
        img_x1 = col_bbox[2]
        img_y0 = y_start_text
        img_y1 = y_end_text

        if associated_graphics:
            g_x0 = min([g['x0'] for g in associated_graphics])
            g_x1 = max([g['x1'] for g in associated_graphics])
            g_y0 = min([g['top'] for g in associated_graphics])
            g_y1 = max([g['bottom'] for g in associated_graphics])
            
            img_x0 = min(img_x0, g_x0)
            img_x1 = max(img_x1, g_x1)
            img_y0 = min(img_y0, g_y0)
            img_y1 = max(img_y1, g_y1)
        
        # Clamp to Page
        img_x0 = max(p_bbox[0], img_x0)
        img_x1 = min(p_bbox[2], img_x1)
        img_y0 = max(p_bbox[1], img_y0)
        img_y1 = min(p_bbox[3], img_y1)
        
        print(f"Final Crop: ({img_x0:.2f}, {img_y0:.2f}, {img_x1:.2f}, {img_y1:.2f})")
        
        # Save
        try:
            p_crop = page.crop((img_x0, img_y0, img_x1, img_y1))
            im = p_crop.to_image(resolution=300)
            img_path = os.path.join(IMAGE_DIR, "debug_p210.png")
            im.save(img_path)
            print(f"Saved: {img_path}")
        except Exception as e:
            print(f"Error saving image: {e}")

if __name__ == "__main__":
    debug_problem_210()
