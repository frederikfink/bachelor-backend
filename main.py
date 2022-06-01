from dotenv import load_dotenv
import os
from Models import DatabaseModel, GraphService, TransferScanner, \
    CollectionService, ApiView, OpenSeaScraper, StatisticsService
from rich.traceback import install

install()
load_dotenv()

infura_url = os.getenv("INFURA_URL")
etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")

def api_main():
    (db, graphs, col_service, scanner, scraper, stats) = instantiate_main_objects()
    api = ApiView.Api(db_model=db, graph_service=graphs, transfer_scanner=scanner, statistics_service=stats)
    api.setup()
    api.start_api()

def main():
    (db, graphs, col_service, scanner, scraper, stats) = instantiate_main_objects()
    # TODO: use begin() instead of session()

    with db.start_session() as session:
        transfers = db.transfers.\
            get_ordered_transfers_from_collection(db_session=session,
                                                  contract_address="0x49cf6f5d44e70224e2e23fdcdd2c053f30ada28b")

        (block_stats, block_dict) = db.transfers.calculate_statistics_collection(transfers=transfers)
        (cycle_stats, cycle_dict) = graphs.\
            calculate_token_graph_statistics(transfers=transfers)

        print(block_stats)
        print(cycle_stats)

def instantiate_main_objects():
    db = DatabaseModel.DatabaseModel()
    col_service = CollectionService.CollectionService()
    graphs = GraphService.GraphService(db=db)
    stats_service = StatisticsService.StatisticsService(db=db, graph_service=graphs)
    scanner = TransferScanner.TransferScanner(infura_url, log_mode=True, db=db, collection_service=col_service)
    scraper = OpenSeaScraper.OpenSeaScraper(db=db, etherscan_api_key=etherscan_api_key)
    return db, graphs, col_service, scanner, scraper, stats_service

def scan_all_slugs():
    (db, graphs, col_service, scanner, scraper, stats) = instantiate_main_objects()

    with db.start_session() as session:
        # ____ Scanning ____
        colls = db.collections.get_all_collections(db_session=session)
        slugs = db.slugs.list_slugs_with_offset(db_session=session, nr_to_offset=0)
        if len(slugs) == 0:
            return -1

        for s in slugs:
            try:
                scan_single(s.contract_address)
            except Exception as e:
                print(f'could not start scan\n{e}')
                continue

        return 1


def estimate_start_block(contract_address: str):
    (db, graphs, col_service, scanner, scraper, stats) = instantiate_main_objects()

    print(col_service.get_start_block_and_slug(contract_address=contract_address))

def scan_single(contract_address: str, from_first_block: bool = False):
    (db, graphs, col_service, scanner, scraper, stats) = instantiate_main_objects()

    scanner.scan_with_progressbar(
        contract_address=contract_address,
        from_first_block=from_first_block
    )
    # scanner.scan(
    #     contract_address=contract_address
    # )

def populate_statistics():
    (db, graphs, col_service, scanner, scraper, stats) = instantiate_main_objects()
    stats.populate_collection_stats()

def insert_statistics_collection(contract_address: str):
    (db, graphs, col_service, scanner, scraper, stats) = instantiate_main_objects()
    with db.start_session() as session:
        collection = db.collections.get_collection(db_session=session, contract_address=contract_address)
        stats.insert_collections_stats(db_session=session, collection=collection)



def single_contract_json_response(contract_address: str):
    (db, graphs, col_service, scanner, scraper, stats) = instantiate_main_objects()
    response = col_service.get_start_block_and_slug(contract_address=contract_address)
    print(response)


def scrape():
    (db, graphs, col_service, scanner, scraper, stats) = instantiate_main_objects()
    # ____ Scraping ____
    print(f'creating scraper')
    print(f'starting scrape')
    scraper.setup()
    scraper.scrape()
    scraper.teardown()

def get_stats_from_single_collection(contract_address: str, token_id: int = None):
    (db, graphs, col_service, scanner, scraper, stats) = instantiate_main_objects()
    with db.start_session() as session:
        col = db.collections.get_collection(db_session=session, contract_address=contract_address)
        stats.get_statistics(db_session=session, collection=col, token_id=token_id)


def get_outliers_from_collection(contract_address: str):
    (db, graphs, col_service, scanner, scraper, stats) = instantiate_main_objects()
    with db.start_session() as session:
        # tokens = db.tokens.get_tokens_in_collection(contract_address=contract_address, db_session=session)
        db.get_token_outliers_from_collection(contract_address=contract_address, db_session=session)

if __name__ == '__main__':
    # get_outliers_from_collection("0x49cf6f5d44e70224e2e23fdcdd2c053f30ada28b")
    # scan_all_slugs()
    # print(scan_single("0x8EE5DD62A654a60f6F17A99d544102f37B58dA26"))
    # single_contract_json_response('0x0326b0688d9869a19388312Df6805d1D72AaB7bC')
    # scrape()
    # get_stats_from_single_collection("0x49cf6f5d44e70224e2e23fdcdd2c053f30ada28b", token_id=5042)
    # api_main()
    # main()
    populate_statistics()
    insert_statistics_collection()
    # estimate_start_block("0x6080B6D2C02E9a0853495b87Ce6a65e353b74744")
    # test(1, 100)





