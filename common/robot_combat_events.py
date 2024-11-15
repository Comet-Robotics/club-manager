from dataclasses import dataclass
from typing import Dict, List
import requests
import bs4
from typing import NamedTuple
from urllib.parse import urlparse, urljoin

@dataclass
class RCERobot:
    name: str
    status: str
    img_url: str
    rce_resource_id: str
    rce_team_id: str
    weight_class: str
    

class RCETeam(NamedTuple):
    name: str
    rce_team_id: str

@dataclass
class RCEEvent:
    event_title: str
    event_description: str
    event_details: Dict[str, str]
    
    robots_by_weight_class: Dict[str, List[RCERobot]]
    robots: List[RCERobot]
    teams: List[RCETeam]

def get_robot_combat_event(rce_event_id: str) -> RCEEvent:
    r = requests.get(f"https://www.robotcombatevents.com/events/{rce_event_id}")
    soup = bs4.BeautifulSoup(r.text, 'html.parser')
    
    # Get event title
    event_title_parent_div = soup.find("div", class_='event-title')
    assert event_title_parent_div is not None
    event_title = event_title_parent_div.text.strip()
    
    # Get event description
    event_description_parent_div = soup.find("div", class_='event-description')
    assert event_description_parent_div is not None
    event_description = event_description_parent_div.text.strip()
    
    # Get event details
    event_details_parent_div = soup.find("div", class_='event-details')
    assert event_details_parent_div is not None
    event_details = {}
    for row in event_details_parent_div.findAll('h4'):
        row_text = row.text.strip()
        colon_index = row_text.find(':')
        if colon_index != -1:
            key = row_text[:colon_index].strip()
            value = row_text[colon_index+1:].strip()
            event_details[key] = value
    
    # Get weight class URLs
    weight_class_list_parent_div = soup.find('div', class_='event-comp-table')
    assert weight_class_list_parent_div is not None
    weight_class_urls = {
        row.text.strip(): 'https://www.robotcombatevents.com' + row['href']
        for row in weight_class_list_parent_div.findAll('a')[0:]
    }
    
    # Get robots for each weight class
    robots_by_weight_class: Dict[str, List[RCERobot]] = {}
    robots: List[RCERobot] = []
    teams: set[RCETeam] = set()
    for weight_class, url in weight_class_urls.items():
        robots_by_weight_class[weight_class] = []
        r = requests.get(url)
        thing = bs4.BeautifulSoup(r.text, 'html.parser')
        
        registration_panel_div = thing.find("div", class_="registrations-panel")
        assert registration_panel_div is not None
        
        registration_panel_table_rows = registration_panel_div.find_all("tr")
        header_row = registration_panel_table_rows[0]
        keys = [th.text.strip() for th in header_row.find_all("th")]
        assert keys == ["", "Bot", "Team", "Status"]
        
        for row in registration_panel_table_rows[1:]:
            cols = [list(col)[0] for col in row.find_all("td")]
            
            img_url: str = row.find("img")["src"]
            img_url_is_relative = urlparse(img_url).scheme == ""
            if img_url_is_relative:
                img_url = urljoin("https://www.robotcombatevents.com", img_url)
            
            robot = RCERobot(
                img_url=img_url,
                name=cols[1].text.strip(),
                rce_team_id=cols[2].attrs["href"].split("/")[-1],
                status=cols[3].text.strip(),
                rce_resource_id=cols[1].attrs["href"].split("/")[-1],
                weight_class=weight_class
            )
            
            teams.add(RCETeam(
                name=cols[2].text.strip(),
                rce_team_id=cols[2].attrs["href"].split("/")[-1]
            ))
            
            robots_by_weight_class[weight_class].append(robot)
            robots.append(robot)
    
    return RCEEvent(
        event_title=event_title,
        event_description=event_description,
        event_details=event_details,
        robots_by_weight_class=robots_by_weight_class,
        teams=list(teams),
        robots=robots
    )
  
