"""Calculation helpers for active manufacturing services."""

__all__ = []

try:
    from .core import (
        calculate_mat_volume, calculate_mat_weight, calculate_mat_price,
        calculate_k_quantity, calculate_printing_work_time,
        calculate_cost, calculate_cycle, resolve_material,
    )
except ImportError:
    # Some electroplating unit tests do not need core.py. In slim archives
    # constants.py may intentionally omit private enterprise structures.
    pass
else:
    __all__ += [
        'calculate_mat_volume', 'calculate_mat_weight', 'calculate_mat_price',
        'calculate_k_quantity', 'calculate_printing_work_time',
        'calculate_cost', 'calculate_cycle', 'resolve_material',
    ]

try:
    from .printing import calculate_printing_price
except ImportError:
    pass
else:
    __all__.append('calculate_printing_price')

from .electroplating import calculate_electroplating_parameters

__all__.append('calculate_electroplating_parameters')
