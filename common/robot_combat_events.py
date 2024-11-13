import requests
import bs4


def get_robot_combat_event(rce_event_id):
  r = requests.get(f"https://www.robotcombatevents.com/events/{rce_event_id}")
  soup = bs4.BeautifulSoup(r.text, 'html.parser')
  
  event_title_parent_div = soup.find("div", class_='event-title')
  assert event_title_parent_div is not None
  event_title = event_title_parent_div.text.strip()
  
  event_description_parent_div = soup.find("div", class_='event-description')
  event_description = event_description_parent_div.text.strip()
  
  event_details_parent_div = soup.find("div", class_='event-details')
  event_details = {}
  for row in event_details_parent_div.findAll('h4'):
    row_text = row.text.strip()
    colon_index = row_text.find(':')
    if colon_index != -1:
      key = row_text[:colon_index].strip()
      value = row_text[colon_index+1:].strip()
      event_details[key] = value
    
  
  weight_class_list_parent_div = soup.find('div', class_='event-comp-table')
  weight_class_urls = {}
  for row in weight_class_list_parent_div.findAll('a')[0:]:
    weight_class_urls[row.text.strip()] = 'https://www.robotcombatevents.com' + row['href']
  
  robots_by_weight_class = {}
  for key, value in weight_class_urls.items():
    robots_by_weight_class[key] = []
    r = requests.get(value)
    thing = bs4.BeautifulSoup(r.text, 'html.parser')
    
    registration_panel_div = thing.find("div", class_="registrations-panel")
    assert registration_panel_div is not None
    
    registration_panel_table_rows = registration_panel_div.find_all("tr")
    header_row = registration_panel_table_rows[0]
    keys = [th.text.strip() for th in header_row.find_all("th")]
    assert keys == ["", "Bot", "Team", "Status"]
    
    for row in registration_panel_table_rows[1:]:
      robot = {
        "img_url": row.find("img")["src"],
      }

      for i, item in enumerate([list(col)[0] for col in row.find_all("td")]):
        if i == 0:
          pass
        elif i == 1:
          robot["name"] = item.text.strip()
          robot["rce_resource_id"] = item.attrs["href"].split("/")[-1]
        elif i == 2:
          robot["team"] = item.text.strip()
          robot["rce_team_id"] = item.attrs["href"].split("/")[-1]
        elif i == 3:
          robot["status"] = item.text.strip()
        
      robots_by_weight_class[key].append(robot)
      
  
  return {"event_title": event_title, "event_description": event_description, "event_details": event_details, "robots_by_weight_class": robots_by_weight_class}
  
out = get_robot_combat_event(2501)
print(out)