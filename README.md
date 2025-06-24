# Clipper - Video Trimming and Encoding Tool

A minimal, modern, and accessible GUI application for video trimming and encoding using FFmpeg. Built with Python and Tkinter, Clipper provides an intuitive interface for video processing tasks with a clean, dark material-inspired design.

## Features

### 🎬 Core Functionality
- **Video File Support**: Browse for input video files (MP4, AVI, MOV, MKV, WMV, FLV)
- **Trimming**: Optional video trimming with interactive timeline and seekbar
- **Auto Output Generation**: Intelligent filename generation with sanitization
- **Encoding Presets**: Choose from Very Fast, Fast, Medium, Slow, Very Slow encoding presets
- **Advanced Export Options**: Enable advanced mode to customize video codec (H.264/H.265), CRF (quality), FPS, audio bitrate, and resolution

### 🎨 User Interface
- **Modern Dark Theme**: Clean, material-inspired dark interface
- **Interactive Timeline**: Click and drag timeline for precise trimming
- **Responsive Design**: Auto-adjusting window size and layout
- **Status Feedback**: Clear processing status and error messages
- **Accessible Controls**: Pill-style buttons, styled radio buttons, and intuitive navigation
- **Consistent Alignment**: All controls and labels are visually aligned for a professional look
- **Dynamic Advanced Options**: Show/hide advanced export settings with a single checkbox

### ⚡ Performance
- **Multi-threaded Processing**: Non-blocking UI during video processing
- **Robust Error Handling**: Comprehensive error catching and user feedback
- **FFmpeg Integration**: Direct FFmpeg command execution for optimal performance
- **Memory Efficient**: Stream-based processing for large video files

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
2. **Configure Output**: The output filename is auto-generated but can be customized
3. **Choose Preset**: Select encoding speed (Very Fast to Very Slow)
4. **Process**: Click "Process Video" to start encoding

### Video Trimming
1. **Enable Trimming**: Check "Enable Video Trimming"
2. **Set Timeline**: Use the interactive timeline or enter start/end times manually
3. **Visual Feedback**: The timeline shows the selected region in blue
4. **Drag Handles**: Click and drag the green (start) and red (end) handles for precise control

### Advanced Export Options
1. **Show Advanced Options**: Check the "Advanced" checkbox below the preset selection
2. **Customize Export**:
   - **Video Codec**: Choose H.264 (MP4) or H.265 (HEVC)
   - **CRF**: Select quality (lower is higher quality, 20 is default)
   - **FPS**: Choose output frame rate (24, 30, 60, 120)
   - **Audio Bitrate**: Select audio quality (96k to 320k)
   - **Resolution**: Choose output resolution (1920x1080, 1280x720, 2560x1440, 3840x2160)
3. **Hide Advanced Options**: Uncheck "Advanced" to return to simple mode (defaults: H.264, CRF 20, 120 FPS, 128k audio, 1920x1080)

### Timeline Controls
- **Click Timeline**: Set start or end time by clicking on the timeline
- **Drag Handles**: Drag the colored handles for precise time selection
- **Manual Entry**: Type times in MM:SS format in the entry fields
- **Auto-correction**: Invalid time ranges are automatically corrected

### Encoding Presets
- **Very Fast**: Quick encoding, larger file size
- **Fast**: Good balance of speed and quality
- **Medium**: Default preset, balanced performance
- **Slow**: Higher quality, longer processing time
- **Very Slow**: Maximum quality, longest processing time

## Error Handling

The application includes comprehensive error handling for:
- Missing FFmpeg installation
- Invalid video files
- File permission issues
- Invalid time ranges
- Processing failures
- Subtitle stream warnings

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

---