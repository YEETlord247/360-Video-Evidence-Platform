360° VIDEO PLAYER & EVIDENCE.COM INTERFACE
------------------------------------------------------------
A full-stack 360° video evidence visualization platform that combines 
a dual-fisheye video player with an Evidence.com-style user interface 
for law enforcement case review and analysis.
Developed at Axon Enterprises by Utkarsh Rai.

------------------------------------------------------------
OVERVIEW
------------------------------------------------------------
The 360° Video Player & Evidence.com Interface allows users to view, 
annotate, and export immersive 360° police body camera footage in real 
time. Designed with dual-format video compatibility (equirectangular 
and fisheye), it includes advanced pin-based navigation, export 
capabilities, and a responsive front-end UI.

This project was inspired by Axon’s Evidence.com system and is designed 
for professional-grade video analysis workflows, bridging the gap 
between interactive visualization and legal video management.

------------------------------------------------------------
SYSTEM ARCHITECTURE
------------------------------------------------------------
Video Input (Dual-Fisheye or Equirectangular)
   ↓
OpenCV Preprocessing + FFmpeg Encoding
   ↓
Web Application (Flask + Three.js Front-End)
   ↓
Interactive 360° Player Interface
   ↓
Timeline Pinning + Metadata Management
   ↓
Video Export (FFmpeg background threads)

Core modules:
1. Dual-fisheye to equirectangular video conversion
2. 360° scene rendering and panning via Three.js
3. Pin-based metadata tagging system
4. Export and transcoding pipeline with FFmpeg
5. Responsive Evidence.com-style web UI

------------------------------------------------------------
KEY FEATURES
------------------------------------------------------------
- Dual-format video support: equirectangular and dual-fisheye
- Pin system for tagging events at specific timestamps
- Auto-snap video view to saved pin positions
- Background export with FFmpeg progress tracking
- Smooth animations and auto-hiding controls for clean playback
- Responsive design supporting desktop and mobile browsers
- Drag-and-drop video upload and preview
- Support for high-resolution exports (up to 4K)

------------------------------------------------------------
TECH STACK
------------------------------------------------------------
Languages: Python (Flask), JavaScript, HTML, CSS
Libraries: Three.js, OpenCV, FFmpeg, jQuery
UI Design: Glassmorphism + Modern Evidence.com color palette
Deployment: Localhost or Axon-internal testing server
Supported OS: Windows, macOS, Linux

------------------------------------------------------------
REPOSITORY STRUCTURE
------------------------------------------------------------
360_video_player/
 ├── web_app.py                   (Flask backend)
 ├── main.py                      (Video processing utilities)
 ├── templates/                   (HTML templates)
 │   ├── index.html               (Evidence.com interface)
 │   └── fullscreen_player.html   (360° player view)
 ├── static/                      (Static assets)
 │   ├── css/                     (Custom styling)
 │   └── js/                      (Interactive scripts)
 ├── uploads/                     (Uploaded videos)
 ├── outputs/                     (Exported videos)
 ├── logs/                        (Application logs)
 └── README.txt

------------------------------------------------------------
SETUP INSTRUCTIONS
------------------------------------------------------------
1. Prerequisites
   - Python >= 3.8
   - FFmpeg installed and added to system PATH
   - Modern browser (Chrome, Firefox, Edge)
   - Optional GPU acceleration for video rendering

2. Installation
   git clone <repo-url>
   cd 360_video_player
   pip install -r requirements.txt

3. Run the Application
   python web_app.py
   Open http://localhost:8080 in your browser

------------------------------------------------------------
USAGE
------------------------------------------------------------
1. Upload a 360° video (supports .mp4, .mov, .avi).
2. Use the Evidence.com-style interface to preview video.
3. Add timeline pins using the 📌 button to mark key moments.
4. Switch to the 360° view and drag your mouse or use gestures to look around.
5. Export the video using “Download” — select desired resolution.
6. Monitor background export progress in real-time.

------------------------------------------------------------
PIN MANAGEMENT SYSTEM
------------------------------------------------------------
- Add Pin: Press SPACEBAR or click “Add Pin”
- Edit Pin: Click pin marker on the timeline
- View Pin Data: Timestamp, yaw, pitch, and FOV
- Synchronization: Pins persist across both 2D and 360° players
- Auto-Snap: Camera automatically aligns to pin’s view angle
- Persistent Metadata: Pins stored locally and in CSV logs

------------------------------------------------------------
PERFORMANCE BENCHMARKS
------------------------------------------------------------
Supported Formats:          MP4, MOV, AVI
Max Resolution Tested:      3840x2160 (4K)
Average Load Time:          1.2 seconds per 100MB
Export Processing Time:     0.5x realtime (CPU), 0.2x (GPU)
Frame Rate:                 60 FPS in WebGL playback
Cross-Browser Support:      Chrome 80+, Firefox 75+, Edge 80+

------------------------------------------------------------
DESIGN HIGHLIGHTS
------------------------------------------------------------
- WebGL-based 360° rendering using Three.js
- Dual-fisheye stitching pipeline for panoramic projection
- FFmpeg multi-threaded encoding for optimized export times
- Responsive HTML/CSS with adaptive scaling
- Tooltip-based UI hints for intuitive interaction
- Modular Flask server supporting API expansion
- Auto-logging system for debugging and event review

------------------------------------------------------------
EXAMPLE WORKFLOW
------------------------------------------------------------
1. Launch application on localhost:8080
2. Upload a 360° video (e.g., "traffic_stop_fisheye.mp4")
3. Add pins at significant moments (e.g., officer exit, command issued)
4. View pins in the 360° player
5. Export video in “High Quality” mode
6. Download finished video with embedded metadata

------------------------------------------------------------
FUTURE WORK
------------------------------------------------------------
- Integrate GPU-accelerated video decoding with CUDA/VAAPI
- Cloud storage for metadata persistence
- Multi-user collaborative annotation mode
- RESTful API for Evidence.com backend integration
- Support for ProRes and DNxHD codecs
- WebAssembly-based client-side processing
- Integration with Axon Fleet dashboard

------------------------------------------------------------
AUTHOR
------------------------------------------------------------
Utkarsh Rai
R&D Intern — Axon Enterprises
Email: rai.utkarsh2007@gmail.com
LinkedIn: linkedin.com/in/utkarsh-rai-7249611b6
