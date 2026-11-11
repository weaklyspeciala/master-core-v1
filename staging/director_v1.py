class AnimationDirector:
    def __init__(self):
        self.timeline = []

    def add_keyframe(self, frame_number, character, x, y):
        self.timeline.append({'frame': frame_number, 'char': character, 'pos': (x, y)})

    def get_animation_data(self):
        return self.timeline