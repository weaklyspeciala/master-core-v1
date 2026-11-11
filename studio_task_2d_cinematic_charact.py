import cv2
import numpy as np

width, height = 1280, 720
fps = 30
total_frames = 120
output_file = "H:\\MASTER_AI_WORKSTATION\\MASTER_AI_WORKSTATION\\MASTER_CORE_V1\\studio_output_2d_cinematic_charact.mp4"
writer = cv2.VideoWriter(output_file, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

print("[RENDER] Rendering cinematic studio frames for: 2D Cinematic Character Animation with Dialogue & Effects")
for frame in range(total_frames + 1):
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (20, 24, 33) # Deep dark studio theme background
    
    # Animated elements
    pos_x = int(640 + 300 * np.sin(frame * 0.05))
    cv2.circle(img, (pos_x, 360), 60, (56, 189, 248), -1)
    cv2.putText(img, "STUDIO PRO: 2D Cinematic Character Animati", (150, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(img, f"Frame: {frame}/{total_frames}", (150, 620), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (74, 222, 128), 2)

    writer.write(img)
writer.release()
print("[SAVED] Studio video rendered successfully.")
