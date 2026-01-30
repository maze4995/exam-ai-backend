import cv2
import numpy as np
import random
import glob
import os
from torch.utils.data import Dataset

class HandwritingSynthesizer(Dataset):
    def __init__(self, background_dir=None, handwriting_dir=None, width=512, height=512, length=1000):
        """
        Args:
            background_dir: Path to folder with clean document images.
                            If None, generates random text images.
            handwriting_dir: Path to folder with transparent handwriting images (optional).
                             If None, generates random strokes.
            width, height: Output image size.
            length: Virtual size of the dataset (for one epoch).
        """
        self.background_dir = background_dir
        self.handwriting_dir = handwriting_dir
        self.width = width
        self.height = height
        self.length = length
        
        self.bg_files = glob.glob(os.path.join(background_dir, "*.*")) if background_dir else []
        
    def __len__(self):
        return self.length

    def __getitem__(self, idx):
        # 1. Generate Clean Document (Input B)
        clean = self._get_background()
        
        # 2. Generate Handwriting Mask (Noise)
        mask, stroke_color = self._get_handwriting_mask()
        
        # 3. Combine (Input A = Clean + Noise)
        # Apply mask: where mask > 0, blend stroke color
        alpha = mask / 255.0
        # Expand alpha to 3 channels
        alpha = np.stack([alpha]*3, axis=-1)
        
        # Stroke color image
        stroke_img = np.full_like(clean, stroke_color)
        
        # Blend: Clean * (1-alpha) + Stroke * alpha
        dirty = clean * (1 - alpha) + stroke_img * alpha
        dirty = dirty.astype(np.uint8)
        
        # Normalize to 0-1 float for PyTorch
        dirty_norm = dirty.astype(np.float32) / 255.0
        clean_norm = clean.astype(np.float32) / 255.0
        
        # Transpose to (C, H, W)
        dirty_tensor = dirty_norm.transpose(2, 0, 1)
        clean_tensor = clean_norm.transpose(2, 0, 1)
        
        return dirty_tensor, clean_tensor

    def _get_background(self):
        """Returns a clean document image."""
        if self.bg_files:
            # Load real image
            fpath = random.choice(self.bg_files)
            img = cv2.imread(fpath)
            if img is None:
                return self._generate_random_text_image()
            img = cv2.resize(img, (self.width, self.height))
            return img
        else:
            return self._generate_random_text_image()

    def _generate_random_text_image(self):
        """Generates a white image with random printed text."""
        img = np.ones((self.height, self.width, 3), dtype=np.uint8) * 255
        
        # Draw random lines of text
        font = cv2.FONT_HERSHEY_SIMPLEX
        num_lines = random.randint(10, 20)
        line_height = self.height // (num_lines + 2)
        
        for i in range(num_lines):
            y = (i + 1) * line_height
            text = " ".join(["Word"] * random.randint(3, 10))
            # Black text
            cv2.putText(img, text, (20, y), font, 0.5 + random.random()*0.5, (0, 0, 0), 1, cv2.LINE_AA)
            
        return img

    def _get_handwriting_mask(self):
        """Generates a grayscale mask of handwriting strokes and a color."""
        mask = np.zeros((self.height, self.width), dtype=np.uint8)
        
        # Random stroke parameters
        num_strokes = random.randint(3, 10)
        thickness = random.randint(1, 3)
        
        # Random Color: Red, Blue, or Black (Simulating pens)
        colors = [
            (0, 0, 255),   # Red
            (255, 0, 0),   # Blue
            (50, 50, 50),  # Dark Gray (Pencil)
        ]
        color = random.choice(colors)
        
        for _ in range(num_strokes):
            # Generate random bezier-like curves using polylines
            pts = np.random.randint(0, self.width, (random.randint(3, 6), 2))
            # Smooth the points? For now just simple polylines or curves
            # To make it look like handwriting, we can use simple straight lines or interpolated curves
            # Let's use polylines with `isClosed=False`
            cv2.polylines(mask, [pts.reshape(-1, 1, 2)], isClosed=False, color=255, thickness=thickness, lineType=cv2.LINE_AA)
            
        # Add some blur to making it look like ink spread
        if random.random() > 0.5:
            mask = cv2.GaussianBlur(mask, (3, 3), 0)
            
        return mask, color

# Debug/Main block to test
if __name__ == "__main__":
    syn = HandwritingSynthesizer(length=5)
    d, c = syn[0]
    print("Shapes:", d.shape, c.shape)
    
    # Save a sample
    d_img = (d.transpose(1, 2, 0) * 255).astype(np.uint8)
    c_img = (c.transpose(1, 2, 0) * 255).astype(np.uint8)
    
    cv2.imwrite("debug_synth_dirty.png", d_img)
    cv2.imwrite("debug_synth_clean.png", c_img)
    print("Saved debug images.")
