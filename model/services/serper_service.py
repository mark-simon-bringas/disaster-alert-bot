import os
import requests
from typing import List
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
CURRENT_INFO_CATEGORIES = {
    "current_weather": [
        "current weather", "lagay ng panahon", "ngayon", "kasalukuyan",
        "weather now", "temperature now", "current temperature", "weather update",
        "pag-ulan", "ulan ngayon", "ulan na", "init ngayon", "bagyo ngayon"
    ],
    "current_forecast": [
        "forecast", "tuloy na lagay ng panahon", "prediction",
        "weather forecast", "next days weather", "upcoming weather", "pag-forecast",
        "panahon sa mga susunod na araw"
    ],
    "current_earthquake": [
        "earthquake now", "lindol", "recent quake", "kasalukuyang lindol",
        "aftershock", "tremor", "lindol ngayon", "lindol sa ph"
    ],
    "current_tsunami": [
        "tsunami alert", "current tsunami", "pag-ula", "storm surge",
        "high tide warning", "wave alert", "babala sa tsunami", "storm surge alert"
    ],
    "current_volcano": [
        "volcano warning", "phivolcs", "bulkang aktibo",
        "volcano alert", "eruption alert", "volcanic activity", "pagputok ng bulkan",
        "phivolcs warning", "active volcano"
    ],
    "current_flood_storm": [
        "flood warning", "storm surge", "flash flood", "gale warning",
        "heavy rain", "ulan na malakas", "river overflow", "babala sa baha",
        "strong wind", "storm warning", "bagyong paparating", "storm surge alert"
    ],
    "current_wildfire": [
        "wildfire", "forest fire", "sunog", "grass fire", "bushfire",
        "fire outbreak", "kalat na sunog", "sunog sa kagubatan"
    ],
    "current_man_made": [
        "accident", "fire incident", "man-made disaster", "traffic incident",
        "chemical spill", "industrial accident", "hazardous event",
        "road accident", "train crash", "factory fire", "oil spill", "panggawaang aksidente"
    ],
    "current_disaster_news": [
        "latest disaster news", "disaster update", "breaking news",
        "recent disasters", "latest calamities", "disaster headlines",
        "news update on disasters", "bagong balita ng sakuna"
    ],
    "disaster_agency_info": [
        "ndrrmc", "pagasa", "phivolcs", "department of disaster", "official",
        "government disaster agencies", "ndrrmc update", "pagasa bulletin",
        "phivolcs advisory", "disaster preparedness officials",
        "chief of ndrrmc", "secretary of disaster", "head of pagasa", "local disaster office"
    ]
}

def fetch_serper_results(query: str, max_results: int = 5) -> List[Document]:
    if not SERPER_API_KEY:
        print("[SERPER] API key not configured")
        return []
    
    try:
        print(f"[SERPER] Searching for: {query}")
        
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "q": f"{query}",
            "num": max_results,
            "gl": "ph",
            "hl": "en"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        documents = []
        
        organic_results = data.get("organic", [])
        print(f"[SERPER] Found {len(organic_results)} organic results")
        
        for result in organic_results[:max_results]:
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            link = result.get("link", "")
            
            if not snippet:
                continue
            
            content = f"{title}\n\n{snippet}"
            
            doc = Document(
                page_content=content,
                metadata={
                    "source": link,
                    "title": title,
                    "source_type": "serper"
                }
            )
            documents.append(doc)
        
        knowledge_graph = data.get("knowledgeGraph")
        if knowledge_graph:
            kg_title = knowledge_graph.get("title", "")
            kg_desc = knowledge_graph.get("description", "")
            if kg_desc:
                kg_content = f"Knowledge Graph: {kg_title}\n\n{kg_desc}"
                documents.insert(0, Document(
                    page_content=kg_content,
                    metadata={
                        "source": "Google Knowledge Graph",
                        "title": kg_title,
                        "source_type": "serper"
                    }
                ))
        
        print(f"[SERPER] Returning {len(documents)} documents")
        return documents
        
    except requests.exceptions.RequestException as e:
        print(f"[SERPER] Request failed: {e}")
        return []
    except Exception as e:
        print(f"[SERPER] Error: {e}")
        return []

def classify_real_time_query(question: str) -> str:
    q = question.lower()
    for category, keywords in CURRENT_INFO_CATEGORIES.items():
        for kw in keywords:
            if kw in q:
                return category
    return "general_current"

def retrieve_realtime_docs(question: str) -> list:
    """
    Calls SERPER with a reinforced context based on the query category.
    """
    category = classify_real_time_query(question)
    print(f"[REINFORCED] Detected category: {category}")

    # Value to fetch for common and uncommon categories
    common_occur, uncommon_occur = 5, 3

    if category == "current_weather":
        return fetch_serper_results(f"current weather Philippines PAGASA", max_results=common_occur)
    elif category == "current_forecast":
        return fetch_serper_results(f"current weather forecast Philippines PAGASA", max_results=common_occur)
    elif category == "current_earthquake":
        return fetch_serper_results(f"current earthquake Philippines PHIVOLCS", max_results=common_occur)
    elif category == "current_tsunami":
        return fetch_serper_results(f"current tsunami warning Philippines PAGASA", max_results=common_occur)
    elif category == "current_volcano":
        return fetch_serper_results(f"current volcano activity Philippines PHIVOLCS", max_results=uncommon_occur)
    elif category == "current_flood_storm":
        return fetch_serper_results(f"current flood storm surge gale warnings Philippines PAGASA", max_results=common_occur)
    elif category == "current_wildfire":
        return fetch_serper_results(f"current wildfire Philippines", max_results=uncommon_occur)
    elif category == "current_man_made":
        return fetch_serper_results(f"current man-made disasters Philippines", max_results=uncommon_occur)
    elif category == "current_disaster_news":
        return fetch_serper_results(f"latest disaster news Philippines NDRRMC PAGASA", max_results=common_occur)
    elif category == "disaster_agency_info":
        return fetch_serper_results(f"disaster preparedness government officials agencies Philippines", max_results=common_occur)
    # fallback general search
    else:
        return fetch_serper_results(f"{question} Philippines", max_results=common_occur)

