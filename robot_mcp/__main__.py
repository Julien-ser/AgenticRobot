"""Entry point: python -m robot_mcp"""
from .server import mcp

mcp.run(transport="stdio")
