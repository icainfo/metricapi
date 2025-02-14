from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from api_client import HelpScoutAPIClient
import numpy as np

class HelpScoutHelper:
    def __init__(self, api_client):
        self.api_client = api_client

    def get_closed_tickets(self):
        page = 1
        all_tickets = []

        while True:
            response = self.api_client.get("conversations", params={"status": "closed", "page": page})
            if not response or "_embedded" not in response:
                break

            all_tickets.extend(response["_embedded"]["conversations"])

            if "next" not in response.get("_links", {}):
                break

            page += 1

        return all_tickets

    def get_all_tickets(self):
        page = 1
        all_tickets = []

        while True:
            response = self.api_client.get("conversations", params={"status": "all", "page": page})
            if not response or "_embedded" not in response:
                break

            all_tickets.extend(response["_embedded"]["conversations"])

            if "next" not in response.get("_links", {}):
                break

            page += 1

        return all_tickets

    def get_ticket_start_time(self, ticket):
        return ticket.get("createdAt")

    def get_ticket_close_time(self, ticket):
        return ticket.get("closedAt")

    def calculate_ticket_duration(self, ticket):
        try:
            start_time_str = self.get_ticket_start_time(ticket)
            close_time_str = self.get_ticket_close_time(ticket)

            if start_time_str and close_time_str:
                start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
                duration = close_time - start_time
                return ticket["id"], duration.total_seconds()
            else:
                return ticket["id"], None
        except Exception as e:
            print(f"Error processing ticket {ticket['id']}: {e}")
            return ticket["id"], None

    def get_tickets_duration_times(self):
        closed_tickets = self.get_closed_tickets()
        durations = {}

        if not closed_tickets:
            return durations

        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(self.calculate_ticket_duration, ticket) for ticket in closed_tickets]

            for future in as_completed(futures):
                ticket_id, duration = future.result()
                if duration is not None:
                    durations[ticket_id] = duration

        return durations

    def filter_outliers(self, durations):
        durations_array = np.array(list(durations.values()))
        q1 = np.percentile(durations_array, 25)
        q3 = np.percentile(durations_array, 75)
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        filtered_durations = {k: v for k, v in durations.items() if lower_bound <= v <= upper_bound}
        return filtered_durations

    def extract_custom_fields(self, tickets):
        """Extract and organize custom fields from tickets."""
        custom_fields_data = []

        for ticket in tickets:
            ticket_id = ticket.get("id")
            custom_fields = ticket.get("customFields", [])
            organized_fields = {field["name"]: field["text"] for field in custom_fields}
            custom_fields_data.append({"ticket_id": ticket_id, **organized_fields})

        return custom_fields_data
    
    def get_departments(self, fields_data):
        return [ticket.get('Department') for ticket in fields_data if 'Department' in ticket]


    def get_locations(self, fields_data):
        return [ticket.get('Location') for ticket in fields_data if 'Location' in ticket]
    
    def get_reportMethod(self, fields_data):
        return [ticket.get('Report Method') for ticket in fields_data if 'Report Method' in ticket]
    
    def get_serviceType(self, fields_data):
        return [ticket.get('Service Type') for ticket in fields_data if 'Service Type' in ticket]
    
    def get_category(self, fields_data):
        return [ticket.get('Category') for ticket in fields_data if 'Category' in ticket]

if __name__ == "__main__":
    client = HelpScoutAPIClient()
    helper = HelpScoutHelper(client)

    try:
        # Example: Extract custom fields
        all_tickets = helper.get_all_tickets()
        print(all_tickets)

        # Example: Calculate and filter ticket durations
        # ticket_durations = helper.get_tickets_duration_times()
        # if ticket_durations:
        #     filtered_durations = helper.filter_outliers(ticket_durations)

        #     if filtered_durations:
        #         total_time = sum(filtered_durations.values())
        #         average_duration_minutes = total_time / len(filtered_durations) / 60
        #         print("\nAverage Duration (in minutes, excluding outliers):", average_duration_minutes)
        #         print("Average Duration (in hours, excluding outliers):", average_duration_minutes / 60)
        # else:
        #     print("No closed tickets found.")
        print('test')
    except Exception as e:
        print(f"An error occurred: {e}")
