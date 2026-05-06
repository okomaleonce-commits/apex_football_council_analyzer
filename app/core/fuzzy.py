from rapidfuzz import fuzz


def similarity(a: str, b: str) -> float:
    return fuzz.token_sort_ratio(a or '', b or '') / 100.0


def best_match(target: str, candidates: list[dict], name_key: str = 'name', min_score: float = 0.72) -> dict | None:
    best = None
    best_score = 0.0
    for item in candidates:
        name = str(item.get(name_key, ''))
        score = similarity(target, name)
        if score > best_score:
            best = item
            best_score = score
    if best and best_score >= min_score:
        best['_match_score'] = best_score
        return best
    return None
