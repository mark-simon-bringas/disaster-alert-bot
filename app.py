from flask import Flask, request, jsonify, render_template
from model.rag_modelv4 import ask_question, refresh_web_data
from datetime import datetime
import logging
import os
import requests
from dotenv import load_dotenv
from typing import Optional, Tuple, List, Dict

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
            url = f"http://api.openweathermap.org/geo/1.0/direct?q={requests.utils.requote_uri(city_name)},PH&limit=1&appid={OPENWEATHER_API_KEY}"
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
        
        nom_url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.requote_uri(city_name)},Philippines&format=json&limit=1"
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

def get_weather_icon(condition_main: str, condition_id: int) -> str:
    if condition_id >= 200 and condition_id < 300:
        return "bi-cloud-lightning-rain"
    elif condition_id >= 300 and condition_id < 400:
        return "bi-cloud-drizzle"
    elif condition_id >= 500 and condition_id < 600:
        if condition_id == 500 or condition_id == 520:
            return "bi-cloud-rain"
        else:
            return "bi-cloud-rain-heavy"
    elif condition_id >= 600 and condition_id < 700:
        return "bi-cloud-snow"
    elif condition_id >= 700 and condition_id < 800:
        return "bi-cloud-fog"
    elif condition_id == 800:
        return "bi-brightness-high"
    elif condition_id == 801:
        return "bi-cloud-sun"
    elif condition_id == 802:
        return "bi-cloud-sun"
    elif condition_id == 803 or condition_id == 804:
        return "bi-cloud"
    else:
        return "bi-cloud"

@app.route("/weather", methods=["GET"])
def get_weather():
    city = request.args.get("city")
    if not city:
        return jsonify({"error": "Please provide a city name via ?city=..."}), 400
    
    if not OPENWEATHER_API_KEY:
        return jsonify({"error": "OpenWeather API key not configured"}), 500
    
    coords = geocode(city)
    if not coords:
        return jsonify({"error": "Unable to geocode city. Please try a different city name."}), 400

    lat, lon, display_city = coords
    
    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}"
            f"&appid={OPENWEATHER_API_KEY}"
            f"&units=metric"
        )
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()

        main = data.get("main", {})
        weather = data.get("weather", [{}])[0]
        wind = data.get("wind", {})
        
        condition_main = weather.get("main", "Unknown")
        condition_desc = weather.get("description", "").title()
        condition_id = weather.get("id", 800)
        
        out = {
            "city": city,
            "display_city": display_city,
            "temp": round(main.get("temp", 0)),
            "feels_like": round(main.get("feels_like", 0)),
            "humidity": main.get("humidity"),
            "wind": round(wind.get("speed", 0) * 3.6, 1),
            "condition": condition_desc,
            "icon": get_weather_icon(condition_main, condition_id),
            "provider": "OpenWeather",
            "fetched_at": datetime.utcnow().isoformat() + "Z"
        }
        return jsonify(out), 200

    except Exception as e:
        app.logger.exception("OpenWeather current fetch failed")
        return jsonify({"error": str(e)}), 500

@app.route("/forecast", methods=["GET"])
def get_forecast():
    city = request.args.get("city")
    if not city:
        return jsonify({"error": "Please provide a city name via ?city=..."}), 400
    
    if not OPENWEATHER_API_KEY:
        return jsonify({"error": "OpenWeather API key not configured"}), 500

    coords = geocode(city)
    if not coords:
        return jsonify({"error": "Unable to geocode city. Please try a different city name."}), 400

    lat, lon, display_city = coords

    try:
        url = (
            f"https://api.openweathermap.org/data/2.5/forecast"
            f"?lat={lat}&lon={lon}"
            f"&appid={OPENWEATHER_API_KEY}"
            f"&units=metric"
            f"&cnt=40"
        )
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()

        forecast_list = data.get("list", [])
        
        daily_data: Dict[str, Dict] = {}
        
        for item in forecast_list:
            dt_txt = item.get("dt_txt", "")
            date = dt_txt.split(" ")[0]
            
            temp = item.get("main", {}).get("temp")
            temp_min = item.get("main", {}).get("temp_min")
            temp_max = item.get("main", {}).get("temp_max")
            weather = item.get("weather", [{}])[0]
            condition_id = weather.get("id", 800)
            condition_main = weather.get("main", "")
            
            if date not in daily_data:
                daily_data[date] = {
                    "date": date,
                    "temps": [],
                    "mins": [],
                    "maxs": [],
                    "condition_id": condition_id,
                    "condition_main": condition_main
                }
            
            if temp is not None:
                daily_data[date]["temps"].append(temp)
            if temp_min is not None:
                daily_data[date]["mins"].append(temp_min)
            if temp_max is not None:
                daily_data[date]["maxs"].append(temp_max)
        
        daily = []
        for date in sorted(daily_data.keys())[:5]:
            day_data = daily_data[date]
            
            avg_temp = round(sum(day_data["temps"]) / len(day_data["temps"])) if day_data["temps"] else None
            min_temp = round(min(day_data["mins"])) if day_data["mins"] else None
            max_temp = round(max(day_data["maxs"])) if day_data["maxs"] else None
            
            daily.append({
                "date": date,
                "temp": avg_temp,
                "min": min_temp,
                "max": max_temp,
                "condition": day_data["condition_main"],
                "icon": get_weather_icon(day_data["condition_main"], day_data["condition_id"])
            })

        return jsonify({"daily": daily, "display_city": display_city}), 200

    except Exception as e:
        app.logger.exception("OpenWeather forecast failed")
        return jsonify({"error": str(e)}), 500

@app.route("/weather_warning", methods=["GET"])
def weather_warning():
    from model.services.pagasa_bulletin_parser import get_latest_bulletin

    try:
        bulletin = get_latest_bulletin()
        if not bulletin:
            return jsonify({"error": "No PAGASA bulletin available"}), 500

        # Extract fields cleanly
        classification = bulletin.get("classification")
        name = bulletin.get("name")
        intensity = bulletin.get("intensity")
        movement = bulletin.get("present_movement")
        location = bulletin.get("location_of_center")
        tcws_list = bulletin.get("tcws") or []

        # Get highest signal
        highest_signal = None
        if tcws_list:
            highest_signal = max(tcws_list, key=lambda s: s.get("signal_no", 0))

        if location:
            loc_description = location.get("description")
            loc_as_of = location.get("as_of")
        else:
            loc_description = None
            loc_as_of = None

        result = {
            "classification": classification,
            "name": name,
            "intensity": intensity,
            "present_movement": movement,
            "location": {
                "description": loc_description,
                "as_of": loc_as_of
            },
            "highest_tcws": {
                "signal_no": highest_signal.get("signal_no") if highest_signal else None,
                "affected_areas": highest_signal.get("affected_areas") if highest_signal else None,
                "impact": (
                    "Unknown" if not highest_signal
                    else f"Signal {highest_signal['signal_no']}"
                )
            },
            "source": bulletin.get("source")
        }

        return jsonify(result), 200

    except Exception as e:
        app.logger.exception("Weather warning fetch failed")
        return jsonify({"error": str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)