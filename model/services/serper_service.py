import os
import requests
from typing import List, Optional
from langchain_core.documents import Document
from dotenv import load_dotenv
from model.contexts.context_keywords import LOCATION_KEYWORDS
from .ph_data import CURRENT_INFO_CATEGORIES

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

def has_location_reference(question: str) -> bool:
    q_lower = question.lower()
    return any(keyword in q_lower for keyword in LOCATION_KEYWORDS)

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

def extract_location_from_context(user_location: Optional[str]) -> str:
    if not user_location:
        return "Philippines"
    
    if "," in user_location:
        city = user_location.split(",")[0].strip()
    else:
        city = user_location.strip()
    
    return f"{city}, Philippines"

def retrieve_realtime_docs(question: str, user_location: Optional[str] = None) -> list:
    category = classify_real_time_query(question)
    has_loc_ref = has_location_reference(question)
    
    location_context = extract_location_from_context(user_location)
    
    if has_loc_ref:
        print(f"[SERPER] Location reference detected! Using: {location_context}")
    else:
        print(f"[SERPER] No location reference. Default: {location_context}")
    
    print(f"[SERPER] Query category: {category}")
    
    common_occur, uncommon_occur = 5, 3
    
    if category == "current_weather":
        if has_loc_ref:
            return fetch_serper_results(f"current weather {location_context} PAGASA", max_results=common_occur)
        return fetch_serper_results(f"current weather Philippines PAGASA", max_results=common_occur)
    
    elif category == "current_forecast":
        if has_loc_ref:
            return fetch_serper_results(f"weather forecast {location_context} PAGASA", max_results=common_occur)
        return fetch_serper_results(f"weather forecast Philippines PAGASA", max_results=common_occur)
    
    elif category == "current_earthquake":
        if has_loc_ref:
            return fetch_serper_results(f"earthquake {location_context} PHIVOLCS", max_results=common_occur)
        return fetch_serper_results(f"current earthquake Philippines PHIVOLCS", max_results=common_occur)
    
    elif category == "current_tsunami":
        if has_loc_ref:
            return fetch_serper_results(f"tsunami warning {location_context} PAGASA", max_results=common_occur)
        return fetch_serper_results(f"tsunami warning Philippines PAGASA", max_results=common_occur)
    
    elif category == "current_volcano":
        if has_loc_ref:
            return fetch_serper_results(f"volcano activity near {location_context} PHIVOLCS", max_results=uncommon_occur)
        return fetch_serper_results(f"volcano activity Philippines PHIVOLCS", max_results=uncommon_occur)
    
    elif category == "current_flood_storm":
        if has_loc_ref:
            return fetch_serper_results(f"flood storm warnings {location_context} PAGASA", max_results=common_occur)
        return fetch_serper_results(f"flood storm warnings Philippines PAGASA", max_results=common_occur)
    
    elif category == "current_wildfire":
        if has_loc_ref:
            return fetch_serper_results(f"wildfire {location_context}", max_results=uncommon_occur)
        return fetch_serper_results(f"wildfire Philippines", max_results=uncommon_occur)
    
    elif category == "current_man_made":
        if has_loc_ref:
            return fetch_serper_results(f"accidents disasters {location_context}", max_results=uncommon_occur)
        return fetch_serper_results(f"man-made disasters Philippines", max_results=uncommon_occur)
    
    elif category == "current_disaster_news":
        if has_loc_ref:
            return fetch_serper_results(f"latest disaster news {location_context} NDRRMC", max_results=common_occur)
        return fetch_serper_results(f"latest disaster news Philippines NDRRMC PAGASA", max_results=common_occur)
    
    elif category == "disaster_agency_info":
        return fetch_serper_results(f"disaster preparedness agencies Philippines", max_results=common_occur)
    
    else:
        if has_loc_ref:
            return fetch_serper_results(f"{question} {location_context}", max_results=common_occur)
        return fetch_serper_results(f"{question} Philippines", max_results=common_occur)