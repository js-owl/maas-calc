"""Utility modules for the manufacturing calculation API.

Lazy exports avoid circular imports during test collection and partial module loading.
"""

from __future__ import annotations

__all__ = [
    "ParameterExtractor",
    "SafeguardManager",
    "CalculationRouter",
    "CompositeMLPredictor",
]


def __getattr__(name: str):
    if name == "ParameterExtractor":
        from .parameter_extractor import ParameterExtractor
        return ParameterExtractor
    if name == "SafeguardManager":
        from .safeguards import SafeguardManager
        return SafeguardManager
    if name == "CalculationRouter":
        from .calculation_router import CalculationRouter
        return CalculationRouter
    if name == "CompositeMLPredictor":
        from .composite_ml_predictor import CompositeMLPredictor
        return CompositeMLPredictor
    raise AttributeError(name)
