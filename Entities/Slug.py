from __future__ import annotations
from sqlalchemy import Column, \
    Integer, Boolean, VARCHAR, \
    DateTime, ForeignKey, select, \
    func, update, exists, delete
from Models import Base, Session

class Slug(Base):
    __tablename__       = 'Slugs'
    contract_address    = Column(VARCHAR(length=42), primary_key=True, nullable=False)
    start_block         = Column(Integer, nullable=False)
    slug                = Column(VARCHAR(length=255), nullable=False)

    def __repr__(self):
        return f'contract_address: {self.contract_address}\n' \
               f'slug: {self.slug}\n' \
               f'start_block: {self.start_block}'

    def to_dict(self):
        return {
            str(Slug.contract_address): self.contract_address,
            str(Slug.start_block): self.start_block,
            str(Slug.slug): self.slug
        }

    @staticmethod
    def add_slug_to_db(db_session: Session, slug, validator: bool = False):
        assert slug is not None
        assert db_session is not None
        try:
            if validator:
                if Slug.slug_exists(db_session, slug):
                    raise Exception("duplicate entry. Slug already exists in the database.")

            db_session.add(slug)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            print(e)

    @staticmethod
    def list_all_slugs(db_session: Session, verbose: bool = False) -> list:
        assert db_session is not None
        stmnt = select(Slug)
        lst_rows = db_session.execute(stmnt).all()
        # getting the index [0] gives us a slug object instead of a row object.
        lst_slugs = [x[0] for x in lst_rows]
        if verbose:
            for s in lst_slugs:
                print(s)
        return lst_slugs

    @staticmethod
    def list_slugs_with_offset(db_session: Session, nr_to_offset: int):
        assert db_session is not None
        stmnt = select(Slug).offset(nr_to_offset)
        rows = db_session.execute(stmnt).all()
        return [x[0] for x in rows]


    @staticmethod
    def slug_exists(db_session: Session, slug: str):
        try:
            stmnt = select(Slug).where(Slug.slug == slug)
            rows = db_session.execute(stmnt).first()
            length = len(rows)
            return length > 0, rows[0]  # len has to be saved as a var, otherwise
        except:
            return False, None

    @staticmethod
    def is_empty(db_session: Session):
        try:
            length = len(Slug.list_all_slugs(db_session))
            return length < 1
        except:
            return False;

