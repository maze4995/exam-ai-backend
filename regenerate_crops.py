
import os
import json
import re
from PIL import Image

from utils import strict_json_parse

def regenerate_crops_for_exam(exam_dir):
    print(f"Regenerating crops for: {os.path.basename(exam_dir)}")
    
    json_files = [f for f in os.listdir(exam_dir) if f.startswith("extracted_") and f.endswith(".json")]
    
    for jf in json_files:
        base_img_name = jf.replace("extracted_", "").replace(".json", "")
        img_path = os.path.join(exam_dir, base_img_name)
        
        if not os.path.exists(img_path):
            continue
            
        # Load JSON (potentially edited by user)
        with open(os.path.join(exam_dir, jf), "r", encoding="utf-8") as f:
            content = f.read()
            
        data = strict_json_parse(content)
        if not data:
            print(f"Skipping {jf} (Parse Error)")
            continue
            
        img = Image.open(img_path)
        width, height = img.size
        
        # Crop folder
        page_bs = base_img_name.replace(".png", "") # page_1
        # Handle cases where extension is part of base_img_name or not
        if page_bs.endswith(".png"): page_bs = page_bs[:-4]
        
        crop_dir = os.path.join(exam_dir, f"crops_{page_bs}")
        if not os.path.exists(crop_dir):
            os.makedirs(crop_dir)
            
        for prob in data:
            if "box_2d" not in prob:
                continue
                
            q_num = prob.get("question_number", "unknown")
            ymin, xmin, ymax, xmax = prob["box_2d"]
            
            # Padding
            pad = 10
            left = max(0, (xmin / 1000) * width - pad)
            top = max(0, (ymin / 1000) * height - pad)
            right = min(width, (xmax / 1000) * width + pad)
            bottom = min(height, (ymax / 1000) * height + pad)
            
            try:
                crop = img.crop((left, top, right, bottom))
                crop_path = os.path.join(crop_dir, f"q_{q_num}.png")
                crop.save(crop_path)
                print(f"  Regenerated: q_{q_num}.png")
            except Exception as e:
                print(f"  Error {q_num}: {e}")

def main():
    if not os.path.exists(BASE_DIR):
        print("Output directory not found.")
        return

    # Regenerate for ALL folders
    for item in os.listdir(BASE_DIR):
        item_path = os.path.join(BASE_DIR, item)
        if os.path.isdir(item_path):
            regenerate_crops_for_exam(item_path)

if __name__ == "__main__":
    main()
