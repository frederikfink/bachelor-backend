import json
import time
import os

import requests
from tqdm import tqdm
from web3 import Web3
from typing import Tuple
from colorama import Fore, Style
from Models import CONTRACT_NAME_ABI, EVENT_SIGNATURE_HASH, CollectionService, Session, StatisticsService
from Models import DatabaseModel as dbm
from Entities import Slug
from rich.traceback import install

install()

OPENSEA_API_KEY = os.getenv('OS_API_KEY')
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
Db_Model, Transfer, Collection = dbm.DatabaseModel, dbm.Transfer.Transfer, dbm.Collection.Collection


# noinspection PyTypeChecker
class TransferScanner:

    def __init__(self,
                 provider_url: str, db: Db_Model,
                 log_mode: bool = False,
                 export_type: str = "db",
                 collection_service: CollectionService.CollectionService = None,
                 statistics_service: StatisticsService.StatisticsService = None):
        self.statistics_service = statistics_service
        self.w3 = Web3(Web3.HTTPProvider(provider_url))
        self.log_mode = log_mode
        self.export_type = export_type
        self.collection_service = collection_service

        self.min_chunk_size = 20
        self.max_chunk_size = 10000

        self.chunk_size_increase = 2.0
        self.chunk_size_decrease = 0.5

        self.db = db
        # Transfer event signature hash
        self.event_signature_hash = EVENT_SIGNATURE_HASH


    def get_latest_block(self):
        latest_block = self.w3.eth.getBlock('latest')
        return latest_block['number']

    def get_filter(self, start_block, chunk_size, contract_address, event_signature_hash):
        return self.w3.eth.filter({
            "fromBlock": start_block,
            "toBlock": start_block + chunk_size,
            "address": contract_address,
            "topics": event_signature_hash
        })

    def set_export_type(self, export_type):
        self.export_type = export_type

    def update_stats(self, events):
        raise NotImplementedError

    def adjust_chunk_size(self, events_found, chunk_size):

        if events_found > 1000:
            chunk_size *= self.chunk_size_decrease
            chunk_size = max(self.min_chunk_size, chunk_size)
        else:
            chunk_size *= self.chunk_size_increase
            chunk_size = min(self.max_chunk_size, chunk_size)

        return int(chunk_size)

    def determine_start_block(self, db_session: Session, contract_address: str):
        (collection_exists, coll) = self.db.collections.collection_exists(db_session=db_session, contract_address=contract_address)
        if collection_exists:
            start_block = coll.latest_block
        else:
            response = self.collection_service.get_start_block_and_slug(contract_address=contract_address)
            start_block = response.start_block
            if not self.db.slugs.slug_exists(db_session=db_session, slug=response.slug):
                sl = Slug.Slug(contract_address=contract_address, start_block=response.start_block, slug=response.slug)
                self.db.slugs.add_slug_to_db(db_session=db_session, slug=sl)
        return start_block

    @staticmethod
    def parse(events):
        json_events = Web3.toJSON(events)
        return json.loads(json_events)

    # set the contract name from the contract using a simplified ABI with a name() function
    # if name cannot be read from the contract it sets the contract name to the contract address.
    # Let some admin set the name manually later on.
    # ONLY USED TO FIND NAME OF CONTRACT TO INSERT IN DB - not used when fetching data.
    def find_contract_name(self, checksum_contract_address: str):
        try:
            abi = json.loads(CONTRACT_NAME_ABI)
            contract = self.w3.eth.contract(address=checksum_contract_address, abi=abi)
            contract_name = contract.functions.name().call()
        except Exception as e:
            contract_name = checksum_contract_address
        return contract_name

    def get_single_block(self, block):
        print(self.w3.eth.get_block_transaction_count(block))
        print(self.w3.eth.get_block(block, full_transactions=True))

    @staticmethod
    def create_transfer_from_json(transfers: list) -> list:
        transfer_list = list()
        for t in transfers:
            #TODO: add some logic to handle this condition. RN we don't know why topics with len < 4 exist.
            if len(t['topics']) != 4:
                continue
            contract_addr = t['address']
            log_index = t['logIndex']
            tx = t['transactionHash']
            block = t['blockNumber']
            token_id = int(t['topics'][3], 16)
            # remove leading zeroes from addresses, since those are not used when searching using etherscan or opensea
            from_addr = t['topics'][1].replace('0x000000000000000000000000', '')
            to_addr = t['topics'][2].replace('0x000000000000000000000000', '')

            transfer_list.append(Transfer(contract_address=contract_addr, log_index=log_index, tx=tx, block=block,
                                          token_id=token_id, from_address=from_addr, to_address=to_addr))
        return transfer_list

    def scan_unknown_start_block(self, contract_address) -> Tuple[int, int, int]:
        block = self.collection_service.\
            get_start_block_and_slug(contract_address).start_block

        return self.scan(contract_address=contract_address, start_block=block)

    def scan(self, *, contract_address: str, start_block: int, progress_bar=None) -> Tuple[int, int, int]:
        latest_block = self.get_latest_block()
        assert start_block <= latest_block

        # address should be converted to EIP-55: Mixed-case checksum address encoding for backwards compatibility
        # https://eips.ethereum.org/EIPS/eip-55
        checksum_contract_address = Web3.toChecksumAddress(contract_address)

        # !--- QUERY DATABASE IF COLLECTION EXISTS HERE ---!
        contract_name = self.find_contract_name(checksum_contract_address=checksum_contract_address)

        # local var for chunk size that will be adjusted if an exception is thrown.
        chunk_size = self.min_chunk_size
        # set end block for current block range scan
        scan_end_block = start_block + chunk_size
        scan_start_block = start_block

        # scan stats for nerds
        total_blocks_scanned, total_events_found, events_in_chunk, api_calls  = 0, 0, 0, 0

        with self.db.start_session() as session:
            (collection_exists, coll) = self.db.collections.collection_exists(session, contract_address)
            if not collection_exists:
                collection = Collection(contract_address=contract_address,
                                        name=contract_name, start_block=start_block)
                self.db.collections.add_collection_to_db(db_session=session, collection=collection)

            print(f' scanning {contract_name}. block {scan_start_block} --> block {latest_block}')

            while scan_end_block <= latest_block:
                # create filter which only looks for event with given signature hash.
                signature_filter = self.get_filter(scan_start_block, chunk_size,
                                                   checksum_contract_address,
                                                   self.event_signature_hash)
                # This is the call that actually fetches the data
                try:
                    transfers_raw = self.w3.eth.get_filter_logs(signature_filter.filter_id)
                    # parse json to dict
                    transfers = self.parse(transfers_raw)
                    # store number of events found for calculating block size
                    transfers_found = len(transfers)
                    transfers_added = 0

                    # !--- INSERT TRANSFERS INTO DATABASE ---!
                    if self.db is not None:
                        if transfers_found > 0:
                            tl = self.create_transfer_from_json(transfers)
                            transfers_added = self.db.transfers.\
                                add_transfer_list_to_db(db_session=session, transfer_list=tl,
                                                        collection_exists=collection_exists)
                    # update scan stats for nerds
                    total_events_found += transfers_found
                    total_blocks_scanned += chunk_size
                    api_calls += 1

                    # prepare next scan chunk
                    # set chunk size with adjust_chunk_size heuristics
                    chunk_size = self.adjust_chunk_size(transfers_found, chunk_size)

                    # need to add 1 to avoid duplicates.
                    scan_start_block = scan_end_block + 1
                    scan_end_block = scan_start_block + chunk_size
                    if transfers_added > 0:
                        self.db.collections.set_collection_latest_block(session, contract_address, scan_end_block)

                    # update the latest block of the collection. Should allow us to resume from where we ended scan.

                    if progress_bar is not None:
                        self._update_progress(start=start_block, end=latest_block, current=scan_start_block,
                                              chunk_size=chunk_size, events_in_chunk=transfers_found,
                                              total_events=total_events_found, total_blocks_scanned=total_blocks_scanned,
                                              api_calls=api_calls, progress_bar=progress_bar)

                # Exception occurs when the API call hits more than 10000 events.
                except ValueError as e:
                    print(e)
                    scan_end_block -= chunk_size
                    chunk_size = self.min_chunk_size

        return total_events_found, total_blocks_scanned, api_calls

    @staticmethod
    def _update_progress(*, start, end, current, chunk_size, events_in_chunk, total_events, total_blocks_scanned, api_calls, progress_bar):
        progress_bar.set_description(f"🚀 chunk_size: { chunk_size } | { total_blocks_scanned }, "
                                     f"events: { events_in_chunk } | { total_events }, api calls: {api_calls}")
        progress_bar.update(chunk_size)

    @staticmethod
    def get_start_block_brute(contract_address: str):

        url = "https://api.etherscan.io/api?module=account&action=txlist&address=" + \
              contract_address + "&startblock=0&endblock=99999999&page=1&offset=10&sort=asc&apikey=" + ETHERSCAN_API_KEY

        print(url)

        response = requests.get(url)

        start_block = json.loads(response.text)['result'][0]['blockNumber']

        return int(start_block)

    # always tries to find the start-block in our database before looking for it using API calls unless from_first_block
    # is true
    def scan_with_progressbar(self, *, contract_address, slug: str = None, from_first_block: bool = False):
        start = time.time()

        if not from_first_block:
            with self.db.start_session() as session:
                start_block = self.determine_start_block(db_session=session, contract_address=contract_address)
        else:
            start_block = self.collection_service.get_start_block_and_slug(contract_address=contract_address).start_block

        with tqdm(total=self.get_latest_block() - start_block) as progress_bar:
            total_events_found, total_blocks_scanned, api_calls = self.scan(start_block=start_block,
                                                                            contract_address=contract_address.strip(),
                                                                            progress_bar=progress_bar)
        duration = round(time.time() - start, 0)

        if slug is not None:
            print(f'Collection: {slug} || {contract_address}')
        print("Finished in \t" + Fore.GREEN + f"{duration}" + Style.RESET_ALL + " seconds ⏱")
        print("Blocks scanned:\t" + Fore.CYAN + f"{total_blocks_scanned:,}" + Style.RESET_ALL + " 🏁")
        print("Events found: \t" + Fore.CYAN + f"{total_events_found:,}" + Style.RESET_ALL + " 📈")
        print("API calls: \t" + Fore.CYAN + f"{api_calls:,}" + Style.RESET_ALL + " 📣")

    # calculates the statistics for every entry in our database.




