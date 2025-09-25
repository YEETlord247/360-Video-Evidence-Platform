#!/usr/bin/env python3
"""
Test script for final 60% transition zone dual-fisheye conversion
"""

import cv2
import numpy as np
from main import Video360Processor

def test_60_percent_transition():
    """Test the final 60% transition zone approach"""
    
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

    # Convert dual-fisheye to equirectangular with 60% transition zone
    if processor.video_format == 'dual_fisheye':
        equirect_frame = processor.dual_fisheye_to_equirectangular(frame)
        print(f"60% transition zone equirectangular frame shape: {equirect_frame.shape}")
        
        # Save the converted frame for inspection
        cv2.imwrite('60_percent_transition_equirectangular.jpg', equirect_frame)
        cv2.imwrite('original_dual_fisheye.jpg', frame)
        
        print("Saved 60_percent_transition_equirectangular.jpg and original_dual_fisheye.jpg for inspection")
        
        # Test perspective conversion at the seam area (around 180 degrees)
        perspective_frame = processor.equirectangular_to_perspective(
            equirect_frame, yaw=180, pitch=0, fov=90, 
            output_width=1920, output_height=1080
        )
        
        cv2.imwrite('60_percent_transition_perspective_seam.jpg', perspective_frame)
        print("Saved 60_percent_transition_perspective_seam.jpg (viewing the seam area)")
        
        # Test front view
        perspective_frame = processor.equirectangular_to_perspective(
            equirect_frame, yaw=0, pitch=0, fov=90, 
            output_width=1920, output_height=1080
        )
        
        cv2.imwrite('60_percent_transition_perspective_front.jpg', perspective_frame)
        print("Saved 60_percent_transition_perspective_front.jpg (front view)")
        
        # Test side view
        perspective_frame = processor.equirectangular_to_perspective(
            equirect_frame, yaw=90, pitch=0, fov=90, 
            output_width=1920, output_height=1080
        )
        
        cv2.imwrite('60_percent_transition_perspective_side.jpg', perspective_frame)
        print("Saved 60_percent_transition_perspective_side.jpg (side view)")
        
        print("60% transition zone conversion test completed successfully!")
        print("Check the generated images to see if the 60% transition zone eliminates the seam.")
        print("This is the maximum transition zone - it should provide complete blending.")
    else:
        print("Video is not dual-fisheye format")

if __name__ == "__main__":
    test_60_percent_transition() 

