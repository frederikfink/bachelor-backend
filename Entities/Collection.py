from __future__ import annotations
from sqlalchemy import Column, \
    Integer, Boolean, VARCHAR, \
    DateTime, ForeignKey, select, func, update, exists, delete, Float
from datetime import datetime
from Models import Base, Session
from Entities import Statistics
from rich.traceback import install


install()

'''
Class which represent a collection in our database. Inherits from the sqlAlchemy declarative base so that it can be 
mapped easily from the database to our class.
'''
class Collection(Base):
    __tablename__       = 'Collections'
    contract_address    = Column(VARCHAR(length=42), nullable=False, primary_key=True)
    name                = Column(VARCHAR(length=255), nullable=False)
    last_update         = Column(DateTime, default=datetime.now(), nullable=False)
    start_block         = Column(Integer, nullable=False)
    latest_block        = Column(Integer, nullable=True)
    cycle_average       = Column(Float, nullable=True, default=0)
    cycle_std           = Column(Float, nullable=True, default=0)
    block_diff_average  = Column(Float, nullable=True, default=0)
    block_diff_std      = Column(Float, nullable=True, default=0)

    def to_dict(self):
        return {
            "contract_address": self.contract_address,
            "name": self.name,
            "last_update": self.last_update,
            "start_block": self.start_block,
            "latest_block": self.latest_block,
            "cycle_average": self.cycle_average,
            "cycle_std": self.cycle_std,
            "block_diff_average": self.block_diff_average,
            "block_diff_std": self.block_diff_std
        }

    '''
    function that adds a collection to the database.
    '''
    @staticmethod
    def add_collection_to_db(db_session: Session, collection):
        assert collection is not None
        assert db_session is not None
        db_session.add(collection)
        db_session.commit()


    '''
    function that retrieves all collections in the database.
    '''
    @staticmethod
    def get_all_collections(db_session: Session):
        stmnt = select(Collection)

        rows = db_session.execute(stmnt).all()
        return rows

    '''
    function used to update the latest block attribute of a collection, so that a scan can start from that block instead
    of starting over completely.
    '''
    @staticmethod
    def set_collection_latest_block(db_session: Session, contract_address: str, block_number: int):
        stmnt = update(Collection).where(Collection.contract_address == contract_address).\
            values(latest_block=block_number, last_update=datetime.now())
        db_session.execute(stmnt)
        db_session.commit()
        return True

    '''
    function used to set the statistics attributes for a collection in the database.
    '''
    @staticmethod
    def set_collection_statistics(db_session: Session,
                                  collection,
                                  block_stats: Statistics.CollectionStatistics,
                                  cycle_stats: Statistics.TokenCycleStatistic):

        try:
            if block_stats.avg != 0 and cycle_stats.avg != 0:
                print("creating statement and executing it.")
                stmnt = update(Collection).where(Collection.contract_address == collection.contract_address)\
                        .values(block_diff_average=block_stats.avg,
                                block_diff_std=block_stats.std_deviation,
                                cycle_std=cycle_stats.std_deviation,
                                cycle_average=cycle_stats.avg)

                db_session.execute(stmnt)
                print("executed update statement")
                db_session.commit()
                print("changes were committed to the database")
                return True
        except Exception as e:
            print(e)
            return False


    '''
    Retrieves a collection from the database as a Collection object.
    '''
    @staticmethod
    def get_collection(*args, db_session: Session, contract_address: str = None) -> Collection:
        try:
            stmnt = select(Collection).where(Collection.contract_address == contract_address)
            rows = db_session.execute(stmnt).first()[0]
            return rows
        except Exception as e:
            print(e)
            print("did not find anything")
        return None

    '''
    returns the latest block for a collection if it exists. If it doesnt, it will return the start block.
    '''
    @staticmethod
    def get_collection_latest_block(db_session: Session, contract_address: str):
        try:
            stmnt = select(Collection.latest_block, Collection.start_block).where(Collection.contract_address == contract_address)
            coll = db_session.execute(stmnt).first()
            if coll['latest_block'] is not None:
                return coll['latest_block']
            else:
                return coll['start_block']
        except Exception as e:
            print(e)
            print("could not get latest_block")
            return -1

    '''
    function used to see if a collection already exists in the database. returns True and the collection in question if 
    they exist.
    '''
    @staticmethod
    def collection_exists(db_session: Session, contract_address: str) -> (bool, Collection):
        try:
            stmnt = select(Collection).where(Collection.contract_address == contract_address)
            rows = db_session.execute(stmnt).first()
            length = len(rows)
            return length > 0, rows[0]
        except:
            return False, None
