_BONUS = (4, 3, 2, 1)


def oom_table(entries):
    """Rank players from names and Stableford scores.

    Each entry has a name and a list of scores. None and 0 are left out of
    the total. A player with no positive score is absent and has bonus 0.
    Snitt is the total divided by the number of counted scores, to one decimal.
    Sort is total descending, then name ascending. Rank starts at 1. Tied
    totals do not share a rank. Bonus for ranks 1 to 4 is 4, 3, 2, and 1.
    """
    ranked = []
    for entry in entries:
        counted = [score for score in entry["scores"] if score]
        if not counted:
            continue
        total = sum(counted)
        ranked.append({
            "name": entry["name"],
            "scores": list(entry["scores"]),
            "total": total,
            "snitt": round(total / len(counted), 1),
        })
    ranked.sort(key=lambda row: (-row["total"], row["name"]))
    for index, row in enumerate(ranked, start=1):
        row["rank"] = index
        row["bonus"] = _BONUS[index - 1] if index <= 4 else 0
    return ranked
