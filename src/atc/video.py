from typing import Optional, Tuple
import cv2
import numpy as np

def open_capture(path: str) -> cv2.VideoCapture:
    return cv2.VideoCapture(path)

def read_or_fallback(cap: Optional[cv2.VideoCapture], fallback_frame: Optional[np.ndarray]) -> Tuple[bool, Optional[np.ndarray]]:
    if cap is None:
        return False, fallback_frame
    ret, frame = cap.read()
    if not ret:
        return False, fallback_frame
    return True, frame