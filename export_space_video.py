import os
import cv2
import numpy as np
import tkinter as tk
from anim_math import calculate_easing

# Setup offscreen or canvas rendering for video capture
width, height = 800, 600
fps = 30
total_frames = 120

output_path = r"H:\MASTER_AI_WORKSTATION\MASTER_AI_WORKSTATION\MASTER_CORE_V1\space_mission.mp4"
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

print(f"[RECORDING] Generating frames and rendering MP4 video...")

# Create frame-by-frame rendering for video export
for frame in range(total_frames + 1):
    # Create a blank black frame (OpenCV uses BGR)
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (25, 15, 11) # Dark space background color (#0b0f19 in BGR approx)
    
    # Draw stars
    for i in range(50):
        sx = (i * 37) % width
        sy = (i * 59) % height
        cv2.circle(img, (sx, sy), 1, (255, 255, 255), -1)
        
    # Calculate rocket position using easing
    dy = int(calculate_easing(frame, 0, -350, total_frames, "quadratic_in"))
    
    # Draw Rocket (Polygon, Window, Flame)
    pts = np.array([[400, 220+dy], [385, 270+dy], [415, 270+dy]], np.int32)
    cv2.fillPoly(img, [pts], (44, 76, 231)) # Red-ish in BGR
    cv2.circle(img, (400, 243+dy), 8, (219, 152, 52), -1) # Window
    
    flame_pts = np.array([[390, 270+dy], [400, 300+dy + (frame%5)*3], [410, 270+dy]], np.int32)
    cv2.fillPoly(img, [flame_pts], (15, 196, 241)) # Flame yellow/orange
    
    # Write frame to video
    video_writer.write(img)

video_writer.release()
print(f"[SUCCESS] MP4 Video successfully generated and saved at: {output_path}")