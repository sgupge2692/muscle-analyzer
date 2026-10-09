import torch
import cv2
import mediapipe as mp
import numpy as np

print(f"✅ PyTorch:    {torch.__version__}")
print(f"✅ MPS(GPU):   {torch.backends.mps.is_available()}")
print(f"✅ OpenCV:     {cv2.__version__}")
print(f"✅ MediaPipe:  {mp.__version__}")
print(f"✅ NumPy:      {np.__version__}")
