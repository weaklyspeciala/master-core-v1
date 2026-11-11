class SceneManager:
    def __init__(self, name):
        self.name = name
        self.characters = {}

    def add_character(self, name, x, y):
        self.characters[name] = (x, y)

    def describe_scene(self):
        return str(self.characters)