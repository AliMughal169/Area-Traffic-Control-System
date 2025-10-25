from typing import Tuple, List, Optional, Sequence
import numpy as np
import torch

def score_frame(model: torch.nn.Module, frame: np.ndarray, device: str, class_order: Optional[Sequence[int]] = None) -> Tuple[List[int], np.ndarray, List[str]]:
    """
    Run model inference on a single frame.

    Returns:
    - labels: list of class indices
    - cords: numpy array shape (n,5) with normalized [x1,y1,x2,y2,conf]
    - names: list of detected class names (lowercased)
    """
    model.to(device)
    if class_order is not None:
        try:
            model.classes = class_order
        except Exception:
            pass

    with torch.no_grad():
        results = model([frame], size=416)

    try:
        xyxyn = results.xyxyn[0].cpu().numpy()  # (n,6) [x1,y1,x2,y2,conf,class]
    except Exception:
        return [], np.zeros((0,5)), []

    if xyxyn.size == 0:
        return [], np.zeros((0,5)), []

    labels = xyxyn[:, -1].astype(int).tolist()
    cords = xyxyn[:, :-1]  # (n,5): x1,y1,x2,y2,conf

    try:
        df = results.pandas().xyxy[0]
        names = [str(n).strip().lower() for n in df.name.tolist()]
    except Exception:
        names = [str(int(l)) for l in labels]

    return labels, cords, names