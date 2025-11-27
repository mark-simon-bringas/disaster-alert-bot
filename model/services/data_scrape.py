from .web_scraper import scrape_urls_sync
from model.contexts.web_sources import WEB_SOURCES
from langchain_core.documents import Document
from typing import List, Optional

# TODO: Add more sources for web scraping

def fetch_disaster_data(pdf_chunks: Optional[List[Document]] = None) -> List[Document]:
    all_docs = []
    
    # Scrape web sources
    try:
        print("[DEBUG] Scraping web sources...")
        web_docs = scrape_urls_sync(WEB_SOURCES)
        print(f"[DEBUG] Scraped {len(web_docs)} web documents")
        
        if web_docs:
            all_docs.extend(web_docs)
        else:
            print("[WARNING] No web documents were scraped successfully")
            
    except Exception as e:
        print(f"[ERROR] Web scraping failed: {e}")

    if not all_docs: 
        print("[WARNING] No documents were collected from web sources!")
    else: 
        print(f"[DEBUG] Total web documents collected: {len(all_docs)}")
    
    return all_docs