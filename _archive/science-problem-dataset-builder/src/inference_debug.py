from ultralytics import YOLO
import pdfplumber
import cv2
import numpy as np
import os

# Paths
BASE_DIR = r"C:\Users\rlgus\.gemini\antigravity\scratch\science-problem-dataset-builder"
MODEL_PATH = os.path.join(BASE_DIR, "runs/detect/science_problem_v1/weights/best.pt")
PDF_PATH = r"C:\Users\rlgus\.gemini\antigravity\scratch\science-problem-recommender\완자 기출픽_통합과학_본책.pdf"
OUTPUT_DIR = os.path.join(BASE_DIR, "output_debug/ai_inference")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def debug_inference(page_num=54):
    print(f"Running inference on Page {page_num} using {MODEL_PATH}...")
    
    # 1. Load Model
    model = YOLO(MODEL_PATH)
    
    # 2. Add Page Image
    with pdfplumber.open(PDF_PATH) as pdf:
        page = pdf.pages[page_num - 1]
        im_obj = page.to_image(resolution=300)
        im_pil = im_obj.original.convert("RGB")
        im_np = np.array(im_pil)
        # Convert RGB to BGR for OpenCV if needed (YOLO handles PIL usually, but let's stick to standard flow)
        
    # 3. Predict
    results = model.predict(im_pil, save=True, project=OUTPUT_DIR, name=f"page_{page_num}", exist_ok=True)
    
    # Analyze Results
    print("\n--- Detection Results ---")
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            conf = box.conf[0].item()
            cls = box.cls[0].item()
            print(f"Problem Block: Conf={conf:.2f}, Box=[{x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f}]")
            
            # Here we could check if this box covers the "210" area
            # 210 was roughly at y=16 (from debug script) in Left Column
            
    print(f"\nSaved visualization to {os.path.join(OUTPUT_DIR, f'page_{page_num}', 'image0.jpg')}")

if __name__ == "__main__":
    debug_inference(54)
