def common_prefix(a: str, b: str) -> str:
    """Determine the common prefix of *a* and *b*."""
    if len(a) > len(b):
        a, b = b, a
    for i in range(len(a)):
        if a[i] != b[i]:
            return a[:i]
    return a
