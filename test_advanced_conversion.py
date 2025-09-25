#!/usr/bin/env python3
"""
Test script for advanced dual-fisheye video processing
"""

import cv2
import numpy as np
from main import Video360Processor

def test_advanced_conversion():
    """Test the advanced dual-fisheye to equirectangular conversion"""
    
    # Initialize processor with the dual-fisheye video
    processor = Video360Processor('video_19700101_010546.mp4')
    
    print(f"Video format: {processor.video_format}")
    print(f"Dimensions: {processor.width}x{processor.height}")
    print(f"Aspect ratio: {processor.width/processor.height:.3f}")
    
    # Read the first frame
    ret, frame = processor.cap.read()
    if not ret:
        print("Could not read frame")
        return
    
    print(f"Frame shape: {frame.shape}")
    
    # Convert dual-fisheye to equirectangular with advanced algorithm
    if processor.video_format == 'dual_fisheye':
        equirect_frame = processor.dual_fisheye_to_equirectangular(frame)
        print(f"Advanced equirectangular frame shape: {equirect_frame.shape}")
        
        # Save the converted frame for inspection
        cv2.imwrite('advanced_equirectangular.jpg', equirect_frame)
        cv2.imwrite('original_dual_fisheye.jpg', frame)
        
        print("Saved advanced_equirectangular.jpg and original_dual_fisheye.jpg for inspection")
        
        # Test perspective conversion at the seam area (around 180 degrees)
        perspective_frame = processor.equirectangular_to_perspective(
            equirect_frame, yaw=180, pitch=0, fov=90, 
            output_width=1920, output_height=1080
        )
        
        cv2.imwrite('advanced_perspective_seam.jpg', perspective_frame)
        print("Saved advanced_perspective_seam.jpg (viewing the seam area)")
        
        # Test front view
        perspective_frame = processor.equirectangular_to_perspective(
            equirect_frame, yaw=0, pitch=0, fov=90, 
            output_width=1920, output_height=1080
        )
        
        cv2.imwrite('advanced_perspective_front.jpg', perspective_frame)
        print("Saved advanced_perspective_front.jpg (front view)")
        
        print("Advanced dual-fisheye conversion test completed successfully!")
        print("Check the generated images to see the improvement in seam quality.")
        print("The seam area should now be much smoother without the vertical distortion line.")
    else:
        print("Video is not dual-fisheye format")

if __name__ == "__main__":
    test_advanced_conversion() 