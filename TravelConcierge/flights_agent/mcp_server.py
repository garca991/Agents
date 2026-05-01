import asyncio
import json
import os
import requests
from mcp.server.stdio import stdio_server
from mcp import types as mcp_types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from dotenv import load_dotenv

import logging

# Configurar logging a un archivo
logging.basicConfig(
    filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_debug.log"),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("flights-mcp")

# Intentar cargar .env desde el directorio padre si no está aquí
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

# Configuración de SerpApi
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SERPAPI_URL = "https://serpapi.com/search.json"

logger.info(f"Servidor MCP iniciado. API Key presente: {bool(SERPAPI_KEY)}")

async def search_flights(departure_id, arrival_id, outbound_date, return_date=None, it_type=None, currency="USD", hl="es"):
    """Consulta vuelos en SerpApi (Google Flights)."""
    logger.info(f"Buscando vuelos: {departure_id} -> {arrival_id} el {outbound_date} (tipo: {it_type})")
    if not SERPAPI_KEY:
        logger.error("Falta SERPAPI_KEY")
        return {"error": "Falta la SERPAPI_KEY en el entorno."}

    # Determinar el tipo de viaje: 1 = Round trip (default), 2 = One way
    # Si hay fecha de regreso, forzamos tipo 1. Si no la hay y no se especificó tipo, usamos tipo 2.
    if return_date:
        final_type = "1"
    else:
        final_type = it_type if it_type else "2"

    params = {
        "engine": "google_flights",
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound_date,
        "type": final_type,
        "currency": currency,
        "hl": hl,
        "api_key": SERPAPI_KEY
    }
    
    if return_date:
        params["return_date"] = return_date
    
    try:
        logger.info(f"Llamando a SerpApi con params: {params}")
        response = requests.get(SERPAPI_URL, params=params, timeout=25)
        response.raise_for_status()
        data = response.json()
        
        if "error" in data:
            logger.error(f"Error de SerpApi: {data['error']}")
            return {"status": "error", "message": data["error"]}

        flights = []
        if "best_flights" in data:
            for flight in data["best_flights"]:
                flights.append({
                    "price": flight.get("price"),
                    "airline": flight.get("flights", [{}])[0].get("airline"),
                    "duration": flight.get("total_duration"),
                    "departure": flight.get("flights", [{}])[0].get("departure_airport", {}).get("time"),
                    "arrival": flight.get("flights", [{}])[-1].get("arrival_airport", {}).get("time"),
                    "type": "Mejor opción"
                })
        
        logger.info(f"Vuelos encontrados: {len(flights)}")
        return {"status": "success", "flights": flights[:5], "total_results": len(flights)}
    except Exception as e:
        logger.error(f"Excepción en search_flights: {str(e)}")
        return {"status": "error", "message": str(e)}

async def search_hotels(q, check_in_date, check_out_date, currency="USD", hl="es"):
    """Consulta hoteles en SerpApi (Google Hotels)."""
    logger.info(f"Buscando hoteles en {q} del {check_in_date} al {check_out_date}")
    if not SERPAPI_KEY:
        return {"error": "Falta la SERPAPI_KEY en el entorno."}
    
    params = {
        "engine": "google_hotels",
        "q": q,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "currency": currency,
        "hl": hl,
        "api_key": SERPAPI_KEY
    }
    try:
        response = requests.get(SERPAPI_URL, params=params, timeout=25)
        response.raise_for_status()
        data = response.json()
        
        hotels = []
        for prop in data.get("properties", [])[:5]:
            hotels.append({
                "name": prop.get("name"),
                "price": prop.get("rate_per_night", {}).get("lowest"),
                "rating": prop.get("overall_rating"),
                "amenities": prop.get("amenities", [])[:3]
            })
        logger.info(f"Hoteles encontrados: {len(hotels)}")
        return {"status": "success", "hotels": hotels}
    except Exception as e:
        logger.error(f"Error en hoteles: {str(e)}")
        return {"status": "error", "message": str(e)}

async def search_events(q, hl="es"):
    """Consulta eventos en SerpApi (Google Events)."""
    logger.info(f"Buscando eventos: {q}")
    if not SERPAPI_KEY:
        return {"error": "Falta la SERPAPI_KEY en el entorno."}
    
    params = {
        "engine": "google_events",
        "q": q,
        "hl": hl,
        "api_key": SERPAPI_KEY
    }
    try:
        response = requests.get(SERPAPI_URL, params=params, timeout=25)
        response.raise_for_status()
        data = response.json()
        
        events = []
        for event in data.get("events_results", [])[:5]:
            events.append({
                "title": event.get("title"),
                "date": event.get("date", {}).get("when"),
                "address": event.get("address", [])[0] if event.get("address") else "Desconocida",
                "link": event.get("link")
            })
        logger.info(f"Eventos encontrados: {len(events)}")
        return {"status": "success", "events": events}
    except Exception as e:
        logger.error(f"Error en eventos: {str(e)}")
        return {"status": "error", "message": str(e)}

async def search_local_places(q, location, hl="es"):
    """Consulta lugares locales en SerpApi (Google Maps)."""
    logger.info(f"Buscando lugares: {q} en {location}")
    if not SERPAPI_KEY:
        return {"error": "Falta la SERPAPI_KEY en el entorno."}
    
    params = {
        "engine": "google_maps",
        "q": f"{q} en {location}",
        "hl": hl,
        "api_key": SERPAPI_KEY
    }
    try:
        response = requests.get(SERPAPI_URL, params=params, timeout=25)
        response.raise_for_status()
        data = response.json()
        
        places = []
        for place in data.get("local_results", [])[:5]:
            places.append({
                "name": place.get("title"),
                "rating": place.get("rating"),
                "address": place.get("address"),
                "type": place.get("type")
            })
        logger.info(f"Lugares encontrados: {len(places)}")
        return {"status": "success", "places": places}
    except Exception as e:
        logger.error(f"Error en lugares locales: {str(e)}")
        return {"status": "error", "message": str(e)}

app = Server("flights-mcp-server")

@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return [
        mcp_types.Tool(
            name="search_flights",
            description="Busca vuelos en tiempo real usando Google Flights a través de SerpApi.",
            inputSchema={
                "type": "object",
                "properties": {
                    "departure_id": {"type": "string", "description": "Código IATA del aeropuerto de origen (ej: MEX)."},
                    "arrival_id": {"type": "string", "description": "Código IATA del aeropuerto de destino (ej: MAD)."},
                    "outbound_date": {"type": "string", "description": "Fecha de salida en formato YYYY-MM-DD."},
                    "return_date": {"type": "string", "description": "Fecha de regreso opcional (YYYY-MM-DD)."},
                    "it_type": {"type": "string", "description": "Tipo de viaje: '1' para redondo (necesita return_date), '2' para solo ida.", "enum": ["1", "2"]},
                    "currency": {"type": "string", "description": "Moneda (ej: USD, MXN).", "default": "USD"}
                },
                "required": ["departure_id", "arrival_id", "outbound_date"]
            }
        ),
        mcp_types.Tool(
            name="search_hotels",
            description="Busca hoteles en un destino y fechas específicas usando Google Hotels a través de SerpApi.",
            inputSchema={
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Destino (ej: Madrid)."},
                    "check_in_date": {"type": "string", "description": "Fecha de entrada en formato YYYY-MM-DD."},
                    "check_out_date": {"type": "string", "description": "Fecha de salida en formato YYYY-MM-DD."},
                    "currency": {"type": "string", "description": "Moneda (ej: USD).", "default": "USD"}
                },
                "required": ["q", "check_in_date", "check_out_date"]
            }
        ),
        mcp_types.Tool(
            name="search_events",
            description="Busca eventos (conciertos, festivales, teatro) en una ciudad usando Google Events a través de SerpApi.",
            inputSchema={
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Consulta de eventos, incluye ciudad y preferiblemente fechas (ej: eventos en Madrid del 15 al 20 de mayo)."}
                },
                "required": ["q"]
            }
        ),
        mcp_types.Tool(
            name="search_local_places",
            description="Busca lugares locales (restaurantes, atracciones) en una ubicación usando Google Local a través de SerpApi.",
            inputSchema={
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "Lo que buscas (ej: restaurantes italianos, museos)."},
                    "location": {"type": "string", "description": "La ciudad o zona (ej: Madrid, España)."}
                },
                "required": ["q", "location"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[mcp_types.Content]:
    if name == "search_flights":
        result = await search_flights(**arguments)
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
    elif name == "search_hotels":
        result = await search_hotels(**arguments)
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
    elif name == "search_events":
        result = await search_events(**arguments)
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
    elif name == "search_local_places":
        result = await search_local_places(**arguments)
        return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]
    raise ValueError(f"Herramienta no encontrada: {name}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, InitializationOptions(server_name="flights-mcp-server", server_version="1.0.0", capabilities=app.get_capabilities(notification_options=NotificationOptions(), experimental_capabilities={})))

if __name__ == "__main__":
    asyncio.run(main())
