import bs4
import functools
import requests
import time
import platformdirs
import json
from datetime import datetime, timedelta

__all__ = ["get_majors", "get_major_from_netid"]

DIRECTORY_TRIES = 5
MAJORS_CACHE_PATH = (
    platformdirs.site_cache_path(appauthor="Comet Robotics", appname="Club Manager", ensure_exists=True)
    / "majors.json"
)
MAJOR_CACHE_MAX_AGE = timedelta(weeks=4)

@functools.lru_cache()
def get_majors() -> dict[str, str]:
    """Fetches the list of majors from the directory dropdown filter. Caches the list for fast retrieval.

    Returns:
        dict[str, str]: The dictionary of major short codes to major full text.
    """

    print("Trying to fetch majors from cache...")
    if MAJORS_CACHE_PATH.exists():
        with open(MAJORS_CACHE_PATH, "r") as f:
            cache_data = json.loads(f.read())
        if datetime.fromisoformat(cache_data["last_updated"]) + MAJOR_CACHE_MAX_AGE > datetime.now():
            return cache_data["majors"]
        else:
            print("Cached majors are outdated. Fetching from directory...")

    for i in range(DIRECTORY_TRIES):
        print(f"Trying to fetch major... ({i + 1}/{DIRECTORY_TRIES})")
        r = requests.get("https://www.utdallas.edu/directory/")
        soup = bs4.BeautifulSoup(r.text, "html.parser")
        dirMajor = soup.find(id="dirMajor")
        if dirMajor:
            break
        time.sleep(3)
    else:
        print("WARNING: Failed to fetch majors.")
        return dict()
    options = {option["value"]: option.string for option in dirMajor.find_all("option")}
    del options["All"]
    now = datetime.now()
    with open(MAJORS_CACHE_PATH, "w") as f:
        f.write(json.dumps({"majors": options, "last_updated": now.isoformat()}))
    return options


def get_major_from_netid(netid: str) -> str | None:
    """Gets the major short code from the directory for a particular NetID.

    Args:
        netid (str): The NetID to look up.

    Returns:
        str | None: The major short code if successful, otherwise None.
    """
    try:
        r = requests.get(
            f"https://websvcs.utdallas.edu/directory/includes/directories.class.php?dirType=displayname&dirSearch={netid}&dirAffil=All&dirDept=All&dirMajor=All&dirSchool=All"
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
