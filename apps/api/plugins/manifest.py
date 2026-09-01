from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

PLUGIN_API_VERSION = "1.0.0"

class PluginType(str, Enum):
    PLATFORM = "PLATFORM"
    AI_PROVIDER = "AI_PROVIDER"
    STORAGE = "STORAGE"
    MEDIA_PROCESSOR = "MEDIA_PROCESSOR"
    ANALYTICS = "ANALYTICS"
    WORKFLOW_ACTION = "WORKFLOW_ACTION"

class PluginPermission(str, Enum):
    CONTENT_READ = "CONTENT_READ"
    CONTENT_WRITE = "CONTENT_WRITE"
    PUBLISH = "PUBLISH"
    ANALYTICS_READ = "ANALYTICS_READ"
    STORAGE_READ = "STORAGE_READ"
    STORAGE_WRITE = "STORAGE_WRITE"
    NETWORK_ACCESS = "NETWORK_ACCESS"

class PluginManifest(BaseModel):
    id: str = Field(..., description="Unique plugin identifier, e.g. youtube-connector")
    name: str = Field(..., description="Human-readable plugin name")
    version: str = Field(..., description="Semantic version string, e.g. 1.0.0")
    description: str = Field(..., description="Plugin description")
    author: str = Field(default="Reflow Team", description="Author or organization")
    type: PluginType = Field(..., description="Plugin category type")
    entrypoint: str = Field(..., description="Python module entrypoint, e.g. plugin:PluginClass")
    api_version: str = Field(default=PLUGIN_API_VERSION, description="Reflow Plugin API version target")
    capabilities: List[str] = Field(default_factory=list, description="Declared capabilities")
    permissions: List[PluginPermission] = Field(default_factory=list, description="Granted permission scopes")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Configuration schema or parameters")
    minimum_reflow_version: str = Field(default="1.0.0", description="Minimum supported Reflow version")
    maximum_reflow_version: Optional[str] = Field(default=None, description="Maximum supported Reflow version")
