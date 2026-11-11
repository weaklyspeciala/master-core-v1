import tkinter as tk
import math
from anim_math import calculate_easing

root = tk.Tk()
root.title("Studio Autonomous - Space Mission Animation")
root.geometry("800x600")

canvas = tk.Canvas(root, width=800, height=600, bg="#0b0f19")
canvas.pack(fill="both", expand=True)

# Generate background stars
stars = []
for i in range(50):
    sx = (i * 37) % 800
    sy = (i * 59) % 600
    size = (i % 3) + 1
    star = canvas.create_oval(sx, sy, sx + size, sy + size, fill="white")
    stars.append(star)

# Draw Rocket / Hero Avatar
# Rocket body
rocket_body = canvas.create_polygon(400, 220, 385, 270, 415, 270, fill="#e74c3c", outline="#c0392b")
rocket_window = canvas.create_oval(392, 235, 408, 251, fill="#3498db")
rocket_flame = canvas.create_polygon(390, 270, 400, 300, 410, 270, fill="#f1c40f")

frame = 0
total_frames = 120

def animate_space_mission():
    global frame
    if frame <= total_frames:
        # Calculate smooth vertical lift-off using quadratic easing
        dy = calculate_easing(frame, 0, -350, total_frames, "quadratic_in")
        
        # Move rocket parts upward
        canvas.coords(rocket_body, 400, 220+dy, 385, 270+dy, 415, 270+dy)
        canvas.coords(rocket_window, 392, 235+dy, 408, 251+dy)
        canvas.coords(rocket_flame, 390, 270+dy, 400, 300+dy+ (frame%5)*3, 410, 270+dy)
        
        frame += 1
        root.after(30, animate_space_mission)
    else:
        # Reset loop for continuous flight
        frame = 0
        root.after(30, animate_space_mission)

if __name__ == "__main__":
    root.after(100, animate_space_mission)
    root.mainloop()