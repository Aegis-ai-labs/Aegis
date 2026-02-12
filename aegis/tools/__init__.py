"""AEGIS1 Tool modules — Health & Wealth tracking tools for Claude function calling."""

from .registry import TOOL_DEFINITIONS, dispatch_tool

__all__ = ["TOOL_DEFINITIONS", "dispatch_tool"]
