# Clipper - Trimmer, Encoder & Uploader

A minimal, modern, and accessible GUI application for video trimming and encoding using FFmpeg. Built with Python and Tkinter, Clipper provides an intuitive interface for video processing and uploading tasks with a clean, dark material-inspired design.

## WHY?

I wanted a quick, intuitive way to clip and encode video files from movies, game captures, and TV shows for personal use. Manually crafting FFmpeg commands every time was tedious and inefficient, especially due to different size constraints and resolution tweaks for every use case, so I built a lightweight GUI that covers most of the useful FFmpeg options, while remaining lightweight and fast, and adding upload and sharing features when needed.

## Features

### 🎬 Core Functionality
- **Video File Support**: Browse for input video files (MP4, AVI, MOV, MKV, WMV, FLV, WebM)
- **Trimming**: Optional video trimming with interactive timeline and seekbar
- **Auto Output Generation**: Intelligent filename generation with sanitization
- **Encoding Presets**: Choose from Very Fast, Fast, Medium, Slow, Very Slow encoding presets
- **Advanced Export Options**: Enable advanced mode to customize video codec, CRF, FPS, audio bitrate, container format, playback speed and resolution (including custom values)
- **Multiple Output Formats**: Export to MP4, MKV or WebM with automatic extension handling
- **File Uploading**: Optionally lets you send your processed video directly to great file hosting websites, choose your preferred service, upload with one click, and instantly get a shareable URL.

### 🎨 User Interface
- **Modern Dark Theme**: Clean, material-inspired UI with high contrast and pill-style buttons
- **Interactive Timeline**: Click and drag handles for precise start/end trimming
- **Responsive Design**: Auto-adjusting layout with dynamic resizing
- **Advanced Mode Toggle**: Show/hide expert-level encoding controls
- **Editable Dropdowns**: Fields allow preset or custom input with validation
- **Real-Time Feedback**: Status updates, error messages, and progress bars

### ⚡ Performance
- **Robust Error Handling**: Comprehensive error catching and user feedback
- **Threaded Processing**: Runs encoding and upload tasks in background threads to avoid UI freezes
- **Memory Efficient**: Optimized command execution avoids unnecessary memory usage

## Installation

### Bundled Executable
A prebuilt `.exe` (with bundled FFmpeg and Python) is available in the [Releases](https://github.com/lunagus/Clipper/releases) page.

### Prerequisites
- Python 3.6+
- FFmpeg installed in system PATH, or bundled in a `bin/` folder

### Run from Source
```bash
python clipper.py
```

## Usage Instructions

### Basic Video Processing
1. **Select Input File**: Click "Browse" to select your video file
2. **Choose Preset**: Select encoding speed (Very Fast to Very Slow)
3. **Process**: Click "Process Video" to start encoding
4. **Open or Show**: Reveal the output file in your system's file explorer or open the processed video directly from the app

### Video Trimming
1. **Enable Trimming**: Check "Enable Video Trimming"
2. **Set Timeline**: Use the interactive timeline or enter start/end times manually
3. **Visual Feedback**: The timeline shows the selected region in blue
4. **Drag Handles**: Click and drag the green (start) and red (end) handles for precise control

### Advanced Encoding Options
- **Video Codec**: H.264, H.265 (HEVC), or VP9
- **CRF (Quality)**: Choose any value (lower number = better quality)
- **FPS**: 24, 30, 60, 120 or custom frame rate
- **Audio Bitrate**: 64k to 320k or strip audio completely
- **Resolution**: Choose preset or custom resolution
- **Speed**: Apply video/audio speed multiplier (e.g., 2x faster)
- **Track Selection**: Choose specific subtitle/audio stream
- **Format**: Output to MP4, MKV, or WebM
- **Hide Advanced Options**: Uncheck "Advanced" to return to simple mode

### Uploading Processed Videos
- **Upload Services**: Upload your processed video to catbox.moe, uguu.se, or temp.sh directly from the app
- **Service Selection**: Choose your preferred upload service with radio buttons
- **Auto-copy URL**: Optionally auto-copy the upload URL to clipboard after upload
- **Copy/Open in Browser**: Copy the upload URL or open it in your browser with a single click

## Error Handling

Clipper offers comprehensive feedback for:
- Invalid input or missing files
- Incorrect time formats
- Missing FFmpeg or ffprobe
- Encoding errors and limitations (e.g., subtitle font issues)
- File size over upload limits

## Acknowledgements

### Open Source Tools and Libraries

#### FFmpeg
- **Description**: Complete, cross-platform solution for recording, converting, and streaming audio and video
- **Website**: [https://ffmpeg.org/](https://ffmpeg.org/)
- **License**: LGPL/GPL
- **Usage**: Core video processing engine for encoding, decoding, and format conversion

#### Python
- **Description**: High-level, interpreted programming language
- **Website**: [https://python.org/](https://python.org/)
- **License**: PSF License
- **Usage**: Primary programming language for the application

#### Tkinter
- **Description**: Python's standard GUI toolkit
- **Website**: [https://docs.python.org/3/library/tkinter.html](https://docs.python.org/3/library/tkinter.html)
- **License**: Python Software Foundation License
- **Usage**: GUI framework for creating the user interface

#### Additional Python Standard Library Modules
- **subprocess**: Process creation and management
- **threading**: Multi-threading support for non-blocking UI
- **pathlib**: Object-oriented filesystem paths
- **json**: JSON data interchange format parsing
- **re**: Regular expression operations
- **os**: Operating system interface
- **filedialog**: File dialog functionality
- **messagebox**: Message box dialogs
- **ttk**: Themed Tkinter widgets

#### File Hosting Websites

This application's upload functionality is made possible thanks to the following free file hosting services:

### catbox.moe
A privacy-focused, no-ads file hosting service supporting a wide range of file types and generous file size limits.
- **Website**: [https://catbox.moe/](https://catbox.moe)
- **Donate to catbox:** [https://catbox.moe/support.php](https://catbox.moe/support.php)

### uguu.se
A simple, anonymous file hosting service with a clean API and automatic file expiration.
- **Website**: [https://uguu.se/](https://uguu.se/)
- **Documentation**: [https://github.com/nokonoko/uguu](https://github.com/nokonoko/uguu)
- **Donate to uguu**: Bitcoin: bc1qhpy0ygu2vk52hkjtypf9wglgy9utj3th9d0c8s

### temp.sh
A minimalist, temporary file hosting service for quick sharing, with files expiring after 3 days.
- **Website**: [https://temp.sh/](https://temp.sh/)
- **Donate to temp.sh**: Bitcoin: bc1qrfugegr75h8d0zlhvydwkky0ayus5jm3jkqd87
---

## License

This project is licensed under the GNU General Public License v3.0.  
See the [LICENSE](./LICENSE) file for full details.

---
