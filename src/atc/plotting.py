import cv2
import numpy as np
from typing import List, Optional, Sequence

def class_to_label(classes: Optional[Sequence[str]], x: int) -> str:
    """Return human readable label for a class index."""
    if classes is None:
        return str(int(x))
    try:
        return str(classes[int(x)])
    except Exception:
        return str(int(x))

def plot_boxes(labels: List[int], cords: np.ndarray, frame: np.ndarray, classes: Optional[Sequence[str]] = None, conf_thresh: float = 0.3) -> np.ndarray:
    """
    Draw bounding boxes and labels on frame.
    - labels: list of class indices
    - cords: nx5 array with normalized [x1, y1, x2, y2, conf]
    - frame: BGR image (will be modified in-place)
    - classes: optional list/dict mapping class index -> name
    - conf_thresh: minimum confidence to draw box
    """
    if cords is None or getattr(cords, "size", 0) == 0 or len(labels) == 0:
        return frame

    h, w = frame.shape[:2]
    for i, lab in enumerate(labels):
        if i >= cords.shape[0]:
            break
        row = cords[i]
        try:
            conf = float(row[4])
        except Exception:
            conf = 0.0
        if conf < conf_thresh:
            continue
        x1 = int(max(0, row[0] * w))
        y1 = int(max(0, row[1] * h))
        x2 = int(min(w - 1, row[2] * w))
        y2 = int(min(h - 1, row[3] * h))

        color = (0, 255, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        label_text = class_to_label(classes, lab)
        text = f"{label_text} {conf:.2f}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 6, y1), color, -1)
        cv2.putText(frame, text, (x1 + 3, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

    return frame