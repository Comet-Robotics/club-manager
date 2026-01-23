import bs4
import functools
import requests
import json
from pathlib import Path

__all__ = ["get_majors", "get_major_from_netid"]

MAJORS_JSON_PATH = Path(__file__).parent / "majors.json"


@functools.lru_cache()
def get_majors() -> dict[str, str]:
    """Fetches the list of majors from disk. Caches the list for fast retrieval.

    Returns:
        dict[str, str]: The dictionary of major short codes to major full text.
    """

    with open(MAJORS_JSON_PATH, "r") as f:
        return json.load(f)


def get_major_from_netid(netid: str) -> str | None:
    """Gets the major short code from the directory for a particular NetID.

    Args:
        netid (str): The NetID to look up.

    Returns:
        str | None: The major short code if successful, otherwise None.
    """
    try:
        r = requests.get(
            f"https://websvcs.utdallas.edu/directory/includes/directories.class.php?dirType=displayname&dirSearch={netid}&dirAffil=All&dirDept=All&dirMajor=All&dirSchool=All",
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
            },
        )
    except Exception as e:
        print(f"WARNING: major_from_netid request failed: ", e)
        return None
    soup = bs4.BeautifulSoup(r.text, "html.parser")
    for p in soup.find_all("p"):
        if p.contents[0].string == "Major":
            major = p.contents[1].string.replace(": ", "")
            matching_short_codes = [o[0] for o in get_majors().items() if o[1] == major]
            return matching_short_codes[0] if len(matching_short_codes) > 0 else None
    return None
