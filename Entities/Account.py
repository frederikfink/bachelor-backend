import datetime as dt
from dataclasses import dataclass
from marshmallow import Schema, fields


#  TODO: implement schema for deserializing users from opensea.
class AccountSchema(Schema):
    name = fields.Str(missing="missing", default="default")
    email = fields.Email()
    created_at = fields.DateTime()


@dataclass
class Account:
    name: str
    email: str
    created_at: dt.datetime = dt.datetime.now()

    def __repr__(self):
        return "<User(name={self.name!r})>".format(self=self)


