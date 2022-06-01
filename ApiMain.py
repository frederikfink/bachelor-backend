from dotenv import load_dotenv
import os
from Models import DatabaseModel, GraphService, TransferScanner, \
    CollectionService, ApiView, OpenSeaScraper, StatisticsService
from rich.traceback import install

install()
load_dotenv()

infura_url = os.getenv("INFURA_URL")
etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")

def instantiate_main_objects():
    db = DatabaseModel.DatabaseModel()
    col_service = CollectionService.CollectionService()
    graphs = GraphService.GraphService(db=db)
    stats_service = StatisticsService.StatisticsService(db=db, graph_service=graphs)
    scanner = TransferScanner.TransferScanner(infura_url, log_mode=True, db=db, collection_service=col_service)
    scraper = OpenSeaScraper.OpenSeaScraper(db=db, etherscan_api_key=etherscan_api_key)
    return db, graphs, col_service, scanner, scraper, stats_service

def api_main():
    (db, graphs, col_service, scanner, scraper, stats) = instantiate_main_objects()
    api = ApiView.Api(db_model=db, graph_service=graphs, transfer_scanner=scanner, statistics_service=stats)
    api.setup()
    api.start_api()

api_main()