import os
import time
import asyncio
from datetime import datetime, timedelta
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from api_client import HelpScoutAPIClient

app = FastAPI(title="HelpScout Metrics API")

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

async def verify_api_key(x_api_key: str = Header(...)):
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        raise HTTPException(status_code=500, detail="API key not configured")
    if x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Unauthorized")
    return x_api_key

def refresh_cache():
    global ticket_cache
    try:
        all_resp = client.get("conversations", params={"status": "all"})
        closed_resp = client.get("conversations", params={"status": "closed"})

        all_tickets = all_resp.get("_embedded", {}).get("conversations", [])
        closed_tickets = closed_resp.get("_embedded", {}).get("conversations", [])

        ticket_durations = {}
        for ticket in closed_tickets:
            created = ticket.get("createdAt")
            closed = ticket.get("closedAt")
            if created and closed:
                duration = (
                    datetime.fromisoformat(closed.replace("Z", "+00:00")) -
                    datetime.fromisoformat(created.replace("Z", "+00:00"))
                ).total_seconds()
                ticket_durations[ticket["id"]] = duration

        def extract_fields(ticket):
            fields = {"ticket_id": ticket["id"]}
            for field in ticket.get("customFields", []):
                fields[field["name"]] = field.get("text")
            return fields

        custom_fields = [extract_fields(ticket) for ticket in all_tickets]

        ticket_cache.update({
            "all_tickets": all_tickets,
            "closed_tickets": closed_tickets,
            "ticket_durations": ticket_durations,
            "custom_fields": custom_fields,
            "last_updated": datetime.utcnow()
        })

        print(f"\u2705 Cache refreshed at {ticket_cache['last_updated']}")
        print(f"\u2705 Sample custom fields: {custom_fields[:3]}")

    except Exception as e:
        print(f"\u274C Error refreshing cache: {e}")

async def background_cache_updater():
    while True:
        try:
            await run_in_threadpool(refresh_cache)
        except Exception as e:
            print(f"\u274C Error refreshing cache: {e}")
        await asyncio.sleep(CACHE_DURATION.total_seconds())

@app.on_event("startup")
async def startup_event():
    await run_in_threadpool(refresh_cache)
    asyncio.create_task(background_cache_updater())

@app.get("/metrics/average-ticket-duration")
async def average_ticket_duration(api_key: str = Depends(verify_api_key)):
    durations = ticket_cache.get("ticket_durations", {})
    if not durations:
        return {"average_ticket_duration": 0}
    avg = sum(durations.values()) / len(durations)
    return {"average_ticket_duration": avg}

@app.get("/metrics/tickets-by-category")
async def tickets_by_category(api_key: str = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    cat_counts = {}
    for ticket in custom_fields:
        cat = ticket.get("Category")
        if cat:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
    return {"tickets_by_category": cat_counts}

@app.get("/metrics/tickets-by-report-method")
async def tickets_by_report_method(api_key: str = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    method_counts = {}
    for ticket in custom_fields:
        method = ticket.get("Report Method")
        if method:
            method_counts[method] = method_counts.get(method, 0) + 1
    return {"tickets_by_report_method": method_counts}

@app.get("/metrics/tickets-by-service-type")
async def tickets_by_service_type(api_key: str = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    service_counts = {}
    for ticket in custom_fields:
        svc = ticket.get("Service Type")
        if svc:
            service_counts[svc] = service_counts.get(svc, 0) + 1
    return {"tickets_by_service_type": service_counts}

@app.get("/metrics/tickets-by-location")
async def tickets_by_location(api_key: str = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    loc_counts = {}
    for ticket in custom_fields:
        loc = ticket.get("Location")
        if loc:
            loc_counts[loc] = loc_counts.get(loc, 0) + 1
    return {"tickets_by_location": loc_counts}

@app.get("/metrics/tickets-by-department")
async def tickets_by_department(api_key: str = Depends(verify_api_key)):
    custom_fields = ticket_cache.get("custom_fields", [])
    dept_counts = {}
    for ticket in custom_fields:
        dept = ticket.get("Department")
        if dept:
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
    return {"tickets_by_department": dept_counts}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
