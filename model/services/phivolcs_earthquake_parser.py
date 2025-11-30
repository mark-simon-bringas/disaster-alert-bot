import re
import urllib.request
import ssl
from bs4 import BeautifulSoup

def parse_earthquake_html(html_content):
    ROMAN_TO_INT = {
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
        'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10
    }
    soup = BeautifulSoup(html_content, 'html.parser')
    
    def parse_intensity_string(intensity_str):
        if not intensity_str:
            return None
        
        parts = re.split(r'Intensity\s+', intensity_str)
        parsed = []
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            match = re.match(r'([IVX]+)\s*-\s*(.+)', part)
            if match:
                roman = match.group(1).strip()
                places = match.group(2).strip()
                
                intensity_num = ROMAN_TO_INT.get(roman)
                if intensity_num:
                    parsed.append({
                        "intensity": intensity_num,
                        "places": places
                    })
        
        return parsed if parsed else None
    
    result: dict[str, str | bool | list | None] = {
        "date": None,
        "time": None,
        "issued_on": None,
        "location": None,
        "depth_of_focus": None,
        "magnitude": None,
        "reported_intensities_raw": None,
        "reported_intensities": None,
        "instrumental_intensities_raw": None,
        "instrumental_intensities": None,
        "aftershock": None
    }
    
    bold_spans = soup.find_all('span', style=lambda x: x is not None and 'color:blue' in x)
    
    for span in bold_spans:
        text = span.get_text(strip=True)
        row = span.find_parent('tr')
        if row:
            row_text = row.get_text()
            
            # Date/Time
            if 'Date/Time' in row_text and result["date"] is None:
                match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})\s*-\s*(.+)', text)
                if match:
                    result["date"] = match.group(1).strip()
                    result["time"] = match.group(2).strip()
            
            # Location
            elif 'Location' in row_text and result["location"] is None:
                result["location"] = text
            
            # Depth of Focus
            elif re.search(r'Depth\s+of\s+Focus', row_text) and result["depth_of_focus"] is None:
                depth = text.strip().lstrip('0') or '0'
                result["depth_of_focus"] = f"{depth} km"
            
            # Issued On
            elif re.search(r'Issued\s+On', row_text) and result["issued_on"] is None:
                result["issued_on"] = text.strip()
            
            elif 'Expecting Aftershocks' in row_text and result["aftershock"] is None:
                result["aftershock"] = text.strip().upper() == "YES"
    
    # Magnitude
    font_tags = soup.find_all('font', color="#0000FF")
    for font in font_tags:
        text = font.get_text(strip=True)
        row = font.find_parent('tr')
        if row:
            row_text = row.get_text()
            if 'Magnitude' in row_text and result["magnitude"] is None:
                result["magnitude"] = text.strip()
    
    all_text = soup.get_text()
    
    # Reported Intensities
    intensity_match = re.search(
        r'Reported\s+Intensities\s*:\s*(.*?)(?=Instrumental\s+Intensities:|Expecting\s+Damage|Expecting\s+Aftershocks|Issued\s+On|Prepared\s+by|IMPORTANT|$)', 
        all_text, 
        re.DOTALL | re.IGNORECASE
    )
    if intensity_match:
        reported = intensity_match.group(1).strip()
        reported = re.sub(r'[ \t]+', ' ', reported)
        reported = re.sub(r'([A-Z])Intensity', r'\1 Intensity', reported)
        reported = re.sub(r'\d{1,2}\.\d{2}[ap].*?(?=Intensity|$)', '', reported, flags=re.DOTALL).strip()
        reported = re.sub(r'\s+', ' ', reported)
        result["reported_intensities_raw"] = reported if reported else None
        result["reported_intensities"] = parse_intensity_string(reported)
    
    # Instrumental Intensities
    instrumental_match = re.search(
        r'Instrumental\s+Intensities:\s*(.*?)(?=Expecting\s+Damage|Expecting\s+Aftershocks|Issued\s+On|Prepared\s+by|IMPORTANT|$)', 
        all_text, 
        re.DOTALL | re.IGNORECASE
    )
    if instrumental_match:
        instrumental = instrumental_match.group(1).strip()
        instrumental = re.sub(r'[ \t]+', ' ', instrumental)
        instrumental = re.sub(r'([A-Z])Intensity', r'\1 Intensity', instrumental)
        instrumental = re.sub(r'\s+', ' ', instrumental)
        result["instrumental_intensities_raw"] = instrumental if instrumental else None
        result["instrumental_intensities"] = parse_intensity_string(instrumental)
    
    return result

def get_latest_significant_earthquake(main_page_html, base_url="https://earthquake.phivolcs.dost.gov.ph/", debug=False):
    soup = BeautifulSoup(main_page_html, 'html.parser')
    all_rows = soup.find_all('tr')
    
    if debug:
        print(f"Found {len(all_rows)} total rows")
    
    for row_idx, row in enumerate(all_rows):
        cells = row.find_all('td')
        
        if len(cells) < 2:
            continue
        
        first_cell = cells[0]
        link = first_cell.find('a')
        
        if not link or not link.get('href'):
            continue
        
        magnitude = None
        try:
            mag_text = cells[4].get_text(strip=True)
            magnitude = float(mag_text)
            if debug:
                datetime_text = first_cell.get_text(strip=True)
                print(f"Row {row_idx}: {datetime_text} - Magnitude: {magnitude}")
        except:
            pass
        
        if magnitude is not None and magnitude >= 4.0:
            href = link.get('href')
            datetime_text = first_cell.get_text(strip=True)
            print(f"Found earthquake >= 4.0: {datetime_text} (Magnitude: {magnitude})")
            
            if not href.startswith('http'):
                href = href.replace('\\', '/')
                full_url = base_url + href
            else:
                full_url = href
            
            return full_url
    
    return None

def fetch_and_parse_latest_earthquake(main_page_url="https://earthquake.phivolcs.dost.gov.ph/"):
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        print(f"Fetching main page: {main_page_url}")
        req = urllib.request.Request(main_page_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context) as response:
            main_page_html = response.read().decode('utf-8', errors='ignore')
        
        earthquake_url = get_latest_significant_earthquake(main_page_html, main_page_url, debug=True)
        
        if not earthquake_url:
            print("No earthquake with magnitude >= 4.0 found")
            return None
        
        print(f"Found earthquake: {earthquake_url}")
        
        req = urllib.request.Request(earthquake_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ssl_context) as response:
            earthquake_html = response.read().decode('windows-1252', errors='ignore')
        
        earthquake_data = parse_earthquake_html(earthquake_html)
        
        return earthquake_data
        
    except Exception as e:
        print(f"Error fetching or parsing earthquake data: {e}")
        import traceback
        traceback.print_exc()
        return None