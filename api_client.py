import os
import requests
import toml
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class HelpScoutAPIClient:
    def __init__(self):
        self.hs_url = "https://api.helpscout.net/v2"
        
        # Get credentials from environment variables (preferred method)
        self.id = os.getenv("HELPSCOUT_ID")
        self.secret = os.getenv("HELPSCOUT_SECRET")
        
        # Fall back to config file if environment variables not set
        if not self.id or not self.secret:
            try:
                config_path = os.getenv("CONFIG_PATH", "./config.toml")
                config_data = toml.load(config_path)
                self.id = config_data.get("keys", {}).get("id")
                self.secret = config_data.get("keys", {}).get("secret")
            except Exception as e:
                print(f"Warning: Failed to load config file: {e}")
        
        if not self.id or not self.secret:
            raise ValueError("HelpScout API credentials not found. Set HELPSCOUT_ID and HELPSCOUT_SECRET environment variables or update config.toml")
            
        # Get authentication token
        self.token = self.get_access_token()
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def get_access_token(self):
        """Get HelpScout OAuth token using client credentials"""
        url = "https://api.helpscout.net/v2/oauth2/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.id,
            "client_secret": self.secret
        }
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            return response.json()['access_token']
        except requests.exceptions.RequestException as e:
            print(f"Authentication error: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise ValueError("Failed to authenticate with HelpScout API")
    
    def get(self, endpoint, params=None):
        """Make a GET request to the HelpScout API"""
        url = f"{self.hs_url}/{endpoint}"
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            return None