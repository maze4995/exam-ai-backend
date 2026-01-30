import torch
import cv2
import numpy as np
import argparse
import os
import matplotlib.pyplot as plt
from models.unet import ResUNet

def inference(args):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # 1. Load Model
    model = ResUNet().to(device)
    if os.path.exists(args.checkpoint):
        model.load_state_dict(torch.load(args.checkpoint, map_location=device, weights_only=True))
        print(f"Loaded checkpoint: {args.checkpoint}")
    else:
        print(f"Error: Checkpoint not found at {args.checkpoint}")
        return

    model.eval()
    
    # 2. Load Image
    img_orig = cv2.imread(args.input)
    if img_orig is None:
        print(f"Error: Would not read image {args.input}")
        return
        
    # Preprocess
    h, w, c = img_orig.shape
    # Resize to multiple of 32 for UNet or expected size (512x512)
    # Ideally we process in patches or resize whole image if not too big
    img = cv2.resize(img_orig, (512, 512))
    img_tensor = img.astype(np.float32) / 255.0
    img_tensor = torch.from_numpy(img_tensor).permute(2, 0, 1).unsqueeze(0).to(device)
    
    # 3. Inference
    with torch.no_grad():
        output_tensor = model(img_tensor)
        
    # 4. Post-process
    output = output_tensor.squeeze().permute(1, 2, 0).cpu().numpy()
    output = np.clip(output * 255, 0, 255).astype(np.uint8)
    output = cv2.resize(output, (w, h)) # Resize back to original
    
    # 5. Save/Show
    if args.output:
        cv2.imwrite(args.output, output)
        print(f"Saved result to {args.output}")
    else:
        # Show comparison
        # Resize output to match height for concatenation
        combined = np.hstack((img_orig, output))
        cv2.imshow('Original vs Cleaned', combined)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, required=True, help="Path to input image")
    parser.add_argument('--output', type=str, default=None, help="Path to save output image")
    parser.add_argument('--checkpoint', type=str, default="checkpoints/last.pth")
    
    args = parser.parse_args()
    inference(args)
