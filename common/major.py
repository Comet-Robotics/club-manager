import functools
import json
from pathlib import Path

__all__ = ["get_majors", "get_major_choices"]

# The major filter UTD's directory page used to offer, plus the programs it was missing.
# UTD retired the filter in January 2026, so additions are by hand; the codes are still
# published at https://ospa.utdallas.edu/definitions-for-codes-used-on-this-site/
MAJORS_JSON_PATH = Path(__file__).parent / "majors.json"

# Majors members pick most often, in the order they are offered. Hand-picked rather than
# derived, so the list stays short and nothing surprising lands at the top of the dropdown.
COMMON_MAJOR_CODES = ("MECH", "BMEN", "EE", "SE", "CE", "CS", "INTS")


@functools.lru_cache()
def get_majors() -> dict[str, str]:
    """Fetches the list of majors from disk. Caches the list for fast retrieval.

    Returns:
        dict[str, str]: The dictionary of major short codes to major full text.
    """

    with open(MAJORS_JSON_PATH, "r") as f:
        return json.load(f)


def get_major_choices() -> list[tuple[str, list[tuple[str, str]]]]:
    """
    The majors as Django choice groups, with the ones members pick most often first.

    `UserProfile.major` stores the short code, so these come from the same list as the
    model's choices and cannot drift from it.
    """
    majors = get_majors()
    common = [(code, majors[code]) for code in COMMON_MAJOR_CODES if code in majors]
    remaining = sorted(
        ((code, name) for code, name in majors.items() if code not in COMMON_MAJOR_CODES),
        key=lambda major: major[1],
    )
    return [("Common majors", common), ("All majors", remaining)]
