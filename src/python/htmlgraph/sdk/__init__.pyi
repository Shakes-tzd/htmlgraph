"""
Type stub for htmlgraph.sdk package.

Exports SDK from the core module.
"""

from htmlgraph.sdk.base import BaseSDK as BaseSDK
from htmlgraph.sdk.constants import SDKSettings as SDKSettings
from htmlgraph.sdk.core import SDK as SDK
from htmlgraph.sdk.discovery import auto_discover_agent as auto_discover_agent
from htmlgraph.sdk.discovery import discover_htmlgraph_dir as discover_htmlgraph_dir
from htmlgraph.sdk.discovery import find_project_root as find_project_root

__all__: list[str]
