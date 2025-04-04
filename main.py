import os
import time
import asyncio
import requests
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from datetime import datetime, timedelta
from functions import HelpScoutHelper  # Adjust import paths if needed
from api_client import HelpScoutAPIClient

# Try to load configuration from config.toml if available.
try:
    config_data = toml.load("./config.toml")
except Exception:
    config_data = {}

def get_config_value(key):
    return os.getenv(key.upper()) or config_data.get("keys", {}).get(key)

app = FastAPI(title="HelpScout Metrics API")

# CORS configuration: only allow your Vercel frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://metricdb.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ticket_cache = {
    "all_tickets": [],
    "closed_tickets": [],
    "ticket_durations": {},
    "custom_fields": [],
    "last_updated": None
}

CACHE_DURATION = timedelta(minutes=10)

client = HelpScoutAPIClient()
helper = HelpScoutHelper(client)

# Dependency: Require a valid API key (from environment variable API_KEY)
async def verify_api_key(x_api_key: str = Header(...)):
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    if x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return x_api_key

def refresh_cache():
    """Refresh the global cache by fetching data from HelpScout."""
    global ticket_cache
    try:
        all_tickets = helper.get_all_tickets()
        closed_tickets = helper.get_closed_tickets()
        ticket_durations = helper.get_tickets_duration_times()
        custom_fields = helper.extract_custom_fields(all_tickets)

        ticket_cache.update({
            "all_tickets": all_tickets,
            "closed_tickets": closed_tickets,
            "ticket_durations": ticket_durations,
            "custom_fields": custom_fields,
            "last_updated": datetime.utcnow()
        })
        print(f"Cache refreshed at {ticket_cache['last_updated']}")
        print("Cached Custom Fields:", custom_fields)
    except Exception as e:
        print(f"Error refreshing cache: {e}")

async def background_cache_updater():
    """Background task to update cache periodically."""
    while True:
        try:
            await run_in_threadpool(refresh_cache)
        except Exception as e:
            print(f"Error refreshing cache: {e}")
        await asyncio.sleep(CACHE_DURATION.total_seconds())

@app.on_event("startup")
async def startup_event():
    await run_in_threadpool(refresh_cache)
    asyncio.create_task(background_cache_updater())

@app.get("/metrics/closed-tickets")
async def closed_tickets(api_key: str = Depends(verify_api_key)):
    tickets = ticket_cache.get("closed_tickets", [])
    return {"closed_tickets": tickets, "count": len(tickets)}

@app.get("/metrics/all-tickets")
async def all_tickets(api_key: str = Depends(verify_api_key)):
    tickets = ticket_cache.get("all_tickets", [])
    return {"all_tickets": tickets, "count": len(tickets)}

@app.get("/metrics/average-ticket-duration")
async def average_ticket_duration(api_key: str = Depends(verify_api_key)):
    durations = ticket_cache.get("ticket_durations", {})
    if not durations:
        return {"average_ticket_duration": 0}
    filtered = helper.filter_outliers(durations)
    avg_duration = sum(filtered.values()) / len(filtered) if filtered else 0
    return {"average_ticket_duration": avg_duration}

@app.get("/metrics/tickets-by-report-method")
async def tickets_by_report_method(api_key: str = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    report_counts = {}
    for ticket in custom_fields:
        rm = ticket.get("Report Method")
        if rm:
            report_counts[rm] = report_counts.get(rm, 0) + 1
        else:
            print(f"Missing Report Method in ticket: {ticket}")
    return {"tickets_by_report_method": report_counts}

@app.get("/metrics/custom-fields")
async def custom_fields(api_key: str = Depends(verify_api_key)):
    custom_fields_data = ticket_cache.get("custom_fields", [])
    return {"custom_fields": custom_fields_data}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
