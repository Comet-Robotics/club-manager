import bs4
import functools
import requests
import time

__all__ = ["get_majors", "get_major_from_netid"]

DIRECTORY_TRIES = 5


@functools.lru_cache()
def get_majors() -> dict[str, str]:
    """Fetches the list of majors from the directory dropdown filter. Caches the list for fast retrieval.

    Returns:
        dict[str, str]: The dictionary of major short codes to major full text.
    """
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
    options = {
        option["value"]: option.string
        for option in dirMajor.find_all("option")
    }
    del options["All"]
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
            matching_short_codes = [
                o[0] for o in get_majors().items() if o[1] == major
            ]
            return (
                matching_short_codes[0]
                if len(matching_short_codes) > 0
                else None
            )
    return None
