import datetime
from dataclasses import dataclass
from typing import List, Optional
from marshmallow import schema, fields
import requests

@dataclass
class EventsClient:
    api_key: str
    header: dict

    def get_assets(self, url, owner):
        query = url + "owner=" + owner
        res = requests.request("GET", query, headers=self.header)
        return res.content
