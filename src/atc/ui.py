import threading
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from .detector import AreaTrafficControl
import datetime


class SimpleLauncher:
    """Tk UI to pick 4 videos, a fallback, and a model, then start/stop detector."""
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Area Traffic Control Launcher")
        self.entries = {}

        defaults = [
            ("Camera 1", "./resources/videos/vid10.mp4"),
            ("Camera 2", "./resources/videos/vid15.mp4"),
            ("Camera 3", "./resources/videos/vid16.mp4"),
            ("Camera 4", "./resources/videos/vid17.mp4"),
            ("Fallback", "./resources/videos/finish.mp4"),
            ("Model (.pt)", "./models/best.pt"),
        ]

        for r, (label, default) in enumerate(defaults):
            tk.Label(root, text=label).grid(row=r, column=0, sticky="w")
            e = tk.Entry(root, width=60)
            e.insert(0, default)
            e.grid(row=r, column=1, padx=5, pady=2)
            btn = tk.Button(root, text="Browse", command=lambda ent=e: self.browse_file(ent))
            btn.grid(row=r, column=2, padx=5)
            self.entries[label] = e

        row = len(defaults)
        self.start_btn = tk.Button(root, text="Start", command=self.start)
        self.start_btn.grid(row=row, column=0, pady=8)
        self.stop_btn = tk.Button(root, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.grid(row=row, column=1, pady=8)
        self.quit_btn = tk.Button(root, text="Quit", command=self.quit)
        self.quit_btn.grid(row=row, column=2, pady=8)

        # 🔹 Status label
        row += 1
        self.status_label = tk.Label(root, text="Status: Idle", fg="gray", font=("Segoe UI", 10, "italic"))
        self.status_label.grid(row=row, column=0, columnspan=3, pady=6)

        # 🔹 Progress bar
        row += 1
        self.progress = ttk.Progressbar(root, mode='indeterminate', length=300)
        self.progress.grid(row=row, column=0, columnspan=3, pady=6)
        self.progress.grid_remove()  # Hidden by default

        # 🔹 Logs panel
        row += 1
        log_frame = tk.Frame(root)
        log_frame.grid(row=row, column=0, columnspan=3, pady=8, padx=10)
        tk.Label(log_frame, text="Logs:").pack(anchor="w")
        self.log_text = tk.Text(log_frame, height=10, width=80, state="disabled", wrap="word", bg="#f7f7f7")
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Thread & detector state
        self.detector_thread: threading.Thread | None = None
        self.detector: AreaTrafficControl | None = None

        self.log("Launcher initialized and ready.")

    # ---------------------------- UI HELPERS ----------------------------

    def browse_file(self, entry_widget: tk.Entry):
        path = filedialog.askopenfilename(title="Select file", initialdir=".")
        if path:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, path)

    def update_status(self, text: str, color: str):
        self.status_label.config(text=f"Status: {text}", fg=color)
        self.log(f"[STATUS] {text}")

    def show_progress(self, show: bool):
        """Start or stop the progress bar animation."""
        if show:
            self.progress.grid()
            self.progress.start(10)
        else:
            self.progress.stop()
            self.progress.grid_remove()

    def log(self, message: str):
        """Append a timestamped log message to the logs panel."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.config(state="disabled")
        self.log_text.see("end")

    # ---------------------------- DETECTOR LOGIC ----------------------------

    def _run_detector(self, cam_paths, black, model):
        try:
            self.log("Initializing detector and loading model...")
            det = AreaTrafficControl(cam_paths, black, model)
            self.detector = det
            self.root.after(0, lambda: self.update_status("Running detection...", "green"))
            self.root.after(0, lambda: self.show_progress(False))
            self.log("Model loaded successfully. Detection started.")
            det.start()  # Blocking until stopped
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Detector Error", str(e)))
            self.root.after(0, lambda: self.update_status(f"Error: {e}", "red"))
            self.root.after(0, lambda: self.show_progress(False))
            self.log(f"❌ Error occurred: {e}")
        finally:
            self.root.after(0, self._on_detector_exit)

    def _on_detector_exit(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.update_status("Stopped", "gray")
        self.show_progress(False)
        self.log("Detector stopped.")
        self.detector = None
        self.detector_thread = None

    def _validate_paths(self, cam_paths, black, model) -> bool:
        for p in cam_paths + [black]:
            if not os.path.exists(p):
                msg = f"File not found: {p}"
                self.log(f"⚠️ {msg}")
                if not messagebox.askyesno("Missing file", f"{msg}\nContinue anyway?"):
                    return False
        return True

    def start(self):
        cam_paths = [self.entries[f"Camera {i}"].get() for i in range(1, 5)]
        black = self.entries["Fallback"].get()
        model = self.entries["Model (.pt)"].get()
        if not self._validate_paths(cam_paths, black, model):
            return

        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.update_status("Loading model and starting detector...", "blue")
        self.show_progress(True)
        self.log("Starting detector thread...")

        self.detector_thread = threading.Thread(
            target=self._run_detector,
            args=(cam_paths, black, model),
            daemon=True
        )
        self.detector_thread.start()

    def stop(self):
        if self.detector:
            self.update_status("Stopping detector...", "orange")
            self.show_progress(True)
            self.log("Stopping detector...")
            self.detector.stop()

    def quit(self):
        if self.detector and getattr(self.detector, "running", False):
            if not messagebox.askyesno("Quit", "Detector running. Stop and quit?"):
                return
            self.log("User requested quit while running. Stopping detector...")
            self.detector.stop()
        self.log("Exiting application.")
        self.root.quit()


# ---------------------------- RUN APP ----------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = SimpleLauncher(root)
    root.mainloop()
