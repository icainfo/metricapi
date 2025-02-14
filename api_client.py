import os
import requests
import toml

# Try to load the config file if it exists
try:
    config_data = toml.load("./config.toml")
except Exception:
    config_data = {}

def get_config_value(key):
    """
    Returns the configuration value for 'key'. It first checks for an environment variable,
    then falls back to the config file (under the "keys" section).
    """
    # Environment variable names are usually uppercase.
    return os.getenv(key.upper()) or config_data.get("keys", {}).get(key)

class HelpScoutAPIClient:
    def __init__(self):
        self.hs_url = "https://api.helpscout.net/v2"
        # Get keys from environment or config file
        self.id = get_config_value("id")
        self.secret = get_config_value("secret")
        if not self.id or not self.secret:
            raise ValueError("API keys not found. Set environment variables or update config.toml.")
        self.token = self.get_access_token()
        print(f"Access token: {self.token}")
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

    def get(self, endpoint, params=None):
        url = f"{self.hs_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return None
