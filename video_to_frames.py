import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import threading
import re
import shutil
import sys

class VideoToFramesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video to Frames · Frame Extractor")
        self.root.geometry("620x450")
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f7fa")

        # Locate ffmpeg/ffprobe paths (supports pyinstaller packaged paths)
        self.ffmpeg_path = self.get_ffmpeg_path("ffmpeg")
        self.ffprobe_path = self.get_ffmpeg_path("ffprobe")

        # Styles
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#f5f7fa", foreground="#2c3e50", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 9), padding=6)

        # Green convert button style (ttk.Button works on macOS, tk.Button ignores bg)
        style.configure("Green.TButton",
                        background="#2ecc71",
                        foreground="white",
                        font=("Segoe UI", 12, "bold"),
                        padding=10,
                        borderwidth=0)
        style.map("Green.TButton",
                  background=[("active", "#27ae60"), ("disabled", "#95a5a6")],
                  foreground=[("disabled", "#ecf0f1")])

        # Custom green progress bar style
        style.configure("Green.Horizontal.TProgressbar",
                        background="#2ecc71",
                        troughcolor="#ecf0f1",
                        bordercolor="#2ecc71",
                        lightcolor="#2ecc71",
                        darkcolor="#27ae60")
        style.map("Green.Horizontal.TProgressbar",
                  background=[("active", "#27ae60")])

        # Variables
        self.video_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.fps = tk.StringVar(value="1")
        self.img_format = tk.StringVar(value="JPEG")

        self.converting = False
        self.process = None

        self.create_widgets()

    def get_ffmpeg_path(self, tool_name):
        """Get ffmpeg/ffprobe path, prioritize bundled resources, then system PATH"""
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
            # Check with platform-specific extension first
            if sys.platform == "win32":
                candidate = os.path.join(base_path, tool_name + ".exe")
                if os.path.exists(candidate):
                    self._ensure_executable(candidate)
                    return candidate
            else:
                # macOS / Linux: binary has no extension
                candidate = os.path.join(base_path, tool_name)
                if os.path.exists(candidate):
                    self._ensure_executable(candidate)
                    return candidate
        # Development mode: check local directory with platform extension
        local_exe = tool_name + ".exe" if sys.platform == "win32" else tool_name
        if os.path.exists(local_exe):
            self._ensure_executable(local_exe)
            return local_exe
        # Last resort: system PATH
        return shutil.which(tool_name)

    @staticmethod
    def _ensure_executable(path):
        """Ensure binary has execute permission (PyInstaller may not preserve it)"""
        try:
            st = os.stat(path)
            if not (st.st_mode & 0o111):
                os.chmod(path, st.st_mode | 0o111)
        except Exception:
            pass

    def create_widgets(self):
        # Title
        title = tk.Label(self.root, text="🎬 Video to Frames Tool", font=("Segoe UI", 16, "bold"),
                         bg="#f5f7fa", fg="#2c3e50")
        title.pack(pady=(20, 15))

        # Main frame
        main_frame = tk.Frame(self.root, bg="#f5f7fa")
        main_frame.pack(fill="both", expand=True, padx=30, pady=10)

        # 1. Video file selection
        row1 = tk.Frame(main_frame, bg="#f5f7fa")
        row1.pack(fill="x", pady=8)
        tk.Label(row1, text="📹 Video file:", width=12, anchor="e", bg="#f5f7fa", font=("Segoe UI", 10)).pack(side="left")
        entry_video = tk.Entry(row1, textvariable=self.video_path, font=("Consolas", 9), bg="white", relief="solid", bd=1)
        entry_video.pack(side="left", fill="x", expand=True, padx=5)
        btn_browse_video = tk.Button(row1, text="Browse", command=self.browse_video, bg="#ecf0f1", font=("Segoe UI", 9), width=6)
        btn_browse_video.pack(side="right")

        # 2. Output folder
        row2 = tk.Frame(main_frame, bg="#f5f7fa")
        row2.pack(fill="x", pady=8)
        tk.Label(row2, text="📁 Output folder:", width=12, anchor="e", bg="#f5f7fa", font=("Segoe UI", 10)).pack(side="left")
        entry_out = tk.Entry(row2, textvariable=self.output_dir, font=("Consolas", 9), bg="white", relief="solid", bd=1)
        entry_out.pack(side="left", fill="x", expand=True, padx=5)
        btn_browse_out = tk.Button(row2, text="Browse", command=self.browse_output_dir, bg="#ecf0f1", font=("Segoe UI", 9), width=6)
        btn_browse_out.pack(side="right")

        # 3. Frames per second
        row3 = tk.Frame(main_frame, bg="#f5f7fa")
        row3.pack(fill="x", pady=8)
        tk.Label(row3, text="Frames per second:", width=12, anchor="e", bg="#f5f7fa", font=("Segoe UI", 10)).pack(side="left")
        spin_fps = tk.Spinbox(row3, from_=0.1, to=30, increment=0.5, textvariable=self.fps, width=8, font=("Consolas", 9),
                              relief="solid", bd=1)
        spin_fps.pack(side="left", padx=5)
        tk.Label(row3, text=" (frames/sec, e.g., 1 = one frame per second)", bg="#f5f7fa", fg="#7f8c8d", font=("Segoe UI", 8)).pack(side="left", padx=10)

        # 4. Image format selection
        row4 = tk.Frame(main_frame, bg="#f5f7fa")
        row4.pack(fill="x", pady=8)
        tk.Label(row4, text="🖼️ Image format:", width=12, anchor="e", bg="#f5f7fa", font=("Segoe UI", 10)).pack(side="left")
        radio_jpg = tk.Radiobutton(row4, text="JPEG", variable=self.img_format, value="JPEG", bg="#f5f7fa", font=("Segoe UI", 9))
        radio_jpg.pack(side="left", padx=10)
        radio_png = tk.Radiobutton(row4, text="PNG", variable=self.img_format, value="PNG", bg="#f5f7fa", font=("Segoe UI", 9))
        radio_png.pack(side="left", padx=10)

        # 5. Progress bar + status (using green style)
        progress_frame = tk.Frame(main_frame, bg="#f5f7fa")
        progress_frame.pack(fill="x", pady=(20, 5))
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=500,
                                            mode="determinate", style="Green.Horizontal.TProgressbar")
        self.progress_bar.pack(fill="x", padx=5)
        self.status_label = tk.Label(main_frame, text="Ready", bg="#f5f7fa", fg="#7f8c8d", font=("Segoe UI", 9))
        self.status_label.pack(pady=(5, 10))

        # 6. Convert button (ttk.Button for proper macOS styling)
        btn_convert = ttk.Button(main_frame, text="✨ Start Conversion ✨",
                                 command=self.start_conversion,
                                 style="Green.TButton")
        btn_convert.pack(pady=(10, 8))
        self.convert_btn = btn_convert

    def browse_video(self):
        path = filedialog.askopenfilename(
            title="Select video file",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.mts"), ("All files", "*.*")]
        )
        if path:
            self.video_path.set(path)
            if not self.output_dir.get():
                self.output_dir.set(os.path.dirname(path))

    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select output folder")
        if directory:
            self.output_dir.set(directory)

    def start_conversion(self):
        if self.converting:
            messagebox.showwarning("Info", "Conversion is already in progress, please wait...")
            return
        if not self.video_path.get():
            messagebox.showerror("Error", "Please select a video file first")
            return
        if not self.output_dir.get():
            messagebox.showerror("Error", "Please select an output folder")
            return
        if not os.path.exists(self.video_path.get()):
            messagebox.showerror("Error", "Video file does not exist")
            return
        # Check if ffmpeg exists
        if not self.ffmpeg_path or not os.path.exists(self.ffmpeg_path):
            messagebox.showerror("Error", "ffmpeg not found. Please ensure ffmpeg is installed and added to PATH, or place it in the same directory as this program.")
            return

        try:
            fps_val = float(self.fps.get())
            if fps_val <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Frames per second must be a positive number")
            return

        self.converting = True
        self.convert_btn.config(state="disabled", text="Converting...")
        self.progress_bar["value"] = 0
        self.progress_bar["mode"] = "determinate"
        self.status_label.config(text="Extracting frames, please wait...", fg="#e67e22")

        thread = threading.Thread(target=self.extract_frames, daemon=True)
        thread.start()

    def extract_frames(self):
        video_file = self.video_path.get()
        out_dir = self.output_dir.get()
        fps = float(self.fps.get())
        fmt = self.img_format.get().lower()
        if fmt == "jpeg":
            fmt = "jpg"

        base_name = os.path.splitext(os.path.basename(video_file))[0]
        out_pattern = os.path.join(out_dir, f"{base_name}_frame_%05d.{fmt}")

        # Get total duration and total frames (for progress)
        duration = self.get_duration(video_file)
        total_frames = int(duration * fps) if duration > 0 else 0

        # If total frames cannot be obtained, switch to indeterminate mode (green scrolling bar)
        if total_frames <= 0:
            self.progress_bar["mode"] = "indeterminate"
            self.progress_bar.start(10)
            self.status_label.config(text="Unable to estimate total frames, but extraction continues...")
        else:
            self.progress_bar["mode"] = "determinate"
            self.progress_bar["value"] = 0
            self.progress_bar.stop()

        cmd = [
            self.ffmpeg_path, "-y",
            "-i", video_file,
            "-vf", f"fps={fps}",
            "-q:v", "2",
            out_pattern
        ]

        try:
            # Hide subprocess window (Windows)
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW

            process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',
                creationflags=creation_flags
            )
            self.process = process

            frame_count = 0
            for line in process.stderr:
                match = re.search(r"frame=\s*(\d+)", line)
                if match:
                    frame_count = int(match.group(1))
                    if total_frames > 0:
                        percent = min(100, (frame_count / total_frames) * 100)
                        self.progress_bar["value"] = percent
                        self.status_label.config(text=f"Extracted {frame_count} frames / ~{total_frames} total frames")
                    else:
                        # Indeterminate mode: show frame count only, progress bar scrolls on its own
                        self.status_label.config(text=f"Extracted {frame_count} frames (total unknown)")
                    self.root.update_idletasks()

            returncode = process.wait()
            if total_frames <= 0:
                self.progress_bar.stop()
                self.progress_bar["mode"] = "determinate"
                self.progress_bar["value"] = 100
            else:
                self.progress_bar["value"] = 100

            if returncode == 0:
                self.status_label.config(text=f"✅ Conversion complete! Extracted {frame_count} images", fg="#27ae60")
                messagebox.showinfo("Complete", f"Successfully extracted {frame_count} frames from video. Saved to:\n{out_dir}")
            else:
                self.status_label.config(text="❌ Conversion failed. Please check video or ffmpeg", fg="#e74c3c")
                messagebox.showerror("Error", "ffmpeg execution error. Please ensure ffmpeg is available and the video file is not corrupted.")
        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", fg="#e74c3c")
            messagebox.showerror("Exception", str(e))
        finally:
            self.converting = False
            self.convert_btn.config(state="normal", text="✨ Start Conversion ✨")
            self.process = None
            if total_frames <= 0:
                self.progress_bar.stop()
            self.progress_bar["value"] = 0
            self.progress_bar["mode"] = "determinate"

    def get_duration(self, video_path):
        """Get video duration in seconds using ffprobe. Returns 0 on failure. Hides subprocess window."""
        if not self.ffprobe_path:
            return 0
        try:
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW
            result = subprocess.run(
                [self.ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                capture_output=True, text=True, timeout=10,
                creationflags=creation_flags
            )
            return float(result.stdout.strip())
        except:
            return 0

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoToFramesApp(root)
    root.mainloop()