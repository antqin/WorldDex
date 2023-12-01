import torch

# Check if CUDA (GPU support) is available
print("CUDA available:", torch.cuda.is_available())

# Set device to GPU (cuda) if available, else CPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", device)

# Create a random tensor and move it to the chosen device
x = torch.rand(5, 5).to(device)
print("Random Tensor on GPU:", x)

# Perform a simple computation
y = x * x
print("Squared Tensor:", y)

