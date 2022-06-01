from __future__ import annotations
from dataclasses import dataclass
from Models import Base, Session, engine, tables_exist
from Entities import Collection, Transfer, Slug, Token
from sqlalchemy import Column, \
    Integer, Boolean, VARCHAR, \
    DateTime, ForeignKey, select, func, update, exists, delete, and_, tuple_, distinct, text

from rich.traceback import install
from rich.console import Console

cons = Console()
install()

# SCALARS are used for getting exactly one row or column.
# Entities need to inherit from declarative base class (mapping python class to db object).
# Any entity that inherits from the Base will be added to our database.
@dataclass
class DatabaseModel:

    def __init__(self):
        self.collections: Collection = Collection.Collection
        self.transfers: Transfer = Transfer.Transfer
        self.slugs: Slug = Slug.Slug
        self.tokens: Token = Token.Token
        if not len(engine.table_names()) == len(Base.__subclasses__()):
            self.create_tables()

    @staticmethod
    def start_session():
        return Session()

    @staticmethod
    def create_tables():
        Base.metadata.create_all(engine)
        return 1

    @staticmethod
    def create_column():
        Base.metadata

    @staticmethod
    def describe_tables():
        return -1

    @staticmethod
    def get_transfers_by_collection(*, db_session: Session, contract_address: str = None, collection_name: str = None) -> list:
        try:
            if contract_address is not None:
                stmnt = select(Transfer.Transfer).where(Transfer.Transfer.contract_address == contract_address)
            else:
                cons.print("not implemented yet tihi")
            rows = db_session.execute(stmnt).all()
            return rows
        except Exception as ex:
            print(ex)

    # when grouping the transfers by tx, we create a list of tokens to go along with it labelled as "tokens".
    @staticmethod
    def get_grouped_transfers(*, db_session: Session, contract_address: str = None):
        stmnt = select(
            Transfer.Transfer.from_address, 
            Transfer.Transfer.to_address,
            Transfer.Transfer.tx,
            Transfer.Transfer.block
        )\
            .where(Transfer.Transfer.contract_address == contract_address)\

        rows = db_session.execute(stmnt).all()
        return rows

    def get_collection_status_name(*, db_session: Session, contract_address):
        stmnt = select(
            func.min('block'),
            func.count('tx')
        )\
            .where(Transfer.Transfer.contract_address == contract_address)

        rows = db_session.execute(stmnt).all()
        return rows

    @staticmethod
    def get_token_transfers(*, db_session: Session, contract_address: str, token_id: int):
        stmnt = select(
            Transfer.Transfer.tx,
            Transfer.Transfer.block,
            Transfer.Transfer.from_address, 
            Transfer.Transfer.to_address,
        )\
            .where(Transfer.Transfer.contract_address == contract_address)\
            .where(Transfer.Transfer.token_id == token_id)\

        rows = db_session.execute(stmnt).all()
        return rows

    @staticmethod
    def get_contract_token_transfers(*, db_session: Session, contract_address: str):
        stmnt = select(
            Transfer.Transfer.token_id,
            func.count('*'),
            func.count(distinct(text('from_address', 'to_address'))).label('unique_addresses')
        )\
            .where(Transfer.Transfer.contract_address == contract_address)\
            .group_by(Transfer.Transfer.token_id)\
            .order_by(func.count('*').desc())\
            .limit(100)

        rows = db_session.execute(stmnt).all()
        return rows

    @staticmethod
    def get_token_outliers_from_collection(*, db_session: Session, contract_address: str):
        collection = Collection.Collection.get_collection(db_session=db_session, contract_address=contract_address)

        tokens = Token.Token.get_tokens_in_collection(db_session=db_session, contract_address=contract_address)

        outlier_tokens = []
        for token in tokens:
            if token.block_diff_average > collection.block_diff_std:
                print(token.block_diff_average, token.token_id)
        return outlier_tokens



    @staticmethod
    def group_to_dict(group):
        return {
            "tx" : group.tx,
            "to": group.to_address,
            "from": group.from_address,
            "tokens": group.tokens.split(",")
        }




