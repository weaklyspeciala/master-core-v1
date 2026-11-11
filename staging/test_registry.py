import os
from MASTER_CORE_V1.staging.asset_registry_v1 import AssetRegistry

if __name__ == '__main__':
    asset_registry = AssetRegistry()
    asset_registry.register_sprite('player_idle', 'assets/player.png')
    print(asset_registry)