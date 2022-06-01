import datetime
from dataclasses import dataclass
from typing import List, Optional
from marshmallow import schema, fields
import requests



# missing is used to give default values when deserializing whereas default is for serialization.
# default values for object creation are done like usual with the "=" sign.
#  TODO: implement schema for deserializing Assets from opensea.

@dataclass
class AssetObj:
    owner: fields.String()
    traits: fields.Dict()
    value: fields.Integer(missing=10, default=10) = 10
    created_at_date: fields.DateTime() = datetime.datetime.now()

    def print_all(self):
        print(self.owner, self.traits)

