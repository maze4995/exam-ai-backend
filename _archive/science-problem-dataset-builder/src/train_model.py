from ultralytics import YOLO
import os
import yaml

# Paths
BASE_DIR = r"C:\Users\rlgus\.gemini\antigravity\scratch\science-problem-dataset-builder"
DATA_DIR = os.path.join(BASE_DIR, "training_data")
YAML_PATH = os.path.join(DATA_DIR, "data.yaml")

def create_yaml():
    data = {
        'path': DATA_DIR,
        'train': 'images',
        'val': 'images', # Use same for validation for now (overfitting check)
        'names': {
            0: 'problem'
        }
    }
    
    with open(YAML_PATH, 'w') as f:
        yaml.dump(data, f)
    print(f"Created {YAML_PATH}")

def train():
    create_yaml()
    
    # Load model
    print("Loading YOLOv8n model...")
    model = YOLO('yolov8n.pt')  # load a pretrained model (nano version for speed)

    # Train
    print("Starting training...")
    try:
        results = model.train(
            data=YAML_PATH,
            epochs=50,          # Fast adaptation
            imgsz=640,
            batch=4,
            name='science_problem_v1',
            project=os.path.join(BASE_DIR, 'runs/detect'),
            exist_ok=True
        )
        print("Training complete.")
        print(f"Best model saved at: {os.path.join(BASE_DIR, 'runs/detect/science_problem_v1/weights/best.pt')}")
    except Exception as e:
        print(f"Training failed: {e}")

if __name__ == "__main__":
    train()
