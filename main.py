import os
import time
import asyncio
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from datetime import datetime, timedelta
from api_client import HelpScoutAPIClient

# Load configuration
try:
    import toml
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

# Initialize API client
client = HelpScoutAPIClient()

# Dependency: Require a valid API key (from environment variable API_KEY)
async def verify_api_key(x_api_key: str = Header(...)):
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    if x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return x_api_key

# Method to refresh cache by fetching data from Help Scout
def refresh_cache():
    """Refresh the global cache by fetching data from HelpScout."""
    global ticket_cache
    try:
        all_tickets = client.get("conversations", params={"status": "all"})
        closed_tickets = client.get("conversations", params={"status": "closed"})
        ticket_durations = {ticket['id']: ticket['createdAt'] for ticket in closed_tickets['conversations']}
        custom_fields = []
        for ticket in all_tickets['conversations']:
            custom_fields.append({
                "ticket_id": ticket['id'],
                "Department": ticket['customFields']['Department'],
                "Service Type": ticket['customFields']['Service Type'],
                "Category": ticket['customFields']['Category'],
                "Location": ticket['customFields']['Location'],
                "Report Method": ticket['customFields']['Report Method']
            })

        ticket_cache.update({
            "all_tickets": all_tickets['conversations'],
            "closed_tickets": closed_tickets['conversations'],
            "ticket_durations": ticket_durations,
            "custom_fields": custom_fields,
            "last_updated": datetime.utcnow()
        })

        print(f"Cache refreshed at {ticket_cache['last_updated']}")
        print(f"Cached Custom Fields: {ticket_cache['custom_fields'][:5]}")  # Log first 5 tickets for review
    except Exception as e:
        print(f"Error refreshing cache: {e}")

# Background task to refresh cache every 10 minutes
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
    """Start cache update task and cache refresh on startup."""
    await run_in_threadpool(refresh_cache)
    asyncio.create_task(background_cache_updater())

# Define endpoint for metrics
@app.get("/metrics/tickets-by-service-type")
async def tickets_by_service_type(api_key: str = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    service_type_counts = {}
    for ticket in custom_fields:
        service_type = ticket.get("Service Type")
        if service_type:
            service_type_counts[service_type] = service_type_counts.get(service_type, 0) + 1
    return {"tickets_by_service_type": service_type_counts}

@app.get("/metrics/tickets-by-category")
async def tickets_by_category(api_key: str = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    category_counts = {}
    for ticket in custom_fields:
        category = ticket.get("Category")
        if category:
            category_counts[category] = category_counts.get(category, 0) + 1
    return {"tickets_by_category": category_counts}

@app.get("/metrics/tickets-by-department")
async def tickets_by_department(api_key: str = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    department_counts = {}
    for ticket in custom_fields:
        department = ticket.get("Department")
        if department:
            department_counts[department] = department_counts.get(department, 0) + 1
    return {"tickets_by_department": department_counts}

@app.get("/metrics/tickets-by-location")
async def tickets_by_location(api_key: str = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    location_counts = {}
    for ticket in custom_fields:
        location = ticket.get("Location")
        if location:
            location_counts[location] = location_counts.get(location, 0) + 1
    return {"tickets_by_location": location_counts}

@app.get("/metrics/average-ticket-duration")
async def average_ticket_duration(api_key: str = Depends(verify_api_key)):
    durations = ticket_cache.get("ticket_durations", {})
    if not durations:
        return {"average_ticket_duration": 0}
    avg_duration = sum(durations.values()) / len(durations) if durations else 0
    return {"average_ticket_duration": avg_duration}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
