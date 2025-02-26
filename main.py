import os
import asyncio
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from fastapi.security import APIKeyHeader
from functions import HelpScoutHelper  # Adjust import paths if needed
from api_client import HelpScoutAPIClient

app = FastAPI(title="HelpScout Metrics API")

# Get allowed origins from environment variable - more secure
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "https://metricdb.vercel.app").split(",")

# CORS configuration: only allow specified frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],  # Only allow GET as needed for your metrics
    allow_headers=["*"],
)

# Global in-memory cache for ticket data
ticket_cache = {
    "all_tickets": [],
    "closed_tickets": [],
    "ticket_durations": {},
    "custom_fields": [],
    "last_updated": None
}
CACHE_DURATION = timedelta(minutes=10)

# Initialize API client and helper once at startup.
client = HelpScoutAPIClient()
helper = HelpScoutHelper(client)

# Secure API key handling
API_KEY_HEADER = APIKeyHeader(name="X-API-Key")
API_SECRET = os.getenv("API_SECRET", "ITServic3!")  # Store this securely in Render environment variables

# Hash the API secret for comparison
HASHED_API_SECRET = hashlib.sha256(API_SECRET.encode()).hexdigest()

async def verify_api_key(api_key: str = Depends(API_KEY_HEADER), request: Request = None):
    """Secure API key verification with time-based check to prevent replay attacks"""
    try:
        # Split the token into timestamp and hash parts
        timestamp_str, received_hash = api_key.split('.')
        timestamp = int(timestamp_str)
        
        # Check if the timestamp is within a reasonable window (5 minutes)
        current_time = int(time.time())
        if current_time - timestamp > 300:  # 5 minutes
            raise HTTPException(status_code=403, detail="Token expired")
            
        # Recreate the hash with our secret to verify
        expected_data = f"{timestamp_str}:{request.url.path}"
        expected_hash = hmac.new(
            API_SECRET.encode(),
            expected_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison to avoid timing attacks
        if not hmac.compare_digest(received_hash, expected_hash):
            raise HTTPException(status_code=403, detail="Invalid authentication")
            
        return True
    except Exception:
        raise HTTPException(status_code=403, detail="Unauthorized")

def refresh_cache():
    """Refresh the global cache by fetching data from HelpScout."""
    global ticket_cache
    # Fetch all and closed tickets.
    all_tickets = helper.get_all_tickets()
    closed_tickets = helper.get_closed_tickets()
    # Compute ticket durations (for closed tickets).
    ticket_durations = helper.get_tickets_duration_times()
    # Extract custom fields from all tickets.
    custom_fields = helper.extract_custom_fields(all_tickets)
    ticket_cache.update({
        "all_tickets": all_tickets,
        "closed_tickets": closed_tickets,
        "ticket_durations": ticket_durations,
        "custom_fields": custom_fields,
        "last_updated": datetime.utcnow()
    })
    print(f"Cache refreshed at {ticket_cache['last_updated']}")

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
    # Eagerly refresh the cache on startup and start the periodic updater.
    await run_in_threadpool(refresh_cache)
    asyncio.create_task(background_cache_updater())

# For each endpoint, the API key dependency is enforced.
@app.get("/metrics/closed-tickets")
async def closed_tickets(authenticated: bool = Depends(verify_api_key)):
    tickets = ticket_cache.get("closed_tickets", [])
    return {"closed_tickets": tickets, "count": len(tickets)}

@app.get("/metrics/all-tickets")
async def all_tickets(authenticated: bool = Depends(verify_api_key)):
    tickets = ticket_cache.get("all_tickets", [])
    return {"all_tickets": tickets, "count": len(tickets)}

@app.get("/metrics/average-ticket-duration")
async def average_ticket_duration(authenticated: bool = Depends(verify_api_key)):
    durations = ticket_cache.get("ticket_durations", {})
    if not durations:
        return {"average_ticket_duration": 0}
    filtered = helper.filter_outliers(durations)
    avg_duration = sum(filtered.values()) / len(filtered) if filtered else 0
    return {"average_ticket_duration": avg_duration}

@app.get("/metrics/tickets-duration-times")
async def tickets_duration_times(authenticated: bool = Depends(verify_api_key)):
    durations = ticket_cache.get("ticket_durations", {})
    return {"ticket_durations": durations}

@app.get("/metrics/custom-fields")
async def custom_fields(authenticated: bool = Depends(verify_api_key)):
    custom_fields_data = ticket_cache.get("custom_fields", [])
    return {"custom_fields": custom_fields_data}

@app.get("/metrics/tickets-by-department")
async def tickets_by_department(authenticated: bool = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    dept_counts = {}
    for ticket in custom_fields:
        dept = ticket.get("Department")
        if dept:
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
    return {"tickets_by_department": dept_counts}

@app.get("/metrics/departments")
async def departments(authenticated: bool = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    depts = [ticket.get('Department') for ticket in custom_fields if 'Department' in ticket]
    return {"departments": depts}

@app.get("/metrics/tickets-by-location")
async def tickets_by_location(authenticated: bool = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    location_counts = {}
    for ticket in custom_fields:
        loc = ticket.get("Location")
        if loc:
            location_counts[loc] = location_counts.get(loc, 0) + 1
    return {"tickets_by_location": location_counts}

@app.get("/metrics/locations")
async def locations(authenticated: bool = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    locs = [ticket.get('Location') for ticket in custom_fields if 'Location' in ticket]
    return {"locations": locs}

@app.get("/metrics/report-method")
async def report_method(authenticated: bool = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    methods = [ticket.get('Report Method') for ticket in custom_fields if 'Report Method' in ticket]
    return {"report_methods": methods}

@app.get("/metrics/tickets-by-report-method")
async def tickets_by_report_method(authenticated: bool = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    report_counts = {}
    for ticket in custom_fields:
        rm = ticket.get("Report Method")
        if rm:
            report_counts[rm] = report_counts.get(rm, 0) + 1
    return {"tickets_by_report_method": report_counts}

@app.get("/metrics/service-type")
async def service_type(authenticated: bool = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    service_types = [ticket.get('Service Type') for ticket in custom_fields if 'Service Type' in ticket]
    return {"service_types": service_types}

@app.get("/metrics/tickets-by-service-type")
async def tickets_by_service_type(authenticated: bool = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    st_counts = {}
    for ticket in custom_fields:
        st = ticket.get("Service Type")
        if st:
            st_counts[st] = st_counts.get(st, 0) + 1
    return {"tickets_by_service_type": st_counts}

@app.get("/metrics/category")
async def category(authenticated: bool = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    categories = [ticket.get('Category') for ticket in custom_fields if 'Category' in ticket]
    return {"categories": categories}

@app.get("/metrics/tickets-by-category")
async def tickets_by_category(authenticated: bool = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    cat_counts = {}
    for ticket in custom_fields:
        cat = ticket.get("Category")
        if cat:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
    return {"tickets_by_category": cat_counts}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)