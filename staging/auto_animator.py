from asset_registry_v1 import AssetRegistry
from scene_manager_v1 import SceneManager
from director_v1 import AnimationDirector

def run_animation():
    registry = AssetRegistry()
    scene = SceneManager(name='Level 1')
    director = AnimationDirector()

    registry.register_asset('Hero', 'hero.png')
    scene.add_character('Hero', 0, 0)

    director.add_keyframe(1, 'Hero', 0, 0)
    director.add_keyframe(10, 'Hero', 50, 0)

    print('Auto-Animator Complete:')
    print(director.get_animation_data())

if __name__ == '__main__':
    run_animation()