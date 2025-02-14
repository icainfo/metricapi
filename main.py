from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from functions import HelpScoutHelper  # Adjust the import paths if needed
from api_client import HelpScoutAPIClient

app = FastAPI(title="HelpScout Metrics API")

# Initialize your API client and helper once at startup.
client = HelpScoutAPIClient()
helper = HelpScoutHelper(client)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for production, you might want to specify only your frontend URL here)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

@app.get("/metrics/closed-tickets")
async def closed_tickets():
    """
    Returns all closed tickets along with a count.
    """
    try:
        tickets = helper.get_closed_tickets()
        return {"closed_tickets": tickets, "count": len(tickets)}
    except Exception as e:
        return {"error": str(e)}

@app.get("/metrics/all-tickets")
async def all_tickets():
    """
    Returns all tickets (regardless of status) along with a count.
    """
    try:
        tickets = helper.get_all_tickets()
        return {"all_tickets": tickets, "count": len(tickets)}
    except Exception as e:
        return {"error": str(e)}

@app.get("/metrics/average-ticket-duration")
async def average_ticket_duration():
    """
    Returns the average duration (in seconds) for closed tickets,
    using the calculated durations with outliers filtered out.
    """
    try:
        durations = helper.get_tickets_duration_times()
        filtered = helper.filter_outliers(durations)
        if filtered:
            avg_duration = sum(filtered.values()) / len(filtered)
        else:
            avg_duration = 0
        return {"average_ticket_duration": avg_duration}
    except Exception as e:
        return {"error": str(e)}

@app.get("/metrics/tickets-duration-times")
async def tickets_duration_times():
    """
    Returns raw ticket durations (in seconds) for each closed ticket.
    """
    try:
        durations = helper.get_tickets_duration_times()
        return {"ticket_durations": durations}
    except Exception as e:
        return {"error": str(e)}

@app.get("/metrics/custom-fields")
async def custom_fields():
    """
    Returns the custom fields extracted from all tickets.
    """
    try:
        tickets = helper.get_all_tickets()
        custom_fields_data = helper.extract_custom_fields(tickets)
        return {"custom_fields": custom_fields_data}
    except Exception as e:
        return {"error": str(e)}

@app.get("/metrics/tickets-by-department")
async def tickets_by_department():
    """
    Returns a breakdown (count) of tickets by department.
    """
    try:
        tickets = helper.get_all_tickets()
        custom_fields = helper.extract_custom_fields(tickets)
        # Build count per department
        dept_counts = {}
        for ticket in custom_fields:
            dept = ticket.get("Department")
            if dept:
                dept_counts[dept] = dept_counts.get(dept, 0) + 1
        return {"tickets_by_department": dept_counts}
    except Exception as e:
        return {"error": str(e)}

@app.get("/metrics/departments")
async def departments():
    """
    Returns an array of departments extracted from the custom fields.
    """
    try:
        tickets = helper.get_all_tickets()
        custom_fields = helper.extract_custom_fields(tickets)
        depts = helper.get_departments(custom_fields)
        return {"departments": depts}
    except Exception as e:
        return {"error": str(e)}

@app.get("/metrics/tickets-by-location")
async def tickets_by_location():
    """
    Returns a breakdown (count) of tickets by location.
    """
    try:
        tickets = helper.get_all_tickets()
        custom_fields = helper.extract_custom_fields(tickets)
        location_counts = {}
        for ticket in custom_fields:
            loc = ticket.get("Location")
            if loc:
                location_counts[loc] = location_counts.get(loc, 0) + 1
        return {"tickets_by_location": location_counts}
    except Exception as e:
        return {"error": str(e)}

@app.get("/metrics/locations")
async def locations():
    """
    Returns an array of locations extracted from the custom fields.
    """
    try:
        tickets = helper.get_all_tickets()
        custom_fields = helper.extract_custom_fields(tickets)
        locs = helper.get_locations(custom_fields)
        return {"locations": locs}
    except Exception as e:
        return {"error": str(e)}

@app.get("/metrics/report-method")
async def report_method():
    """
    Returns an array of report methods extracted from the custom fields.
    """
    try:
        tickets = helper.get_all_tickets()
        custom_fields = helper.extract_custom_fields(tickets)
        methods = helper.get_reportMethod(custom_fields)
        return {"report_methods": methods}
    except Exception as e:
        return {"error": str(e)}

@app.get("/metrics/tickets-by-report-method")
async def tickets_by_report_method():
    """
    Returns a breakdown (count) of tickets by report method.
    """
    try:
        tickets = helper.get_all_tickets()
        custom_fields = helper.extract_custom_fields(tickets)
        report_counts = {}
        for ticket in custom_fields:
            rm = ticket.get("Report Method")
            if rm:
                report_counts[rm] = report_counts.get(rm, 0) + 1
        return {"tickets_by_report_method": report_counts}
    except Exception as e:
        return {"error": str(e)}

@app.get("/metrics/service-type")
async def service_type():
    """
    Returns an array of service types extracted from the custom fields.
    """
    try:
        tickets = helper.get_all_tickets()
        custom_fields = helper.extract_custom_fields(tickets)
        service_types = helper.get_serviceType(custom_fields)
        return {"service_types": service_types}
    except Exception as e:
        return {"error": str(e)}

@app.get("/metrics/tickets-by-service-type")
async def tickets_by_service_type():
    """
    Returns a breakdown (count) of tickets by service type.
    """
    try:
        tickets = helper.get_all_tickets()
        custom_fields = helper.extract_custom_fields(tickets)
        st_counts = {}
        for ticket in custom_fields:
            st = ticket.get("Service Type")
            if st:
                st_counts[st] = st_counts.get(st, 0) + 1
        return {"tickets_by_service_type": st_counts}
    except Exception as e:
        return {"error": str(e)}

@app.get("/metrics/category")
async def category():
    """
    Returns an array of categories extracted from the custom fields.
    """
    try:
        tickets = helper.get_all_tickets()
        custom_fields = helper.extract_custom_fields(tickets)
        categories = helper.get_category(custom_fields)
        return {"categories": categories}
    except Exception as e:
        return {"error": str(e)}

@app.get("/metrics/tickets-by-category")
async def tickets_by_category():
    """
    Returns a breakdown (count) of tickets by category.
    """
    try:
        tickets = helper.get_all_tickets()
        custom_fields = helper.extract_custom_fields(tickets)
        cat_counts = {}
        for ticket in custom_fields:
            cat = ticket.get("Category")
            if cat:
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
        return {"tickets_by_category": cat_counts}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
