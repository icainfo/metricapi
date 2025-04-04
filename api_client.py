import os
import time
import requests
import random
import toml
from datetime import datetime

# Try to load configuration from config.toml if available.
try:
    config_data = toml.load("./config.toml")
except Exception:
    config_data = {}

def get_config_value(key):
    return os.getenv(key.upper()) or config_data.get("keys", {}).get(key)

class HelpScoutAPIClient:
    def __init__(self):
        self.hs_url = "https://api.helpscout.net/v2"
        self.id = get_config_value("CLIENT_ID")
        self.secret = get_config_value("CLIENT_SECRET")
        if not self.id or not self.secret:
            raise ValueError("API keys not found. Set environment variables or update config.toml.")
        self.token = self.get_access_token()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def get_access_token(self):
        url = "https://api.helpscout.net/v2/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.id,
            "client_secret": self.secret
        }
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()['access_token']

    def get(self, endpoint, params=None, retries=5):
        url = f"{self.hs_url}/{endpoint}"
        attempt = 0
        while attempt < retries:
            try:
                response = requests.get(url, headers=self.headers, params=params)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))  # Default to 60 seconds
                    print(f"Rate limit hit. Retrying after {retry_after} seconds...")
                    time.sleep(retry_after)
                    attempt += 1
                else:
                    response.raise_for_status()  # Raise an error for other 4xx/5xx status codes
                    print("API Response:", response.json())  # Log the API response
                    return response.json()
            except requests.exceptions.RequestException as e:
                print(f"Request Error: {e}")
                return None
            # Exponential backoff if 429 error
            if response.status_code == 429:
                backoff_time = (2 ** attempt) + random.uniform(0, 1)  # Exponential backoff
                print(f"Retrying in {backoff_time:.2f} seconds")
                time.sleep(backoff_time)
                attempt += 1
        print("Exceeded retry attempts")
        return None
