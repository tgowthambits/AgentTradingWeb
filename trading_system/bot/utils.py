"""
Utility classes and functions for the trading bot.
"""

import json
import numpy as np


class NumpyJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy types (NumPy 2.0 compatible)."""
    
    def default(self, obj):
        # Handle integers - np.integer is the abstract base class that covers all integer types
        if isinstance(obj, np.integer):
            return int(obj)
        # Handle floating point - np.floating is the abstract base class that covers all float types
        elif isinstance(obj, np.floating):
            return float(obj)
        # Handle booleans - check for np.bool_ (NumPy 2.0 compatible)
        elif isinstance(obj, (bool, np.bool_)) or (hasattr(np, 'bool_') and isinstance(obj, np.bool_)):
            return bool(obj)
        # Handle arrays
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)
