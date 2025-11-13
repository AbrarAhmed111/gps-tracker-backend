from typing import Dict, List


def generate_fibonacci(count: int) -> List[int]:
    if count < 0:
        raise ValueError("count must be non-negative")
    if count > 10000:
        raise ValueError("count too large; must be <= 10000")
    sequence: List[int] = []
    a, b = 0, 1
    for _ in range(count):
        sequence.append(a)
        a, b = b, a + b
    return sequence


def count_words(text: str) -> Dict[str, int]:
    words = [w for w in text.split() if w]
    counts: Dict[str, int] = {}
    for w in words:
        key = w.lower()
        counts[key] = counts.get(key, 0) + 1
    return counts


def normalize_numbers(values: List[float]) -> List[float]:
    if len(values) == 0:
        return []
    vmin = min(values)
    vmax = max(values)
    if vmax == vmin:
        return [0.0 for _ in values]
    return [(v - vmin) / (vmax - vmin) for v in values]

