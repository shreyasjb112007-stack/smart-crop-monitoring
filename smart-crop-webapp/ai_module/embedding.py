"""
embedding.py
------------
Converts a crop image into a 512-dimensional feature vector using a
pretrained ResNet18 (final classification layer removed), as described
in the project doc:

    Crop Image -> Resize/Preprocess -> ResNet18 -> 512-D Embedding
                -> Normalize -> Store in / Query Milvus

NOTE: the first time you run this, PyTorch will download the pretrained
ResNet18 weights (~45 MB) from the internet. That needs to happen once,
on your machine, before the demo (do it now / with wifi on, not during
the live demo).
"""

import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np

_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

_preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],   # standard ImageNet stats
        std=[0.229, 0.224, 0.225],
    ),
])

_model = None  # lazy-loaded singleton so Streamlit doesn't reload it every rerun


def _load_model():
    global _model
    if _model is None:
        base = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        base.fc = nn.Identity()   # strip the final classification layer -> 512-D output
        base.eval()
        base.to(_device)
        _model = base
    return _model


def get_embedding(image: Image.Image) -> np.ndarray:
    """
    Takes a PIL image, returns a normalized 512-D numpy float32 vector
    suitable for cosine-similarity search in Milvus.
    """
    model = _load_model()
    image = image.convert("RGB")
    tensor = _preprocess(image).unsqueeze(0).to(_device)   # shape (1, 3, 224, 224)

    with torch.no_grad():
        vec = model(tensor).squeeze(0).cpu().numpy().astype(np.float32)  # (512,)

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def get_embedding_from_path(image_path: str) -> np.ndarray:
    """Convenience wrapper used by the dataset-loading script."""
    with Image.open(image_path) as img:
        return get_embedding(img)
