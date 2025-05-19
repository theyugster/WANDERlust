import sys
import pandas as pd
from geopy.geocoders import Nominatim
import requests
import os
from pandas import json_normalize
from dotenv import load_dotenv
from google import genai
import json
def configure():
    load_dotenv()

if len(sys.argv) >1:
    client = genai.Client(api_key=f"{os.getenv('api_ai_key')}")
    response = client.models.generate_content(
    model="gemini-2.0-flash", contents=f"Suggest some tourist locations for this city{sys.argv[1]}. Do not use Markdown for the response.Seperate each tourist location with a comma")
    attractions = response.text.split(", ")
    list_items = "".join([f"<li>{attraction.strip()}.</li>" for attraction in attractions if attraction])
    html_output = f"<p>Here are some popular options:</p><ul>{list_items}</ul>"
    print(json.dumps(attractions))


