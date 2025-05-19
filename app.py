import flask 
from flask import Flask, render_template, request, redirect, session
from flask import Flask, request, jsonify
from flask_cors import CORS
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import subprocess
import pandas as pd
import os
import requests
from pandas import json_normalize
import cred
import joblib
import csv
import json
geolocator = Nominatim(user_agent="weather_app")
app = Flask(__name__)
app.secret_key = "supersecretkey"  


USER_DB = "usersf.csv"
LOCATION_DB = "locations.xlsx"


if not os.path.exists(USER_DB):
    df = pd.DataFrame(columns=["Name", "UserID", "Password", "Favorites", "RecentlyViewed"])
    df.to_excel(USER_DB, index=False)
if not os.path.exists(LOCATION_DB):
    df_locations = pd.DataFrame({"Location": ["Paris", "Tokyo", "New York"], "Rating": [5, 4.8, 4.7]})
    df_locations.to_excel(LOCATION_DB, index=False)
CORS(app)
def load_destination():
    df = pd.read_excel('locations.xlsx')
    return df.to_dict('records')
#PointsOfInterest webpage
@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')
CSV_FILENAME = 'saved_points_of_interest.csv'

@app.route('/save_poi', methods=['POST'])
def save_poi_to_csv():
    if "user" not in session:
        
        return jsonify({'status': 'error', 'message': 'Please log in to save points of interest'}), 401

    # --- 2. Get User ID from session ---
    user_id = session["user"]
    """Receives POI text from the frontend and appends it to a CSV file."""
    try:
        data = request.get_json()
        poi_text = data.get('poi') 

        if not poi_text:
            
            return jsonify({'status': 'error', 'message': 'Missing point of interest text'}), 400

        
        file_exists = os.path.isfile(CSV_FILENAME)

        
        with open(CSV_FILENAME, 'a', newline='', encoding='utf-8') as csvfile:
            
            writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)

            
            if not file_exists:
                writer.writerow(['UserID','PointOfInterest']) 

            
            writer.writerow([user_id,poi_text])

       
        return jsonify({'status': 'success', 'message': 'Point of interest saved'})

    except Exception as e:
        
        print(f"Error saving POI to CSV: {e}")
        
        return jsonify({'status': 'error', 'message': 'Internal server error occurred'}), 500

def get_coordinates(city_name):
    try:
        location = geolocator.geocode(city_name)
        if location:
            return (location.latitude, location.longitude)
        else:
            return None
    except GeocoderTimedOut:
        return None

# Function to fetch weather data using coordinates
def get_weather(lat, lon):
    wapi_key = "enter weather_api_key"  
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={wapi_key}&units=metric"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None
def get_city_images(city):
    UNSPLASH_ACCESS_KEY='enter image_key'
    url = f"https://api.unsplash.com/search/photos?query={city}&per_page=5&client_id={UNSPLASH_ACCESS_KEY}"
    try:
        response = requests.get(url, timeout=10) # Added timeout
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        image_urls = [img["urls"]["regular"] for img in results if img.get("urls") and img["urls"].get("regular")]
        return image_urls
    except requests.exceptions.RequestException as e:
        print(f"Error fetching images from Unsplash: {e}")
        return []
    except Exception as e: # Catch potential errors during parsing
        print(f"Error processing Unsplash response: {e}")
        return []
@app.route('/weather/',methods=["GET"])
def weather_page():
    return render_template('weather.html')

@app.route('/weather/<city>')
def weather_by_city(city):
    coordinates = get_coordinates(city)
    if not coordinates:
        return jsonify({"error": "Could not find the city. Please check the city name and try again."})

    
    weather_data = get_weather(coordinates[0], coordinates[1])
    if not weather_data:
        return jsonify({"error": "Could not fetch weather data. Please try again later."})
    images = get_city_images(city)
    response = {
        "city": city,
        "temperature": weather_data['main']['temp'],
        "description": weather_data['weather'][0]['description'],
        "images":images
    }
    return jsonify(response)
@app.route('/flightpricepredictor',methods=["GET","POST"])
def handle_ticket():
    if request.method =="POST":
        try:
            data = request.get_json()
            df2 = pd.DataFrame(data)
            reg_loaded = joblib.load('random_forest_model.joblib')
            pred = reg_loaded.predict(df2)
        
        
            return jsonify({
                "status": "success",
                "result": f"Predicted price: ₹{float(pred[0]):.2f}",  # Formatted string
                "prediction": float(pred[0])  
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
    else:
        return render_template('flightpricepredictor.html')
@app.route("/suggest", methods=["POST","GET"])
def submit_input():
    if request.method=="POST":
        data = request.get_json()
        city = data.get("month")
        if city:
            result = run_other_script(city)
            response = {
            # "message": f"Received City: {city}",
            # "status": "Successful",
            "result": result
            }
            print(response)
            return jsonify(response), 200
        else:
            response = {
            # "message": "Received no valid input (neither month nor integer)",
            # "status": "Failure",
            "result": "[]"
            }
            return jsonify(response), 400
    else:
        return render_template("suggest.html")

def run_other_script(city):
    result = subprocess.run(
        [".venv\\Scripts\\python.exe", "helper.py", city],  
        capture_output=True,                   
        text=True,
        check=False,
        encoding="UTF-8"                             
    )
    print(result)
    if result.returncode != 0:
            print(f"Error executing helper.py (Return Code: {result.returncode}): {result.stderr}")
            return [] 
    try:
        attractions_list = json.loads(result.stdout)
        return attractions_list if isinstance(attractions_list, list) else []
    except json.JSONDecodeError:
        print(f"Error decoding JSON from helper.py stdout: {result.stdout}")
        print(f"helper.py stderr: {result.stderr}") 
        return [] 

    except FileNotFoundError:
        print(f"Error: Could not find Python executable or script")
        return []
    except Exception as e:
        print(f"General error in run_other_script: {e}")
        return []

@app.route("/")
def home():
    saved_pois = [] 
    user_id = session.get("user")
    print(f"\n--- Loading Homepage ('/') ---") 
    print(f"[DEBUG] User ID from session: '{user_id}' (Type: {type(user_id)})") 
    if user_id: 
        print(f"[DEBUG] User '{user_id}' is logged in. Attempting to load POIs...")
        poi_file_path = os.path.abspath(CSV_FILENAME) 
        print(f"[DEBUG] Checking for POI file at: {poi_file_path}")

        
        if os.path.exists(CSV_FILENAME):
            print(f"[DEBUG] File '{CSV_FILENAME}' exists.")
            try:
                with open(CSV_FILENAME, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.reader(csvfile)
                    print("[DEBUG] Opened CSV file for reading.")

                    header = next(reader, None) 
                    print(f"[DEBUG] Read header: {header} (Type: {type(header)})")

                    expected_header = ['UserID', 'PointOfInterest']
                    
                    if header:
                        print(f"[DEBUG] Comparing read header '{header}' with expected '{expected_header}'")
                        if header == expected_header:
                            print("[DEBUG] Header MATCHES! Processing rows...")
                            row_count = 0
                            matches_found = 0
                            for row in reader:
                                row_count += 1
                                print(f"[DEBUG] Processing Row {row_count}: {row} (Type: {type(row)}, Length: {len(row)})")
                                # Ensure row has 2 columns before accessing index 0 and 1
                                if len(row) == 2:
                                    row_user_id = row[0]
                                    poi_name = row[1]
                                    print(f"[DEBUG] Comparing Row UserID '{row_user_id}' (Type: {type(row_user_id)}) with Session UserID '{user_id}' (Type: {type(user_id)})")
                                    if row_user_id.strip() == str(user_id).strip():
                                        print(f"[DEBUG] UserID MATCH! Appending POI: '{poi_name}'")
                                        saved_pois.append(poi_name)
                                        matches_found += 1
                                    else:
                                        print(f"[DEBUG] UserID mismatch ('{row_user_id}' != '{user_id}')")
                                else:
                                    print(f"[DEBUG] Skipping row {row_count} due to incorrect length ({len(row)} columns).")
                            print(f"[DEBUG] Finished processing {row_count} data rows. Found {matches_found} matches for user '{user_id}'.")
                        else:
                             print(f"[DEBUG] Header MISMATCH! Expected '{expected_header}', but got '{header}'. Skipping row processing.")
                    else:
                         print("[DEBUG] Header is None (File might be empty or only contains header).")

            except Exception as e:
                print(f"[ERROR] Error reading saved POIs from {CSV_FILENAME}: {e}")
                

        else:
             print(f"[DEBUG] POI file '{CSV_FILENAME}' does NOT exist.")

        print(f"[DEBUG] Final saved_pois list for user '{user_id}': {saved_pois}")
        poi_images = []
        for i in saved_pois:
            poi_images.append(get_city_images(i))
        
        return render_template("home_old.html",
                               user=user_id,
                               saved_pois=saved_pois,
                               saved_images=poi_images)
    else:
        print("[DEBUG] User is NOT logged in. Rendering index.html.")
        return render_template("index.html", user=None) 

# Signup Page
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        user_id = request.form["user_id"]
        password = request.form["password"]
        df = pd.read_csv(USER_DB)
        if user_id in df["UserID"].values:
            return "User ID already exists. Try another one!"
        new_user = pd.DataFrame([[name, user_id, password, "", ""]], columns=df.columns)
        df = pd.concat([df, new_user], ignore_index=True)
        df.to_csv(USER_DB, index=False)
        return redirect("/")
    return render_template("signup.html")

# Login Page
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form["user_id"]
        password = request.form["password"]

        df = pd.read_csv(USER_DB)
        user = df[(df["UserID"] == user_id) & (df["Password"] == password)]

        if not user.empty:
            session["user"] = user_id
            return redirect("/")
        else:
            print(df)
            return "Invalid Credentials!"
    
    return render_template("login.html")

# Logout
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
