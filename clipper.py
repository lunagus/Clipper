import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import threading
from pathlib import Path
import json
import re
import urllib.request
import urllib.parse
import time


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
        self.save_as_enabled = tk.BooleanVar(value=False)
        self.advanced_enabled = tk.BooleanVar(value=False)
        self.auto_copy_url = tk.BooleanVar(value=False)
        self.last_output_path = None
        self.upload_service = tk.StringVar(value="catbox")
        self.upload_url = tk.StringVar(value="")

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
        # Progress bar style (blue)
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
        # Add Danger style for Cancel button
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
        self.browse_btn = ttk.Button(
            file_selection_frame,
            text="Browse",
            command=self.browse_input_file,
            style="Secondary.TButton",
        )
        self.browse_btn.grid(row=0, column=1)
        self.file_info_label = ttk.Label(
            main_container, text="No file selected", style="Info.TLabel"
        )
        self.file_info_label.grid(row=2, column=0, pady=(8, 0), sticky=tk.W)
        # Trimming toggle (pill style)
        self.trim_check = ttk.Checkbutton(
            main_container,
            text="Enable Video Trimming",
            variable=self.trim_enabled,
            command=self.toggle_trim_section,
            style="Pill.TCheckbutton",
        )
        self.trim_check.grid(row=3, column=0, sticky=tk.W, pady=(8, 8), padx=0)
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
        output_file_row = ttk.Frame(main_container)
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
            main_container,
            text="Custom Output Name and Location (Save As...)",
            variable=self.save_as_enabled,
            style="Pill.TCheckbutton",
        )
        self.save_as_checkbox.grid(row=7, column=0, sticky=tk.W, pady=(0, 8))
        # Preset row (always visible)
        ttk.Label(main_container, text="Preset:", style="Subtitle.TLabel").grid(
            row=8, column=0, sticky=tk.W, pady=(8, 8)
        )
        self.preset_options = [
            ("Very Fast", "veryfast"),
            ("Fast", "fast"),
            ("Medium", "medium"),
            ("Slow", "slow"),
            ("Very Slow", "veryslow"),
        ]
        self.selected_preset = tk.StringVar(value="medium")
        self.preset_radios = []
        preset_buttons_frame = ttk.Frame(main_container)
        preset_buttons_frame.grid(row=9, column=0, sticky="ew", pady=(0, 8))
        main_container.columnconfigure(0, weight=1)
        for i in range(len(self.preset_options)):
            preset_buttons_frame.columnconfigure(i, weight=1)
        for i, (label, value) in enumerate(self.preset_options):
            rb = ttk.Radiobutton(
                preset_buttons_frame,
                text=label,
                variable=self.selected_preset,
                value=value,
                style="Pill.TRadiobutton",
            )
            rb.grid(row=0, column=i, padx=4, pady=2, sticky="ew")
            self.preset_radios.append(rb)
        # Advanced checkbox
        self.advanced_enabled = tk.BooleanVar(value=False)
        self.advanced_checkbox = ttk.Checkbutton(
            main_container,
            text="Advanced",
            variable=self.advanced_enabled,
            command=self.toggle_advanced_options,
            style="Pill.TCheckbutton",
        )
        self.advanced_checkbox.grid(row=10, column=0, sticky=tk.W, pady=(0, 0))
        # Advanced options frame (hidden by default)
        self.advanced_frame = ttk.Frame(main_container)
        self.advanced_frame.grid(row=11, column=0, sticky=(tk.W, tk.E), pady=(8, 0))
        self.advanced_frame.columnconfigure(0, weight=1)
        self.advanced_frame.columnconfigure(1, weight=1)
        self.advanced_frame.columnconfigure(2, weight=1)
        self.advanced_frame.columnconfigure(3, weight=1)
        self.advanced_frame.columnconfigure(4, weight=1)
        # Video Codec
        ttk.Label(
            self.advanced_frame, text="Video Codec:", style="Subtitle.TLabel"
        ).grid(row=0, column=0, sticky=tk.W)
        self.codec_options = [
            ("H.264 (MP4)", "libx264"),
            ("H.265 (HEVC)", "libx265"),
            ("WebM (VP9)", "libvpx-vp9"),
        ]
        self.selected_codec = tk.StringVar(value="H.264 (MP4)")
        self.codec_menu = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.selected_codec,
            values=[label for label, val in self.codec_options],
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
        self.crf_options = ["18", "20", "23", "25", "28"]
        self.selected_crf = tk.StringVar(value=self.crf_options[1])
        self.crf_menu = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.selected_crf,
            values=self.crf_options,
            state="normal",
            width=4,
            font=("Segoe UI", 9),
        )
        self.crf_menu.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 8))
        # FPS
        ttk.Label(self.advanced_frame, text="FPS:", style="Subtitle.TLabel").grid(
            row=0, column=2, sticky=tk.W
        )
        self.fps_options = ["24", "30", "60", "120"]
        self.selected_fps = tk.StringVar(value=self.fps_options[2])
        self.fps_menu = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.selected_fps,
            values=self.fps_options,
            state="normal",
            width=4,
            font=("Segoe UI", 9),
        )
        self.fps_menu.grid(row=1, column=2, sticky=(tk.W, tk.E), padx=(0, 8))
        # Audio Bitrate (high to low)
        ttk.Label(
            self.advanced_frame, text="Audio Bitrate:", style="Subtitle.TLabel"
        ).grid(row=0, column=3, sticky=tk.W)
        self.audio_bitrate_options = [
            "320k",
            "256k",
            "192k",
            "128k",
            "96k",
            "64k",
            "Remove Audio",
        ]
        self.selected_audio_bitrate = tk.StringVar(value=self.audio_bitrate_options[3])
        self.audio_bitrate_menu = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.selected_audio_bitrate,
            values=self.audio_bitrate_options,
            state="normal",
            width=8,
        )
        self.audio_bitrate_menu.grid(row=1, column=3, padx=(0, 8), sticky="ew")
        # Resolution (high to low, add 4K and 2K)
        ttk.Label(
            self.advanced_frame, text="Resolution:", style="Subtitle.TLabel"
        ).grid(row=0, column=4, sticky=tk.W)
        self.resolution_options = [
            ("3840x2160", "3840:2160"),  # 4K
            ("2560x1440", "2560:1440"),  # 2K
            ("1920x1080", "1920:1080"),
            ("1280x720", "1280:720"),
            ("854x480", "854:480"),
            ("640x360", "640:360"),
        ]
        self.selected_resolution = tk.StringVar(value="1920x1080")
        self.resolution_menu = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.selected_resolution,
            values=[label for label, val in self.resolution_options],
            state="normal",
            width=10,
            font=("Segoe UI", 9),
        )
        self.resolution_menu.grid(row=1, column=4, sticky=(tk.W, tk.E), padx=(0, 8))
        self.advanced_frame.grid_remove()
        self.status_label = ttk.Label(
            main_container, text="Ready to process video", style="Info.TLabel"
        )
        self.status_label.grid(row=12, column=0, pady=(16, 4))
        # Progress bar frame (fixed height)
        self.progress_frame = ttk.Frame(main_container, height=24)
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
        # Button group frame
        button_frame = ttk.Frame(main_container)
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
        # Upload section (hidden by default)
        self.upload_frame = ttk.Frame(main_container)
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
            command=self.upload_to_catbox,
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
        self.root.update_idletasks()
        self.root.geometry("")
        self.root.update()

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
            if not self.is_processing:
                self.set_controls_state(False)

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
                output_name = f"{base_name}-{start_str}-{end_str}-clip"
            else:
                output_name = f"{base_name}-clip"
            # Extension based on codec
            codec_label = self.selected_codec.get()
            if codec_label == "WebM (VP9)":
                output_name += ".webm"
            else:
                output_name += ".mp4"
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
        # Validate advanced options
        if self.advanced_enabled.get():
            # CRF
            crf = self.selected_crf.get()
            codec_label = self.selected_codec.get()
            try:
                crf_val = int(crf)
                if codec_label == "WebM (VP9)":
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
                import re

                if not re.match(r"^(\d{2,3})k$", audio_bitrate):
                    messagebox.showerror(
                        "Error",
                        "Audio Bitrate must be in the form '96k', '128k', etc. (8k-512k). Or select 'Remove Audio'.",
                    )
                    return
                ab_val = int(audio_bitrate[:-1])
                if not (8 <= ab_val <= 512):
                    messagebox.showerror(
                        "Error", "Audio Bitrate must be between 8k and 512k."
                    )
                    return
            # Resolution
            res = self.selected_resolution.get()
            import re

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
        # Save As dialog if enabled
        output_path = None
        if self.save_as_enabled.get():
            # Extension based on codec
            codec_label = self.selected_codec.get()
            ext = ".webm" if codec_label == "WebM (VP9)" else ".mp4"
            output_path = filedialog.asksaveasfilename(
                defaultextension=ext,
                filetypes=[
                    ("WebM files", "*.webm"),
                    ("MP4 files", "*.mp4"),
                    ("All files", "*.*"),
                ],
                initialfile=self.custom_output_name.get(),
            )
            if not output_path:
                return  # Cancel if no path selected
            import os

            self.custom_output_name.set(os.path.basename(output_path))
        else:
            input_path_obj = Path(self.input_file.get())
            output_name = self.custom_output_name.get()
            # Extension based on codec
            codec_label = self.selected_codec.get()
            ext = ".webm" if codec_label == "WebM (VP9)" else ".mp4"
            if not output_name.endswith(ext):
                output_name = (
                    re.sub(r"\.(mp4|webm|mkv|avi|mov)$", "", output_name, flags=re.I)
                    + ext
                )
            output_path = input_path_obj.parent / output_name
        self.start_processing(str(output_path))

    def set_controls_state(self, disabled):
        state = "disabled" if disabled else "normal"
        # Main controls
        self.input_entry.config(state=state)
        self.browse_btn.config(state=state)
        self.save_as_checkbox.config(state=state)
        self.output_entry.config(state=state)
        self.process_btn.config(state=state)
        self.reset_btn.config(state=state)
        self.trim_check.config(state=state)
        self.advanced_checkbox.config(state=state)
        # Timeline controls
        self.start_entry.config(state=state)
        self.end_entry.config(state=state)
        # Preset radios
        for rb in self.preset_radios:
            rb.config(state=state)
        # Advanced controls
        self.codec_menu.config(
            state=state if self.advanced_enabled.get() else "disabled"
        )
        self.crf_menu.config(state=state if self.advanced_enabled.get() else "disabled")
        self.fps_menu.config(state=state if self.advanced_enabled.get() else "disabled")
        self.audio_bitrate_menu.config(
            state=state if self.advanced_enabled.get() else "disabled"
        )
        self.resolution_menu.config(
            state=state if self.advanced_enabled.get() else "disabled"
        )
        # Upload controls
        self.catbox_radio.config(state=state)
        self.uguu_radio.config(state=state)
        self.tempsh_radio.config(state=state)
        self.upload_btn.config(state=state)
        self.upload_checkbox.config(state=state)
        self.copy_url_btn.config(state=state)
        self.open_in_browser_btn.config(state=state)
        # Open/Show in Explorer
        self.open_file_btn.config(state=state)
        self.show_in_explorer_btn.config(state=state)
        # Cancel button always enabled during processing
        if disabled:
            self.cancel_btn.config(state="normal")
        else:
            self.cancel_btn.config(state="disabled")

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
        self.set_controls_state(True)
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
            # Get options
            if self.advanced_enabled.get():
                codec_label = self.selected_codec.get()
                codec = dict(self.codec_options)[codec_label]
                crf = self.selected_crf.get()
                fps = self.selected_fps.get()
                audio_bitrate = self.selected_audio_bitrate.get()
                res_label = self.selected_resolution.get()
                preset_res_dict = dict(self.resolution_options)
                if res_label in preset_res_dict:
                    resolution = preset_res_dict[res_label]
                else:
                    # Accept custom input, convert "236x556" to "236:556"
                    resolution = res_label.replace("x", ":")
            else:
                codec = "libx264"
                crf = "20"
                fps = "120"
                audio_bitrate = "128k"
                resolution = "1920:1080"
            preset = self.selected_preset.get()
            command = ["ffmpeg", "-y", "-i", input_path, "-sn"]
            trim = self.trim_enabled.get()
            if trim:
                start_seconds = self.time_to_seconds(self.start_time.get())
                duration = self.time_to_seconds(self.end_time.get()) - start_seconds
                command.extend(["-ss", str(start_seconds), "-t", str(duration)])
            command.extend(
                [
                    "-vf",
                    f"scale={resolution},fps={fps}",
                    "-vcodec",
                    codec,
                    "-crf",
                    crf,
                    "-preset",
                    preset,
                ]
            )
            # Audio codec and bitrate or remove audio
            if codec == "libvpx-vp9":
                # WebM: use libopus for audio
                if audio_bitrate == "Remove Audio":
                    command.append("-an")
                else:
                    command.extend(["-acodec", "libopus", "-b:a", audio_bitrate])
            else:
                command.extend(["-acodec", "aac"])
                if audio_bitrate == "Remove Audio":
                    command.append("-an")
                else:
                    command.extend(["-b:a", audio_bitrate])
            command.append(output_path)
            # Calculate total duration for progress
            if trim:
                total_duration = duration
            else:
                total_duration = self.video_duration
            if total_duration <= 0:
                total_duration = 1  # Avoid division by zero
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            self.ffmpeg_process = process
            import re

            time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
            last_percent = 0
            ffmpeg_stderr = []
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
            process.wait()
            if process.returncode == 0:
                self.root.after(
                    0,
                    self.processing_complete,
                    True,
                    "Video processing completed successfully!",
                )
            else:
                # Show actual ffmpeg error output
                error_output = "\n".join(ffmpeg_stderr[-20:])  # Show last 20 lines
                self.root.after(
                    0,
                    self.processing_complete,
                    False,
                    f"FFmpeg error: Processing failed.\n\n{error_output}",
                )
        except FileNotFoundError:
            error_msg = "FFmpeg not found! Please make sure FFmpeg is installed and available in your system PATH."
            self.root.after(0, self.processing_complete, False, error_msg)
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.root.after(0, self.processing_complete, False, error_msg)

    def cancel_processing(self):
        if not self.is_processing:
            return
        self.cancel_requested = True
        self.cancel_btn.config(state="disabled")
        self.status_label.config(text="Cancelling...", style="Error.TLabel")
        self.set_controls_state(False)
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
            self.selected_codec.set("H.264 (MP4)")
            self.selected_crf.set("20")
            self.selected_fps.set("120")
            self.selected_audio_bitrate.set("128k")
            self.selected_resolution.set("1920x1080")
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
        self.set_controls_state(False)
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
        else:
            self.advanced_frame.grid_remove()
        self.root.update_idletasks()
        self.root.geometry("")
        self.root.update()

    def upload_to_catbox(self):
        if not self.last_output_path or not os.path.exists(self.last_output_path):
            messagebox.showerror("Error", "No processed video file found!")
            return

        service = self.upload_service.get()
        self.upload_btn.config(state="disabled", text="Uploading...")
        self.status_label.config(text="Uploading...", style="Info.TLabel")

        # Start upload in background thread
        thread = threading.Thread(
            target=self._upload_file, args=(self.last_output_path, service)
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

            # Success
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
        with urllib.request.urlopen(req, timeout=60) as response:
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
        self.upload_btn.config(state="normal", text="Upload")
        self.status_label.config(
            text=f"✅ Uploaded to {service}", style="Success.TLabel"
        )
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
        codec_label = self.selected_codec.get()
        if codec_label == "WebM (VP9)":
            # Change output extension to .webm
            name = self.custom_output_name.get()
            if not name.endswith(".webm"):
                name = re.sub(r"\.(mp4|mkv|avi|mov)$", "", name, flags=re.I)
                self.custom_output_name.set(name + ".webm")
        else:
            # Change output extension to .mp4
            name = self.custom_output_name.get()
            if not name.endswith(".mp4"):
                name = re.sub(r"\.(webm|mkv|avi|mov)$", "", name, flags=re.I)
                self.custom_output_name.set(name + ".mp4")


def main():
    root = tk.Tk()
    ClipperGUI(root)
    root.update_idletasks()
    min_width = 700
    min_height = root.winfo_height()
    root.minsize(min_width, min_height)
    x = (root.winfo_screenwidth() // 2) - (min_width // 2)
    y = (root.winfo_screenheight() // 3) - (min_height // 2)  # Start at 33% from top
    root.geometry(f"{min_width}x{min_height}+{x}+{y}")
    root.mainloop()


if __name__ == "__main__":
    main()
