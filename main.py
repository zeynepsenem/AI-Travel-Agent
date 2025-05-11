from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

OPENTRIPMAP_API_KEY = os.getenv("OPENTRIPMAP_API_KEY")
FOURSQUARE_API_KEY = os.getenv("FOURSQUARE_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"


app = Flask(__name__)
CORS(app, origins=["http://localhost:63342"])

def get_opentripmap_recommendations(city, limit=8):
    if not OPENTRIPMAP_API_KEY:
        return "OpenTripMap data not available."

    url = "https://api.opentripmap.com/0.1/en/places/text"
    params = {
        "name": city,
        "apikey": OPENTRIPMAP_API_KEY,
        "limit": limit,
        "lang": "en"
    }

    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        results = data.get("features", [])
        places = []

        for place in results:
            name = place.get("properties", {}).get("name")
            description = place.get("properties", {}).get("wikidataDescription", "No description available.")
            if name:
                places.append(f"{name}: {description}")

        return "\n".join(places) if places else "No interesting places found in OpenTripMap."
    else:
        return f"OpenTripMap API error: {response.status_code}"

def get_foursquare_recommendations(city, limit=8):
    if not FOURSQUARE_API_KEY:
        return "Foursquare data not available."

    url = "https://api.foursquare.com/v3/places/search"
    headers = {
        "Accept": "application/json",
        "Authorization": FOURSQUARE_API_KEY
    }
    params = {
        "near": city,
        "limit": limit,
        "sort": "RELEVANCE",
        "categories": "16000,13000,12000"  # Sights, restaurants, arts, etc.
    }

    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        data = response.json()
        results = data.get("results", [])
        places = []

        for place in results:
            name = place.get("name")
            location = place.get("location", {})
            address = location.get("formatted_address", "")
            if name:
                places.append(f"{name} - {address}")

        return "\n".join(places) if places else "No popular places found."
    else:
        return f"Foursquare API error: {response.status_code}"

def get_weather(city):
    if not WEATHER_API_KEY:
        return "Weather data not available"

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": WEATHER_API_KEY,
        "units": "metric",
        "lang": "en"
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        description = data["weather"][0]["description"]
        temp = data["main"]["temp"]
        return f"{description}, {temp}°C"
    else:
        return "Weather data could not be retrieved"

def get_travel_suggestion(full_prompt):
    if not GEMINI_API_KEY:
        return "Error: Gemini API anahtarı bulunamadı. Lütfen ortam değişkenini kontrol edin."

    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "contents": [
            {
                "parts": [
                    {"text": full_prompt}
                ]
            }
        ],
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
    }

    url_with_key = f"{BASE_URL}?key={GEMINI_API_KEY}"
    response = requests.post(url_with_key, headers=headers, json=data)

    if response.status_code == 200:
        try:
            response_data = response.json()
            if "candidates" in response_data and response_data["candidates"]:
                return response_data["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return "Error: Beklenen Gemini API yanıtı bulunamadı."
        except json.JSONDecodeError:
            return f"Error: Gemini API yanıtı JSON olarak çözümlenemedi: {response.text}"
    else:
        return f"Error: Gemini API'ye istek başarısız oldu. Durum kodu: {response.status_code}, Yanıt: {response.text}"

@app.route("/plan", methods=["POST"])

def plan_trip():
    data = request.json
    user_preferences = data.get("preferences", "")
    city = data.get("city", "")

    if not user_preferences or not city:
        return jsonify({"error": "preferences and city fields are required"}), 400

    weather_info = get_weather(city)
    foursquare_info = get_foursquare_recommendations(city)
    opentripmap_info = get_opentripmap_recommendations(city)


    full_prompt = f"""
    User Preferences: {user_preferences}

    Current weather in {city}:
    - {weather_info}

    Popular places to visit:
    - From Foursquare:
    {foursquare_info}

    - From OpenTripMap:
    {opentripmap_info}

    Now, based on the user's travel preferences, local weather, popular attractions, and nearby flight opportunities, create a personalized day travel plan for {city}. Include both indoor and outdoor suggestions. Also consider whether the user might want to explore nearby destinations or stay local.
    """

    suggestion = get_travel_suggestion(full_prompt)
    return jsonify({"suggestion": suggestion})

if __name__ == "__main__":
    app.run(debug=True)
