from typing import Optional
import torch

def get_device(prefer_cuda: bool = True) -> str:
    """Return 'cuda' if available and preferred, otherwise 'cpu'."""
    return "cuda" if prefer_cuda and torch.cuda.is_available() else "cpu"

def load_model(path: Optional[str], force_reload: bool = False):
    """
    Load a YOLOv5/Ultralytics model via torch.hub.
    - If path is provided, load a custom model from that .pt file.
    - If path is None, load pretrained yolov5s.
    """
    if path:
        return torch.hub.load("ultralytics/yolov5", "custom", path=path, force_reload=force_reload)
    return torch.hub.load("ultralytics/yolov5", "yolov5s", pretrained=True)