import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import threading
from pathlib import Path
import json
import re


class ClipperGUI:
    """
    A minimal, modern, and accessible GUI for video trimming and encoding using FFmpeg.
    Features:
    - Drag-and-drop or browse for input video files
    - Optional trimming with timeline and seekbar
    - Output filename auto-generation and sanitization
    - Encoding preset selection
    - Robust error handling and clear status feedback
    - Clean, dark, material-inspired UI (no extra dependencies)
    """

    COLORS = {
        "primary": "#2196F3",
        "primary_dark": "#1976D2",
        "primary_light": "#64B5F6",
        "accent": "#FFC107",
        "surface": "#1A1A1A",
        "surface_elevated": "#23272b",
        "surface_border": "#2d3136",
        "pill_selected": "#2a3950",
        "text_primary": "#F1F1F1",
        "text_secondary": "#B0B3B8",
        "success": "#4CAF50",
        "error": "#F44336",
    }

    def __init__(self, root):
        self.root = root
        self.root.title("Clipper")
        self.root.resizable(True, True)

        # Configure style
        self.setup_styles()

        # Variables
        self.input_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.custom_output_name = tk.StringVar()
        self.is_processing = False
        self.selected_preset = tk.StringVar(value="medium")
        self.trim_enabled = tk.BooleanVar(value=False)
        self.start_time = tk.StringVar(value="0:00")
        self.end_time = tk.StringVar(value="0:00")
        self.video_duration = 0  # in seconds
        self.dragging_start = False
        self.dragging_end = False

        self.setup_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        c = self.COLORS
        style.configure("TFrame", background=c["surface"])
        style.configure("TLabel", background=c["surface"], foreground=c["text_primary"])
        style.configure(
            "Subtitle.TLabel",
            font=("Segoe UI", 11, "bold"),
            foreground=c["text_primary"],
            background=c["surface"],
        )
        style.configure(
            "Info.TLabel",
            font=("Segoe UI", 9),
            foreground=c["text_secondary"],
            background=c["surface"],
        )
        style.configure(
            "Success.TLabel",
            font=("Segoe UI", 9),
            foreground=c["success"],
            background=c["surface"],
        )
        style.configure(
            "Error.TLabel",
            font=("Segoe UI", 9),
            foreground=c["error"],
            background=c["surface"],
        )
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(16, 8),
            background=c["primary"],
            foreground=c["text_primary"],
            relief="flat",
            borderwidth=0,
        )
        style.map(
            "Primary.TButton",
            background=[("active", c["primary_dark"]), ("pressed", c["primary_dark"])],
        )
        style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 9),
            padding=(12, 6),
            background=c["surface_elevated"],
            foreground=c["text_primary"],
            relief="flat",
            borderwidth=1,
            bordercolor=c["surface_border"],
        )
        style.map(
            "Secondary.TButton",
            background=[("active", c["primary"]), ("pressed", c["primary_dark"])],
        )
        style.configure(
            "Success.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(16, 8),
            background=c["success"],
            foreground=c["text_primary"],
            relief="flat",
            borderwidth=0,
        )
        style.map(
            "Success.TButton",
            background=[("active", "#388E3C"), ("pressed", "#2E7D32")],
        )
        style.configure(
            "Pill.TLabelframe",
            background=c["surface_elevated"],
            borderwidth=1,
            relief="groove",
            bordercolor=c["surface_border"],
        )
        style.configure(
            "Pill.TLabelframe.Label",
            background=c["surface_elevated"],
            foreground=c["text_primary"],
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "Pill.TRadiobutton",
            font=("Segoe UI", 9, "bold"),
            foreground=c["text_primary"],
            background=c["surface_elevated"],
            indicatorcolor=c["surface_elevated"],
            indicatorrelief="flat",
            borderwidth=0,
            padding=6,
            relief="flat",
        )
        style.map(
            "Pill.TRadiobutton",
            background=[
                ("selected", c["pill_selected"]),
                ("active", c["primary"]),
                ("!selected", c["surface_elevated"]),
                ("!active", c["surface_elevated"]),
            ],
            foreground=[
                ("selected", c["primary_light"]),
                ("active", c["text_primary"]),
                ("!selected", c["text_primary"]),
            ],
            indicatorcolor=[
                ("selected", c["accent"]),
                ("active", c["accent"]),
            ],
        )
        style.configure(
            "Pill.TCheckbutton",
            font=("Segoe UI", 9, "bold"),
            foreground=c["text_primary"],
            background=c["surface_elevated"],
            indicatorcolor=c["surface_elevated"],
            indicatorrelief="flat",
            borderwidth=0,
            padding=6,
            relief="flat",
        )
        style.map(
            "Pill.TCheckbutton",
            background=[
                ("selected", c["pill_selected"]),
                ("active", c["primary"]),
                ("!selected", c["surface_elevated"]),
                ("!active", c["surface_elevated"]),
            ],
            foreground=[
                ("selected", c["primary_light"]),
                ("active", c["text_primary"]),
                ("!selected", c["text_primary"]),
            ],
            indicatorcolor=[
                ("selected", c["accent"]),
                ("active", c["accent"]),
            ],
        )
        style.configure(
            "TEntry",
            fieldbackground=c["surface_elevated"],
            foreground=c["text_primary"],
            borderwidth=1,
            relief="flat",
            bordercolor=c["surface_border"],
        )
        style.map(
            "TEntry",
            fieldbackground=[("focus", c["primary_light"])],
            bordercolor=[("focus", c["primary"])],
        )

    def setup_ui(self):
        self.root.configure(bg="#1A1A1A")
        main_container = ttk.Frame(self.root, padding="15")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        # Input file selection
        input_label = ttk.Label(
            main_container, text="Input File:", style="Subtitle.TLabel"
        )
        input_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 4))
        file_selection_frame = ttk.Frame(main_container)
        file_selection_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        file_selection_frame.columnconfigure(0, weight=1)
        self.input_entry = ttk.Entry(
            file_selection_frame, textvariable=self.input_file, font=("Segoe UI", 9)
        )
        self.input_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 8))
        browse_btn = ttk.Button(
            file_selection_frame,
            text="Browse",
            command=self.browse_input_file,
            style="Secondary.TButton",
        )
        browse_btn.grid(row=0, column=1)
        self.file_info_label = ttk.Label(
            main_container, text="No file selected", style="Info.TLabel"
        )
        self.file_info_label.grid(row=2, column=0, pady=(8, 0), sticky=tk.W)
        # Trimming toggle (pill style)
        trim_toggle_frame = ttk.Frame(main_container)
        trim_toggle_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(8, 8))
        self.trim_check = ttk.Checkbutton(
            trim_toggle_frame,
            text="Enable Video Trimming",
            variable=self.trim_enabled,
            command=self.toggle_trim_section,
            style="Pill.TCheckbutton",
        )
        self.trim_check.grid(row=0, column=0, sticky=tk.W, padx=4, pady=2)
        # Timeline section (pill/box style)
        self.timeline_frame = ttk.LabelFrame(
            main_container,
            text="Timeline & Trimming",
            padding="12",
            style="Pill.TLabelframe",
        )
        self.timeline_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        self.timeline_frame.columnconfigure(0, weight=1)
        self.timeline_frame.grid_remove()  # Initially hidden
        self.timeline_canvas = tk.Canvas(
            self.timeline_frame,
            height=80,
            bg="#23272b",
            relief="flat",
            bd=0,
            highlightthickness=0,
        )
        self.timeline_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        self.timeline_canvas.bind("<Button-1>", self.on_timeline_click)
        self.timeline_canvas.bind("<B1-Motion>", self.on_timeline_drag)
        self.timeline_canvas.bind("<ButtonRelease-1>", self.on_timeline_release)
        time_controls_frame = ttk.Frame(self.timeline_frame)
        time_controls_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
        # Start time
        start_frame = ttk.Frame(time_controls_frame)
        start_frame.grid(row=0, column=0, padx=(0, 16))
        ttk.Label(start_frame, text="Start Time:", style="Subtitle.TLabel").grid(
            row=0, column=0, sticky=tk.W
        )
        self.start_entry = ttk.Entry(
            start_frame, textvariable=self.start_time, width=10, font=("Segoe UI", 9)
        )
        self.start_entry.grid(row=1, column=0, pady=(4, 0))
        # End time
        end_frame = ttk.Frame(time_controls_frame)
        end_frame.grid(row=0, column=1, padx=(0, 16))
        ttk.Label(end_frame, text="End Time:", style="Subtitle.TLabel").grid(
            row=0, column=0, sticky=tk.W
        )
        self.end_entry = ttk.Entry(
            end_frame, textvariable=self.end_time, width=10, font=("Segoe UI", 9)
        )
        self.end_entry.grid(row=1, column=0, pady=(4, 0))
        # Duration
        duration_frame = ttk.Frame(time_controls_frame)
        duration_frame.grid(row=0, column=2)
        ttk.Label(duration_frame, text="Duration:", style="Subtitle.TLabel").grid(
            row=0, column=0, sticky=tk.W
        )
        self.duration_label = ttk.Label(
            duration_frame,
            text="0:00",
            style="Success.TLabel",
            font=("Segoe UI", 9, "bold"),
        )
        self.duration_label.grid(row=1, column=0, pady=(4, 0))
        # Output filename (no box)
        ttk.Label(
            main_container, text="Output Filename:", style="Subtitle.TLabel"
        ).grid(row=5, column=0, sticky=tk.W, pady=(8, 0))
        self.output_entry = ttk.Entry(
            main_container, textvariable=self.custom_output_name, font=("Segoe UI", 9)
        )
        self.output_entry.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=(0, 12))
        # Encoding preset (no box, just label)
        ttk.Label(
            main_container, text="Encoding Preset:", style="Subtitle.TLabel"
        ).grid(row=7, column=0, sticky=tk.W, pady=(8, 0))
        preset_frame = ttk.Frame(main_container)
        preset_frame.grid(row=8, column=0, sticky=(tk.W, tk.E))
        presets = [
            ("Very Fast", "veryfast"),
            ("Fast", "fast"),
            ("Medium", "medium"),
            ("Slow", "slow"),
            ("Very Slow", "veryslow"),
        ]
        for i, (label, value) in enumerate(presets):
            preset_btn = ttk.Radiobutton(
                preset_frame,
                text=label,
                variable=self.selected_preset,
                value=value,
                command=self.update_output_name,
                style="Pill.TRadiobutton",
            )
            preset_btn.grid(row=0, column=i, padx=(0, 8), pady=2)
        # Status section (no progress bar)
        self.status_label = ttk.Label(
            main_container, text="Ready to process video", style="Info.TLabel"
        )
        self.status_label.grid(row=9, column=0, pady=(16, 12))
        self.process_btn = ttk.Button(
            main_container,
            text="Process Video",
            command=self.process_video,
            style="Success.TButton",
        )
        self.process_btn.grid(row=10, column=0, pady=(0, 8))
        # Bind events
        self.input_file.trace("w", self.on_file_selected)
        self.start_time.trace("w", self.on_time_changed)
        self.end_time.trace("w", self.on_time_changed)
        # Auto-adjust window size
        self.root.update_idletasks()
        self.root.geometry("")  # Let the window size itself

    def toggle_trim_section(self):
        """Show/hide the trimming section based on checkbox state"""
        if self.trim_enabled.get():
            self.timeline_frame.grid()
            self.start_entry.config(state="normal")
            self.end_entry.config(state="normal")
        else:
            self.timeline_frame.grid_remove()
            self.start_entry.config(state="disabled")
            self.end_entry.config(state="disabled")

    def browse_input_file(self):
        filetypes = [
            ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv"),
            ("MP4 files", "*.mp4"),
            ("All files", "*.*"),
        ]
        filename = filedialog.askopenfilename(
            title="Select input video file", filetypes=filetypes
        )
        if filename:
            self.input_file.set(filename)

    def on_file_selected(self, *args):
        input_path = self.input_file.get()
        if input_path and os.path.exists(input_path):
            self.get_video_duration(input_path)
            self.update_output_name()
            filename = os.path.basename(input_path)
            self.file_info_label.config(
                text=f"Selected: {filename}", style="Success.TLabel"
            )

    def get_video_duration(self, video_path):
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            self.video_duration = float(data["format"]["duration"])
            self.end_time.set(self.seconds_to_time(self.video_duration))
            self.draw_timeline()
        except Exception as e:
            print(f"Error getting video duration: {e}")
            self.video_duration = 0

    def draw_timeline(self):
        self.timeline_canvas.delete("all")
        if self.video_duration <= 0:
            return

        canvas_width = self.timeline_canvas.winfo_width()
        if canvas_width <= 1:
            canvas_width = 800

        # Draw background
        self.timeline_canvas.create_rectangle(
            0, 25, canvas_width, 55, fill="#404040", outline="#505050", width=1
        )

        # Draw time markers
        for i in range(0, int(self.video_duration) + 1, 10):
            x = (i / self.video_duration) * canvas_width
            self.timeline_canvas.create_line(x, 20, x, 60, fill="#606060", width=1)
            self.timeline_canvas.create_text(
                x,
                18,
                text=self.seconds_to_time(i),
                font=("Segoe UI", 7),
                fill="#CCCCCC",
            )

        # Draw start and end handles
        start_seconds = self.time_to_seconds(self.start_time.get())
        end_seconds = self.time_to_seconds(self.end_time.get())
        start_x = (start_seconds / self.video_duration) * canvas_width
        end_x = (end_seconds / self.video_duration) * canvas_width

        # Start handle (green)
        self.timeline_canvas.create_rectangle(
            start_x - 8,
            12,
            start_x + 8,
            68,
            fill="#4CAF50",
            outline="#388E3C",
            width=1,
            tags="start_handle",
        )
        self.timeline_canvas.create_text(
            start_x, 70, text="START", font=("Segoe UI", 7, "bold"), fill="#4CAF50"
        )

        # End handle (red)
        self.timeline_canvas.create_rectangle(
            end_x - 8,
            12,
            end_x + 8,
            68,
            fill="#F44336",
            outline="#D32F2F",
            width=1,
            tags="end_handle",
        )
        self.timeline_canvas.create_text(
            end_x, 70, text="END", font=("Segoe UI", 7, "bold"), fill="#F44336"
        )

        # Highlight selected region
        if start_x < end_x:
            self.timeline_canvas.create_rectangle(
                start_x,
                25,
                end_x,
                55,
                fill="#2196F3",
                stipple="gray50",
                outline="#1976D2",
                width=1,
            )

    def on_timeline_click(self, event):
        if self.video_duration <= 0:
            return
        canvas_width = self.timeline_canvas.winfo_width()
        if canvas_width <= 1:
            canvas_width = 800
        click_ratio = event.x / canvas_width
        click_seconds = click_ratio * self.video_duration
        start_seconds = self.time_to_seconds(self.start_time.get())
        end_seconds = self.time_to_seconds(self.end_time.get())
        start_x = (start_seconds / self.video_duration) * canvas_width
        end_x = (end_seconds / self.video_duration) * canvas_width
        if abs(event.x - start_x) < 12:
            self.dragging_start = True
        elif abs(event.x - end_x) < 12:
            self.dragging_end = True
        else:
            if abs(click_seconds - start_seconds) < abs(click_seconds - end_seconds):
                self.start_time.set(self.seconds_to_time(click_seconds))
            else:
                self.end_time.set(self.seconds_to_time(click_seconds))

    def on_timeline_drag(self, event):
        if self.video_duration <= 0:
            return
        canvas_width = self.timeline_canvas.winfo_width()
        if canvas_width <= 1:
            canvas_width = 800
        drag_ratio = max(0, min(1, event.x / canvas_width))
        drag_seconds = drag_ratio * self.video_duration
        if self.dragging_start:
            self.start_time.set(self.seconds_to_time(drag_seconds))
        elif self.dragging_end:
            self.end_time.set(self.seconds_to_time(drag_seconds))

    def on_timeline_release(self, event):
        self.dragging_start = False
        self.dragging_end = False

    def on_time_changed(self, *args):
        # Enforce start < end
        start_seconds = self.time_to_seconds(self.start_time.get())
        end_seconds = self.time_to_seconds(self.end_time.get())
        if start_seconds >= end_seconds:
            # Auto-correct: set end to start+1s
            self.end_time.set(self.seconds_to_time(start_seconds + 1))
        self.update_duration()
        self.draw_timeline()
        self.update_output_name()

    def update_duration(self):
        start_seconds = self.time_to_seconds(self.start_time.get())
        end_seconds = self.time_to_seconds(self.end_time.get())
        if end_seconds > start_seconds:
            duration = end_seconds - start_seconds
            self.duration_label.config(text=self.seconds_to_time(duration))
        else:
            self.duration_label.config(text="0:00")

    def time_to_seconds(self, time_str):
        try:
            parts = time_str.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                return 0
        except Exception:
            return 0

    def seconds_to_time(self, seconds):
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def sanitize_filename(self, name):
        # Remove or replace characters not allowed in Windows filenames
        return re.sub(r'[<>:"/\\|?*]', "_", name)

    def update_output_name(self, *args):
        input_path = self.input_file.get()
        if input_path:
            input_path_obj = Path(input_path)
            base_name = self.sanitize_filename(input_path_obj.stem)
            if self.trim_enabled.get():
                start_str = self.start_time.get().replace(":", "-")
                end_str = self.end_time.get().replace(":", "-")
                output_name = f"{base_name}-{start_str}-{end_str}-clip.mp4"
            else:
                output_name = f"{base_name}-clip.mp4"
            self.custom_output_name.set(output_name)

    def process_video(self):
        if not self.input_file.get():
            messagebox.showerror("Error", "Please select an input video file first!")
            return
        if self.is_processing:
            messagebox.showinfo(
                "Processing", "Video is already being processed. Please wait."
            )
            return
        if self.trim_enabled.get():
            start_seconds = self.time_to_seconds(self.start_time.get())
            end_seconds = self.time_to_seconds(self.end_time.get())
            if start_seconds >= end_seconds:
                messagebox.showerror("Error", "Start time must be before end time!")
                return
            if end_seconds > self.video_duration:
                messagebox.showerror("Error", "End time cannot exceed video duration!")
                return
        input_path_obj = Path(self.input_file.get())
        output_name = self.custom_output_name.get()
        if not output_name.endswith(".mp4"):
            output_name += ".mp4"
        output_path = input_path_obj.parent / output_name
        # No confirmation dialog, just start processing
        self.start_processing(str(output_path))

    def start_processing(self, output_path):
        self.is_processing = True
        self.process_btn.config(state="disabled")
        self.status_label.config(
            text="Processing video... Please wait.", style="Info.TLabel"
        )
        thread = threading.Thread(target=self.run_ffmpeg, args=(output_path,))
        thread.daemon = True
        thread.start()

    def run_ffmpeg(self, output_path):
        try:
            input_path = self.input_file.get()
            preset = self.selected_preset.get()
            command = ["ffmpeg", "-y", "-i", input_path, "-sn"]
            if self.trim_enabled.get():
                start_seconds = self.time_to_seconds(self.start_time.get())
                duration = self.time_to_seconds(self.end_time.get()) - start_seconds
                command.extend(["-ss", str(start_seconds), "-t", str(duration)])
            command.extend(
                [
                    "-vf",
                    "scale=1920:1080,fps=120",
                    "-vcodec",
                    "libx264",
                    "-crf",
                    "24",
                    "-preset",
                    preset,
                    "-acodec",
                    "aac",
                    "-b:a",
                    "128k",
                    output_path,
                ]
            )
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            self.root.after(
                0,
                self.processing_complete,
                True,
                "Video processing completed successfully!",
            )
        except subprocess.CalledProcessError as e:
            # Only show error if it's not about subtitles or overwriting
            if "subtitle" in e.stderr or "Invalid argument" in e.stderr:
                error_msg = "FFmpeg warning: Subtitle or output file issue ignored."
            else:
                error_msg = f"FFmpeg error: {e.stderr}"
            self.root.after(0, self.processing_complete, False, error_msg)
        except FileNotFoundError:
            error_msg = "FFmpeg not found! Please make sure FFmpeg is installed and available in your system PATH."
            self.root.after(0, self.processing_complete, False, error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.root.after(0, self.processing_complete, False, error_msg)

    def processing_complete(self, success, message):
        self.is_processing = False
        self.process_btn.config(state="normal")
        if success:
            self.status_label.config(text="✅ " + message, style="Success.TLabel")
            messagebox.showinfo("Success", message)
        else:
            self.status_label.config(text="❌ Processing failed", style="Error.TLabel")
            messagebox.showerror("Error", message)


def main():
    root = tk.Tk()
    app = ClipperGUI(root)
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    root.mainloop()


if __name__ == "__main__":
    main()
