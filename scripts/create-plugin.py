#!/usr/bin/env python3
import os
import sys
import json

TEMPLATE_MANIFEST = {
    "id": "{plugin_id}",
    "name": "{plugin_name}",
    "version": "1.0.0",
    "description": "Custom {plugin_type} plugin for Reflow.",
    "author": "Developer",
    "type": "{plugin_type_upper}",
    "entrypoint": "plugin:CustomPlugin",
    "api_version": "1.0.0",
    "capabilities": ["custom_action"],
    "permissions": ["NETWORK_ACCESS"],
    "configuration": {{}}
}

TEMPLATE_CODE = """# Reflow Plugin Entrypoint
from plugins.base_plugin import BasePlugin
from plugins.manifest import PluginManifest
from typing import Dict, Any

class CustomPlugin(BasePlugin):
    def __init__(self, manifest: PluginManifest, config=None):
        super().__init__(manifest, config)

    async def initialize(self) -> bool:
        print(f"Initialized {{self.manifest.name}}")
        return True

    async def shutdown(self) -> None:
        print(f"Shutdown {{self.manifest.name}}")

    async def health_check(self) -> Dict[str, Any]:
        return {{"status": "ok", "plugin": self.manifest.id}}
"""

TEMPLATE_README = """# {plugin_name} (Reflow Plugin)

Custom Reflow plugin of type `{plugin_type_upper}`.

## Installation
Place this directory inside `./plugins/` or register via `PluginRegistry`.
"""

def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/create-plugin.py <plugin-id> <plugin-type>")
        print("Types: platform, ai_provider, storage, media_processor, analytics, workflow_action")
        sys.exit(1)

    plugin_id = sys.argv[1].lower().replace(" ", "-")
    plugin_type = sys.argv[2].lower()
    plugin_name = plugin_id.replace("-", " ").title()
    plugin_type_upper = plugin_type.upper()

    target_dir = os.path.join("plugins", plugin_id)
    os.makedirs(target_dir, exist_ok=True)

    manifest_data = json.loads(json.dumps(TEMPLATE_MANIFEST).format(
        plugin_id=plugin_id,
        plugin_name=plugin_name,
        plugin_type=plugin_type,
        plugin_type_upper=plugin_type_upper
    ))

    with open(os.path.join(target_dir, "plugin.json"), "w") as f:
        json.dump(manifest_data, f, indent=2)

    with open(os.path.join(target_dir, "plugin.py"), "w") as f:
        f.write(TEMPLATE_CODE.format(plugin_name=plugin_name))

    with open(os.path.join(target_dir, "README.md"), "w") as f:
        f.write(TEMPLATE_README.format(plugin_name=plugin_name, plugin_type_upper=plugin_type_upper))

    print(f"✅ Successfully created starter plugin template at: {target_dir}")

if __name__ == "__main__":
    main()
