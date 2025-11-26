from typing import Optional, Dict
from model.services.pagasa_bulletin_parser import get_latest_bulletin
import logging

logger = logging.getLogger(__name__)

def fetch_weather_warning() -> Optional[Dict]:
    try:
        bulletin = get_latest_bulletin()
        if not bulletin:
            return None

        tcws_list = bulletin.get("tcws") or []
        highest_signal = max(tcws_list, key=lambda s: s.get("signal_no", 0)) if tcws_list else None
        location = bulletin.get("location_of_center", {})

        return {
            "classification": bulletin.get("classification"),
            "name": bulletin.get("name"),
            "intensity": bulletin.get("intensity"),
            "present_movement": bulletin.get("present_movement"),
            "location": {
                "description": location.get("description"),
                "as_of": location.get("as_of")
            },
            "highest_tcws": {
                "signal_no": highest_signal.get("signal_no") if highest_signal else None,
                "affected_areas": highest_signal.get("affected_areas") if highest_signal else None,
                "impact": "Unknown" if not highest_signal else f"Signal {highest_signal['signal_no']}"
            },
            "source": bulletin.get("source")
        }

    except Exception as e:
        logger.exception("Failed to fetch weather warning")
        return None
