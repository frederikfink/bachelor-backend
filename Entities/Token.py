from __future__ import annotations
from sqlalchemy import Column, \
    Integer, Boolean, VARCHAR, \
    DateTime, ForeignKey, select, func, update, exists, delete, Float
from Models import Base, Session, Utils
from rich.traceback import install
from Entities import Statistics

install()
utils = Utils.Utils
collectionStats = Statistics.CollectionStatistics
tokenStats = Statistics.TokenStatistics

'''
Object which represent "Tokens" from the blockchain in our database. It uses SqlAlchemy to easily map objects to 
entities in the database.
'''
class Token(Base):
    __tablename__       = 'Tokens'
    contract_address    = Column(VARCHAR(length=42), ForeignKey('Collections.contract_address')
                                 , primary_key=True, nullable=False)
    token_id            = Column(Integer, nullable=False, primary_key=True)
    cycle_count         = Column(Float, nullable=True, default=0)
    block_diff_average  = Column(Float, nullable=True, default=0)
    block_diff_std      = Column(Float, nullable=True, default=0)
    transfer_count      = Column(Integer, nullable=True, default=0)

    def __repr__(self):
        return """
                    contract_address : %s
                    token_id : %s
                    block_diff_average: %s
                    transfer_count: %s
                    """ % (self.contract_address, self.token_id, self.block_diff_average, self.transfer_count)

    '''
    function to represent the Token as a database. Can be useful when converting object to json format.
    '''
    def to_dict(self):
        return {
            "contract_address": self.contract_address,
            "token_id": self.token_id,
            "cycle_count": self.cycle_count,
            "block_diff_average": self.block_diff_average,
            "block_diff_std": self.block_diff_std,
            "transfer_count": self.transfer_count
        }


    '''
    function to retrieve a single token given a contract address and a token id.
    '''
    @staticmethod
    def get_token(*, db_session: Session, contract_address:str, token_id: int) -> Token:
        stmnt = select(Token)\
            .where(Token.contract_address == contract_address)\
            .where(Token.token_id == token_id)

        token = db_session.execute(stmnt).first()
        return token

    @staticmethod
    def get_tokens_in_collection(*, db_session: Session, contract_address: str) -> list[Token]:
        stmnt = select(Token).where(Token.contract_address == contract_address).limit(100).order_by(Token.transfer_count.desc())

        tokens = [x[0] for x in db_session.execute(stmnt).all()]
        return tokens

    '''
    function to determine whether a token already exists in the database. If it does, it returns True and the token.
    '''
    @staticmethod
    def token_exists(*, db_session: Session, contract_address: str, token_id: int):
        stmnt = select(Token)\
            .where(Token.contract_address == contract_address)\
            .where(Token.token_id == token_id)

        token = db_session.execute(stmnt).first()
        if token is None:
            return False, token
        length = len(token)
        return length > 0, token

    '''
    adds a token to the database if it does not have a block_diff_average of 0.
    '''
    @staticmethod
    def add_token(*, db_session: Session, token):
        (token_exists, _) = Token.token_exists(db_session=db_session, contract_address=token.contract_address, token_id=token.token_id)

        if not token_exists and token.block_diff_average > 0:
            db_session.add(token)
            db_session.commit()
            return True
        return False

