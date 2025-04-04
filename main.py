import os
import time
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from api_client import HelpScoutAPIClient

app = FastAPI(title="ICA IT Metrics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://metricdb.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache to store ticket and metric data
ticket_cache = {
    "all_tickets": [],
    "closed_tickets": [],
    "ticket_durations": {},
    "custom_fields": [],
    "last_updated": None
}

CACHE_DURATION = timedelta(minutes=10)
client = HelpScoutAPIClient()

async def verify_api_key(x_api_key: str = Header(...)):
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    if x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return x_api_key

def fetch_all_conversations(status):
    all_convos = []
    page = 1
    while True:
        resp = client.get("conversations", params={"status": status, "page": page})
        if not resp:
            break
        convos = resp.get("_embedded", {}).get("conversations", [])
        all_convos.extend(convos)
        if "next" not in resp.get("_links", {}):
            break
        page += 1
        time.sleep(0.25)
    return all_convos

def refresh_cache():
    global ticket_cache
    try:
        all_tickets = fetch_all_conversations("all")
        closed_tickets = fetch_all_conversations("closed")

        durations = {}
        for ticket in closed_tickets:
            created = ticket.get("createdAt")
            closed = ticket.get("closedAt")
            if created and closed:
                duration = (
                    datetime.fromisoformat(closed.replace("Z", "+00:00")) -
                    datetime.fromisoformat(created.replace("Z", "+00:00"))
                ).total_seconds()
                durations[ticket["id"]] = duration

        def extract_fields(ticket):
            fields = {"ticket_id": ticket.get("id")}
            for field in ticket.get("customFields", []):
                fields[field.get("name")] = field.get("text")
            return fields

        custom_fields = [extract_fields(ticket) for ticket in all_tickets if ticket.get("customFields")]

        ticket_cache.update({
            "all_tickets": all_tickets,
            "closed_tickets": closed_tickets,
            "ticket_durations": durations,
            "custom_fields": custom_fields,
            "last_updated": datetime.utcnow()
        })

        print(f"✅ Cache refreshed at {ticket_cache['last_updated']}")
        print(f"✅ Custom Fields: {custom_fields[:3]}")

    except Exception as e:
        print(f"❌ Error refreshing cache: {e}")

async def background_cache_updater():
    while True:
        await run_in_threadpool(refresh_cache)
        await asyncio.sleep(CACHE_DURATION.total_seconds())

@app.on_event("startup")
async def startup_event():
    await run_in_threadpool(refresh_cache)
    asyncio.create_task(background_cache_updater())

@app.get("/metrics/average-ticket-duration")
async def average_ticket_duration(api_key: str = Depends(verify_api_key)):
    durations = list(ticket_cache.get("ticket_durations", {}).values())
    if not durations:
        return {"average_ticket_duration": 0}

    # Remove top 5% extreme durations
    durations.sort()
    cutoff = int(len(durations) * 0.95)
    filtered = durations[:cutoff] if cutoff > 0 else durations

    avg = sum(filtered) / len(filtered) if filtered else 0
    return {"average_ticket_duration": avg}

@app.get("/metrics/tickets-by-category")
async def tickets_by_category(api_key: str = Depends(verify_api_key)):
    result = {}
    for item in ticket_cache["custom_fields"]:
        key = item.get("Category")
        if key:
            result[key] = result.get(key, 0) + 1
    return {"tickets_by_category": result}

@app.get("/metrics/tickets-by-report-method")
async def tickets_by_report_method(api_key: str = Depends(verify_api_key)):
    result = {}
    for item in ticket_cache["custom_fields"]:
        key = item.get("Report Method")
        if key:
            result[key] = result.get(key, 0) + 1
    return {"tickets_by_report_method": result}

@app.get("/metrics/tickets-by-service-type")
async def tickets_by_service_type(api_key: str = Depends(verify_api_key)):
    result = {}
    for item in ticket_cache["custom_fields"]:
        key = item.get("Service Type")
        if key:
            result[key] = result.get(key, 0) + 1
    return {"tickets_by_service_type": result}

@app.get("/metrics/tickets-by-location")
async def tickets_by_location(api_key: str = Depends(verify_api_key)):
    result = {}
    for item in ticket_cache["custom_fields"]:
        key = item.get("Location")
        if key:
            result[key] = result.get(key, 0) + 1
    return {"tickets_by_location": result}

@app.get("/metrics/tickets-by-department")
async def tickets_by_department(api_key: str = Depends(verify_api_key)):
    result = {}
    for item in ticket_cache["custom_fields"]:
        key = item.get("Department")
        if key:
            result[key] = result.get(key, 0) + 1
    return {"tickets_by_department": result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
