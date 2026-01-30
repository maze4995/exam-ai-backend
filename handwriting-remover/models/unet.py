import torch
import torch.nn as nn
import torch.nn.functional as F

class ResBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super(ResBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(out_channels)
        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_channels)
        
        self.shortcut = nn.Sequential()
        if stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(out_channels)
            )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out

class ResUNet(nn.Module):
    def __init__(self, in_channels=3, out_channels=3):
        super(ResUNet, self).__init__()
        
        # Encoder
        self.init_conv = nn.Sequential(
            nn.Conv2d(in_channels, 64, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True)
        )
        
        self.enc1 = ResBlock(64, 128, stride=2)  # 256 -> 128
        self.enc2 = ResBlock(128, 256, stride=2) # 128 -> 64
        self.enc3 = ResBlock(256, 512, stride=2) # 64 -> 32
        
        # Bridge
        self.bridge = ResBlock(512, 1024, stride=2) # 32 -> 16
        
        # Decoder
        self.up3 = nn.ConvTranspose2d(1024, 512, kernel_size=2, stride=2)
        self.dec3 = ResBlock(512 + 512, 512)
        
        self.up2 = nn.ConvTranspose2d(512, 256, kernel_size=2, stride=2)
        self.dec2 = ResBlock(256 + 256, 256)
        
        self.up1 = nn.ConvTranspose2d(256, 128, kernel_size=2, stride=2)
        self.dec1 = ResBlock(128 + 128, 128)

        self.up0 = nn.ConvTranspose2d(128, 64, kernel_size=2, stride=2)
        self.dec0 = ResBlock(64 + 64, 64)
        
        self.final = nn.Conv2d(64, out_channels, kernel_size=1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # Encoder
        x0 = self.init_conv(x)      # 512
        e1 = self.enc1(x0)          # 256
        e2 = self.enc2(e1)          # 128
        e3 = self.enc3(e2)          # 64
        
        # Bridge
        b = self.bridge(e3)         # 32
        
        # Decoder
        d3 = self.up3(b)
        # Pad if needed (not needed for power of 2 sizes)
        d3 = torch.cat((e3, d3), dim=1)
        d3 = self.dec3(d3)
        
        d2 = self.up2(d3)
        d2 = torch.cat((e2, d2), dim=1)
        d2 = self.dec2(d2)
        
        d1 = self.up1(d2)
        d1 = torch.cat((e1, d1), dim=1)
        d1 = self.dec1(d1)
        
        d0 = self.up0(d1)
        d0 = torch.cat((x0, d0), dim=1)
        d0 = self.dec0(d0)
        
        out = self.final(d0)
        return self.sigmoid(out)

if __name__ == "__main__":
    # Test Model
    x = torch.randn(1, 3, 512, 512)
    model = ResUNet()
    y = model(x)
    print(f"Input: {x.shape}, Output: {y.shape}")
    assert y.shape == x.shape
