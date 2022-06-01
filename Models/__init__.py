from dotenv import load_dotenv
import os
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, MetaData
from sqlalchemy_utils import create_database, database_exists


load_dotenv()

entities = ["slugs", "collections", "transfers"]

# if the database does not exist, we create it and let the database model know that the tables must also be created.
# apparently, if can create the tables no matter where the db mappings are located?
engine = create_engine(os.getenv("connection_string"))
Base = declarative_base()
Session = sessionmaker(bind=engine, future=True)
metadata_obj = MetaData()

db_already_exists = database_exists(engine.url)
if not db_already_exists:
    create_database(engine.url)
tables_exist = len(engine.table_names()) == len(entities)

EVENT_SIGNATURE_HASH = ["0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"]
CONTRACT_NAME_ABI = """
[
    {
        "inputs": [

        ],
        "name":"name",
        "outputs": [
            {
                "internalType":"string",
                "name":"",
                "type":"string"
            }
        ],
        "type":"function"
    }
]
"""
