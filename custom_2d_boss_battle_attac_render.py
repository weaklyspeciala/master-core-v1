import cv2
import numpy as np

width, height = 1280, 720
fps = 30
total_frames = 150
output_path = "H:\\MASTER_AI_WORKSTATION\\MASTER_AI_WORKSTATION\\MASTER_CORE_V1\\custom_2d_boss_battle_attac.mp4"
writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

print("[RENDER] Starting 2D Boss Battle Cutscene Render...")
for frame in range(total_frames + 1):
    img = np.zeros((height, width, 3), dtype=np.uint8)
    img[:] = (15, 10, 25) # Dark battle arena
    
    # Draw Boss
    cv2.circle(img, (640, 280), 80, (100, 0, 150), -1)
    cv2.circle(img, (640, 280), 40, (0, 0, 255), -1)
    cv2.putText(img, "BOSS: ABYSSAL MECHA", (480, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    
    # Health Bar decreasing
    cv2.rectangle(img, (340, 60), (940, 90), (50, 50, 50), -1)
    hp = max(0, 600 - (frame * 4))
    cv2.rectangle(img, (340, 60), (340 + hp, 90), (0, 255, 0), -1)
    
    # Attack beam firing
    if frame > 50:
        cv2.rectangle(img, (620, 360), (660, 720), (0, 255, 255), -1)

    writer.write(img)
writer.release()
print("[SAVED] Boss battle video rendered successfully.")
