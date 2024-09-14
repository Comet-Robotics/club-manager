import bs4
import functools
import requests

@functools.lru_cache()
def get_majors():
    r = requests.get("https://www.utdallas.edu/directory/")
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    dirMajor = soup.find(id="dirMajor")
    options = { option['value']: option.string for option in dirMajor.find_all('option') }
    del options['All']
    return options
