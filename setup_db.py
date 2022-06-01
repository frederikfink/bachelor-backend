from dotenv import load_dotenv
import os
from Models import DatabaseModel, GraphService, TransferScanner, CollectionService, ApiView
from rich.traceback import install

install()

load_dotenv()
infura_url = os.getenv("INFURA_URL")


if __name__ == '__main__':
    db = DatabaseModel.DatabaseModel()
    graphs = GraphService.GraphService(db=db)
    col_service = CollectionService.CollectionService()
    scanner = TransferScanner.TransferScanner(infura_url, log_mode=True, db=db)