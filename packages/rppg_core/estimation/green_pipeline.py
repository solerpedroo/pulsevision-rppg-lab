"""Backward-compatible imports; the shared engine defaults to GREEN."""

from .pipeline import WindowAnalysis, analyze_trace, analyze_window

__all__ = ["WindowAnalysis", "analyze_trace", "analyze_window"]
