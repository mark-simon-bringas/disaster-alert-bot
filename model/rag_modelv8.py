"""
    NOTE: Still in development. Will use if deadline is not on 12-02-2025.
"""

import os
from .services.data_scrape import fetch_disaster_data
from .services.serper_service import retrieve_realtime_docs
from .services.weather_service import fetch_current_weather, fetch_forecast
from .services.warning_service import fetch_weather_warning
from .services.phivolcs_earthquake_parser import fetch_and_parse_latest_earthquake
from .contexts.context_keywords import CURRENT_INFO_KEYWORDS, LOCATION_KEYWORDS, WEATHER_KEYWORDS, TYPHOON_KEYWORDS, EARTHQUAKE_KEYWORDS
from .contexts.prompt_template import PROMPT_TEMPLATE
from .contexts.ph_locations import HARDCODED_LOCATIONS
from collections import deque
from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM
from typing import List, Dict, Optional

load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_FILE = "DisasteAlertBot_Data_v1.pdf"
PDF_PATH = os.path.join(BASE_DIR, "pdf", PDF_FILE)
DB_DIR = os.path.join(BASE_DIR, "chroma_db")
os.makedirs(DB_DIR, exist_ok=True)

MAX_HISTORY_LENGTH = 5
TOP_K_CHUNKS = 5
user_sessions: Dict[str, deque] = {}

""" CONTEXT REINFORCEMENT """
# Helper function: determines if real-time info is needed
def needs_real_time_info(question: str) -> bool:
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in CURRENT_INFO_KEYWORDS)

# Helper function: determines if weather data is needed
def needs_weather_data(question: str) -> bool:
    q_lower = question.lower()
    has_current = any(kw in q_lower for kw in LOCATION_KEYWORDS)
    has_weather = any(kw in q_lower for kw in WEATHER_KEYWORDS)
    return has_current and has_weather

# Helper function: determines if typhoon data is needed
def needs_typhoon_data(question: str) -> bool:
    q_lower = question.lower()
    has_current = any(kw in q_lower for kw in LOCATION_KEYWORDS)
    has_typhoon = any(kw in q_lower for kw in TYPHOON_KEYWORDS)
    return has_current and has_typhoon

# Helper function: determines if earthquake data is needed
def needs_earthquake_data(question: str) -> bool:
    q_lower = question.lower()
    has_current = any(kw in q_lower for kw in LOCATION_KEYWORDS)
    has_earthquake = any(kw in q_lower for kw in EARTHQUAKE_KEYWORDS)
    return has_current and has_earthquake

# Geocode location
def geocode_from_location(location: Optional[str]) -> Optional[tuple]:
    if not location:
        return None
    
    clean_name = location.replace(", Philippines", "").strip()
    
    if clean_name in HARDCODED_LOCATIONS:
        return HARDCODED_LOCATIONS[clean_name]
    
    return None

""" SERVICE DATA FETCHING """
# Fetch weather service data
def fetch_weather_service_data(user_location: Optional[str]) -> Optional[Document]:
    try:
        coords = geocode_from_location(user_location)
        if not coords:
            print("[WEATHER SERVICE] No valid location, using Manila as default")
            coords = (14.5995, 120.9842, "Manila, Philippines")
        
        lat, lon, display_city = coords
        
        if not OPENWEATHER_API_KEY:
            print("[WEATHER SERVICE] OpenWeather API key not configured")
            return None
        
        print(f"[WEATHER SERVICE] Fetching current weather for {display_city}")
        current = fetch_current_weather(lat, lon, OPENWEATHER_API_KEY)
        
        print(f"[WEATHER SERVICE] Fetching forecast for {display_city}")
        forecast = fetch_forecast(lat, lon, OPENWEATHER_API_KEY)
        
        weather_text = f"Current Weather in {display_city}:\n"
        weather_text += f"Temperature: {current.get('temp')}°C\n"
        weather_text += f"Feels Like: {current.get('feels_like')}°C\n"
        weather_text += f"Condition: {current.get('condition')}\n"
        weather_text += f"Humidity: {current.get('humidity')}%\n"
        weather_text += f"Wind Speed: {current.get('wind')} km/h\n\n"
        
        weather_text += f"5-Day Forecast for {display_city}:\n"
        for day in forecast.get('daily', []):
            weather_text += f"- {day.get('date')}: High {day.get('max')}°C, Low {day.get('min')}°C, {day.get('condition')}\n"
        
        return Document(
            page_content=weather_text,
            metadata={
                "source": f"OpenWeather API - {display_city}",
                "source_type": "weather_service",
                "priority": "highest"
            }
        )
    except Exception as e:
        print(f"[WEATHER SERVICE] Error: {e}")
        return None

# Fetch typhoon service data
def fetch_typhoon_service_data() -> Optional[Document]:
    try:
        print("[TYPHOON SERVICE] Fetching PAGASA bulletin...")
        data = fetch_weather_warning()

        if not data:
            print("[TYPHOON SERVICE] No bulletin retrieved.")
            return None

        typhoon_text = "PAGASA Tropical Cyclone Bulletin\n\n"

        # Basic metadata
        typhoon_text += f"Name: {data.get('name', 'N/A')}\n"
        typhoon_text += f"Classification: {data.get('classification', 'N/A')}\n\n"

        # Intensity
        intensity = data.get("intensity") or {}
        typhoon_text += "Intensity:\n"
        typhoon_text += f"- Maximum Winds: {intensity.get('max_winds_kmh', 'N/A')} km/h\n"
        typhoon_text += f"- Gustiness: {intensity.get('gustiness_kmh', 'N/A')} km/h\n"
        typhoon_text += f"- Pressure: {intensity.get('pressure_hpa', 'N/A')} hPa\n\n"

        # Movement
        movement = data.get("present_movement") or {}
        direction = movement.get("direction") or "Unavailable"
        speed = movement.get("speed_kmh") or "Unavailable"
        typhoon_text += f"Movement: {direction} at {speed} km/h\n\n"

        # Location
        location = data.get("location") or {}
        typhoon_text += "Location:\n"
        typhoon_text += f"- Description: {location.get('description', 'N/A')}\n"
        typhoon_text += f"- As of: {location.get('as_of', 'N/A')}\n\n"

        # Highest TCWS
        highest_tcws = data.get("highest_tcws") or {}
        if highest_tcws.get("signal_no"):
            typhoon_text += "Highest TCWS:\n"
            typhoon_text += f"- Signal: {highest_tcws.get('signal_no')}\n"
            typhoon_text += f"- Affected Areas: {highest_tcws.get('affected_areas', 'N/A')}\n"
            typhoon_text += f"- Impact: {highest_tcws.get('impact', 'N/A')}\n\n"
        else:
            typhoon_text += "No Tropical Cyclone Wind Signals in effect.\n\n"

        # Source link
        typhoon_text += f"Source: {data.get('source','N/A')}\n"

        return Document(
            page_content=typhoon_text,
            metadata={
                "source": "PAGASA Tropical Cyclone Bulletin",
                "source_type": "typhoon_service",
                "priority": "highest"
            }
        )

    except Exception as e:
        print(f"[TYPHOON SERVICE] Error: {e}")
        return None

# Fetch earthquake service data
def fetch_earthquake_service_data() -> Optional[Document]:
    try:
        print("[EARTHQUAKE SERVICE] Fetching PHIVOLCS data...")
        eq = fetch_and_parse_latest_earthquake()
        
        if not eq:
            print("[EARTHQUAKE SERVICE] No significant earthquake data")
            return None
        
        date_time = f"{eq.get('date','N/A')} {eq.get('time','')}".strip()

        # Latest significant earthquake information
        eq_text = "Latest Significant Earthquake (PHIVOLCS):\n\n"
        eq_text += f"Magnitude: {eq.get('magnitude','N/A')}\n"
        eq_text += f"Date & Time: {date_time}\n"
        eq_text += f"Issued On: {eq.get('issued_on','N/A')}\n"
        eq_text += f"Location: {eq.get('location','N/A')}\n"
        eq_text += f"Depth: {eq.get('depth_of_focus','N/A')}\n\n"

        coords = eq.get("coordinates", {})
        if coords:
            eq_text += f"Coordinates: {coords.get('latitude','N/A')}°N, {coords.get('longitude','N/A')}°E\n"

        if eq.get("reported_intensities"):
            eq_text += "\nReported Intensities:\n"
            for item in eq["reported_intensities"]:
                eq_text += f"- Intensity {item['intensity']}: {item['places']}\n"

        if eq.get("aftershock") is not None:
            eq_text += f"\nAftershock Expected: {'Yes' if eq['aftershock'] else 'No'}\n"

        return Document(
            page_content=eq_text,
            metadata={
                "source": "PHIVOLCS Latest Earthquake Bulletin",
                "source_type": "earthquake_service",
                "priority": "highest"
            }
        )

    except Exception as e:
        print(f"[EARTHQUAKE SERVICE] Error: {e}")
        return None

""" VECTOR STORE INITIALIZATION """
# Loader for PDF data
def load_pdf_chunks() -> List[Document]:
    try:
        loader = PyMuPDFLoader(str(PDF_PATH))
        pdf_docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", "?", "!"]
        )
        pdf_chunks = text_splitter.split_documents(pdf_docs)
        for chunk in pdf_chunks:
            chunk.metadata["source_type"] = "pdf"
            chunk.metadata["priority"] = "high"
        return pdf_chunks
    except Exception as e:
        print(f"[ERROR] Failed to load PDF: {e}")
        return []

# Loader for web data
def load_web_chunks() -> List[Document]:
    try:
        web_docs = fetch_disaster_data(pdf_chunks=None)
        if not web_docs:
            return []
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", "?", "!"]
        )
        web_chunks = []
        for doc in web_docs:
            chunks = text_splitter.split_documents([doc])
            for chunk in chunks:
                chunk.metadata["source_type"] = "web"
                chunk.metadata["priority"] = "medium"
            web_chunks.extend(chunks)
        return web_chunks
    except Exception as e:
        print(f"[ERROR] Failed to load web sources: {e}")
        return []

def initialize_vector_stores():
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    pdf_chunks = load_pdf_chunks()
    pdf_store = Chroma.from_documents(
        pdf_chunks,
        embedding=embeddings,
        persist_directory=os.path.join(DB_DIR, "pdf_store")
    )
    
    web_chunks = load_web_chunks()
    web_store = None
    if web_chunks:
        web_store = Chroma.from_documents(
            web_chunks,
            embedding=embeddings,
            persist_directory=os.path.join(DB_DIR, "web_store")
        )
    
    if not os.path.exists(os.path.join(DB_DIR, "serper_store")):
        os.makedirs(os.path.join(DB_DIR, "serper_store"), exist_ok=True)
    serper_store = Chroma(
        embedding_function=embeddings,
        persist_directory=os.path.join(DB_DIR, "serper_store")
    )

    return pdf_store, web_store, serper_store, embeddings

""" MAIN RAG MODEL LOGIC """
pdf_vector_store, web_vector_store, serper_vector_store, embeddings = initialize_vector_stores()
llm = OllamaLLM(model="llama3.2:3b", temperature=0.6)

def retrieve_data(question: str, user_location: Optional[str] = None, k: int = 5) -> tuple[list[Document], str]:
    print(f"[RETRIEVAL] Analyzing question: {question}")
    if user_location:
        print(f"[RETRIEVAL] User location: {user_location}")
    
    service_docs = []
    
    if needs_weather_data(question):
        print("[RETRIEVAL] Weather query detected - fetching weather service data")
        weather_doc = fetch_weather_service_data(user_location)
        if weather_doc:
            service_docs.append(weather_doc)
    
    if needs_typhoon_data(question):
        print("[RETRIEVAL] Typhoon query detected - fetching PAGASA bulletin")
        typhoon_doc = fetch_typhoon_service_data()
        if typhoon_doc:
            service_docs.append(typhoon_doc)
    
    if needs_earthquake_data(question):
        print("[RETRIEVAL] Earthquake query detected - fetching PHIVOLCS data")
        earthquake_doc = fetch_earthquake_service_data()
        if earthquake_doc:
            service_docs.append(earthquake_doc)
    
    if service_docs:
        print(f"[RETRIEVAL] Retrieved {len(service_docs)} service documents")
        pdf_docs = pdf_vector_store.similarity_search(question, k=2)
        combined_docs = service_docs + pdf_docs
        print(f"[RETRIEVAL] Strategy: service_priority ({len(service_docs)} service + {len(pdf_docs)} pdf)")
        return combined_docs, "service_priority"
    
    is_current_query = needs_real_time_info(question)
    print(f"[RETRIEVAL] Real-time query detected: {is_current_query}")
    
    if is_current_query:
        print(f"[RETRIEVAL] Fetching real-time data from Serper...")
        serper_docs = retrieve_realtime_docs(question, user_location=user_location)
        
        if serper_docs:
            print(f"[RETRIEVAL] Retrieved {len(serper_docs)} results from Serper")
            for d in serper_docs:
                d.metadata["source_type"] = "serper"
                d.metadata["priority"] = "highest"
            
            pdf_docs = pdf_vector_store.similarity_search(question, k=2)
            combined_docs = serper_docs + pdf_docs
            
            print(f"[RETRIEVAL] Strategy: serper_priority ({len(serper_docs)} serper + {len(pdf_docs)} pdf)")
            return combined_docs, "serper_priority"
        else:
            print(f"[RETRIEVAL] Serper returned no results, falling back to PDF/Web")
    
    pdf_results = pdf_vector_store.similarity_search_with_score(question, k=k)
    pdf_docs = [doc for doc, score in pdf_results]
    
    pdf_text_len = sum(len(d.page_content) for d in pdf_docs)
    if pdf_text_len > 800:
        print(f"[RETRIEVAL] Strategy: pdf_only (sufficient content: {pdf_text_len} chars)")
        return pdf_docs, "pdf_only"
    
    combined_docs = pdf_docs.copy()
    
    if web_vector_store:
        web_docs = web_vector_store.similarity_search(question, k=2)
        combined_docs.extend(web_docs)
        print(f"[RETRIEVAL] Strategy: pdf_and_web ({len(pdf_docs)} pdf + {len(web_docs)} web)")
        return combined_docs, "pdf_and_web"
    
    print(f"[RETRIEVAL] Strategy: pdf_only (no web sources)")
    return combined_docs, "pdf_only"

def get_session_history(session_id: str) -> deque:
    if session_id not in user_sessions:
        user_sessions[session_id] = deque(maxlen=MAX_HISTORY_LENGTH)
    return user_sessions[session_id]

def ask_question(question: str, session_id: str = "default", user_location: Optional[str] = None) -> str:
    print(f"\n[SESSION: {session_id}] User asked: {question}")
    if user_location:
        print(f"[SESSION: {session_id}] User location: {user_location}")
    
    chat_history = get_session_history(session_id)
    
    history_text = ""
    if chat_history:
        print(f"[CHAT HISTORY] Loading {len(chat_history)} previous exchanges:")
        for idx, (q, a) in enumerate(list(chat_history), 1):
            print(f"  {idx}. User: {q[:50]}...")
            print(f"     Bot: {a[:50]}...")
            history_text += f"User: {q}\nBot: {a}\n"
    else:
        print("[CHAT HISTORY] No previous history for this session")
    
    docs, strategy = retrieve_data(question, user_location=user_location, k=TOP_K_CHUNKS)
    print(f"[CONTEXT] Building context from {len(docs)} documents (strategy: {strategy})")
    
    source_labels = {
        "weather_service": "Weather Service (Real-time)",
        "typhoon_service": "PAGASA Bulletin (Real-time)",
        "earthquake_service": "PHIVOLCS Data (Real-time)",
        "pdf": "PDF Handbook",
        "web": "Web Official Source",
        "serper": "Real-time Search"
    }
    context_parts = []
    for i, d in enumerate(docs, 1):
        source = d.metadata.get("source", "Unknown")
        source_type = d.metadata.get("source_type", "unknown")
        label_prefix = source_labels.get(source_type, "Unknown")

        context_parts.append(
            f"[Source {i}: {label_prefix} - {source} | priority={d.metadata.get('priority','')}]"
            f"\n{d.page_content.strip()}"
        )
    
    context = "\n\n".join(context_parts) or "No relevant context found."
    
    prompt = PROMPT_TEMPLATE.format(chat_history=history_text, context=context, question=question)
    
    print(f"[GENERATING] Calling LLM...")
    result = llm.generate([prompt])
    answer = result.generations[0][0].text.strip()
    
    chat_history.append((question, answer))
    print(f"[RESPONSE] Generated answer ({len(answer)} chars)")
    print(f"[CHAT HISTORY] Updated. Total exchanges in session: {len(chat_history)}\n")
    
    return answer

def refresh_web_data():
    global web_vector_store
    web_chunks = load_web_chunks()
    if web_chunks:
        web_vector_store = Chroma.from_documents(
            web_chunks,
            embedding=embeddings,
            persist_directory=os.path.join(DB_DIR, "web_store")
        )