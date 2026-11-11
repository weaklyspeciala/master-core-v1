import tkinter as tk
from anim_math import calculate_easing

root = tk.Tk()
root.title('Studio Visualizer - Hero Animation')
root.geometry('800x600')

canvas = tk.Canvas(root, width=800, height=600, bg='black')
canvas.pack()

# Draw Hero circle
hero = canvas.create_oval(40, 280, 60, 300, fill='red')

frame = 0
total_frames = 60

def animate():
    global frame
    if frame <= total_frames:
        # Correct argument order: (t, start, end, duration, easing_type)
        x = calculate_easing(frame, 50, 700, total_frames, 'quadratic_in')
        canvas.coords(hero, x, 280, x + 20, 300)
        frame += 1
        root.after(30, animate)

if __name__ == '__main__':
    root.after(100, animate)
    root.mainloop()