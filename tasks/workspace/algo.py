def dedup(items):
    seen = []
    out = []
    for x in items:
        if x not in seen:      # O(n) membership on a list
            seen.append(x)
            out.append(x)
    return out
