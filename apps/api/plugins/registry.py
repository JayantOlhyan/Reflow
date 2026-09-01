import os
import sys
import json
import asyncio
import importlib
from typing import Dict, Any, List, Optional
from plugins.manifest import PluginManifest, PluginType, PLUGIN_API_VERSION
from plugins.base_plugin import BasePlugin
from utils.logging import get_logger

logger = get_logger("PluginRegistry")

class PluginRegistry:
    """
    Central Plugin Registry for Reflow.
    Manages plugin discovery, explicit loading, enabling, disabling, and health checks.
    """
    _instance: Optional['PluginRegistry'] = None

    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}
        self._disabled: set = set()
        self._plugin_errors: Dict[str, str] = {}

    @classmethod
    def get_instance(cls) -> 'PluginRegistry':
        if cls._instance is None:
            cls._instance = PluginRegistry()
        return cls._instance

    def register(self, plugin: BasePlugin) -> bool:
        """Registers a plugin instance."""
        manifest = plugin.manifest
        
        # Verify API version compatibility
        if manifest.api_version != PLUGIN_API_VERSION:
            err = f"Plugin {manifest.id} API version '{manifest.api_version}' incompatible with Reflow target '{PLUGIN_API_VERSION}'"
            logger.error(err)
            self._plugin_errors[manifest.id] = err
            return False

        self._plugins[manifest.id] = plugin
        self._plugin_errors.pop(manifest.id, None)
        logger.info(f"Registered plugin: {manifest.id} (v{manifest.version}, type={manifest.type})")
        return True

    def unregister(self, plugin_id: str) -> bool:
        """Unregisters a plugin."""
        if plugin_id in self._plugins:
            del self._plugins[plugin_id]
            self._disabled.discard(plugin_id)
            logger.info(f"Unregistered plugin: {plugin_id}")
            return True
        return False

    def enable_plugin(self, plugin_id: str) -> bool:
        """Enables a registered plugin."""
        if plugin_id in self._plugins:
            self._disabled.discard(plugin_id)
            self._plugins[plugin_id].enabled = True
            logger.info(f"Enabled plugin: {plugin_id}")
            return True
        return False

    def disable_plugin(self, plugin_id: str) -> bool:
        """Disables a registered plugin."""
        if plugin_id in self._plugins:
            self._disabled.add(plugin_id)
            self._plugins[plugin_id].enabled = False
            logger.info(f"Disabled plugin: {plugin_id}")
            return True
        return False

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """Gets a plugin if registered and enabled."""
        if plugin_id in self._disabled:
            return None
        return self._plugins.get(plugin_id)

    def list_plugins(self, plugin_type: Optional[PluginType] = None, include_disabled: bool = True) -> List[Dict[str, Any]]:
        """Lists plugins with metadata, health, and status."""
        results = []
        for pid, plugin in self._plugins.items():
            manifest = plugin.manifest
            if plugin_type and manifest.type != plugin_type:
                continue

            is_enabled = pid not in self._disabled and plugin.enabled
            if not include_disabled and not is_enabled:
                continue

            results.append({
                "id": manifest.id,
                "name": manifest.name,
                "version": manifest.version,
                "description": manifest.description,
                "author": manifest.author,
                "type": manifest.type.value if hasattr(manifest.type, 'value') else str(manifest.type),
                "api_version": manifest.api_version,
                "capabilities": manifest.capabilities,
                "permissions": [p.value if hasattr(p, 'value') else str(p) for p in manifest.permissions],
                "enabled": is_enabled,
                "status": "FAILED" if pid in self._plugin_errors else "HEALTHY" if is_enabled else "DISABLED",
                "error": self._plugin_errors.get(pid)
            })
        return results

    async def health_check(self, plugin_id: str) -> Dict[str, Any]:
        """Performs isolated health check on a specific plugin."""
        plugin = self._plugins.get(plugin_id)
        if not plugin:
            return {"status": "NOT_FOUND", "details": f"Plugin {plugin_id} not registered."}
        
        if plugin_id in self._disabled or not plugin.enabled:
            return {"status": "DISABLED", "details": "Plugin is currently disabled."}

        try:
            res = await asyncio.wait_for(plugin.health_check(), timeout=5.0)
            return {"status": "HEALTHY", "details": res}
        except Exception as e:
            logger.error(f"Health check failed for plugin {plugin_id}: {e}")
            self._plugin_errors[plugin_id] = str(e)
            return {"status": "FAILED", "details": str(e)}

    async def health_check_all(self) -> Dict[str, Any]:
        """Runs health checks across all registered active plugins."""
        results = {}
        for pid in self._plugins:
            results[pid] = await self.health_check(pid)
        return results

    def discover_local_plugins(self, plugins_dir: str = "./plugins") -> List[str]:
        """
        Discovers local plugin manifests in plugins_dir.
        Enforces safe loading: manifest must exist and entrypoint must be a valid module path.
        No arbitrary uploaded python file execution.
        """
        discovered = []
        if not os.path.isdir(plugins_dir):
            return discovered

        for item in os.listdir(plugins_dir):
            item_path = os.path.join(plugins_dir, item)
            manifest_file = os.path.join(item_path, "plugin.json")
            if os.path.isdir(item_path) and os.path.isfile(manifest_file):
                try:
                    with open(manifest_file, "r") as f:
                        data = json.load(f)
                    manifest = PluginManifest.model_validate(data)
                    discovered.append(manifest.id)
                    logger.info(f"Discovered local plugin manifest: {manifest.id} in {item_path}")
                except Exception as e:
                    logger.warning(f"Failed to parse plugin manifest in {item_path}: {e}")

        return discovered

plugin_registry = PluginRegistry.get_instance()
