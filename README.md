# Clipper - Video Trimming and Encoding Tool

A minimal, modern, and accessible GUI application for video trimming and encoding using FFmpeg. Built with Python and Tkinter, Clipper provides an intuitive interface for video processing and uploading tasks with a clean, dark material-inspired design.

## Features

### 🎬 Core Functionality
- **Video File Support**: Browse for input video files (MP4, AVI, MOV, MKV, WMV, FLV)
- **Trimming**: Optional video trimming with interactive timeline and seekbar
- **Auto Output Generation**: Intelligent filename generation with sanitization
- **Encoding Presets**: Choose from Very Fast, Fast, Medium, Slow, Very Slow encoding presets
- **Advanced Export Options**: Enable advanced mode to customize video codec (H.264/H.265/WebM), CRF (quality), FPS, audio bitrate, and resolution (including custom values)
- **Multiple Output Formats**: Export to MP4 or WebM (VP9) with automatic extension handling
- **File Uploading**: Optionally lets you send your processed video directly to great file hosting websites, choose your preferred service, upload with one click, and instantly get a shareable URL.

### 🎨 User Interface
- **Modern Dark Theme**: Clean, material-inspired dark interface
- **Interactive Timeline**: Click and drag timeline for precise trimming
- **Responsive Design**: Auto-adjusting window size and layout, including dynamic resizing when sections are shown/hidden
- **Status Feedback**: Clear processing status and error messages
- **Accessible Controls**: Pill-style buttons, styled radio buttons, and intuitive navigation
- **Consistent Alignment**: All controls and labels are visually aligned for a professional look
- **Dynamic Advanced Options**: Show/hide advanced export settings with a single checkbox
- **Editable Dropdowns**: All advanced fields (CRF, FPS, Audio Bitrate, Resolution) allow both preset selection and custom user input, with validation

### ⚡ Performance
- **Robust Error Handling**: Comprehensive error catching and user feedback, including display of FFmpeg error output
- **FFmpeg Integration**: Direct FFmpeg command execution for optimal performance
- **Memory Efficient**: Stream-based processing for large video files
- **UI Responsiveness**: All controls are disabled during processing (except Cancel), and re-enabled after completion or error

## Installation

### Prerequisites
- Python 3.6 or higher
- FFmpeg installed and available in system PATH

### Running Clipper
1. Clone or download the `clipper.py` file
2. Run the application:
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

### Encoding Presets
- **Very Fast**: Quick encoding, larger file size
- **Fast**: Good balance of speed and quality
- **Medium**: Default preset, balanced performance
- **Slow**: Higher quality, longer processing time
- **Very Slow**: Maximum quality, longest processing time

### Advanced Export Options
1. **Show Advanced Options**: Check the "Advanced" checkbox below the preset selection
2. **Customize Export**:
   - **Video Codec**: Choose H.264 (MP4), H.265 (HEVC), or WebM (VP9)
   - **CRF**: Select or enter a custom quality value (lower is higher quality, 20 is default, full FFmpeg range supported)
   - **FPS**: Choose or enter output frame rate (24, 30, 60, 120, or any custom value)
   - **Audio Bitrate**: Select or enter audio quality (64k–320k, or choose "Remove Audio" to export video without audio)
   - **Resolution**: Choose from 4K, 2K, 1080p, 720p, 480p, 360p, or enter a custom resolution (e.g., 236x556)
3. **Hide Advanced Options**: Uncheck "Advanced" to return to simple mode (defaults: H.264, CRF 20, 120 FPS, 128k audio, 1920x1080)

### Uploading Processed Videos
- **Upload Services**: Upload your processed video to catbox.moe, uguu.se, or temp.sh directly from the app
- **Service Selection**: Choose your preferred upload service with radio buttons
- **Auto-copy URL**: Optionally auto-copy the upload URL to clipboard after upload
- **Copy/Open in Browser**: Copy the upload URL or open it in your browser with a single click

## Error Handling

The application includes comprehensive error handling for:
- Missing FFmpeg installation
- Invalid video files
- File permission issues
- Invalid time ranges
- Processing failures (with detailed FFmpeg error output)

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