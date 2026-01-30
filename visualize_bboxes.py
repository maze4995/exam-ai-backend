
import os
import cv2
import json
import re
import numpy as np

from utils import strict_json_parse

def draw_bboxes(exam_dir):
    print(f"Visualizing: {os.path.basename(exam_dir)}")
    
    # Find all json files
    json_files = [f for f in os.listdir(exam_dir) if f.startswith("extracted_") and f.endswith(".json")]
    
    for jf in json_files:
        # Correspond image: extracted_page_2.png.json -> page_2.png
        # Format might be extracted_{img_name}.json
        base_img_name = jf.replace("extracted_", "").replace(".json", "")
        img_path = os.path.join(exam_dir, base_img_name)
        
        if not os.path.exists(img_path):
            print(f"Image not found: {img_path}")
            continue
            
        # Load JSON
        with open(os.path.join(exam_dir, jf), "r", encoding="utf-8") as f:
            content = f.read()
            
        data = strict_json_parse(content)
        if not data:
            print(f"JSON parse info for {jf}")
            continue
            
        # Load Image
        img = cv2.imread(img_path)
        if img is None:
            continue
            
        h, w, _ = img.shape
        
        # Draw
        for item in data:
            if "box_2d" not in item:
                continue
            
            q_num = item.get("question_number", "?")
            ymin, xmin, ymax, xmax = item["box_2d"]
            
            x1 = int((xmin / 1000) * w)
            y1 = int((ymin / 1000) * h)
            x2 = int((xmax / 1000) * w)
            y2 = int((ymax / 1000) * h)
            
            # Draw rectangle (Blue)
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
            # Put label
            cv2.putText(img, f"Q{q_num}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 0), 2)
            
        # Save debug image
        debug_path = os.path.join(exam_dir, f"visualized_{base_img_name}")
        cv2.imwrite(debug_path, img)
        print(f"Attributes drawn to {debug_path}")

def main():
    if not os.path.exists(BASE_DIR):
        print(f"Directory {BASE_DIR} not found.")
        return

    # Iterate all exam folders
    for item in os.listdir(BASE_DIR):
        item_path = os.path.join(BASE_DIR, item)
        if os.path.isdir(item_path):
            draw_bboxes(item_path)

if __name__ == "__main__":
    main()
