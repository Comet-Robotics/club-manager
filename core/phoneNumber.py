import json
import phonenumbers
from phonenumbers import geocoder as ge

# Load JSON file
with open("countries.json", "r", encoding="utf-8") as file:
    country_data = json.load(file)

# Function to get country info from dial code
def get_country_info(dial_code):
    for country in country_data:
        if country["dialCode"] == dial_code:
            return f"{country['name']} ({country['code']})"
    return "Unknown Country"

while True:
    phone = input("Enter: ").strip()
    if not phone:
        break
    if (len(phone) > 10) and not(phone.startswith("+")):
        print("Invalid phone number, please include country code with '+'")
        continue

    try:
        if phone.startswith("+"):
            x = phonenumbers.parse(phone, None)
        else:
            x = phonenumbers.parse(phone, "US")

        country_name = ge.description_for_number(x, "en")
        dial_code = f"+{x.country_code}"  # Extract dial code
        
        country_info = get_country_info(dial_code)  # Get country from JSON

        if len(str(x.national_number)) == 10:
            print(f"State: {country_name} | Country: {country_info}")
            print(f"Parsed: {x}")
        else:
            print("Invalid phone number, must be 10 digits")

    except phonenumbers.NumberParseException as e:
        print(f"Error parsing phone number: {e}")
