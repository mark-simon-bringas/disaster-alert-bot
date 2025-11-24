from flask import Flask, request, jsonify, render_template
from model.rag_modelv4 import ask_question, refresh_web_data
from datetime import datetime
import logging
import os
import requests
from dotenv import load_dotenv
from typing import Optional, Tuple

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

def geocode(city_name: str) -> Optional[Tuple[float, float, str]]:
    try:
        if OPENWEATHER_API_KEY:
            url = f"http://api.openweathermap.org/geo/1.0/direct?q={requests.utils.requote_uri(city_name)}&limit=1&appid={OPENWEATHER_API_KEY}"
            r = requests.get(url, timeout=6)
            arr = r.json()
            if isinstance(arr, list) and len(arr) > 0:
                lat = arr[0].get("lat")
                lon = arr[0].get("lon")
                name = arr[0].get("name") or city_name
                state = arr[0].get("state")
                country = arr[0].get("country")
                display = f"{name}" + (f", {state}" if state else "") + (f", {country}" if country else "")
                return float(lat), float(lon), display
        
        nom_url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.requote_uri(city_name)}&format=json&limit=1"
        r = requests.get(nom_url, headers={"User-Agent": "DisasterAlertBot/1.0"}, timeout=6)
        arr = r.json()
        if isinstance(arr, list) and len(arr) > 0:
            lat = arr[0].get("lat")
            lon = arr[0].get("lon")
            display = arr[0].get("display_name", city_name)
            return float(lat), float(lon), display
    except Exception:
        app.logger.exception("Geocode failed")
    return None

@app.route('/', endpoint='index')
def index():
    return render_template('index.html', title='DisasterAlertBot')

@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()
        if not data:
            logger.error("No JSON data received")
            return jsonify({"answer": "Error: No data received"}), 400
        message = data.get("message", "").strip()
        if not message:
            logger.warning("Empty message received")
            return jsonify({"answer": "Please enter a question."}), 400
        logger.info(f"Received question: {message}")
        answer = ask_question(message)
        logger.info(f"Generated answer: {answer[:100]}...")
        return jsonify({"answer": answer}), 200
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}", exc_info=True)
        return jsonify({"answer": "Sorry, I encountered an error. Please try again."}), 500

@app.route("/refresh", methods=["POST"])
def refresh():
    try:
        logger.info("Refreshing web data...")
        refresh_web_data()
        logger.info("Web data refreshed successfully")
        return jsonify({"status": "success", "message": "Web sources refreshed!"}), 200
    except Exception as e:
        logger.error(f"Error refreshing data: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": f"Refresh failed: {str(e)}"}), 500

WEATHERCODE_MAP = {
    0: ("Clear Sky", "bi-brightness-high"),
    1: ("Mainly Clear", "bi-brightness-high"),
    2: ("Partly Cloudy", "bi-cloud-sun"),
    3: ("Overcast", "bi-cloud"),
    45: ("Fog", "bi-cloud-fog"),
    48: ("Fog", "bi-cloud-fog"),
    51: ("Light Drizzle", "bi-cloud-drizzle"),
    53: ("Drizzle", "bi-cloud-drizzle"),
    55: ("Heavy Drizzle", "bi-cloud-drizzle"),
    61: ("Light Rain", "bi-cloud-rain"),
    63: ("Moderate Rain", "bi-cloud-rain-heavy"),
    65: ("Heavy Rain", "bi-cloud-rain-heavy"),
    80: ("Rain Showers", "bi-cloud-rain"),
    81: ("Rain Showers", "bi-cloud-rain"),
    82: ("Heavy Rain Showers", "bi-cloud-rain-heavy"),
    95: ("Thunderstorm", "bi-cloud-lightning"),
    96: ("Thunderstorm w/ Hail", "bi-cloud-lightning-rain"),
    99: ("Severe Thunderstorm", "bi-cloud-lightning-rain")
}

def get_weather_description(code: Optional[int]) -> Tuple[str, str]:
    if code is None:
        return ("Unknown", "bi-cloud")
    return WEATHERCODE_MAP.get(code, ("Unknown", "bi-cloud"))

@app.route("/weather", methods=["GET"])
def get_weather():
    city = request.args.get("city")
    if not city:
        return jsonify({"error": "Please provide a city name via ?city=..."}), 400
    
    coords = geocode(city)
    if not coords:
        return jsonify({"error": "Unable to geocode city. Please try a different city name."}), 400

    lat, lon, display_city = coords
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&current_weather=true"
            "&daily=temperature_2m_max,temperature_2m_min,weathercode,precipitation_sum"
            "&timezone=Asia%2FManila"
            "&forecast_days=1"
        )
        r = requests.get(url, timeout=8)
        data = r.json()

        cw = data.get("current_weather") or {}
        fetched_at = cw.get("time")

        raw_code = cw.get("weathercode")
        code = int(raw_code) if raw_code is not None else None
        cond, icon = get_weather_description(code)

        temp = cw.get("temperature")
        out = {
            "city": city,
            "display_city": display_city,
            "temp": round(temp) if temp is not None else None,
            "feels_like": None,
            "humidity": None,
            "wind": cw.get("windspeed"),
            "condition": cond,
            "icon": icon,
            "provider": "Open-Meteo",
            "fetched_at": fetched_at
        }
        return jsonify(out), 200

    except Exception as e:
        app.logger.exception("Open-Meteo current fetch failed")
        return jsonify({"error": str(e)}), 500

@app.route("/forecast", methods=["GET"])
def get_forecast():
    city = request.args.get("city")
    if not city:
        return jsonify({"error": "Please provide a city name via ?city=..."}), 400

    coords = geocode(city)
    if not coords:
        return jsonify({"error": "Unable to geocode city. Please try a different city name."}), 400

    lat, lon, display_city = coords

    try:
        om_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&daily=temperature_2m_max,temperature_2m_min,weathercode,precipitation_sum"
            "&timezone=Asia%2FManila"
            "&forecast_days=7"
        )
        r = requests.get(om_url, timeout=8)
        om = r.json()

        daily = []
        d = om.get("daily", {})
        dates = d.get("time", [])
        maxes = d.get("temperature_2m_max", [])
        mins = d.get("temperature_2m_min", [])
        codes = d.get("weathercode", [])

        for i, date in enumerate(dates):
            if i >= 5:
                break
            
            maxv = maxes[i] if i < len(maxes) else None
            minv = mins[i] if i < len(mins) else None
            
            raw_code = codes[i] if i < len(codes) else None
            code = int(raw_code) if raw_code is not None else None
            cond, icon = get_weather_description(code)
            
            if maxv is not None and minv is not None:
                temp_rep = round((maxv + minv) / 2)
            elif maxv is not None:
                temp_rep = round(maxv)
            else:
                temp_rep = None
            
            daily.append({
                "date": date,
                "temp": temp_rep,
                "min": round(minv) if minv is not None else None,
                "max": round(maxv) if maxv is not None else None,
                "condition": cond,
                "icon": icon
            })

        return jsonify({"daily": daily, "display_city": display_city}), 200

    except Exception as e:
        app.logger.exception("Open-Meteo forecast failed")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)