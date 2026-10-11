import numpy as np

def clean_for_json(obj):

    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}

    elif isinstance(obj, list):
        return [clean_for_json(v) for v in obj]

    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return 0
        return obj

    return obj