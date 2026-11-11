import sys
import math
import cv2
import numpy as np
import random
from anim_math import calculate_easing

# Professional Studio Settings (1280x720 Cinematic Widescreen at 30 FPS)
width, height = 1280, 720
fps = 30
total_frames = 180

output_path = r"H:\MASTER_AI_WORKSTATION\MASTER_AI_WORKSTATION\MASTER_CORE_V1\cinematic_space_cutscene.mp4"
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

print(f"[CINEMATIC RENDER] Generating High-End Studio Cutscene...")

# Generate multi-layered star field for parallax depth effect
stars_layer1 = [{'x': random.randint(0, width), 'y': random.randint(0, height), 'speed': 1, 'size': 1} for _ in range(60)]
stars_layer2 = [{'x': random.randint(0, width), 'y': random.randint(0, height), 'speed': 3, 'size': 2} for _ in range(40)]
stars_layer3 = [{'x': random.randint(0, width), 'y': random.randint(0, height), 'speed': 6, 'size': 3} for _ in range(20)]

for frame in range(total_frames + 1):
    # Professional deep space gradient background
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (10, 5, 15) # Rich dark nebula tone
    
    # Render Parallax Star Layers
    for s in stars_layer1:
        sy = (s['y'] + frame * s['speed']) % height
        cv2.circle(img, (s['x'], sy), s['size'], (100, 100, 150), -1)
    for s in stars_layer2:
        sy = (s['y'] + frame * s['speed']) % height
        cv2.circle(img, (s['x'], sy), s['size'], (180, 180, 220), -1)
    for s in stars_layer3:
        sy = (s['y'] + frame * s['speed']) % height
        cv2.circle(img, (s['x'], sy), s['size'], (255, 255, 255), -1)

    # Smooth cinematic easing for rocket ascent
    progress_y = calculate_easing(frame, 0, -500, total_frames, "quadratic_in")
    base_y = int(550 + progress_y)
    
    # Dynamic Thrust Flame with flickering effect
    flicker = random.randint(-5, 5)
    flame_len = int(60 + math.sin(frame * 0.8) * 20 + flicker)
    
    # Outer Flame Glow (Orange/Red)
    pts_outer_flame = np.array([[640, base_y + 85], [620, base_y + 85 + flame_len], [660, base_y + 85 + flame_len]], np.int32)
    cv2.fillPoly(img, [pts_outer_flame], (0, 100, 255))
    
    # Inner Core Flame (Bright Yellow/White)
    pts_inner_flame = np.array([[640, base_y + 85], [632, base_y + 85 + (flame_len * 0.7)], [648, base_y + 85 + (flame_len * 0.7)]], np.int32)
    cv2.fillPoly(img, [pts_inner_flame], (0, 255, 255))

    # Sleek Professional Rocket Hull
    pts_body = np.array([[640, base_y], [605, base_y + 90], [675, base_y + 90]], np.int32)
    cv2.fillPoly(img, [pts_body], (240, 60, 60)) # Metallic Red
    
    # Wing Fins
    pts_lfin = np.array([[605, base_y + 50], [580, base_y + 105], [605, base_y + 90]], np.int32)
    pts_rfin = np.array([[675, base_y + 50], [700, base_y + 105], [675, base_y + 90]], np.int32)
    cv2.fillPoly(img, [pts_lfin], (120, 120, 130))
    cv2.fillPoly(img, [pts_rfin], (120, 120, 130))
    
    # Holographic / Glass Cockpit Window
    cv2.circle(img, (640, base_y + 35), 11, (255, 200, 100), -1)
    cv2.circle(img, (640, base_y + 35), 8, (255, 255, 255), -1)

    # Write frame to cinematic output
    video_writer.write(img)

video_writer.release()
print(f"[SUCCESS] Professional Cinematic Cutscene generated at: {output_path}")