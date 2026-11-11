import sys
import math
import cv2
import numpy as np
import random
from anim_math import calculate_easing

# Studio Quality Settings (Full HD 1080p scale down to 60fps cinematic)
width, height = 1280, 720
fps = 30
total_frames = 150

output_path = r"H:\MASTER_AI_WORKSTATION\MASTER_AI_WORKSTATION\MASTER_CORE_V1\studio_quality_space.mp4"
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

print(f"[STUDIO RENDER] Generating Cinematic Studio-Quality Space Animation...")

# Generate high-density star field with varying brightness
stars = []
for _ in range(120):
    stars.append({
        'x': random.randint(0, width),
        'y': random.randint(0, height),
        'size': random.choice([1, 2, 3]),
        'brightness': random.randint(150, 255)
    })

for frame in range(total_frames + 1):
    # Deep space gradient background
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (15, 8, 20) # Deep cosmic purple/black
    
    # Draw glowing stars
    for star in stars:
        sy = (star['y'] + frame * (star['size'] * 2)) % height
        color = (star['brightness'], star['brightness'], 255)
        cv2.circle(img, (star['x'], sy), star['size'], color, -1)
        
    # Cinematic camera movement using easing for rocket lift-off
    progress_y = calculate_easing(frame, 0, -450, total_frames, "quadratic_in")
    base_y = int(500 + progress_y)
    
    # Draw Exhaust Flame / Particle Glow
    flame_height = int(40 + math.sin(frame * 0.5) * 15)
    pts_flame = np.array([[625, base_y + 80], [640, base_y + 120 + flame_height], [655, base_y + 80]], np.int32)
    cv2.fillPoly(img, [pts_flame], (0, 165, 255)) # Glowing orange flame
    
    # Draw Sleek Studio-Grade Rocket Body
    pts_body = np.array([[640, base_y], [610, base_y + 80], [670, base_y + 80]], np.int32)
    cv2.fillPoly(img, [pts_body], (230, 50, 50)) # Crimson red body
    
    # Rocket Fins
    pts_left_fin = np.array([[610, base_y + 50], [590, base_y + 90], [610, base_y + 80]], np.int32)
    pts_right_fin = np.array([[670, base_y + 50], [690, base_y + 90], [670, base_y + 80]], np.int32)
    cv2.fillPoly(img, [pts_left_fin], (100, 100, 100))
    cv2.fillPoly(img, [pts_right_fin], (100, 100, 100))
    
    # Glass Window Cockpit (Cyan Glow)
    cv2.circle(img, (640, base_y + 35), 10, (255, 255, 0), -1)
    
    video_writer.write(img)

video_writer.release()
print(f"[SUCCESS] Studio-Quality MP4 generated at: {output_path}")