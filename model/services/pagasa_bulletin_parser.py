from bs4 import BeautifulSoup
from datetime import datetime
import io
import json
import pdfplumber
import requests
import re
from typing import Optional, Dict, List

BASE_URL = "https://pubfiles.pagasa.dost.gov.ph/tamss/weather/bulletin/"

def clean_pdf_text(raw_text):
    # Normalize unicode punctuation
    text = raw_text.replace("\u201c", "\"").replace("\u201d", "\"")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u2026", "...")
    text = text.replace("\u00b0", "°")

    boilerplate_patterns = [
        r"MMSS-04 Rev\.1.*?Weather Division",
        r"Republic of the Philippines.*?Weather Division",
        r"DOST-PAGASA.*?(?=MMSS|\Z)",  # footer block
        r"Page \d+ of \d+\s*Prepared by:.*?(?=MMSS|\Z)",
        r"tracking the sky.*?Philippines",
    ]

    for pattern in boilerplate_patterns:
        text = re.sub(pattern, "", text, flags=re.DOTALL | re.IGNORECASE)

    text = re.sub(r"\n{2,}", "\n", text)

    return text.strip()

def extract_tcws_impact(signal_no: int) -> str:
    impacts = {
        5: "Extreme threat to life and property",
        4: "Significant to severe threat to life and property",
        3: "Moderate to significant threat to life and property",
        2: "Minor to moderate threat to life and property",
        1: "Minimal to minor threat to life and property"
    }
    return impacts.get(signal_no, "Unknown")

def parse_bulletin(text: str, bulletin: str) -> Dict:
    # Classification and Name
    m = re.search(
        r"(Tropical\s+Depression|Tropical\s+Storm|Severe\s+Tropical\s+Storm|Typhoon|Super\s+Typhoon)\s+([A-Z0-9\-]+)",
        text, re.IGNORECASE)
    classification = m.group(1) if m else None
    name = m.group(2).upper() if m else None

    # Issued Time
    m = re.search(r"Issued at ([0-9: ]+(?:AM|PM)),?\s*([0-9]{1,2}\s+\w+\s+\d{4})", text)
    issued = f"{m.group(1)}, {m.group(2)}" if m else None

    # Location of Center
    m_coords = re.search(r"\(([0-9.]+)[°º]?\s*([NS]),\s*([0-9.]+)[°º]?\s*([EW])\)", text)
    location_desc = None
    location_as_of = None
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "Location of Center" in line:
            desc_lines = []
            for j in range(i+1, len(lines)):
                if m_coords and m_coords.group(0) in lines[j]:
                    break
                desc_lines.append(lines[j].strip())
            location_desc = " ".join(desc_lines)
            m_asof = re.search(r"\((.*?)\)", line)
            if m_asof:
                location_as_of = m_asof.group(1)
            break

    loc_match = re.search(
        r"(The center of.*?\([0-9.]+[°º]?\s*[NS],\s*[0-9.]+[°º]?\s*[EW]\))",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    location_desc = None
    if loc_match:
        location_desc = loc_match.group(1).strip()
        location_desc = " ".join(location_desc.split())
    
    location = {
        "description": location_desc,
        "coordinates": None,
        "as_of": location_as_of
    }
    
    if m_coords:
        lat = float(m_coords.group(1)) * (1 if m_coords.group(2) == "N" else -1)
        lon = float(m_coords.group(3)) * (1 if m_coords.group(4) == "E" else -1)
        location["coordinates"] = {"lat": lat, "lon": lon}

    # Intensity
    m = re.search(
        r"Maximum sustained winds of (\d+)\s*km/h.*?gustiness of up to (\d+)\s*km/h.*?pressure of (\d+)\s*hPa",
        text, re.DOTALL)
    intensity = {
        "max_winds_kmh": int(m.group(1)) if m else None,
        "gustiness_kmh": int(m.group(2)) if m else None,
        "pressure_hpa": int(m.group(3)) if m else None
    }

    # Present Movement
    m = re.search(r"Present Movement\s*([A-Za-z ]+?)\s+at\s+(\d+)\s*km/h", text)
    movement = {
        "direction": m.group(1).strip() if m else None,
        "speed_kmh": int(m.group(2)) if m else None
    }

    # Extent of Tropical Cyclone Winds
    m = re.search(r"([Ss]trong(?: to [A-Za-z-]+)? winds extend outwards up to [\d,]+ km(?: from the center)?)", text)
    extent_of_winds = m.group(1).strip() if m else None

    # Tropical Cyclone Wind Signals (TCWS)
    # NOTE: BUGGY - may not capture all edge cases
    tcws_array = []
    tcws_section = re.search(
        r"TROPICAL CYCLONE WIND SIGNALS.*?(?=OTHER HAZARDS|HAZARDS|TRACK AND|$)",
        text,
        re.DOTALL | re.IGNORECASE
    )
    if tcws_section:
        section_text = tcws_section.group(0)
        signal_splits = re.split(r"(?<=\n)(\d+)\s+(?=[A-Z])", section_text)
        idx = 1
        
        while idx < len(signal_splits):
            signal_no = int(signal_splits[idx].strip())
            content = signal_splits[idx + 1].strip()

            affected_areas = re.split(r"Warning lead time:|Range of wind speeds:|Potential impacts of winds:", content, flags=re.IGNORECASE)[0]
            affected_areas = re.sub(r"\s+", " ", affected_areas).replace("\uf0b7", "").strip()
            affected_areas = re.sub(r"(?<=\s)-(?=\s)|^-|-$", "", affected_areas).strip()
            if affected_areas.lower().endswith(" winds"):
                affected_areas = affected_areas[:-6].strip()
            if affected_areas.endswith(" Wind threat:"):
                affected_areas = affected_areas[:-13].strip()

            range_of_wind_speeds = re.search(r"Range of wind speeds:\s*(.*)", content, re.IGNORECASE)
            potential_impacts = re.search(r"Potential impacts of winds:\s*(.*)", content, re.IGNORECASE)
            warning_lead_time = re.search(r"Warning lead time:\s*(\d+)\s*hours", content, re.IGNORECASE)

            tcws_array.append({
                "signal_no": signal_no,
                "affected_areas": affected_areas,
                "range_of_wind_speeds": range_of_wind_speeds.group(1).strip() if range_of_wind_speeds else None,
                "potential_impacts": potential_impacts.group(1).strip() if potential_impacts else None,
                "warning_lead_time_hours": int(warning_lead_time.group(1)) if warning_lead_time else None
            })

            idx += 2

    return {
        "classification": classification,
        "name": name,
        "issued": issued,
        "location_of_center": location,
        "intensity": intensity,
        "present_movement": movement,
        "extent_of_tropical_cyclone_winds": extent_of_winds,
        "tcws": tcws_array if tcws_array else None,
        "source": bulletin,
        "content": text
    }

def fetch_directory_listing() -> str:
    r = requests.get(BASE_URL, timeout=10)
    r.raise_for_status()
    return r.text

def parse_listing(html: str) -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    pre = soup.find("pre")

    if not pre:
        raise Exception("Directory listing <pre> not found")

    entries = []
    for a in pre.find_all("a"):
        filename: str = a.text.strip()
        if filename == "../":
            continue
        
        tail = a.next_sibling
        if not tail:
            continue
        tail_str = str(tail).strip()
        if not tail_str:
            continue
        
        parts = tail_str.split()
        if len(parts) < 3:
            continue
        
        date_str, time_str, size = parts[0], parts[1], parts[2]
        try:
            dt = datetime.strptime(date_str + " " + time_str, "%d-%b-%Y %H:%M")
        except ValueError:
            continue

        entries.append({
            "filename": filename,
            "datetime": dt,
            "size": size
        })

    return entries

def download_pdf(filename: str) -> bytes:
    safe_name = filename.replace("#", "%23")
    r = requests.get(BASE_URL + safe_name, timeout=10)
    r.raise_for_status()
    return r.content

def extract_pdf_text(data: bytes) -> str:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

def get_latest_bulletin() -> Optional[Dict]:
    try:
        html = fetch_directory_listing()
        entries = parse_listing(html)
        
        if not entries:
            return None
        
        recent = max(entries, key=lambda e: e["datetime"])
        bulletin_source = BASE_URL + recent["filename"]
        
        pdf_data = download_pdf(recent["filename"])
        raw_pdf_text = extract_pdf_text(pdf_data)
        pdf_text = clean_pdf_text(raw_pdf_text)
        
        parsed = parse_bulletin(pdf_text, bulletin_source)
        return parsed
        
    except Exception as e:
        print(f"Error fetching bulletin: {e}")
        return None

def get_latest_bulletin_json() -> str:
    bulletin = get_latest_bulletin()
    if bulletin:
        return json.dumps(bulletin, indent=4, ensure_ascii=False)
    return json.dumps({"error": "No bulletin available"})

if __name__ == "__main__":
    bulletin = get_latest_bulletin()
    if bulletin:
        print(json.dumps(bulletin, indent=4, ensure_ascii=False))
    else:
        print("ERROR: Could not fetch bulletin")