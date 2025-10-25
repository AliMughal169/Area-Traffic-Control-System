import ctypes
import cv2
import numpy as np
from typing import List, Optional
from .model import load_model, get_device
from .video import open_capture
from .timers import TimerManager
from .scoring import score_frame
from .plotting import plot_boxes



class AreaTrafficControl:
    def __init__(self, cam_paths: List[str], black_path: str, model_path: Optional[str] = None, usage: str = "pedes"):
        assert len(cam_paths) == 4, "Provide 4 camera/video paths"
        self.cam_paths = cam_paths
        self.black = black_path
        self.model_path = model_path
        self.usage = usage

        self.timer_mgr = TimerManager(4)
        self.sides = [{"side": i+1, "person_alert": False, "count": 0, "path": cam_paths[i], "status": False} for i in range(4)]
        self.current_side = 1
        self.prev = 0

        self.model = None
        self.classes = None
        self.device = get_device()
        self.running = False

    def _allot_time(self, count: int) -> int:
        if 0 < count < 20:
            return 5
        if 19 < count < 40:
            return 25
        if count >= 40:
            return 35
        return 5

    def _on_timer_expire(self, side_idx: int):
        if self.current_side == 4:
            self.current_side = 1
        else:
            self.current_side += 1
        self.sides[side_idx]["status"] = False

    def _handle_detection_events(self, side_idx: int, names: List[str]):
        side = self.sides[side_idx]
        # ambulance overrides
        if any(n == "ambulance" for n in names):
            self.timer_mgr.cancel_all()
            side["count"] = max(0, len([n for n in names if n != "person"]))
            side["status"] = False
            self.prev = self.current_side
            return
        # person detected -> debounce
        if any(n == "person" for n in names):
            side["person_alert"] = True
            self.timer_mgr.start_timer(side_idx, 2.0, self._clear_person_alert, args=(side_idx,))
            return
        # if no special events, update count and possibly start timer for current side
        side["count"] = max(0, len([n for n in names if n != "person"]))
        if side["status"]:
            return
        if self.current_side == side["side"]:
            sec = self._allot_time(side["count"])
            self.timer_mgr.start_timer(side_idx, sec, self._on_timer_expire, args=(side_idx,))
            side["status"] = True

    def _clear_person_alert(self, side_idx: int):
        self.sides[side_idx]["person_alert"] = False

    def load_model(self):
        if self.model is None:
            self.model = load_model(self.model_path, force_reload=False)
            self.classes = getattr(self.model, "names", None)

    def start(self):
        self.load_model()
        self.running = True

        caps = [open_capture(p) for p in self.cam_paths]
        black_cap = open_capture(self.black)

        for i, c in enumerate(caps, 1):
            if not c.isOpened():
                raise RuntimeError(f"Video capture {i} failed to open: {self.cam_paths[i-1]}")
        if not black_cap.isOpened():
            raise RuntimeError(f"Fallback video failed to open: {self.black}")

        winname = 'Area Traffic Control System'
        cv2.namedWindow(winname, cv2.WINDOW_NORMAL)
        try:
            user32 = ctypes.windll.user32
            cv2.resizeWindow(winname, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
        except Exception:
            pass

        blret, blframe = black_cap.read()
        if not blret or blframe is None:
            blframe = 255 * np.ones((500,500,3), dtype=np.uint8)

        counter = 0
        flags = [False] * 4

        while self.running:
            if counter % 15 == 0:
                frames = []
                rets = []
                for idx, cap in enumerate(caps):
                    ret, frame = cap.read()
                    if not ret or frame is None:
                        frame = blframe.copy()
                        flags[idx] = True
                    else:
                        flags[idx] = False
                    frames.append(frame)
                    rets.append(ret)
                if all(r is False for r in rets):
                    break

                out_frames = []
                for i, frame in enumerate(frames):
                    labels, cords, names = score_frame(self.model, frame, self.device, class_order=[0,1,2,4,3])
                    self._handle_detection_events(i, names)
                    resized = cv2.resize(frame, (500,500))
                    rendered = plot_boxes(labels, cords, resized, classes=self.classes)
                    color = (0,255,0) if self.sides[i]["status"] else (0,0,255)
                    cv2.putText(rendered, f'count: {int(self.sides[i]["count"])}', (10,50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255,255,255), 10)
                    cv2.circle(rendered, (447,30), 20, color, -1)
                    out_frames.append(rendered)

                stacked1 = np.hstack((out_frames[0], out_frames[1]))
                stacked2 = np.hstack((out_frames[2], out_frames[3]))
                stack = np.vstack((stacked1, stacked2))

                cv2.imshow(winname, stack)
                key = cv2.waitKey(5) & 0xFF
                if key == 27:
                    break
                if cv2.getWindowProperty(winname, cv2.WND_PROP_VISIBLE) < 1:
                    break
            counter += 1

        for c in caps:
            c.release()
        black_cap.release()
        cv2.destroyAllWindows()
        self.running = False

    def stop(self):
        self.running = False
        self.timer_mgr.cancel_all()
