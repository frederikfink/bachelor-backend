from __future__ import annotations
import math
from sqlalchemy import Column, \
    Integer, Boolean, VARCHAR, \
    DateTime, ForeignKey, select, func, update, exists, delete
from Models import Base, Session, Utils
from rich.traceback import install
from Entities import Statistics

install()
utils = Utils.Utils
collectionStats = Statistics.CollectionStatistics
tokenStats = Statistics.TokenStatistics

class Transfer(Base):
    __tablename__       = 'Transfers'
    contract_address    = Column(VARCHAR(length=42), ForeignKey('Collections.contract_address'), nullable=False)
    tx                  = Column(VARCHAR(length=66), primary_key=True)
    log_index           = Column(Integer, primary_key=True)
    from_address        = Column(VARCHAR(length=42), nullable=False)
    to_address          = Column(VARCHAR(length=42), nullable=False)
    token_id            = Column(Integer, nullable=False)
    block               = Column(Integer, nullable=False)

    def __repr__(self):
        return """
                    from : %s
                    to : %s
                    token_id : %s
                    """ % (self.from_address, self.to_address, self.token_id)

    def to_dict(self):
        return {
            str(Transfer.contract_address): self.contract_address,
            str(Transfer.tx): self.tx,
            str(Transfer.log_index): self.log_index,
            str(Transfer.from_address): self.from_address,
            str(Transfer.to_address): self.to_address,
            str(Transfer.token_id): self.token_id,
            str(Transfer.block): self.block
        }

    '''
    function that checks if a transfer already exists in the database. If it does, it returns True and the Transfer in 
    question.
    '''
    @staticmethod
    def check_transfer_exists(db_session: Session, tx_hash: str, log_index: int):
        try:
            stmnt = select(Transfer).where(Transfer.tx == tx_hash, Transfer.log_index == log_index)
            rows = db_session.execute(stmnt).first()
            length = len(rows)
            return length > 0, rows[0]
        except:
            return False, None

    '''
    function that adds a list of transfers to the database, if they do not already exist in it. Returns the number of 
    successful additions to the database.
    '''
    @staticmethod
    def add_transfer_list_to_db(db_session: Session, transfer_list: list, collection_exists: bool = False):
        if len(transfer_list) == 0:
            return 0
        assert type(transfer_list[0]) == Transfer
        successful_additions = 0
        for t in transfer_list:
            try:

                if collection_exists:
                    (transfer_exists, value) = Transfer.\
                        check_transfer_exists(db_session=db_session, tx_hash=t.tx, log_index=t.log_index)

                    if transfer_exists:
                        continue
                db_session.add(t)
                successful_additions += 1
            except Exception as e:
                db_session.rollback()
                print(f"could not add {t.tx}")
        db_session.commit()
        return successful_additions

    '''
    function that retrieves transfers that are connected to a collection by the contract_address.
    '''
    @staticmethod
    def get_ordered_transfers_from_collection(*, db_session: Session, contract_address: str):
        transfers_stmnt = select(Transfer) \
            .where(Transfer.contract_address == contract_address) \
            .order_by(Transfer.token_id.asc()) \
            .order_by(Transfer.block.asc())

        transfer_rows = db_session.execute(transfers_stmnt).all()

        return transfer_rows





