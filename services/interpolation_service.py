def linear_interpolation(value1: float, value2: float, progress: float) -> float:
    if progress <= 0.0:
        return value1
    if progress >= 1.0:
        return value2
    return value1 + (value2 - value1) * progress

