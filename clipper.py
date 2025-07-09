import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import sys
import threading
from pathlib import Path
import json
import re
import urllib.request
import urllib.parse
import time
from typing import Optional, List
from dataclasses import dataclass

# Ensure FFmpeg and FFprobe work from bundled folder
if getattr(sys, "frozen", False):
    # Running from PyInstaller bundle
    ffmpeg_dir = os.path.join(sys._MEIPASS, "bin")
else:
    # Running normally (script or IDE)
    ffmpeg_dir = os.path.join(os.path.dirname(__file__), "bin")

os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ["PATH"]

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

# UI Configuration
WINDOW_MIN_WIDTH = 700
WINDOW_START_Y_PERCENT = 33  # Start window at 33% from top of screen

# File Configuration
SUPPORTED_VIDEO_FORMATS = [".mp4", ".webm", ".mkv", ".avi", ".mov", ".wmv", ".flv"]
MAX_FILE_SIZE_MB = 1024  # 1GB limit for uploads

# Time Configuration
DEFAULT_START_TIME = "0:00"
DEFAULT_END_TIME = "0:00"
TIME_FORMAT_REGEX = r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$"

# FFmpeg Configuration
FFMPEG_TIMEOUT_SECONDS = 300  # 5 minutes
FFMPEG_VERSION_TIMEOUT = 5

# Upload Configuration
UPLOAD_TIMEOUT_SECONDS = 60
UPLOAD_BOUNDARY_PREFIX = "----WebKitFormBoundary"

# UI Colors (Material Design inspired)
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

# Encoding Presets
ENCODING_PRESETS = [
    ("Very Fast", "veryfast"),
    ("Fast", "fast"),
    ("Medium", "medium"),
    ("Slow", "slow"),
    ("Very Slow", "veryslow"),
]

# Video Codecs
VIDEO_CODECS = [
    ("H.264", "libx264"),
    ("H.265 (HEVC)", "libx265"),
    ("VP9", "libvpx-vp9"),
]

# Container Formats
CONTAINER_FORMATS = [
    ("MP4", "mp4"),
    ("MKV", "mkv"),
    ("WebM", "webm"),
]

# CRF Values
CRF_OPTIONS = ["18", "20", "23", "25", "28"]

# FPS Options
FPS_OPTIONS = ["24", "30", "60", "120"]

# Audio Bitrate Options
AUDIO_BITRATE_OPTIONS = ["320k", "256k", "192k", "128k", "96k", "64k", "Remove Audio"]

# Resolution Options
RESOLUTION_OPTIONS = [
    ("3840x2160", "3840:2160"),  # 4K
    ("2560x1440", "2560:1440"),  # 2K
    ("1920x1080", "1920:1080"),
    ("1280x720", "1280:720"),
    ("854x480", "854:480"),
    ("640x360", "640:360"),
]


@dataclass
class SubtitleStream:
    index: int
    map_index: int
    codec_name: str
    language: str
    title: str = ""


@dataclass
class AudioStream:
    index: int
    codec_name: str
    language: str
    title: str = ""


@dataclass
class UploadService:
    key: str
    name: str
    url: str
    field_name: str
    reqtype: Optional[str]
    max_size_mb: int
    expiration: str


UPLOAD_SERVICES_LIST: List[UploadService] = [
    UploadService(
        key="catbox",
        name="catbox.moe",
        url="https://catbox.moe/user/api.php",
        field_name="fileToUpload",
        reqtype="fileupload",
        max_size_mb=200,
        expiration="Indefinite",
    ),
    UploadService(
        key="uguu",
        name="uguu.se",
        url="https://uguu.se/upload",
        field_name="files[]",
        reqtype=None,
        max_size_mb=134,
        expiration="~3 hours",
    ),
    UploadService(
        key="tempsh",
        name="temp.sh",
        url="https://temp.sh/upload",
        field_name="file",
        reqtype=None,
        max_size_mb=4096,
        expiration="3 days",
    ),
]


def get_upload_service_by_key(key: str) -> Optional[UploadService]:
    for service in UPLOAD_SERVICES_LIST:
        if service.key == key:
            return service
    return None


class FFmpegCommandBuilder:
    def __init__(self):
        self.cmd = ["ffmpeg", "-y"]
        self._vf_filters = []
        self._af_filters = []
        self._has_subtitles = False
        self._has_speed = False
        self._setpts_filter = None

    def with_input(self, path):
        self.cmd.extend(["-i", path])
        return self

    def with_trim(self, start, duration):
        self.cmd.extend(["-ss", str(start), "-t", str(duration)])
        return self

    def with_hybrid_trim(self, start, duration):
        self.cmd.extend(["-ss", str(start)])
        self.input_added = True
        return self

    def with_post_input_trim(self, offset, duration):
        self.cmd.extend(["-ss", str(offset), "-t", str(duration)])
        return self

    def with_video_settings(self, scale, fps):
        filters = []
        if scale and scale != "" and scale != "None":
            filters.append(f"scale={scale}")
        if fps and fps != "" and fps != "None":
            filters.append(f"fps={fps}")
        if filters:
            self._vf_filters.extend(filters)
        return self

    def with_subtitles(self, sub_path, si_opt):
        self._has_subtitles = True
        self._vf_filters.insert(0, f"subtitles='{sub_path}{si_opt}'")
        return self

    def with_speed(self, speed: float):
        if speed != 1.0:
            self._has_speed = True
            self._setpts_filter = f"setpts=PTS/{speed}"
            # Audio speed adjustment (atempo only supports 0.5-2.0, so chain if needed)
            af_filters = []
            remaining = speed
            while remaining > 2.0:
                af_filters.append("atempo=2.0")
                remaining /= 2.0
            while remaining < 0.5:
                af_filters.append("atempo=0.5")
                remaining /= 0.5
            af_filters.append(f"atempo={remaining:.2f}")
            self._af_filters.extend(af_filters)
        return self

    def with_extra(self, extra_args):
        self.cmd.extend(extra_args)
        return self

    def with_map(self, map_args):
        self.cmd.extend(map_args)
        return self

    def with_codec(self, codec, crf, preset):
        self.cmd.extend(["-c:v", codec, "-crf", str(crf), "-preset", preset])
        return self

    def with_audio(self, codec, bitrate):
        self.cmd.extend(["-c:a", codec, "-b:a", bitrate])
        return self

    def build(self, output_path):
        vf_chain = list(self._vf_filters)
        if self._has_speed and self._setpts_filter:
            vf_chain.append(self._setpts_filter)
        if vf_chain:
            self.cmd.extend(["-vf", ",".join(vf_chain)])
        if self._af_filters:
            self.cmd.extend(["-filter:a", ",".join(self._af_filters)])
        return self.cmd + [output_path]

    def get_upload_service_info(self, service: str) -> Optional[UploadService]:
        """
        Get information about an upload service as a dataclass.
        """
        return get_upload_service_by_key(service)

    def validate_file_size_for_upload(self, file_path: str, service: str) -> bool:
        """
        Validate that the file size is within the upload service's limits.
        Args:
            file_path: Path to the file to upload
            service: Upload service key (catbox, uguu, tempsh)
        Returns:
            True if file size is acceptable, False otherwise
        """
        try:
            file_size_bytes = os.path.getsize(file_path)
            file_size_mb = file_size_bytes / (1024 * 1024)  # Convert to MB
            service_config = get_upload_service_by_key(service)
            if not service_config:
                messagebox.showerror("Error", f"Unknown upload service: {service}")
                return False
            max_size_mb = service_config.max_size_mb
            service_name = service_config.name
            if file_size_mb > max_size_mb:
                messagebox.showerror(
                    "File Too Large",
                    f"File size ({file_size_mb:.1f} MB) exceeds the limit for {service_name} ({max_size_mb} MB).\n\n"
                    f"Please choose a different upload service or reduce the file size.",
                )
                return False
            return True
        except (OSError, FileNotFoundError) as e:
            messagebox.showerror("Error", f"Could not check file size: {e}")
            return False


class ClipperGUI:
    """
    A minimal, modern, and accessible GUI for video trimming and encoding using FFmpeg.
    Features:
    - Drag-and-drop or browse for input video files
    - Optional trimming with timeline and seekbar, draggable or manual input
    - Output filename auto-generation and sanitization
    - Encoding preset selection
    - Advanced options for more control over the output video
    - Robust error handling and clear status feedback
    - Upload to fast and free file hosting services
    - Clean, dark, material-inspired UI (no extra dependencies)
    """

    def __init__(self, root: tk.Tk) -> None:
        """
        Initialize the Clipper GUI application.

        Args:
            root: The main Tkinter root window
        """
        self.root = root
        self.root.title("Clipper")
        self.root.resizable(True, True)

        # Configure style
        self.setup_styles()

        # Initialize variables with type hints
        self.input_file: tk.StringVar = tk.StringVar()
        self.output_file: tk.StringVar = tk.StringVar()
        self.custom_output_name: tk.StringVar = tk.StringVar()
        self.is_processing: bool = False
        self.selected_preset: tk.StringVar = tk.StringVar(value="medium")
        self.trim_enabled: tk.BooleanVar = tk.BooleanVar(value=False)
        self.start_time: tk.StringVar = tk.StringVar(value=DEFAULT_START_TIME)
        self.end_time: tk.StringVar = tk.StringVar(value=DEFAULT_END_TIME)
        self.video_duration: float = 0.0
        self.dragging_start: bool = False
        self.dragging_end: bool = False
        self.save_as_enabled: tk.BooleanVar = tk.BooleanVar(value=False)
        self.advanced_enabled: tk.BooleanVar = tk.BooleanVar(value=False)
        self.auto_copy_url: tk.BooleanVar = tk.BooleanVar(value=False)
        self.last_output_path: Optional[str] = None
        self.upload_service: tk.StringVar = tk.StringVar(value="catbox")
        self.upload_url: tk.StringVar = tk.StringVar(value="")

        # Processing state
        self.cancel_requested: bool = False
        self.ffmpeg_process: Optional[subprocess.Popen] = None
        self.processing_thread: Optional[threading.Thread] = None

        self.setup_ui()

        # --- Widget grouping for UI state ---
        self.main_controls = [
            self.input_entry,
            self.browse_btn,
            self.save_as_checkbox,
            self.output_entry,
            self.process_btn,
            self.reset_btn,
            self.trim_check,
            self.advanced_checkbox,
            self.start_entry,
            self.end_entry,
        ]
        self.advanced_controls = [
            self.codec_menu,
            self.crf_menu,
            self.fps_menu,
            self.audio_bitrate_menu,
            self.resolution_menu,
            self.container_menu,
            self.track_selection_frame,
            self.speed_menu,
        ]
        self.upload_controls = [
            self.catbox_radio,
            self.uguu_radio,
            self.tempsh_radio,
            self.upload_btn,
            self.upload_checkbox,
            self.copy_url_btn,
            self.open_in_browser_btn,
        ]
        self.file_controls = [self.open_file_btn, self.show_in_explorer_btn]
        self.cancel_control = [self.cancel_btn]

    def setup_styles(self) -> None:
        """Configure the application's visual styles and themes."""
        style = ttk.Style()
        style.theme_use("clam")
        c = COLORS  # Use the global COLORS constant

        # Configure frame styles
        style.configure("TFrame", background=c["surface"])
        style.configure("TLabel", background=c["surface"], foreground=c["text_primary"])

        # Configure label styles
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

        # Configure button styles
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
            "Danger.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(16, 8),
            background=c["error"],
            foreground=c["text_primary"],
            relief="flat",
            borderwidth=0,
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#b71c1c"), ("pressed", "#b71c1c")],
        )

        # Configure frame and label frame styles
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

        # Configure radio button and checkbox styles
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

        # Configure entry styles
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

        # Configure progress bar styles
        style.layout(
            "Blue.Horizontal.TProgressbar",
            [
                (
                    "Horizontal.Progressbar.trough",
                    {
                        "children": [
                            (
                                "Horizontal.Progressbar.pbar",
                                {"side": "left", "sticky": "ns"},
                            )
                        ],
                        "sticky": "nswe",
                    },
                )
            ],
        )
        style.configure(
            "Blue.Horizontal.TProgressbar",
            troughcolor=c["surface_elevated"],
            bordercolor=c["surface_border"],
            background=c["primary"],
            lightcolor=c["primary"],
            darkcolor=c["primary"],
            thickness=16,
        )

    def create_scrollable_checkbox_frame(self, parent, max_height=60):
        """Create a compact scrollable frame with checkboxes for track selection."""
        # Create a frame to hold the canvas and scrollbar
        container_frame = ttk.Frame(parent)
        container_frame.columnconfigure(0, weight=1)
        container_frame.rowconfigure(0, weight=1)

        canvas = tk.Canvas(
            container_frame,
            height=max_height,
            borderwidth=0,
            background="#23272b",
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(
            container_frame, orient="vertical", command=canvas.yview
        )
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Pack the container frame into the parent
        container_frame.pack(fill="both", expand=True)

        return scroll_frame, canvas, scrollbar

    def setup_ui(self) -> None:
        """Set up the main user interface components."""
        self.root.configure(bg=COLORS["surface"])
        main_container = ttk.Frame(self.root, padding="15")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)

        # Input file section
        self._setup_input_section(main_container)

        # Trimming section
        self._setup_trimming_section(main_container)

        # Output filename section
        self._setup_output_section(main_container)

        # Preset section
        self._setup_preset_section(main_container)

        # Advanced options section
        self._setup_advanced_section(main_container)

        # Status and progress section
        self._setup_status_section(main_container)

        # Button section
        self._setup_button_section(main_container)

        # Upload section
        self._setup_upload_section(main_container)

        # Bind events
        self._bind_events()

        # Auto-adjust window size
        self.root.update_idletasks()
        self.root.geometry("")  # Let the window size itself

    def _setup_input_section(self, container):
        input_label = ttk.Label(container, text="Input File:", style="Subtitle.TLabel")
        input_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 4))
        file_selection_frame = ttk.Frame(container)
        file_selection_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        file_selection_frame.columnconfigure(0, weight=1)
        self.input_entry = ttk.Entry(
            file_selection_frame, textvariable=self.input_file, font=("Segoe UI", 9)
        )
        self.input_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 8))
        self.browse_btn = ttk.Button(
            file_selection_frame,
            text="Browse",
            command=self.browse_input_file,
            style="Secondary.TButton",
        )
        self.browse_btn.grid(row=0, column=1)
        self.file_info_label = ttk.Label(
            container, text="No file selected", style="Info.TLabel"
        )
        self.file_info_label.grid(row=2, column=0, pady=(8, 0), sticky=tk.W)

    def _setup_trimming_section(self, container):
        # Trimming toggle (pill style)
        self.trim_check = ttk.Checkbutton(
            container,
            text="Enable Video Trimming",
            variable=self.trim_enabled,
            command=self.toggle_trim_section,
            style="Pill.TCheckbutton",
        )
        self.trim_check.grid(row=3, column=0, sticky=tk.W, pady=(8, 8), padx=0)
        # Timeline section (pill/box style)
        self.timeline_frame = ttk.LabelFrame(
            container,
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

    def _setup_output_section(self, container):
        ttk.Label(container, text="Output Filename:", style="Subtitle.TLabel").grid(
            row=5, column=0, sticky=tk.W, pady=(8, 0)
        )
        output_file_row = ttk.Frame(container)
        output_file_row.grid(row=6, column=0, sticky=(tk.W, tk.E), pady=(0, 4))
        output_file_row.columnconfigure(0, weight=1)
        self.output_entry = ttk.Entry(
            output_file_row, textvariable=self.custom_output_name, font=("Segoe UI", 9)
        )
        self.output_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 8))
        # Open button (hidden by default)
        self.open_file_btn = ttk.Button(
            output_file_row,
            text="Open",
            command=self.open_output_file,
            style="Secondary.TButton",
        )
        self.open_file_btn.grid(row=0, column=2)
        self.open_file_btn.grid_remove()
        # Show in File Explorer button (hidden by default)
        self.show_in_explorer_btn = ttk.Button(
            output_file_row,
            text="Show in File Explorer",
            command=self.show_in_file_explorer,
            style="Secondary.TButton",
        )
        self.show_in_explorer_btn.grid(row=0, column=3, padx=(8, 0))
        self.show_in_explorer_btn.grid_remove()
        # Save As checkbox
        self.save_as_enabled = tk.BooleanVar(value=False)
        self.save_as_checkbox = ttk.Checkbutton(
            container,
            text="Custom Output Name and Location (Save As...)",
            variable=self.save_as_enabled,
            style="Pill.TCheckbutton",
        )
        self.save_as_checkbox.grid(row=7, column=0, sticky=tk.W, pady=(0, 8))

    def _setup_preset_section(self, container):
        ttk.Label(container, text="Preset:", style="Subtitle.TLabel").grid(
            row=8, column=0, sticky=tk.W, pady=(8, 8)
        )

        # Use the global ENCODING_PRESETS constant
        self.preset_radios = []
        preset_buttons_frame = ttk.Frame(container)
        preset_buttons_frame.grid(row=9, column=0, sticky="ew", pady=(0, 8))
        container.columnconfigure(0, weight=1)

        for i in range(len(ENCODING_PRESETS)):
            preset_buttons_frame.columnconfigure(i, weight=1)

        for i, (label, value) in enumerate(ENCODING_PRESETS):
            rb = ttk.Radiobutton(
                preset_buttons_frame,
                text=label,
                variable=self.selected_preset,
                value=value,
                style="Pill.TRadiobutton",
            )
            rb.grid(row=0, column=i, padx=4, pady=2, sticky="ew")
            self.preset_radios.append(rb)

    def _setup_advanced_section(self, container):
        # Advanced checkbox
        self.advanced_enabled = tk.BooleanVar(value=False)
        self.advanced_checkbox = ttk.Checkbutton(
            container,
            text="Advanced",
            variable=self.advanced_enabled,
            command=self.toggle_advanced_options,
            style="Pill.TCheckbutton",
        )
        self.advanced_checkbox.grid(row=10, column=0, sticky=tk.W, pady=(0, 0))

        # Advanced options frame (hidden by default)
        self.advanced_frame = ttk.Frame(container)
        self.advanced_frame.grid(row=11, column=0, sticky=(tk.W, tk.E), pady=(8, 0))
        self.advanced_frame.columnconfigure(0, weight=1)
        self.advanced_frame.columnconfigure(1, weight=1)
        self.advanced_frame.columnconfigure(2, weight=1)
        self.advanced_frame.columnconfigure(3, weight=1)
        self.advanced_frame.columnconfigure(4, weight=1)
        self.advanced_frame.columnconfigure(5, weight=1)
        self.advanced_frame.columnconfigure(6, weight=1)

        # Video Codec
        ttk.Label(
            self.advanced_frame, text="Video Codec:", style="Subtitle.TLabel"
        ).grid(row=0, column=0, sticky=tk.W)

        self.selected_codec = tk.StringVar(value="H.264")
        self.codec_menu = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.selected_codec,
            values=[label for label, val in VIDEO_CODECS],
            state="readonly",
            width=12,
            font=("Segoe UI", 9),
        )
        self.codec_menu.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 8))
        self.codec_menu.current(0)
        self.codec_menu.configure(style="TCombobox")
        self.codec_menu.bind("<<ComboboxSelected>>", self.on_codec_changed)

        # CRF
        ttk.Label(self.advanced_frame, text="CRF:", style="Subtitle.TLabel").grid(
            row=0, column=1, sticky=tk.W
        )
        self.selected_crf = tk.StringVar(value=CRF_OPTIONS[1])  # Default to "20"
        self.crf_menu = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.selected_crf,
            values=CRF_OPTIONS,
            state="normal",
            width=4,
            font=("Segoe UI", 9),
        )
        self.crf_menu.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 8))

        # FPS
        ttk.Label(self.advanced_frame, text="FPS:", style="Subtitle.TLabel").grid(
            row=0, column=2, sticky=tk.W
        )
        self.selected_fps = tk.StringVar(value="60")  # Default to "60"
        self.fps_menu = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.selected_fps,
            values=FPS_OPTIONS,
            state="normal",
            width=4,
            font=("Segoe UI", 9),
        )
        self.fps_menu.grid(row=1, column=2, sticky=(tk.W, tk.E), padx=(0, 8))

        # Audio Bitrate
        ttk.Label(
            self.advanced_frame, text="Audio Bitrate:", style="Subtitle.TLabel"
        ).grid(row=0, column=3, sticky=tk.W)
        self.selected_audio_bitrate = tk.StringVar(
            value=AUDIO_BITRATE_OPTIONS[3]
        )  # Default to "128k"
        self.audio_bitrate_menu = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.selected_audio_bitrate,
            values=AUDIO_BITRATE_OPTIONS,
            state="normal",
            width=8,
        )
        self.audio_bitrate_menu.grid(row=1, column=3, padx=(0, 8), sticky="ew")

        # Resolution
        ttk.Label(
            self.advanced_frame, text="Resolution:", style="Subtitle.TLabel"
        ).grid(row=0, column=4, sticky=tk.W)
        self.selected_resolution = tk.StringVar(value="1920x1080")
        self.resolution_menu = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.selected_resolution,
            values=[label for label, val in RESOLUTION_OPTIONS],
            state="normal",
            width=10,
            font=("Segoe UI", 9),
        )
        self.resolution_menu.grid(row=1, column=4, sticky=(tk.W, tk.E), padx=(0, 8))

        # Container Format
        ttk.Label(
            self.advanced_frame, text="Container Format:", style="Subtitle.TLabel"
        ).grid(row=0, column=5, sticky=tk.W)
        self.selected_container = tk.StringVar(value="mp4")
        self.container_menu = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.selected_container,
            values=[label for label, val in CONTAINER_FORMATS],
            state="readonly",
            width=8,
            font=("Segoe UI", 9),
        )
        self.container_menu.grid(row=1, column=5, sticky=(tk.W, tk.E), padx=(0, 8))
        self.container_menu.current(0)
        self.container_menu.configure(style="TCombobox")
        self.container_menu.bind("<<ComboboxSelected>>", self.on_container_changed)

        # Speed Multiplier
        ttk.Label(self.advanced_frame, text="Speed:", style="Subtitle.TLabel").grid(
            row=0, column=6, sticky=tk.W
        )
        self.selected_speed = tk.StringVar(value="1.0x (Normal)")
        self.speed_menu = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.selected_speed,
            values=["1.0x (Normal)", "0.5x", "0.75x", "1.5x", "1.75x", "2.0x", "4.0x"],
            state="readonly",
            width=10,
            font=("Segoe UI", 9),
        )
        self.speed_menu.grid(row=1, column=6, sticky=(tk.W, tk.E), padx=(0, 8))

        # Subtitles and Audio Tracks (expandable checkbox, always single-select)
        self.include_tracks = tk.BooleanVar(value=False)
        self.include_tracks_checkbox = ttk.Checkbutton(
            self.advanced_frame,
            text="Subtitles and Audio Tracks",
            variable=self.include_tracks,
            command=self.toggle_track_selection,
            style="Pill.TCheckbutton",
        )
        self.include_tracks_checkbox.grid(row=2, column=0, sticky=tk.W, pady=(8, 0))
        self.include_tracks_checkbox.grid_remove()
        # Track selection frame (hidden by default, shown when checkbox is checked)
        self.track_selection_frame = ttk.Frame(self.advanced_frame)
        self.track_selection_frame.grid(
            row=3, column=0, columnspan=6, sticky="ew", pady=(4, 8)
        )
        self.track_selection_frame.columnconfigure(0, weight=1)
        self.track_selection_frame.columnconfigure(1, weight=1)
        self.track_selection_frame.grid_remove()
        # Subtitle track selection (left side)
        self.subtitle_streams = []
        self.subtitle_combobox = None
        self.subtitle_combobox_holder = ttk.Frame(self.track_selection_frame)
        self.subtitle_combobox_holder.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.subtitle_combobox_holder.grid_remove()
        # Audio track selection (right side)
        self.audio_streams = []
        self.audio_combobox = None
        self.audio_combobox_holder = ttk.Frame(self.track_selection_frame)
        self.audio_combobox_holder.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.audio_combobox_holder.grid_remove()

        self.advanced_frame.grid_remove()

    def _setup_status_section(self, container):
        self.status_label = ttk.Label(
            container, text="Ready to process video", style="Info.TLabel"
        )
        self.status_label.grid(row=12, column=0, pady=(16, 4))
        # Progress bar frame (fixed height)
        self.progress_frame = ttk.Frame(container, height=24)
        self.progress_frame.grid_propagate(False)
        self.progress_frame.grid(row=13, column=0, sticky="ew", pady=(0, 8))
        # Progress bar (inside frame)
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            orient="horizontal",
            length=300,
            mode="determinate",
            maximum=100,
            style="Blue.Horizontal.TProgressbar",
        )
        self.progress_bar.pack(fill="x", expand=True)
        self.progress_bar.pack_forget()  # Hide initially

    def _setup_button_section(self, container):
        button_frame = ttk.Frame(container)
        button_frame.grid(row=14, column=0, pady=(0, 8), sticky=(tk.W, tk.E))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=0)
        # Process Video button (center)
        self.process_btn = ttk.Button(
            button_frame,
            text="Process Video",
            command=self.process_video,
            style="Success.TButton",
        )
        self.process_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        # Cancel button (center, hidden by default)
        self.cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel_processing,
            style="Danger.TButton",
        )
        self.cancel_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.cancel_btn.grid_remove()
        # Reset button (always to the right)
        self.reset_btn = ttk.Button(
            button_frame,
            text="Reset",
            command=self.reset_settings,
            style="Secondary.TButton",
        )
        self.reset_btn.grid(row=0, column=1, sticky=tk.E)

    def _setup_upload_section(self, container):
        # Upload section (hidden by default)
        self.upload_frame = ttk.Frame(container)
        self.upload_frame.grid(row=15, column=0, pady=(8, 0), sticky=(tk.W, tk.E))
        self.upload_frame.columnconfigure(0, weight=1)
        self.upload_frame.columnconfigure(1, weight=0)
        self.upload_frame.columnconfigure(2, weight=0)
        # Upload service selection row
        upload_service_row = ttk.Frame(self.upload_frame)
        upload_service_row.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 0))
        for i in range(3):
            upload_service_row.columnconfigure(i, weight=0)
        upload_service_row.columnconfigure(3, weight=1)
        ttk.Label(
            upload_service_row, text="Upload Service:", style="Subtitle.TLabel"
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 0), padx=(0, 8))
        self.catbox_radio = ttk.Radiobutton(
            upload_service_row,
            text="catbox.moe",
            variable=self.upload_service,
            value="catbox",
            style="Pill.TRadiobutton",
        )
        self.catbox_radio.grid(row=0, column=1, padx=(0, 8), pady=2, sticky="w")
        self.uguu_radio = ttk.Radiobutton(
            upload_service_row,
            text="uguu.se",
            variable=self.upload_service,
            value="uguu",
            style="Pill.TRadiobutton",
        )
        self.uguu_radio.grid(row=0, column=2, padx=(0, 8), pady=2, sticky="w")
        self.tempsh_radio = ttk.Radiobutton(
            upload_service_row,
            text="temp.sh",
            variable=self.upload_service,
            value="tempsh",
            style="Pill.TRadiobutton",
        )
        self.tempsh_radio.grid(row=0, column=3, padx=(0, 8), pady=2, sticky="w")
        # Upload button to the right
        self.upload_btn = ttk.Button(
            upload_service_row,
            text="Upload",
            command=self.upload_to_selected_service,
            style="Primary.TButton",
        )
        self.upload_btn.grid(row=0, column=4, sticky=tk.E, padx=(8, 0))
        # Auto-copy checkbox below
        self.upload_checkbox = ttk.Checkbutton(
            self.upload_frame,
            text="Auto-copy upload URL to clipboard",
            variable=self.auto_copy_url,
            style="Pill.TCheckbutton",
        )
        self.upload_checkbox.grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        # Upload URL display and copy/open buttons row
        url_row = ttk.Frame(self.upload_frame)
        url_row.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(8, 0))
        url_row.columnconfigure(0, weight=1)
        self.upload_url_entry = ttk.Entry(
            url_row,
            textvariable=self.upload_url,
            font=("Segoe UI", 9),
            state="readonly",
            width=50,  # Make it wider
        )
        self.upload_url_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 8))
        self.copy_url_btn = ttk.Button(
            url_row,
            text="Copy",
            command=self.copy_upload_url,
            style="Secondary.TButton",
        )
        self.copy_url_btn.grid(row=0, column=1)
        self.open_in_browser_btn = ttk.Button(
            url_row,
            text="Open in Browser",
            command=self.open_upload_url_in_browser,
            style="Secondary.TButton",
        )
        self.open_in_browser_btn.grid(row=0, column=2, padx=(8, 0))
        url_row.grid_remove()
        self.url_row = url_row

    def _bind_events(self):
        self.input_file.trace("w", self.on_file_selected)
        self.start_time.trace("w", self.on_time_changed)
        self.end_time.trace("w", self.on_time_changed)

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
        self.root.update_idletasks()
        self.root.geometry("")
        self.root.update()

    def browse_input_file(self) -> None:
        """Open file dialog to select input video file."""
        filetypes = [
            ("Video files", f"*{' *'.join(SUPPORTED_VIDEO_FORMATS)}"),
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
            # Fetch duration in a background thread to avoid UI freeze
            def _update_duration_bg():
                self.get_video_duration(input_path)
                self.root.after(0, self.draw_timeline)

            threading.Thread(target=_update_duration_bg, daemon=True).start()
            self.update_output_name()
            filename = os.path.basename(input_path)
            self.file_info_label.config(
                text=f"Selected: {filename}", style="Success.TLabel"
            )
            # Detect subtitle and audio streams
            subs = self.get_video_subtitle_streams(input_path)
            self.subtitle_streams = subs
            audio_streams = self.get_video_audio_streams(input_path)
            self.audio_streams = audio_streams
            self.audio_indices = [s.index for s in audio_streams]

            # Show track selection checkbox if we have any tracks
            if subs or audio_streams:
                self.include_tracks_checkbox.grid()
                # Setup track selection UI based on container format
                self.setup_track_selection_ui(subs, audio_streams)
            else:
                self.include_tracks_checkbox.grid_remove()
                self.include_tracks.set(False)
                self.track_selection_frame.grid_remove()

            if not self.is_processing:
                self.set_processing_ui_state(False)

            # Update container-specific UI state
            self.on_container_changed()

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
        except Exception:
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
        self.timeline_canvas.update_idletasks()
        self.timeline_canvas.update()

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
        # Don't auto-correct user input, just update display
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

    def time_to_seconds(self, time_str: str) -> float:
        """
        Convert time string to seconds with minimal validation.

        Args:
            time_str: Time string in MM:SS or HH:MM:SS format

        Returns:
            Time in seconds, or 0 if invalid
        """
        try:
            parts = time_str.split(":")

            if len(parts) == 2:
                minutes, seconds = map(int, parts)
                if seconds >= 60:
                    return 0.0  # Invalid, but don't show error yet
                if minutes < 0:
                    return 0.0  # Invalid, but don't show error yet
                return minutes * 60 + seconds

            elif len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                if seconds >= 60:
                    return 0.0  # Invalid, but don't show error yet
                if minutes >= 60:
                    return 0.0  # Invalid, but don't show error yet
                if hours < 0:
                    return 0.0  # Invalid, but don't show error yet
                return hours * 3600 + minutes * 60 + seconds

            else:
                return 0.0  # Invalid format, but don't show error yet

        except (ValueError, TypeError):
            return 0.0  # Invalid input, but don't show error yet

    def validate_time_format(self, time_str: str) -> bool:
        """
        Validate time format and show error if invalid.

        Args:
            time_str: Time string to validate

        Returns:
            True if valid, False otherwise
        """
        # Handle empty strings - not an error
        if not time_str or time_str.strip() == "":
            return True

        try:
            parts = time_str.split(":")

            if len(parts) == 2:
                minutes, seconds = map(int, parts)
                if seconds >= 60:
                    messagebox.showerror(
                        "Invalid Time",
                        f"Seconds must be 0-59, got {seconds}",
                    )
                    return False
                if minutes < 0:
                    messagebox.showerror(
                        "Invalid Time",
                        f"Minutes cannot be negative: {minutes}",
                    )
                    return False
                return True

            elif len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                if seconds >= 60:
                    messagebox.showerror(
                        "Invalid Time",
                        f"Seconds must be 0-59, got {seconds}",
                    )
                    return False
                if minutes >= 60:
                    messagebox.showerror(
                        "Invalid Time",
                        f"Minutes must be 0-59, got {minutes}",
                    )
                    return False
                if hours < 0:
                    messagebox.showerror(
                        "Invalid Time",
                        f"Hours cannot be negative: {hours}",
                    )
                    return False
                return True

            else:
                messagebox.showerror(
                    "Invalid Time",
                    f"Invalid time format: {time_str}\nPlease use MM:SS or HH:MM:SS",
                )
                return False

        except (ValueError, TypeError):
            messagebox.showerror(
                "Invalid Time",
                f"Invalid time format: {time_str}\nPlease use MM:SS or HH:MM:SS",
            )
            return False

    def seconds_to_time(self, seconds: float) -> str:
        """
        Convert seconds to MM:SS format.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string
        """
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"

    def sanitize_filename(self, name: str) -> str:
        """
        Remove or replace characters not allowed in Windows filenames.

        Args:
            name: Original filename

        Returns:
            Sanitized filename safe for Windows
        """
        return re.sub(r'[<>:"/\\|?*]', "_", name)

    def update_output_name(self, *args) -> None:
        """Update the output filename based on current settings."""
        input_path = self.input_file.get()
        if input_path:
            input_path_obj = Path(input_path)
            base_name = self.sanitize_filename(input_path_obj.stem)
            if input_path_obj.suffix.lower() in SUPPORTED_VIDEO_FORMATS:
                base_name = input_path_obj.stem
            if self.trim_enabled.get():
                start_str = self.start_time.get().replace(":", "-")
                end_str = self.end_time.get().replace(":", "-")
                output_name = f"{base_name}-{start_str}-{end_str}-clip"
            else:
                output_name = f"{base_name}-clip"
            # Extension based on container
            container_label = self.selected_container.get()
            ext = ".mp4"
            for label, val in CONTAINER_FORMATS:
                if label == container_label:
                    ext = f".{val}"
            output_name += ext
            self.custom_output_name.set(output_name)

    def _validate_inputs(self):
        """Validate all user inputs before processing"""
        # Check FFmpeg installation
        if not self.check_ffmpeg_installation():
            messagebox.showerror(
                "Error",
                "FFmpeg not found! Please install FFmpeg and ensure it's in your system PATH.",
            )
            return False

        # Check input file
        if not self.input_file.get():
            messagebox.showerror("Error", "Please select an input video file first!")
            return False

        input_path = Path(self.input_file.get())
        if not input_path.exists():
            messagebox.showerror("Error", "Input file does not exist!")
            return False

        # Validate time inputs if trimming is enabled
        if self.trim_enabled.get():
            # Validate time formats first
            if not self.validate_time_format(self.start_time.get()):
                return False
            if not self.validate_time_format(self.end_time.get()):
                return False

            start_seconds = self.time_to_seconds(self.start_time.get())
            end_seconds = self.time_to_seconds(self.end_time.get())

            if start_seconds >= end_seconds:
                messagebox.showerror("Error", "Start time must be before end time!")
                return False

            if end_seconds > self.video_duration:
                messagebox.showerror("Error", "End time cannot exceed video duration!")
                return False

        return True

    def set_processing_ui_state(self, processing: bool):
        """Enable/disable widgets based on processing state using grouped widget lists."""
        state = "disabled" if processing else "normal"
        for widget in self.main_controls:
            widget.config(state=state)
        adv_state = state if self.advanced_enabled.get() else "disabled"
        for widget in self.advanced_controls:
            # Frame widgets don't have a state option, so skip them
            if hasattr(widget, "config") and "state" in widget.config():
                widget.config(state=adv_state)
        # Explicitly handle speed_menu
        if hasattr(self, "speed_menu"):
            self.speed_menu.config(state=adv_state)
        # Explicitly handle include_tracks_checkbox, subtitle_combobox, audio_combobox
        if hasattr(self, "include_tracks_checkbox"):
            self.include_tracks_checkbox.config(state=adv_state)
        if hasattr(self, "subtitle_combobox") and self.subtitle_combobox:
            self.subtitle_combobox.config(state=adv_state)
        if hasattr(self, "audio_combobox") and self.audio_combobox:
            self.audio_combobox.config(state=adv_state)
        for widget in self.upload_controls:
            widget.config(state=state)
        for widget in self.file_controls:
            widget.config(state=state)
        # Cancel button always enabled during processing
        for widget in self.cancel_control:
            widget.config(state="normal" if processing else "disabled")

    def get_output_path(self) -> Optional[str]:
        """Centralized output file path and extension logic with logging and extension validation."""
        container_label = self.selected_container.get()
        ext = ".mp4"
        for label, val in CONTAINER_FORMATS:
            if label == container_label:
                ext = f".{val}"
        if self.save_as_enabled.get():
            output_path = filedialog.asksaveasfilename(
                defaultextension=ext,
                filetypes=[
                    (f"{container_label} files", f"*{ext}"),
                    ("All files", "*.*"),
                ],
                initialfile=self.custom_output_name.get(),
            )
            if not output_path:
                return None
            # Validate extension (prevent double-extension)
            base, file_ext = os.path.splitext(output_path)
            if file_ext.lower() != ext:
                output_path = base + ext
            self.custom_output_name.set(os.path.basename(output_path))
            return output_path
        else:
            input_path_obj = Path(self.input_file.get())
            output_name = self.custom_output_name.get()
            if not output_name.endswith(ext):
                output_name_path = Path(output_name)
                output_name = str(output_name_path.with_suffix(ext))
            output_path = input_path_obj.parent / output_name
            return str(output_path)

    def process_video(self):
        if self.is_processing:
            messagebox.showinfo(
                "Processing", "Video is already being processed. Please wait."
            )
            return

        # Validate all inputs before processing
        if not self._validate_inputs():
            return

        # Validate advanced options
        if self.advanced_enabled.get():
            # CRF
            crf = self.selected_crf.get()
            codec_label = self.selected_codec.get()
            try:
                crf_val = int(crf)
                if codec_label == "VP9":
                    if not (0 <= crf_val <= 63):
                        raise ValueError
                else:
                    if not (0 <= crf_val <= 51):
                        raise ValueError
            except Exception:
                messagebox.showerror(
                    "Error",
                    "CRF must be an integer within the valid range for the selected codec (0-51 for H.264/H.265, 0-63 for VP9).",
                )
                return
            # FPS
            fps = self.selected_fps.get()
            try:
                fps_val = int(fps)
                if not (1 <= fps_val <= 240):
                    raise ValueError
            except Exception:
                messagebox.showerror("Error", "FPS must be a positive integer (1-240).")
                return
            # Audio Bitrate
            audio_bitrate = self.selected_audio_bitrate.get()
            if audio_bitrate != "Remove Audio":
                try:
                    ab_val = int(audio_bitrate[:-1])
                    if not (8 <= ab_val <= 512):
                        raise ValueError
                except Exception:
                    messagebox.showerror(
                        "Error", "Audio Bitrate must be between 8k and 512k."
                    )
                    return
            # Resolution
            res = self.selected_resolution.get()
            if not re.match(r"^\d{2,5}x\d{2,5}$", res):
                messagebox.showerror(
                    "Error",
                    "Resolution must be in the form WIDTHxHEIGHT, e.g., 1920x1080.",
                )
                return
            w, h = map(int, res.lower().split("x"))
            if not (16 <= w <= 7680 and 16 <= h <= 4320):
                messagebox.showerror(
                    "Error", "Resolution width and height must be between 16 and 7680."
                )
                return
        # Use output path helper
        output_path = self.get_output_path()
        if not output_path:
            return
        self.start_processing(str(output_path))

    def start_processing(self, output_path):
        self.is_processing = True
        self.cancel_requested = False
        self.ffmpeg_process = None
        self.process_btn.grid_remove()
        self.cancel_btn.grid()
        self.reset_btn.grid(row=0, column=1, sticky=tk.E)
        self.reset_btn.config(state="disabled")
        self.status_label.config(
            text="Processing video... Please wait.", style="Info.TLabel"
        )
        self.progress_bar["value"] = 0
        self.progress_bar.pack(fill="x", expand=True)
        self.set_processing_ui_state(True)
        thread = threading.Thread(
            target=self.run_ffmpeg_with_progress, args=(output_path,)
        )
        thread.daemon = True
        self.processing_thread = thread
        thread.start()
        self.last_output_path = output_path

    def run_ffmpeg_with_progress(self, output_path):
        try:
            input_path = self.input_file.get()
            trimming = self.trim_enabled.get()
            if self.video_duration <= 0:
                self.get_video_duration(input_path)
            if self.advanced_enabled.get():
                codec_label = self.selected_codec.get()
                codec = dict(VIDEO_CODECS)[codec_label]
                crf = self.selected_crf.get()
                fps = self.selected_fps.get()
                audio_bitrate = self.selected_audio_bitrate.get()
                res_label = self.selected_resolution.get()
                preset_res_dict = dict(RESOLUTION_OPTIONS)
                if res_label in preset_res_dict:
                    resolution = preset_res_dict[res_label]
                else:
                    resolution = res_label.replace("x", ":")
                preset = self.selected_preset.get()
                speed_label = self.selected_speed.get()
                speed_value = 1.0
                if speed_label.startswith("1.0"):
                    speed_value = 1.0
                else:
                    speed_value = float(speed_label.split("x")[0])
                container_label = self.selected_container.get().lower()
            else:
                codec = "libx264"
                crf = "20"
                fps = "120"
                audio_bitrate = "128k"
                resolution = "1920:1080"
                preset = "medium"
                speed_value = 1.0
                container_label = "mp4"

            def get_input_info(path):
                try:
                    cmd = [
                        "ffprobe",
                        "-v",
                        "error",
                        "-select_streams",
                        "v:0",
                        "-show_entries",
                        "stream=width,height,r_frame_rate",
                        "-of",
                        "json",
                        path,
                    ]
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, check=True
                    )
                    data = json.loads(result.stdout)
                    stream = data["streams"][0]
                    width = int(stream["width"])
                    height = int(stream["height"])
                    fps_val = eval(stream["r_frame_rate"])
                    return width, height, fps_val
                except Exception:
                    return None, None, None

            input_w, input_h, input_fps = get_input_info(input_path)
            if self.advanced_enabled.get():
                selected_subtitle = None
                if (
                    self.include_tracks.get()
                    and self.subtitle_combobox
                    and self.subtitle_combobox.winfo_ismapped()
                ):
                    idx = self.subtitle_combobox.current()
                    if idx > 0 and idx <= len(self.subtitle_streams):
                        selected_subtitle = self.subtitle_streams[idx - 1]
                if (
                    self.include_tracks.get()
                    and self.audio_combobox
                    and self.audio_combobox.winfo_ismapped()
                ):
                    idx = self.audio_combobox.current()
                    if idx >= 0 and idx < len(self.audio_streams):
                        selected_audio_index = self.audio_streams[idx].index
                    else:
                        selected_audio_index = (
                            self.audio_streams[0].index if self.audio_streams else 0
                        )
                else:
                    selected_audio_index = (
                        self.audio_streams[0].index if self.audio_streams else 0
                    )
            else:
                selected_subtitle = None
                selected_audio_index = (
                    self.audio_streams[0].index if self.audio_streams else 0
                )
            builder = FFmpegCommandBuilder()
            use_copy = (
                not self.advanced_enabled.get()
                and not trimming
                and input_w is not None
                and input_h is not None
                and input_fps is not None
            )
            if use_copy:
                builder.with_input(input_path)
                builder.with_extra(["-c:v", "copy", "-c:a", "copy"])
            else:
                if trimming:
                    start_seconds = self.time_to_seconds(self.start_time.get())
                    duration = self.time_to_seconds(self.end_time.get()) - start_seconds
                    builder.with_hybrid_trim(start_seconds, duration)
                    builder.with_input(input_path)
                    builder.with_post_input_trim(0, duration)
                else:
                    builder.with_input(input_path)
                if selected_subtitle is not None:
                    if container_label in ("mp4", "webm"):
                        sub_path = self.escape_subtitles_path(input_path)
                        si_opt = f":si={selected_subtitle.map_index}"
                        builder.with_subtitles(sub_path, si_opt)
                        builder.with_video_settings(resolution, fps)
                        builder.with_speed(speed_value)
                        builder.with_extra(["-sn"])
                    elif container_label == "mkv":
                        builder.with_video_settings(resolution, fps)
                        builder.with_speed(speed_value)
                        builder.with_extra(
                            [
                                "-map",
                                f"0:s:{selected_subtitle.map_index}",
                                "-c:s",
                                "copy",
                            ]
                        )
                else:
                    scale_needed = True
                    fps_needed = True
                    if input_w and input_h and resolution:
                        try:
                            w, h = map(int, resolution.split(":"))
                            if w == input_w and h == input_h:
                                scale_needed = False
                        except Exception:
                            pass
                    if input_fps and fps:
                        try:
                            if float(fps) == float(input_fps):
                                fps_needed = False
                        except Exception:
                            pass
                    if scale_needed or fps_needed:
                        builder.with_video_settings(
                            resolution if scale_needed else None,
                            fps if fps_needed else None,
                        )
                    builder.with_speed(speed_value)
                    builder.with_extra(["-sn"])
                map_args = ["-map", "0:v"]
                if self.audio_streams:
                    audio_idx = (
                        self.audio_indices.index(selected_audio_index)
                        if selected_audio_index in self.audio_indices
                        else 0
                    )
                    map_args.extend(["-map", f"0:a:{audio_idx}"])
                builder.with_map(map_args)
                builder.with_codec(codec, crf, preset)
                if audio_bitrate == "Remove Audio":
                    builder.with_extra(["-an"])
                else:
                    builder.with_audio(
                        "libopus" if codec == "libvpx-vp9" else "aac", audio_bitrate
                    )
            command = builder.build(output_path)
            # Actually run the FFmpeg process and handle errors
            import re

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            self.ffmpeg_process = process
            time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
            last_percent = 0
            ffmpeg_stderr = []
            total_duration = duration if trimming else self.video_duration
            if total_duration <= 0:
                total_duration = 1
            # Read stderr lines as they come, but also collect all output for error analysis
            while True:
                if getattr(self, "cancel_requested", False):
                    try:
                        process.terminate()
                    except Exception:
                        pass
                    self.root.after(
                        0,
                        self.processing_complete,
                        False,
                        "Processing cancelled by user.",
                    )
                    return
                line = process.stderr.readline()
                if not line:
                    break
                ffmpeg_stderr.append(line)
                match = time_pattern.search(line)
                if match:
                    h, m, s = match.groups()
                    current = int(h) * 3600 + int(m) * 60 + float(s)
                    percent = int((current / total_duration) * 100)
                    percent = min(percent, 100)
                    if percent != last_percent:
                        last_percent = percent
                        self.root.after(0, self.progress_bar.config, {"value": percent})
            # After process ends, read any remaining stderr output (in case of buffer)
            remaining = process.stderr.read()
            if remaining:
                ffmpeg_stderr.extend(remaining.splitlines())
            process.wait()
            # Now check for errors as soon as process ends
            if process.returncode == 0:
                self.root.after(
                    0,
                    self.processing_complete,
                    True,
                    "Video processing completed successfully!",
                )
            else:
                error_lines = [line.strip() for line in ffmpeg_stderr if line.strip()]
                # Check for Unicode libass error
                unicode_libass_error = any(
                    "libass wasn't built with ASS_FEATURE_WRAP_UNICODE support" in line
                    for line in error_lines
                )
                if unicode_libass_error:
                    user_msg = (
                        "❌ FFmpeg/libass does not support Unicode subtitle line wrapping on your system.\n\n"
                        "This is required to burn many non-English subtitles.\n\n"
                        "To fix: Download the latest 'release full' build of FFmpeg from https://www.gyan.dev/ffmpeg/builds/ and replace your ffmpeg.exe."
                    )
                    self.root.after(0, self.processing_complete, False, user_msg)
                    return
                relevant_errors = []
                for line in reversed(error_lines[-10:]):
                    if any(
                        keyword in line.lower()
                        for keyword in ["error", "failed", "invalid", "not found"]
                    ):
                        relevant_errors.append(line)
                if relevant_errors:
                    error_output = "\n".join(relevant_errors[-3:])
                else:
                    error_output = "\n".join(error_lines[-20:])
                self.root.after(
                    0,
                    self.processing_complete,
                    False,
                    f"FFmpeg processing failed (exit code: {process.returncode}).\n\nError details:\n{error_output}",
                )
        except FileNotFoundError:
            error_msg = "FFmpeg not found! Please make sure FFmpeg is installed and available in your system PATH."
            self.root.after(0, self.processing_complete, False, error_msg)
        except subprocess.TimeoutExpired:
            error_msg = (
                "FFmpeg process timed out. The operation took too long to complete."
            )
            self.root.after(0, self.processing_complete, False, error_msg)
        except PermissionError:
            error_msg = "Permission denied. Please check file permissions and ensure you have write access to the output directory."
            self.root.after(0, self.processing_complete, False, error_msg)
        except Exception as e:
            error_msg = f"Unexpected error during processing: {str(e)}"
            self.root.after(0, self.processing_complete, False, error_msg)

    def cancel_processing(self):
        if not self.is_processing:
            return
        self.cancel_requested = True
        self.cancel_btn.config(state="disabled")
        self.status_label.config(text="Cancelling...", style="Error.TLabel")
        self.set_processing_ui_state(False)

        # Try graceful termination first
        if self.ffmpeg_process:
            try:
                self.ffmpeg_process.terminate()
                # Wait a bit for graceful termination
                self.ffmpeg_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # Force kill if graceful termination fails
                try:
                    self.ffmpeg_process.kill()
                    self.ffmpeg_process.wait(timeout=2)
                except Exception:
                    pass  # Process already terminated or other error

        self.root.update()

    def reset_settings(self):
        if messagebox.askyesno("Reset", "Are you sure you want to reset all fields?"):
            self.input_file.set("")
            self.start_time.set("0:00")
            self.end_time.set("0:00")
            self.trim_enabled.set(False)
            self.save_as_enabled.set(False)
            self.custom_output_name.set("")
            self.selected_preset.set("medium")
            self.advanced_enabled.set(False)
            self.selected_codec.set("H.264")
            self.selected_crf.set("20")
            self.selected_fps.set("120")
            self.selected_audio_bitrate.set("128k")
            self.selected_resolution.set("1920x1080")
            self.selected_container.set("mp4")
            self.selected_speed.set("1.0x (Normal)")
            self.file_info_label.config(text="No file selected", style="Info.TLabel")
            self.status_label.config(text="Ready to process video", style="Info.TLabel")
            self.progress_bar["value"] = 0
            self.progress_bar.pack_forget()
            self.process_btn.config(state="normal")
            self.cancel_btn.grid_remove()
            self.process_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))
            self.reset_btn.grid(row=0, column=1, sticky=tk.E)
            self.reset_btn.config(state="normal")
            self.timeline_frame.grid_remove()
            self.advanced_frame.grid_remove()
            self.upload_frame.grid_remove()
            self.track_selection_frame.grid_remove()
            self.last_output_path = None
            self.open_file_btn.grid_remove()
            self.show_in_explorer_btn.grid_remove()

            # Update window size to accommodate hidden content
            self.root.update_idletasks()
            self.root.geometry("")

    def processing_complete(self, success, message):
        self.is_processing = False
        self.cancel_btn.grid_remove()
        self.process_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.reset_btn.grid(row=0, column=1, sticky=tk.E)
        self.reset_btn.config(state="normal")
        self.process_btn.config(state="normal")
        self.progress_bar["value"] = 100 if success else 0
        self.progress_bar.pack_forget()
        self.set_processing_ui_state(False)
        if success:
            self.status_label.config(text="✅ " + message, style="Success.TLabel")
            messagebox.showinfo("Success", message)
            self.upload_frame.grid()
            self.open_file_btn.grid()
            self.show_in_explorer_btn.grid()
        else:
            self.status_label.config(text="❌ Processing failed", style="Error.TLabel")
            messagebox.showerror("Error", message)
            self.upload_frame.grid_remove()
            self.open_file_btn.grid_remove()
            self.show_in_explorer_btn.grid_remove()
        self.root.update()

    def toggle_advanced_options(self):
        if self.advanced_enabled.get():
            self.advanced_frame.grid()
            # Enable advanced controls if not processing
            if not self.is_processing:
                self.codec_menu.config(state="normal")
                self.crf_menu.config(state="normal")
                self.fps_menu.config(state="normal")
                self.audio_bitrate_menu.config(state="normal")
                self.resolution_menu.config(state="normal")
                self.container_menu.config(state="normal")
                # Enable speed_menu
                if hasattr(self, "speed_menu"):
                    self.speed_menu.config(state="normal")
                # Enable include_tracks_checkbox, subtitle_combobox, audio_combobox
                if hasattr(self, "include_tracks_checkbox"):
                    self.include_tracks_checkbox.config(state="normal")
                if hasattr(self, "subtitle_combobox") and self.subtitle_combobox:
                    self.subtitle_combobox.config(state="normal")
                if hasattr(self, "audio_combobox") and self.audio_combobox:
                    self.audio_combobox.config(state="normal")
        else:
            self.advanced_frame.grid_remove()
        self.root.update_idletasks()
        self.root.geometry("")
        self.root.update()

    def upload_to_selected_service(self):
        selected_key = self.upload_service.get()
        if not self.last_output_path or not os.path.exists(self.last_output_path):
            messagebox.showerror("Error", "No processed video file found!")
            return
        # Validate file size before upload
        if not self.validate_file_size_for_upload(self.last_output_path, selected_key):
            return
        self.upload_btn.config(state="disabled", text="Uploading...")
        self.status_label.config(text="Uploading...", style="Info.TLabel")
        thread = threading.Thread(
            target=self._upload_file, args=(self.last_output_path, selected_key)
        )
        thread.daemon = True
        thread.start()

    def _upload_file(self, file_path, service):
        try:
            if service == "catbox":
                result_url = self._upload_to_catbox(file_path)
            elif service == "uguu":
                result_url = self._upload_to_uguu(file_path)
            elif service == "tempsh":
                result_url = self._upload_to_tempsh(file_path)
            else:
                raise Exception("Unknown upload service")
            self.root.after(0, self._upload_success, result_url)
        except Exception as e:
            self.root.after(0, self._upload_error, f"Upload error: {str(e)}")

    def _upload_to_catbox(self, file_path):
        url = "https://catbox.moe/user/api.php"

        # Prepare the multipart form data
        boundary = f"----WebKitFormBoundary{int(time.time() * 1000)}"

        with open(file_path, "rb") as f:
            file_data = f.read()

        # Build multipart form data
        data = []
        data.append(f"--{boundary}".encode())
        data.append(b'Content-Disposition: form-data; name="reqtype"')
        data.append(b"")
        data.append(b"fileupload")

        data.append(f"--{boundary}".encode())
        data.append(
            f'Content-Disposition: form-data; name="fileToUpload"; filename="{os.path.basename(file_path)}"'.encode()
        )
        data.append(b"Content-Type: video/mp4")
        data.append(b"")
        data.append(file_data)

        data.append(f"--{boundary}--".encode())
        data.append(b"")

        body = b"\r\n".join(data)

        # Create request
        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("Content-Length", str(len(body)))

        # Upload file
        with urllib.request.urlopen(req, timeout=600) as response:
            result_url = response.read().decode("utf-8").strip()

            if result_url.startswith("http"):
                return result_url
            else:
                raise Exception(f"Upload failed: {result_url}")

    def _upload_to_uguu(self, file_path):
        url = "https://uguu.se/upload"

        # Prepare the multipart form data
        boundary = f"----WebKitFormBoundary{int(time.time() * 1000)}"

        with open(file_path, "rb") as f:
            file_data = f.read()

        # Build multipart form data for uguu.se
        data = []
        data.append(f"--{boundary}".encode())
        data.append(
            f'Content-Disposition: form-data; name="files[]"; filename="{os.path.basename(file_path)}"'.encode()
        )
        data.append(b"Content-Type: video/mp4")
        data.append(b"")
        data.append(file_data)
        data.append(f"--{boundary}--".encode())
        data.append(b"")

        body = b"\r\n".join(data)

        # Create request
        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("Content-Length", str(len(body)))

        # Upload file
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))

            if "files" in result and len(result["files"]) > 0:
                return result["files"][0]["url"]
            else:
                raise Exception("Upload failed: Invalid response from uguu.se")

    def _upload_to_tempsh(self, file_path):
        url = "https://temp.sh/upload"
        boundary = f"----WebKitFormBoundary{int(time.time() * 1000)}"
        with open(file_path, "rb") as f:
            file_data = f.read()
        data = []
        data.append(f"--{boundary}".encode())
        data.append(
            f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(file_path)}"'.encode()
        )
        data.append(b"Content-Type: video/mp4")
        data.append(b"")
        data.append(file_data)
        data.append(f"--{boundary}--".encode())
        data.append(b"")
        body = b"\r\n".join(data)
        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        req.add_header("Content-Length", str(len(body)))
        with urllib.request.urlopen(req, timeout=60) as response:
            result_url = response.read().decode("utf-8").strip()
            if result_url.startswith("http"):
                return result_url
            else:
                raise Exception(f"Upload failed: {result_url}")

    def _upload_success(self, url):
        service = self.upload_service.get()
        service_info = self.get_upload_service_info(service)

        # Create success message with expiration info
        success_msg = f"✅ Uploaded to {service}"
        if service_info and getattr(service_info, "expiration", None):
            success_msg += f" (expires: {service_info.expiration})"

        self.upload_btn.config(state="normal", text="Upload")
        self.status_label.config(text=success_msg, style="Success.TLabel")
        self.upload_url.set(url)
        self.url_row.grid()

        # Copy to clipboard if enabled
        if self.auto_copy_url.get():
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(url)
                self.copy_url_btn.config(text="✅ Copied")
                self.root.after(2000, lambda: self.copy_url_btn.config(text="Copy"))
            except Exception:
                pass

        # Show success alert
        service_name = (
            getattr(service_info, "name", service) if service_info else service
        )
        alert_msg = f"Video uploaded successfully to {service_name}!\n\nURL: {url}"
        if service_info and getattr(service_info, "expiration", None):
            alert_msg += f"\n\nNote: This file will expire in {service_info.expiration}"
        messagebox.showinfo("Upload Success", alert_msg)

        # Update window size to accommodate new content
        self.root.update_idletasks()
        self.root.geometry("")

    def _upload_error(self, error_message):
        self.upload_btn.config(state="normal", text="Upload")
        self.status_label.config(text="❌ Upload failed", style="Error.TLabel")
        messagebox.showerror("Upload Error", error_message)
        self.upload_url.set("")
        self.url_row.grid_remove()

    def copy_upload_url(self):
        url = self.upload_url.get()
        if url:
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(url)
                self.copy_url_btn.config(text="✅ Copied")
                self.root.after(2000, lambda: self.copy_url_btn.config(text="Copy"))
            except Exception:
                messagebox.showerror("Copy Error", "Failed to copy URL to clipboard.")

    def open_output_file(self):
        if not self.last_output_path or not os.path.exists(self.last_output_path):
            messagebox.showerror("Error", "No output file to open.")
            return
        path = os.path.abspath(self.last_output_path)
        try:
            if os.name == "nt":
                os.startfile(os.path.normpath(path))
            elif os.name == "posix":
                import sys
                import subprocess

                if sys.platform == "darwin":
                    subprocess.run(["open", path])
                else:
                    subprocess.run(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")

    def show_in_file_explorer(self):
        if not self.last_output_path or not os.path.exists(self.last_output_path):
            messagebox.showerror("Error", "No output file to show.")
            return
        path = os.path.abspath(self.last_output_path)
        try:
            if os.name == "nt":
                # Windows: open folder and select file
                import subprocess

                subprocess.run(["explorer", "/select,", os.path.normpath(path)])
            elif os.name == "posix":
                # macOS or Linux
                import sys
                import subprocess

                if sys.platform == "darwin":
                    subprocess.run(["open", "-R", path])
                else:
                    subprocess.run(["xdg-open", os.path.dirname(path)])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file explorer: {e}")

    def open_upload_url_in_browser(self):
        url = self.upload_url.get()
        if url:
            import webbrowser

            webbrowser.open(url)

    def on_codec_changed(self, event=None):
        # Update extension based on container, not codec
        name = self.custom_output_name.get()
        container_label = self.selected_container.get()
        ext = ".mp4"
        for label, val in CONTAINER_FORMATS:
            if label == container_label:
                ext = f".{val}"
        if not name.endswith(ext):
            name_path = Path(name)
            self.custom_output_name.set(str(name_path.with_suffix(ext)))

    def toggle_track_selection(self):
        if self.include_tracks.get():
            self.track_selection_frame.grid()
        else:
            self.track_selection_frame.grid_remove()
        self.root.update_idletasks()
        self.root.geometry("")

    def setup_track_selection_ui(self, subtitle_streams, audio_streams):
        # Always use single-select combobox for both
        for widget in self.subtitle_combobox_holder.winfo_children():
            widget.destroy()
        for widget in self.audio_combobox_holder.winfo_children():
            widget.destroy()
        self.subtitle_combobox = None
        self.audio_combobox = None
        if subtitle_streams:
            self.subtitle_combobox_holder.grid()
            frame = ttk.Frame(self.subtitle_combobox_holder)
            frame.pack(fill="both", expand=True)
            self.subtitle_combobox = ttk.Combobox(
                frame, state="readonly", width=30, font=("Segoe UI", 9)
            )
            self.subtitle_combobox.pack(fill="x", padx=4, pady=4)
            values = ["None"]
            for stream in subtitle_streams:
                label = f"[{stream.index}] {stream.language}"
                if stream.title:
                    label += f" | {stream.title}"
                values.append(label)
            self.subtitle_combobox["values"] = values
            self.subtitle_combobox.current(0)
        else:
            self.subtitle_combobox_holder.grid_remove()
        if audio_streams:
            self.audio_combobox_holder.grid()
            frame = ttk.Frame(self.audio_combobox_holder)
            frame.pack(fill="both", expand=True)
            self.audio_combobox = ttk.Combobox(
                frame, state="readonly", width=30, font=("Segoe UI", 9)
            )
            self.audio_combobox.pack(fill="x", padx=4, pady=4)
            values = []
            for stream in audio_streams:
                label = f"[{stream.index}] {stream.language}"
                if stream.title:
                    label += f" | {stream.title}"
                values.append(label)
            self.audio_combobox["values"] = values
            if values:
                self.audio_combobox.current(0)
        else:
            self.audio_combobox_holder.grid_remove()

    def on_container_changed(self, event=None):
        """Handle container format changes to update track selection UI."""
        # Re-setup the track selection UI with the new container format
        if hasattr(self, "subtitle_streams") and hasattr(self, "audio_streams"):
            self.setup_track_selection_ui(self.subtitle_streams, self.audio_streams)

    def check_ffmpeg_installation(self) -> bool:
        """
        Check if FFmpeg is available in system PATH.

        Returns:
            True if FFmpeg is available, False otherwise
        """
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                check=True,
                timeout=FFMPEG_VERSION_TIMEOUT,
            )
            return True
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ):
            return False

    def validate_file_size_for_upload(self, file_path: str, service: str) -> bool:
        """
        Validate that the file size is within the upload service's limits.

        Args:
            file_path: Path to the file to upload
            service: Upload service key (catbox, uguu, tempsh)

        Returns:
            True if file size is acceptable, False otherwise
        """
        try:
            file_size_bytes = os.path.getsize(file_path)
            file_size_mb = file_size_bytes / (1024 * 1024)  # Convert to MB
            service_config = get_upload_service_by_key(service)
            if not service_config:
                messagebox.showerror("Error", f"Unknown upload service: {service}")
                return False
            max_size_mb = service_config.max_size_mb
            service_name = service_config.name
            if file_size_mb > max_size_mb:
                messagebox.showerror(
                    "File Too Large",
                    f"File size ({file_size_mb:.1f} MB) exceeds the limit for {service_name} ({max_size_mb} MB).\n\n"
                    f"Please choose a different upload service or reduce the file size.",
                )
                return False
            return True
        except (OSError, FileNotFoundError) as e:
            messagebox.showerror("Error", f"Could not check file size: {e}")
            return False

    def get_upload_service_info(self, service: str) -> Optional[UploadService]:
        """
        Get information about an upload service as a dataclass.
        """
        return get_upload_service_by_key(service)

    def get_video_subtitle_streams(self, video_path) -> List[SubtitleStream]:
        """
        Return a list of SubtitleStream dataclass objects using ffprobe.
        """
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "s",
                "-show_entries",
                "stream=index,codec_name:stream_tags=language,title",
                "-of",
                "json",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            subtitle_streams = []
            for i, s in enumerate(streams):
                tags = s.get("tags", {})
                subtitle_streams.append(
                    SubtitleStream(
                        index=s.get("index", i),
                        map_index=i,
                        codec_name=s.get("codec_name", ""),
                        language=tags.get("language", "und"),
                        title=tags.get("title", ""),
                    )
                )
            return subtitle_streams
        except Exception:
            return []

    def get_video_audio_streams(self, video_path) -> List[AudioStream]:
        """
        Return a list of AudioStream dataclass objects using ffprobe.
        """
        try:
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=index,codec_name:stream_tags=language,title",
                "-of",
                "json",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            streams = data.get("streams", [])
            audio_streams = []
            for s in streams:
                tags = s.get("tags", {})
                audio_streams.append(
                    AudioStream(
                        index=s.get("index", 0),
                        codec_name=s.get("codec_name", ""),
                        language=tags.get("language", "und"),
                        title=tags.get("title", ""),
                    )
                )
            return audio_streams
        except Exception:
            return []

    def escape_subtitles_path(self, path):
        # For FFmpeg subtitles filter on Windows: use forward slashes and escape colons
        path = os.path.abspath(path).replace("\\", "/").replace(":", "\\:")
        return path


def main() -> None:
    """Main entry point for the Clipper application."""
    root = tk.Tk()
    ClipperGUI(root)
    root.update_idletasks()

    min_width = WINDOW_MIN_WIDTH
    min_height = root.winfo_height()
    root.minsize(min_width, min_height)

    x = (root.winfo_screenwidth() // 2) - (min_width // 2)
    y = (root.winfo_screenheight() // 3) - (min_height // 2)  # Start at 33% from top
    root.geometry(f"{min_width}x{min_height}+{x}+{y}")
    root.mainloop()


if __name__ == "__main__":
    main()
