import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import argparse
import os
from tqdm import tqdm
import matplotlib.pyplot as plt

# Import custom modules
from data.synthesizer import HandwritingSynthesizer
from models.unet import ResUNet
from torchvision import models

# VGG Perceptual Loss
class VGGPerceptualLoss(nn.Module):
    def __init__(self, device):
        super(VGGPerceptualLoss, self).__init__()
        # Load VGG19 pretrained features
        vgg = models.vgg19(weights=models.VGG19_Weights.IMAGENET1K_V1).features
        # We only need up to a certain layer (e.g., block3_conv4 or block4_conv4)
        # Using first 16 layers covers typical perceptual features
        self.vgg_features = nn.Sequential(*list(vgg.children())[:16]).to(device).eval()
        for param in self.vgg_features.parameters():
            param.requires_grad = False
            
    def forward(self, x, y):
        # Normalize for VGG (assuming input is 0-1)
        # VGG expects mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
        mean = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1).to(x.device)
        std = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1).to(x.device)
        x_norm = (x - mean) / std
        y_norm = (y - mean) / std
        
        x_feat = self.vgg_features(x_norm)
        y_feat = self.vgg_features(y_norm)
        
        return F.l1_loss(x_feat, y_feat)

import torch.nn.functional as F

def train(args):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # 1. Dataset
    dataset = HandwritingSynthesizer(
        background_dir=args.bg_dir,  # Can be None for random text
        width=args.img_size,
        height=args.img_size,
        length=args.epoch_size
    )
    dataloader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0) # Windows spawn fix by using num_workers=0
    
    # 2. Model
    model = ResUNet().to(device)
    
    # 3. Optim & Loss
    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    l1_loss = nn.L1Loss()
    try:
        perceptual_loss = VGGPerceptualLoss(device)
        use_perceptual = True
    except Exception as e:
        print(f"Warning: Could not load VGG for perceptual loss ({e}). Using L1 only.")
        use_perceptual = False
    
    os.makedirs(args.save_dir, exist_ok=True)
    
    # 4. Training Loop
    for epoch in range(args.epochs):
        model.train()
        loop = tqdm(dataloader, desc=f"Epoch {epoch+1}/{args.epochs}")
        total_loss = 0
        
        for batch_idx, (dirty, clean) in enumerate(loop):
            dirty, clean = dirty.to(device), clean.to(device)
            
            optimizer.zero_grad()
            outputs = model(dirty)
            
            loss_pixel = l1_loss(outputs, clean)
            loss = loss_pixel
            
            if use_perceptual:
                loss_perceptual = perceptual_loss(outputs, clean)
                loss = loss_pixel + 0.1 * loss_perceptual # Weight for perceptual loss
                
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            loop.set_postfix(loss=loss.item())
            
            # Simple debug visualization first batch of every 5th epoch
            if batch_idx == 0 and epoch % 5 == 0:
                with torch.no_grad():
                    debug_img = torch.cat([dirty[0], outputs[0], clean[0]], dim=2).cpu()
                    # (C, H, W) -> (H, W, C)
                    debug_img = debug_img.permute(1, 2, 0).numpy()
                    plt.imsave(os.path.join(args.save_dir, f"epoch_{epoch}.png"), debug_img)

        # Save Checkpoint
        torch.save(model.state_dict(), os.path.join(args.save_dir, "last.pth"))
        print(f"Epoch {epoch+1} finished. Loss: {total_loss/len(dataloader):.4f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=10)
    parser.add_argument('--batch_size', type=int, default=4)
    parser.add_argument('--img_size', type=int, default=512)
    parser.add_argument('--epoch_size', type=int, default=1000, help="Number of samples per epoch")
    parser.add_argument('--lr', type=float, default=1e-4)
    parser.add_argument('--bg_dir', type=str, default=None, help="Path to clean background images")
    parser.add_argument('--save_dir', type=str, default="checkpoints")
    
    args = parser.parse_args()
    train(args)
