class AssetRegistry:
    def __init__(self):
        self.assets = {}

    def register_asset(self, name, path):
        self.assets[name] = path

    def list_assets(self):
        return list(self.assets.keys())