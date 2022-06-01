import datetime as dt
from dataclasses import dataclass
from marshmallow import Schema, fields, post_load

# mint_address is the origin address whenever a token is minted.
mint_address = "0x0000000000000000000000000000000000000000000000000000000000000000"
topic_names = ["function_hash", "from", "to", "token_id"]


# Class that represents the topics that are found in the event data fetched using INFURA
# Origin represents the "from" hash and destination represents the "to" hash.
# 'from' is a reserved name in python.
# attributes are IN ORDER and must not be changed to anything other than [function_hash, origin, destination, token_id]
@dataclass
class Topics:
    function_hash: str
    origin: str
    destination: str
    token_id: int

    # Used to generate iterable so that foreach can be used
    def __iter__(self):
        return iter(zip(topic_names, [self.function_hash, self.origin, self.destination, self.token_id]))

    # Used for the iterable.
    def __next__(self):
        self.current += 1
        if self.current < self.high:
            return self.current
        raise StopIteration

    def to_list(self):
        return [self.function_hash, self.origin, self.destination, self.token_id]

# Class that represents the events we fetch using INFURA. The fields are in order, and the deserialization WILL fail
# if the order is changed.
@dataclass
class Event:
    topics: Topics
    contract_address: str
    transaction_hash: str

    def __repr__(self):
        return "hash: " + self.transaction_hash + " | " \
               + "contract: " + self.contract_address + \
               "\n" + format_args(*self.topics)

    def get_topics(self):
        return self.topics.to_list()

# Scheme for (de)serialization of Event Data.
class EventSchema(Schema):
    contract_address = fields.Str(data_key="address")
    transaction_hash = fields.Str(data_key="transactionHash")

    # Method that is run after deserializing the fields stated above (trx and contract address).
    # This allows us to manipulate the json data as we see fit.
    # "original_data" is the data not automatically deserialized and "data" is the automatically serialized attributes.
    @post_load(pass_original=True)
    def make_events(self, data, original_data, **kwargs):
        topics = Topics(*original_data["topics"])
        return Event(topics, **data)




# formats the topic args for pretty printing.
def format_args(*args):
    string = ""
    for arg in args:
        string += str(arg) + "\n"
    return string
