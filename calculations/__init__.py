"""calculations package.

Keep service-specific modules importable even when optional business constants used by
legacy/core pricing modules are absent in a slim test archive.
"""

__all__ = []

try:
    from .core import (
        calculate_mat_volume, calculate_mat_volume_cylindrical, calculate_mat_volume_printing,
        calculate_mat_weight, calculate_mat_price, calculate_work_price, calculate_work_time,
        calculate_k_complexity, calculate_k_quantity, calculate_printing_work_time,
        calculate_cost, calculate_cycle, resolve_material,
    )
except ImportError:
    # Some electroplating unit tests do not need core.py. In the current slim
    # archives constants.py may intentionally omit COST_STRUCTURE/MACHINES, so
    # importing core.py at package import time would prevent independent testing
    # of calculations.electroplating.
    pass
else:
    __all__ += [
        'calculate_mat_volume', 'calculate_mat_volume_cylindrical', 'calculate_mat_volume_printing',
        'calculate_mat_weight', 'calculate_mat_price', 'calculate_work_price', 'calculate_work_time',
        'calculate_k_complexity', 'calculate_k_quantity', 'calculate_printing_work_time',
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
