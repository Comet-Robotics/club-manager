import bs4
import functools
import requests

__all__ = ['get_majors', 'get_major_from_netid']

@functools.lru_cache()
def get_majors() -> dict[str, str]:
    r = requests.get("https://www.utdallas.edu/directory/")
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    dirMajor = soup.find(id="dirMajor")
    options = { option['value']: option.string for option in dirMajor.find_all('option') }
    del options['All']
    return options

def get_major_from_netid(netid: str):
    r = requests.get(
        f"https://websvcs.utdallas.edu/directory/includes/directories.class.php?dirType=displayname&dirSearch={netid}&dirAffil=All&dirDept=All&dirMajor=All&dirSchool=All"
    )
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    for p in soup.find_all('p'):
        if p.contents[0].string == 'Major':
            major = p.contents[1].string.replace(': ','')
            matching_short_codes = [ o[0] for o in get_majors().items() if o[1] == major ]
            return matching_short_codes[0] if len(matching_short_codes) > 0 else None
    return None
