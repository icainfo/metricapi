import requests
import toml

data = toml.load("./config.toml")

class HelpScoutAPIClient:

    def __init__(self):
        self.hs_url="https://api.helpscout.net/v2"
        self.id = data["keys"]['id']
        self.secret = data["keys"]["secret"]
        self.token = self.get_access_token()
        print(self.token)
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def get_access_token(self):
        url="https://api.helpscout.net/v2/oauth2/token"
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
            print(f"{e}")
            return None
