# DisasterAlertBot: Local Disaster Preparedness Chatbot

> ***Note for Developers**: Please read the instructions first located in* `instructions.txt`

## Project Description

The Philippines is struck by numerous disasters each year, including typhoons, earthquakes, and floods. Its location along the Pacific Ring of Fire and typhoon belt makes it highly vulnerable to these hazards. 

To address this, **DisasterAlertBot** aims to enhance community preparedness through real-time alerts and accessible disaster information. It serves as a **localized disaster preparedness assistant** that provides users with emergency contact information and practical disaster response guides tailored to their location.

### Main Features
- **Interactive Chat Assistant** — Users can ask questions and receive personalized disaster preparedness guidance.  
- **Live Weather Display** — Integrates real-time weather data to provide instant updates and respond to urgent queries.
- **Retrieval-Augmented Generation (RAG) Integration** — Accesses verified government and NGO-issued disaster preparedness guides, compiled in PDF format to ensure reliability.  
- **Live Agent Integrations** — Fetches real-time weather data to alert users when disasters occur.

## Problem to Solve

During disasters, people often face difficulties in **accessing accurate and timely information**. There should be immediate access to:
- Disaster preparedness tips  
- Local emergency contacts  
- Evacuation routes  
- Other relevant information during crisis situations  

**DisasterAlertBot** addresses this by providing all of these through a single, intelligent, and localized chatbot interface.

## Chatbot Type

**Informational and Assistive Chatbot**  
*(using Retrieval-Augmented Generation [RAG] Model)*

## Target Users

- Local residents (general public and travelers)  
- Government organizations  
- NGOs focused on disaster preparedness and risk reduction  

## Tools and Technologies
[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)](#) [![Ollama](https://img.shields.io/badge/Ollama-fff?logo=ollama&logoColor=000)](#)  [![LangChain](https://img.shields.io/badge/LangChain-1c3c3c.svg?logo=langchain&logoColor=white)](#) [![Hugging Face](https://img.shields.io/badge/Hugging%20Face-FFD21E?logo=huggingface&logoColor=000)](#) [![Flask](https://img.shields.io/badge/Flask-000?logo=flask&logoColor=fff)](#) [![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=000)](#) [![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=fff)](#)
| Component | Technology |
|------------|-------------|
| **AI Model** | Llama 3.2 (`llama3.2:3b`) |
| **AI Training** | Python (Ollama, Langchain, HuggingFace) |
| **Frontend & Backend** | Python (Flask, FastAPI), CSS, JavaScript |
| **Weather API** | OpenWeatherMap API, Serper |
| **Deployment** | Docker |

## Members

- **BRINGAS**, MARK SIMON ZUILAN
- **BUGNAY**, KEF HARVEY MASAOAY
- **CHAMOS**, RHONE BRYCE MOLTIO
- **FERNANDO**, ERWIN CHRIS PEREZ
- **OSTING**, NADINE KYLA GABALDON
- **RIZALDE**, JEREMIAH TABALON
- **SAN MIGUEL**, WIFRAIM NEIL RAMIREZ

---

> *This project is developed as a final project in fulfillment of the subject Intelligent Systems (INTSYS1) to promote community disaster resilience through AI-driven preparedness assistance.* 
> *This project also supports global efforts toward SDG 11 — Sustainable Cities and Communities, and SDG 13 — Climate Action*.
