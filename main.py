import cv2
import numpy as np
import json
import os
from typing import Dict, List, Tuple, Optional
import argparse
from dataclasses import dataclass
from datetime import timedelta
import math

@dataclass
class ViewConfig:
    """Configuration for viewing angle at a specific timestamp"""
    timestamp: float  # seconds
    yaw: float       # horizontal rotation (degrees)
    pitch: float     # vertical rotation (degrees)
    fov: float       # field of view (degrees)

class Video360Processor:
    def __init__(self, video_path: str):
        """
        Initialize the 360 video processor
        
        Args:
            video_path: Path to the 360-degree video file
        """
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        
        if not self.cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        # Get video properties
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = self.frame_count / self.fps
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"Video loaded: {self.width}x{self.height}, {self.fps} FPS, {self.duration:.2f}s duration")
        
        # Detect video format
        self.video_format = self._detect_video_format()
        print(f"Detected video format: {self.video_format}")
        
        # Default view configurations
        self.view_configs: List[ViewConfig] = []
        
    def _detect_video_format(self) -> str:
        """
        Detect if the video is equirectangular or dual-fisheye based on aspect ratio
        
        Returns:
            'equirectangular' or 'dual_fisheye'
        """
        aspect_ratio = self.width / self.height
        
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
        
    def add_view_config(self, timestamp: float, yaw: float, pitch: float = 0, fov: float = 90):
        """
        Add a view configuration for a specific timestamp
        
        Args:
            timestamp: Time in seconds
            yaw: Horizontal rotation in degrees
            pitch: Vertical rotation in degrees
            fov: Field of view in degrees
        """
        config = ViewConfig(timestamp=timestamp, yaw=yaw, pitch=pitch, fov=fov)
        self.view_configs.append(config)
        # Sort by timestamp
        self.view_configs.sort(key=lambda x: x.timestamp)
        
    def get_view_config_at_time(self, time: float) -> ViewConfig:
        """
        Get the view configuration for a specific time
        Uses stepwise (hold) logic: holds the last pin's view until the next pin.
        """
        if not self.view_configs:
            # Default view if no configurations
            return ViewConfig(time, 0, 0, 90)
        
        # Find the two closest configurations
        if time <= self.view_configs[0].timestamp:
            return self.view_configs[0]
        elif time >= self.view_configs[-1].timestamp:
            return self.view_configs[-1]
        
        # Stepwise (hold) logic: use the config at the last pin before this time
        for i in range(len(self.view_configs) - 1):
            if self.view_configs[i].timestamp <= time < self.view_configs[i + 1].timestamp:
                return self.view_configs[i]
        return self.view_configs[-1]
    
    def equirectangular_to_perspective(self, frame: np.ndarray, yaw: float, pitch: float, fov: float, 
                                     output_width: int = 1920, output_height: int = 1080) -> np.ndarray:
        """
        Convert equirectangular 360 video to perspective view
        
        Args:
            frame: Input equirectangular frame
            yaw: Horizontal rotation in degrees
            pitch: Vertical rotation in degrees
            fov: Field of view in degrees
            output_width: Output video width
            output_height: Output video height
            
        Returns:
            Perspective view frame
        """
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
    
    def dual_fisheye_to_equirectangular(self, frame: np.ndarray) -> np.ndarray:
        """
        Convert dual-fisheye video to equirectangular format using extrapolation
        
        Args:
            frame: Input dual-fisheye frame (two circular fisheye lenses side by side)
            
        Returns:
            Equirectangular frame
        """
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
                    color = self._sample_fisheye_extrapolated(frame, center_x1, center_y, circle_radius, dir_x, dir_y, dir_z, width, height)
                    
                    if color is None:
                        # If left lens doesn't have data, extrapolate from right lens
                        color = self._sample_fisheye_extrapolated(frame, center_x2, center_y, circle_radius, -dir_x, dir_y, -dir_z, width, height)
                else:
                    # Use right fisheye lens with extrapolation
                    center_x = center_x2
                    sample_x, sample_y, sample_z = -dir_x, dir_y, -dir_z
                    
                    # Try to sample from right lens first
                    color = self._sample_fisheye_extrapolated(frame, center_x2, center_y, circle_radius, -dir_x, dir_y, -dir_z, width, height)
                    
                    if color is None:
                        # If right lens doesn't have data, extrapolate from left lens
                        color = self._sample_fisheye_extrapolated(frame, center_x1, center_y, circle_radius, dir_x, dir_y, dir_z, width, height)
                
                if color is not None:
                    equirect[y, x] = color
        
        # Apply minimal smoothing to fill any remaining gaps
        equirect = self._minimal_smooth_equirectangular(equirect)
        
        return equirect
    
    def _sample_fisheye_direct(self, frame, center_x, center_y, circle_radius, dir_x, dir_y, dir_z, width, height):
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

    def _sample_fisheye_extrapolated(self, frame, center_x, center_y, circle_radius, dir_x, dir_y, dir_z, width, height):
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
    
    def _sample_fisheye(self, frame, center_x, center_y, circle_radius, dir_x, dir_y, dir_z, width, height):
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
    
    def _final_smooth_equirectangular(self, equirect: np.ndarray) -> np.ndarray:
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
    
    def _advanced_smooth_equirectangular(self, equirect: np.ndarray) -> np.ndarray:
        """
        Apply advanced smoothing to reduce artifacts in equirectangular conversion
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
    
    def _minimal_smooth_equirectangular(self, equirect: np.ndarray) -> np.ndarray:
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
    
    def _smooth_equirectangular_edges(self, equirect: np.ndarray) -> np.ndarray:
        """
        Apply edge smoothing to reduce artifacts in equirectangular conversion
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
    
    def process_video(self, output_path: str, output_width: int = 1920, output_height: int = 1080, progress_callback=None):
        """
        Process the 360 video and export as 2D video
        
        Args:
            output_path: Path for the output MP4 file
            output_width: Output video width
            output_height: Output video height
            progress_callback: Optional callback function for progress updates
        """
        # Set up video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.fps, (output_width, output_height))
        
        if not out.isOpened():
            raise ValueError(f"Could not create output video file: {output_path}")
        
        frame_count = 0
        total_frames = self.frame_count
        
        print(f"Processing {total_frames} frames...")
        if progress_callback:
            progress_callback(0, "Starting", "Initializing video processing...")
        
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Calculate current time
            current_time = frame_count / self.fps
            
            # Get view configuration for this time
            view_config = self.get_view_config_at_time(current_time)
            
            # Debug: Print configuration for first few frames
            if frame_count < 5 or frame_count % 300 == 0:  # First 5 frames and every 300 frames
                print(f"Frame {frame_count}, Time {current_time:.2f}s: yaw={view_config.yaw:.1f}°, pitch={view_config.pitch:.1f}°, fov={view_config.fov:.1f}°")
            
            # Convert frame format if needed
            if self.video_format == 'dual_fisheye':
                # Convert dual-fisheye to equirectangular first
                equirect_frame = self.dual_fisheye_to_equirectangular(frame)
                # Then convert to perspective view
                perspective_frame = self.equirectangular_to_perspective(
                    equirect_frame, view_config.yaw, view_config.pitch, view_config.fov,
                    output_width, output_height
                )
            else:
                # Direct equirectangular to perspective conversion
                perspective_frame = self.equirectangular_to_perspective(
                    frame, view_config.yaw, view_config.pitch, view_config.fov,
                    output_width, output_height
                )
            
            # Write frame
            out.write(perspective_frame)
            
            frame_count += 1
            
            # Progress update
            if frame_count % 30 == 0:  # Every 30 frames
                progress = (frame_count / total_frames) * 100
                print(f"Progress: {progress:.1f}% ({frame_count}/{total_frames})")
                if progress_callback:
                    progress_callback(progress, "Processing", f"Processing frame {frame_count}/{total_frames} ({progress:.1f}%)")
        
        # Clean up
        self.cap.release()
        out.release()
        if progress_callback:
            progress_callback(100, "Complete", "Video processing completed successfully!")
        print(f"Video processing complete! Output saved to: {output_path}")
    
    def save_config(self, config_path: str):
        """Save view configurations to JSON file"""
        config_data = {
            'video_path': self.video_path,
            'fps': self.fps,
            'duration': self.duration,
            'view_configs': [
                {
                    'timestamp': config.timestamp,
                    'yaw': config.yaw,
                    'pitch': config.pitch,
                    'fov': config.fov
                }
                for config in self.view_configs
            ]
        }
        
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        print(f"Configuration saved to: {config_path}")
    
    def load_config(self, config_path: str):
        """Load view configurations from JSON file"""
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        self.view_configs = []
        for config in config_data['view_configs']:
            self.view_configs.append(ViewConfig(
                timestamp=config['timestamp'],
                yaw=config['yaw'],
                pitch=config['pitch'],
                fov=config['fov']
            ))
        
        print(f"Configuration loaded from: {config_path}")
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()

def create_sample_config():
    """Create a sample configuration for testing"""
    processor = Video360Processor("sample_360_video.mp4")  # Placeholder
    
    # Example: 3-minute video with different viewing angles
    # Minute 1: Look straight ahead
    processor.add_view_config(0, yaw=0, pitch=0, fov=90)
    processor.add_view_config(60, yaw=0, pitch=0, fov=90)
    
    # Minute 2: Look to the right
    processor.add_view_config(60, yaw=0, pitch=0, fov=90)
    processor.add_view_config(120, yaw=90, pitch=0, fov=90)
    
    # Minute 3: Look up and to the left
    processor.add_view_config(120, yaw=90, pitch=0, fov=90)
    processor.add_view_config(180, yaw=-45, pitch=30, fov=90)
    
    processor.save_config("sample_config.json")
    return processor



def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(description='360 Video Processor')
    parser.add_argument('input_video', help='Input 360-degree video file')
    parser.add_argument('output_video', help='Output 2D video file')
    parser.add_argument('--config', help='Configuration JSON file')
    parser.add_argument('--width', type=int, default=1920, help='Output width')
    parser.add_argument('--height', type=int, default=1080, help='Output height')
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = Video360Processor(args.input_video)
    
    # Load configuration if provided
    if args.config:
        processor.load_config(args.config)
    else:
        # Create a simple default configuration
        processor.add_view_config(0, yaw=0, pitch=0, fov=90)
        processor.add_view_config(processor.duration, yaw=360, pitch=0, fov=90)
    
    # Process video
    processor.process_video(args.output_video, args.width, args.height)

if __name__ == "__main__":
    # Example usage
    print("360 Video Processor")
    print("==================")
    print()
    print("This script can process 360-degree videos and export them as 2D videos")
    print("with configurable viewing angles for different timestamps.")
    print()
    print("To use:")
    print("1. Place your 360 video in the same directory")
    print("2. Create a configuration or use the default")
    print("3. Run: python main.py input_video.mp4 output_video.mp4")
    print()
    print("For more options: python main.py --help")
    
    # Uncomment the line below to run with command line arguments
    # main(

