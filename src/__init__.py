"""
Azure Terraform MCP Server Package.

A comprehensive Model Context Protocol (MCP) server for Azure Terraform operations.
"""

__version__ = "0.1.0"
__author__ = "Azure Terraform MCP Team"
__email__ = "tfai@microsoft.com"

# Import main functionality when available
try:
    from .core.server import create_server, run_server
    from .core.config import Config
    __all__ = ["create_server", "run_server", "Config"]
except ImportError:
    # During development, imports may not be available yet
    __all__ = []
