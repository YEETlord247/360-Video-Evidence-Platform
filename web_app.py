#!/usr/bin/env python3
"""
360 Video Player Web Application

This Flask application provides a web-based 360-degree video player
that renders equirectangular videos on a sphere using Three.js.
The user is positioned at the center and can look around in 360 degrees.
"""

from flask import Flask, render_template, request, jsonify, send_file, Response
from werkzeug.utils import secure_filename
import os
import cv2
import numpy as np
import tempfile
from datetime import datetime
import json
import threading
import time

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global variable to store current video info
current_video_info = None

# Global variable to store export progress
export_progress = {'progress': 0, 'status': 'idle', 'message': ''}

# Global variable to store timeline pins
timeline_pins = {}

@app.route('/')
def index():
    """Main Evidence.com-style interface page"""
    global current_video_info, timeline_pins
    
    # Clear pins if no video is currently loaded
    if current_video_info is None:
        timeline_pins = {}
    
    return render_template('evidence_interface.html')

@app.route('/fullscreen')
def fullscreen_player():
    """Fullscreen 360 video player page"""
    video = request.args.get('video')
    return render_template('fullscreen_player.html', video=video)

@app.route('/upload', methods=['POST'])
def upload_video():
    """Handle video upload"""
    global current_video_info, timeline_pins
    
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Get video properties
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                return jsonify({'error': 'Could not open video file'}), 400
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            
            current_video_info = {
                'filename': filename,
                'filepath': filepath,
                'duration': duration,
                'fps': fps,
                'width': width,
                'height': height,
                'frame_count': frame_count
            }
            
            # Clear pins for the new video
            timeline_pins[filename] = []
            
            return jsonify({
                'success': True,
                'filename': filename,
                'duration': duration,
                'fps': fps,
                'width': width,
                'height': height
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 400

@app.route('/video/<filename>')
def serve_video(filename):
    """Serve video files"""
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/frame_image')
def frame_image():
    """Extract a frame at a given timestamp and return as JPEG image"""
    global current_video_info
    if current_video_info is None:
        return jsonify({'error': 'No video loaded'}), 400
    
    ts = request.args.get('timestamp', type=float)
    if ts is None:
        return jsonify({'error': 'No timestamp provided'}), 400
    
    cap = cv2.VideoCapture(current_video_info['filepath'])
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_idx = int(ts * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return jsonify({'error': 'Could not extract frame'}), 400
    
    # Convert BGR to RGB
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    # Encode as JPEG
    _, buf = cv2.imencode('.jpg', frame)
    return Response(buf.tobytes(), mimetype='image/jpeg')

def detect_video_format(width, height):
    """Detect if the video is equirectangular or dual-fisheye based on aspect ratio"""
    aspect_ratio = width / height
    
    # Dual-fisheye typically has aspect ratio around 2.25:1 (two circles side by side)
    # Equirectangular typically has aspect ratio around 2:1 (360° x 180°)
    if 2.0 <= aspect_ratio <= 2.5:
        # Check if it's closer to dual-fisheye (2.25:1) or equirectangular (2:1)
        if abs(aspect_ratio - 2.25) < abs(aspect_ratio - 2.0):
            return 'dual_fisheye'
        else:
            return 'equirectangular'
    elif aspect_ratio > 2.5:
        # Very wide aspect ratio, likely dual-fisheye
        return 'dual_fisheye'
    else:
        # Narrower aspect ratio, likely equirectangular
        return 'equirectangular'

def dual_fisheye_to_equirectangular(frame):
    """Convert dual-fisheye video to equirectangular format using extrapolation"""
    height, width = frame.shape[:2]
    
    # Create equirectangular output (2:1 aspect ratio)
    equirect_width = width // 2
    equirect_height = equirect_width // 2
    equirect = np.zeros((equirect_height, equirect_width, 3), dtype=np.uint8)
    
    # Calculate fisheye circle parameters
    circle_radius = min(height // 2, width // 4)
    center_y = height // 2
    center_x1 = width // 4  # Left circle center
    center_x2 = 3 * width // 4  # Right circle center
    
    # For each pixel in the equirectangular output
    for y in range(equirect_height):
        for x in range(equirect_width):
            # Convert equirectangular coordinates to spherical coordinates
            lon = (x / equirect_width) * 2 * np.pi  # longitude: 0 to 2π
            lat = (y / equirect_height - 0.5) * np.pi  # latitude: -π/2 to π/2
            
            # Convert spherical coordinates to 3D unit vector
            cos_lat = np.cos(lat)
            dir_x = cos_lat * np.sin(lon)
            dir_y = np.sin(lat)
            dir_z = cos_lat * np.cos(lon)
            
            # Use extrapolation approach - extend each lens beyond its natural boundary
            # Map directly from spherical coordinates to fisheye coordinates with extrapolation
            
            # Calculate which fisheye lens to use based on longitude
            x_normalized = x / equirect_width
            
            if x_normalized < 0.5:
                # Use left fisheye lens with extrapolation
                center_x = center_x1
                sample_x, sample_y, sample_z = dir_x, dir_y, dir_z
                
                # Try to sample from left lens first
                color = sample_fisheye_extrapolated(frame, center_x1, center_y, circle_radius, dir_x, dir_y, dir_z, width, height)
                
                if color is None:
                    # If left lens doesn't have data, extrapolate from right lens
                    color = sample_fisheye_extrapolated(frame, center_x2, center_y, circle_radius, -dir_x, dir_y, -dir_z, width, height)
            else:
                # Use right fisheye lens with extrapolation
                center_x = center_x2
                sample_x, sample_y, sample_z = -dir_x, dir_y, -dir_z
                
                # Try to sample from right lens first
                color = sample_fisheye_extrapolated(frame, center_x2, center_y, circle_radius, -dir_x, dir_y, -dir_z, width, height)
                
                if color is None:
                    # If right lens doesn't have data, extrapolate from left lens
                    color = sample_fisheye_extrapolated(frame, center_x1, center_y, circle_radius, dir_x, dir_y, dir_z, width, height)
            
            if color is not None:
                equirect[y, x] = color
    
    # Apply minimal smoothing to fill any remaining gaps
    equirect = minimal_smooth_equirectangular(equirect)
    
    return equirect

def sample_fisheye(frame, center_x, center_y, circle_radius, dir_x, dir_y, dir_z, width, height):
    """Sample a color from the fisheye image at the given direction"""
    if dir_z <= 0:
        return None
    
    # Calculate fisheye coordinates
    angle = np.arctan2(np.sqrt(dir_x**2 + dir_y**2), dir_z)
    r = circle_radius * np.tan(angle)
    
    if r > circle_radius:
        return None
    
    if r > 0:
        fisheye_x = center_x + int((dir_x / np.sqrt(dir_x**2 + dir_y**2)) * r)
        fisheye_y = center_y + int((dir_y / np.sqrt(dir_x**2 + dir_y**2)) * r)
    else:
        fisheye_x = center_x
        fisheye_y = center_y
    
    # Check bounds and sample the frame
    if 0 <= fisheye_x < width and 0 <= fisheye_y < height:
        return frame[fisheye_y, fisheye_x]
    
    return None

def sample_fisheye_direct(frame, center_x, center_y, circle_radius, dir_x, dir_y, dir_z, width, height):
    """Sample from fisheye image using direct spherical mapping"""
    if dir_z <= 0:
        return None
    
    # Calculate angle from optical axis
    angle = np.arctan2(np.sqrt(dir_x**2 + dir_y**2), dir_z)
    
    # Use equisolid angle projection for better quality
    r = circle_radius * np.sin(angle)
    
    if r > circle_radius:
        return None
    
    # Calculate fisheye coordinates
    if r > 0:
        fisheye_x = center_x + int((dir_x / np.sqrt(dir_x**2 + dir_y**2)) * r)
        fisheye_y = center_y + int((dir_y / np.sqrt(dir_x**2 + dir_y**2)) * r)
    else:
        fisheye_x = center_x
        fisheye_y = center_y
    
    # Sample from fisheye image
    if 0 <= fisheye_x < width and 0 <= fisheye_y < height:
        return frame[fisheye_y, fisheye_x]
    
    return None

def sample_fisheye_extrapolated(frame, center_x, center_y, circle_radius, dir_x, dir_y, dir_z, width, height):
    """Sample from fisheye image using extrapolation beyond natural boundaries"""
    if dir_z <= 0:
        return None
    
    # Calculate angle from optical axis
    angle = np.arctan2(np.sqrt(dir_x**2 + dir_y**2), dir_z)
    
    # Use equisolid angle projection for better quality
    r = circle_radius * np.sin(angle)
    
    # Allow extrapolation beyond the natural circle radius
    # This extends the lens coverage beyond its physical limits
    extrapolation_factor = 1.5  # Extend 50% beyond natural radius
    max_r = circle_radius * extrapolation_factor
    
    if r > max_r:
        return None
    
    # Calculate fisheye coordinates
    if r > 0:
        fisheye_x = center_x + int((dir_x / np.sqrt(dir_x**2 + dir_y**2)) * r)
        fisheye_y = center_y + int((dir_y / np.sqrt(dir_x**2 + dir_y**2)) * r)
    else:
        fisheye_x = center_x
        fisheye_y = center_y
    
    # Sample from fisheye image with extrapolation
    if 0 <= fisheye_x < width and 0 <= fisheye_y < height:
        # If within natural radius, use direct sampling
        if r <= circle_radius:
            return frame[fisheye_y, fisheye_x]
        else:
            # Extrapolate beyond natural radius using nearest neighbor
            # Find the nearest valid pixel within the natural radius
            natural_r = circle_radius
            if r > natural_r:
                # Scale back to natural radius
                scale_factor = natural_r / r
                natural_x = center_x + int((dir_x / np.sqrt(dir_x**2 + dir_y**2)) * natural_r)
                natural_y = center_y + int((dir_y / np.sqrt(dir_x**2 + dir_y**2)) * natural_r)
                
                if 0 <= natural_x < width and 0 <= natural_y < height:
                    return frame[natural_y, natural_x]
    
    return None

def minimal_smooth_equirectangular(equirect):
    """
    Apply minimal smoothing only to fill gaps, preserving sharp details
    """
    height, width = equirect.shape[:2]
    
    # Create a mask only for black pixels (gaps)
    mask = np.zeros((height, width), dtype=np.uint8)
    
    # Mark only areas with black pixels
    for y in range(height):
        for x in range(width):
            pixel = equirect[y, x]
            if np.all(pixel == 0):  # Black pixel (gap)
                mask[y, x] = 1
    
    # Apply very light Gaussian blur to the mask
    kernel_size = 3
    mask = cv2.GaussianBlur(mask.astype(np.float32), (kernel_size, kernel_size), 0)
    
    # Apply very light smoothing to the original image
    smoothed = cv2.GaussianBlur(equirect, (3, 3), 0.5)
    
    # Blend original and smoothed images based on mask
    result = equirect.copy()
    for y in range(height):
        for x in range(width):
            if mask[y, x] > 0.1:  # Only fill gaps
                alpha = min(mask[y, x], 0.3)  # Very light smoothing
                result[y, x] = (1 - alpha) * equirect[y, x] + alpha * smoothed[y, x]
    
    return result

def final_smooth_equirectangular(equirect):
    """
    Apply final smoothing to eliminate any remaining artifacts
    """
    height, width = equirect.shape[:2]
    
    # Create a mask for areas that need smoothing
    mask = np.zeros((height, width), dtype=np.uint8)
    
    # Mark areas with black pixels or sharp transitions
    for y in range(height):
        for x in range(width):
            pixel = equirect[y, x]
            if np.all(pixel == 0):  # Black pixel
                mask[y, x] = 1
            elif x > 0 and y > 0:
                # Check for sharp transitions
                prev_pixel = equirect[y, x-1]
                above_pixel = equirect[y-1, x]
                if (np.linalg.norm(pixel - prev_pixel) > 50 or 
                    np.linalg.norm(pixel - above_pixel) > 50):
                    mask[y, x] = 1
    
    # Apply Gaussian blur to smooth the mask
    kernel_size = 5
    mask = cv2.GaussianBlur(mask.astype(np.float32), (kernel_size, kernel_size), 0)
    
    # Apply smoothing to the original image
    smoothed = cv2.GaussianBlur(equirect, (3, 3), 0)
    
    # Blend original and smoothed images based on mask
    result = equirect.copy()
    for y in range(height):
        for x in range(width):
            if mask[y, x] > 0.1:  # Only smooth problematic areas
                alpha = min(mask[y, x], 0.8)  # Limit smoothing strength
                result[y, x] = (1 - alpha) * equirect[y, x] + alpha * smoothed[y, x]
    
    return result

def advanced_smooth_equirectangular(equirect):
    """Apply advanced smoothing to reduce artifacts in equirectangular conversion"""
    height, width = equirect.shape[:2]
    
    # Create a mask for areas that need smoothing
    mask = np.zeros((height, width), dtype=np.uint8)
    
    # Mark areas with black pixels or sharp transitions
    for y in range(height):
        for x in range(width):
            pixel = equirect[y, x]
            if np.all(pixel == 0):  # Black pixel
                mask[y, x] = 1
            elif x > 0 and y > 0:
                # Check for sharp transitions
                prev_pixel = equirect[y, x-1]
                above_pixel = equirect[y-1, x]
                if (np.linalg.norm(pixel - prev_pixel) > 50 or 
                    np.linalg.norm(pixel - above_pixel) > 50):
                    mask[y, x] = 1
    
    # Apply Gaussian blur to smooth the mask
    kernel_size = 5
    mask = cv2.GaussianBlur(mask.astype(np.float32), (kernel_size, kernel_size), 0)
    
    # Apply smoothing to the original image
    smoothed = cv2.GaussianBlur(equirect, (3, 3), 0)
    
    # Blend original and smoothed images based on mask
    result = equirect.copy()
    for y in range(height):
        for x in range(width):
            if mask[y, x] > 0.1:  # Only smooth problematic areas
                alpha = min(mask[y, x], 0.8)  # Limit smoothing strength
                result[y, x] = (1 - alpha) * equirect[y, x] + alpha * smoothed[y, x]
    
    return result

def smooth_equirectangular_edges(equirect):
    """Apply edge smoothing to reduce artifacts in equirectangular conversion"""
    height, width = equirect.shape[:2]
    
    # Create a mask for areas that need smoothing
    mask = np.zeros((height, width), dtype=np.uint8)
    
    # Mark areas with black pixels or sharp transitions
    for y in range(height):
        for x in range(width):
            pixel = equirect[y, x]
            if np.all(pixel == 0):  # Black pixel
                mask[y, x] = 1
            elif x > 0 and y > 0:
                # Check for sharp transitions
                prev_pixel = equirect[y, x-1]
                above_pixel = equirect[y-1, x]
                if (np.linalg.norm(pixel - prev_pixel) > 50 or 
                    np.linalg.norm(pixel - above_pixel) > 50):
                    mask[y, x] = 1
    
    # Apply Gaussian blur to smooth the mask
    kernel_size = 5
    mask = cv2.GaussianBlur(mask.astype(np.float32), (kernel_size, kernel_size), 0)
    
    # Apply smoothing to the original image
    smoothed = cv2.GaussianBlur(equirect, (3, 3), 0)
    
    # Blend original and smoothed images based on mask
    result = equirect.copy()
    for y in range(height):
        for x in range(width):
            if mask[y, x] > 0.1:  # Only smooth problematic areas
                alpha = min(mask[y, x], 0.8)  # Limit smoothing strength
                result[y, x] = (1 - alpha) * equirect[y, x] + alpha * smoothed[y, x]
    
    return result

def equirectangular_to_perspective(frame, yaw, pitch, fov, output_width, output_height):
    """Convert equirectangular 360 video to perspective view"""
    # Clamp pitch to avoid singularity at the poles
    pitch = np.clip(pitch, -85, 85)
    # Convert degrees to radians
    yaw_rad = np.radians(yaw)
    pitch_rad = np.radians(pitch)
    fov_rad = np.radians(fov)
    
    # Create output image
    output = np.zeros((output_height, output_width, 3), dtype=np.uint8)
    
    # Calculate focal length from FOV
    focal_length = output_width / (2 * np.tan(fov_rad / 2))
    
    # Create coordinate grids
    x_grid, y_grid = np.meshgrid(np.arange(output_width), np.arange(output_height))
    
    # Convert to normalized coordinates
    x_norm = (x_grid - output_width / 2) / focal_length
    y_norm = (y_grid - output_height / 2) / focal_length
    
    # Create direction vectors
    directions = np.stack([x_norm, y_norm, np.ones_like(x_norm)], axis=-1)
    
    # Apply rotation matrices
    # Pitch rotation (around X axis) FIRST
    cos_pitch, sin_pitch = np.cos(pitch_rad), np.sin(pitch_rad)
    pitch_matrix = np.array([
        [1, 0, 0],
        [0, cos_pitch, -sin_pitch],
        [0, sin_pitch, cos_pitch]
    ])
    directions = np.dot(directions, pitch_matrix.T)
    
    # Yaw rotation (around Y axis) SECOND
    cos_yaw, sin_yaw = np.cos(yaw_rad), np.sin(yaw_rad)
    yaw_matrix = np.array([
        [cos_yaw, 0, sin_yaw],
        [0, 1, 0],
        [-sin_yaw, 0, cos_yaw]
    ])
    directions = np.dot(directions, yaw_matrix.T)
    
    # Convert to spherical coordinates
    x, y, z = directions[..., 0], directions[..., 1], directions[..., 2]
    
    # Convert to equirectangular coordinates
    lat = np.arcsin(y)
    lon = np.arctan2(x, z)
    
    # Convert to pixel coordinates
    u = (lon / (2 * np.pi) + 0.5) * frame.shape[1]
    v = (lat / np.pi + 0.5) * frame.shape[0]
    
    # Ensure coordinates are within bounds
    u = np.clip(u, 0, frame.shape[1] - 1)
    v = np.clip(v, 0, frame.shape[0] - 1)
    
    # Sample the frame using bilinear interpolation
    u_floor, v_floor = np.floor(u).astype(int), np.floor(v).astype(int)
    u_ceil, v_ceil = np.minimum(u_floor + 1, frame.shape[1] - 1), np.minimum(v_floor + 1, frame.shape[0] - 1)
    
    # Interpolation weights
    w_u = u - u_floor
    w_v = v - v_floor
    
    # Bilinear interpolation
    output = (
        (1 - w_u)[..., np.newaxis] * (1 - w_v)[..., np.newaxis] * frame[v_floor, u_floor] +
        w_u[..., np.newaxis] * (1 - w_v)[..., np.newaxis] * frame[v_floor, u_ceil] +
        (1 - w_u)[..., np.newaxis] * w_v[..., np.newaxis] * frame[v_ceil, u_floor] +
        w_u[..., np.newaxis] * w_v[..., np.newaxis] * frame[v_ceil, u_ceil]
    ).astype(np.uint8)
    
    return output

def get_view_config_at_time(view_configs, time):
    """Get the view configuration for a specific time (stepwise logic)"""
    if not view_configs:
        return {'yaw': 0, 'pitch': 0, 'fov': 90}
    
    # Find the two closest configurations
    if time <= view_configs[0]['timestamp']:
        return view_configs[0]
    elif time >= view_configs[-1]['timestamp']:
        return view_configs[-1]
    
    # Stepwise (hold) logic: use the config at the last pin before this time
    for i in range(len(view_configs) - 1):
        if view_configs[i]['timestamp'] <= time < view_configs[i + 1]['timestamp']:
            return view_configs[i]
    return view_configs[-1]

def process_video_export(video_path, view_configs, output_width, output_height, progress_callback):
    """Process video export with progress updates"""
    global export_progress
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_frames = frame_count
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Detect video format
    video_format = detect_video_format(width, height)
    print(f"Detected video format: {video_format}")
    
    # Create output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"export_{timestamp}.mp4"
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
    
    # Set up video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (output_width, output_height))
    
    if not out.isOpened():
        raise ValueError(f"Could not create output video file: {output_path}")
    
    frame_idx = 0
    
    progress_callback(0, "Starting", "Initializing video processing...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Calculate current time
        current_time = frame_idx / fps
        
        # Get view configuration for this time
        view_config = get_view_config_at_time(view_configs, current_time)
        
        # Convert frame format if needed
        if video_format == 'dual_fisheye':
            # Convert dual-fisheye to equirectangular first
            equirect_frame = dual_fisheye_to_equirectangular(frame)
            # Then convert to perspective view
            perspective_frame = equirectangular_to_perspective(
                equirect_frame, view_config['yaw'], view_config['pitch'], view_config['fov'],
                output_width, output_height
            )
        else:
            # Direct equirectangular to perspective conversion
            perspective_frame = equirectangular_to_perspective(
                frame, view_config['yaw'], view_config['pitch'], view_config['fov'],
                output_width, output_height
            )
        
        # Write frame
        out.write(perspective_frame)
        
        frame_idx += 1
        
        # Progress update every 30 frames
        if frame_idx % 30 == 0:
            progress = (frame_idx / total_frames) * 100
            progress_callback(progress, "Processing", f"Processing frame {frame_idx}/{total_frames} ({progress:.1f}%)")
    
    # Clean up
    cap.release()
    out.release()
    
    progress_callback(100, "Complete", "Video processing completed successfully!")
    return output_filename

@app.route('/export_video', methods=['POST'])
def export_video():
    """Handle video export request"""
    global current_video_info, export_progress
    
    print("Export request received")
    print("Current video info:", current_video_info)
    
    if current_video_info is None:
        print("Error: No video loaded")
        return jsonify({'error': 'No video loaded'}), 400
    
    try:
        data = request.get_json()
        print("Received data:", data)
        
        view_configs = data.get('viewConfigs', [])
        resolution = data.get('resolution', {'width': 1920, 'height': 1080})
        
        print("View configs:", view_configs)
        print("Resolution:", resolution)
        
        if not view_configs:
            print("Error: No view configurations provided")
            return jsonify({'error': 'No view configurations provided'}), 400
        
        # Reset progress
        export_progress = {'progress': 0, 'status': 'starting', 'message': 'Initializing...'}
        
        def progress_callback(progress, status, message):
            global export_progress
            export_progress = {'progress': progress, 'status': status, 'message': message}
        
        # Start export in a separate thread
        def export_thread():
            try:
                output_filename = process_video_export(
                    current_video_info['filepath'],
                    view_configs,
                    resolution['width'],
                    resolution['height'],
                    progress_callback
                )
                
                # Update progress with success
                export_progress.update({
                    'success': True,
                    'filename': output_filename,
                    'download_url': f'/download/{output_filename}'
                })
            except Exception as e:
                export_progress.update({
                    'success': False,
                    'error': str(e)
                })
        
        thread = threading.Thread(target=export_thread)
        thread.start()
        
        return jsonify({'success': True, 'message': 'Export started'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/export_progress')
def get_export_progress():
    """Get current export progress"""
    global export_progress
    return jsonify(export_progress)

@app.route('/download/<filename>')
def download_file(filename):
    """Download exported video file"""
    return send_file(
        os.path.join(app.config['UPLOAD_FOLDER'], filename),
        as_attachment=True,
        download_name=filename
    )

@app.route('/add_pin', methods=['POST'])
def add_pin():
    """Add a timeline pin"""
    global timeline_pins, current_video_info
    
    if current_video_info is None:
        return jsonify({'error': 'No video loaded'}), 400
    
    data = request.get_json()
    timestamp = data.get('timestamp')
    yaw = data.get('yaw', 0)
    pitch = data.get('pitch', 0)
    fov = data.get('fov', 90)
    
    if timestamp is None:
        return jsonify({'error': 'No timestamp provided'}), 400
    
    video_filename = current_video_info['filename']
    if video_filename not in timeline_pins:
        timeline_pins[video_filename] = []
    
    pin_id = len(timeline_pins[video_filename])
    pin = {
        'id': pin_id,
        'timestamp': timestamp,
        'yaw': yaw,
        'pitch': pitch,
        'fov': fov
    }
    
    timeline_pins[video_filename].append(pin)
    return jsonify({'success': True, 'pin': pin})

@app.route('/get_pins')
def get_pins():
    """Get timeline pins for current video"""
    global timeline_pins, current_video_info
    
    if current_video_info is None:
        return jsonify({'pins': []})
    
    video_filename = current_video_info['filename']
    pins = timeline_pins.get(video_filename, [])
    return jsonify({'pins': pins})

@app.route('/clear_pins', methods=['POST'])
def clear_pins():
    """Clear all pins for current video"""
    global timeline_pins, current_video_info
    
    if current_video_info is None:
        return jsonify({'error': 'No video loaded'}), 400
    
    video_filename = current_video_info['filename']
    if video_filename in timeline_pins:
        timeline_pins[video_filename] = []
    
    return jsonify({'success': True, 'message': 'Pins cleared'})

@app.route('/clear_all_pins', methods=['POST'])
def clear_all_pins():
    """Clear all pins for all videos"""
    global timeline_pins
    timeline_pins = {}
    return jsonify({'success': True, 'message': 'All pins cleared'})

if __name__ == '__main__':
    print("Starting 360 Video Player...")
    print("Open your browser and go to: http://localhost:8080")
    app.run(debug=True, host='0.0.0.0', port=8080) 