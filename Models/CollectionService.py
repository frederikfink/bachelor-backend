from datetime import datetime
import requests
import arrow  # package for datetime conversion
import json
from dataclasses import dataclass
from web3 import Web3
from dotenv import load_dotenv
from Entities import OpenseaResponse
import os
from rich.traceback import install


install()
OpenseaRes = OpenseaResponse.OpenseaResponse

# the provider to make web3 api calls
w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/8ee8f90dd1f949b68aed10e9a0b19c44"))
# get the latest block.
w3_latest_block = w3.eth.get_block('latest')['number']
# load environment file to get opensea api key
load_dotenv()
OPENSEA_API_KEY = os.getenv('OS_API_KEY')

@dataclass
class CollectionService:

    # function to get timestamp of block
    @staticmethod
    def block_timestamp(i_block):
        return w3.eth.get_block(i_block).timestamp

    # given a contract address, returns details about the collection. Specifically the section called "collection"
    # which contains information such as the created_at_date (used to determine the starting block), slug, and address.
    # todo: sometimes this will just fail for no reason. Something about the request goes bad. Don't know if it's our key
    @staticmethod
    def _get_date_and_slug(*, contract_address) -> dict:
        base_url = "https://api.opensea.io/api/v1/asset_contract/"
        url_contract_address = f'{contract_address}'
        url = base_url + url_contract_address
        headers = {"X-API-KEY":  OPENSEA_API_KEY, "Accept": "application/json"}

        response = requests.request("GET", url=url, headers=headers)
        json_res = json.loads(response.text)
        collection = json_res["collection"]
        return collection

    def get_start_block_and_slug(self, *, contract_address: str) -> OpenseaResponse:
        collection_json = self._get_date_and_slug(contract_address=contract_address)

        created_date = collection_json['created_date']
        slug = collection_json['slug']
        start_block = self.__find_nearest_block_by_estimate(str_timestamp=created_date)
        res = OpenseaRes(slug, start_block)
        return res

    # lowest block starts at 1 and highest block starts at the latest one from w3.
    # only API calls this are the ones to get the block timestamps, which is called 3 times each call
    # Don't ask me about the math behind this :=)
    # Inspired by answer from user 'P i'
    # from https://ethereum.stackexchange.com/questions/62007/how-to-get-the-blocks-between-timestamp?newreg=74b95cedea3a46b3b4ec53e5d1f79d0f
    def __find_nearest_block_by_estimate(self, *,
                                         str_timestamp: str,
                                         block_low: int = 1,
                                         block_high: int = w3_latest_block,
                                         verbose: bool = False,
                                         depth: int = 0
                                         ) -> float:
        input_timestamp = arrow.get(str_timestamp).timestamp()
        block_low = max(1, block_low)
        block_high = min(w3_latest_block, block_high)
        # subtract this value to ensure that the returned block is always before the creation of the collection.
        # necessary since we might be off by a few blocks.
        subtract_from_return_block = 100

        # determine if we've hit the block yet.
        if block_low == block_high or depth > 100:
            if verbose:
                print('Got it')
            return block_low - subtract_from_return_block

        timestamp_low, timestamp_high = self.block_timestamp(block_low), self.block_timestamp(block_high)

        # divide the difference in timestamp with the difference in block height to find the average block time based
        # the provided blocks. This gives an estimate of the "time" each block takes to create.
        avg_block_time = (timestamp_high - timestamp_low) / (block_high - block_low)

        # if block-times were evenly-spaced, get expected block number.
        # calculate the expected block.
        k = (input_timestamp - timestamp_low) / (timestamp_high - timestamp_low)
        block_estimate = int(block_low + k * (block_high - block_low))

        # get the timestamp for the block that we are guessing contains the first transaction.
        block_estimate_timestamp = self.block_timestamp(block_estimate)

        # use the discrepancy to improve our guess
        est_n_blocks_from_expected_to_target = int((input_timestamp - block_estimate_timestamp) / avg_block_time)

        # create an adjusted guess of the expected value
        adjusted_estimate = block_estimate + est_n_blocks_from_expected_to_target

        r = abs(est_n_blocks_from_expected_to_target)

        if verbose:
            self.print_info(adjusted_estimate, avg_block_time, block_estimate, block_estimate_timestamp, block_high,
                            block_low, est_n_blocks_from_expected_to_target, input_timestamp, k, timestamp_high,
                            timestamp_low)

        return self.__find_nearest_block_by_estimate(str_timestamp=str_timestamp,
                                                     block_low=adjusted_estimate - r,
                                                     block_high=adjusted_estimate + r,
                                                     depth=depth+1)

    # prints information about the estimation in __find_nearest_block_by_estimate
    def print_info(self, adjusted_estimate, avg_block_time, block_estimate, block_estimate_timestamp, block_high,
                   block_low, est_n_blocks_from_expected_to_target, input_timestamp, k, timestamp_high, timestamp_low):
        print(f'block_low =\t{block_low} \t\t\t| block_high =\t{block_high}')
        print(f'timestamp_low=\t{timestamp_low}\t\t| timestamp_high=\t{timestamp_high}')
        print(f'avg block time = {avg_block_time}')
        print(f'k value = {k}')
        print()
        print(
            f'target timestamp ({input_timestamp}) lies {k:.3f} of the way from block# {block_low} (t={timestamp_low}) to block# {block_high} (t={timestamp_high})')
        print(f'Expected block# assuming linearity: {block_estimate} (t={block_estimate_timestamp})')
        print('Expected n blocks required to reach target (again assuming linearity):',
              est_n_blocks_from_expected_to_target)
        print('New guess at block #:', adjusted_estimate)
        print('\n')

    # takes a slug and returns its created_date
    # generally not used
    @staticmethod
    def get_collection_create_date(*, slug: str) -> str:
        base_url = "https://api.opensea.io/api/v1/collection/"
        url = base_url + slug
        response = requests.request("GET", url)
        return json.loads(response.text)['collection']['created_date']

    # takes a limit n and an offset as input and returns a dict with k=slug and v=created_dates
    # Not very useful. Only retrieves up to 50000 of the newest collections on opensea, which basically have no trading
    # volume.
    @staticmethod
    def get_collections(limit: int = 300, offset: int = 0) -> dict:
        base_url = "https://api.opensea.io/api/v1/collections"
        url_offset = f'?offset={offset}'
        url_limit = f'&limit={limit}'
        url = base_url + url_offset + url_limit
        headers = {"Accept": "application/json"}

        response = requests.request("GET", url=url, headers=headers)

        collections = json.loads(response.text)['collections']
        collections_dict = dict()

        for coll in collections:
            collections_dict[coll['slug']] = coll['created_date']

        return collections_dict

    # takes a list of collection slugs and returns a dict with k=slugs and v=start_block.
    def get_collection_list_start_block(self, collection_slugs: list) -> dict:

        collections_dict = dict()

        for slug in collection_slugs:
            created_date = self.get_collection_create_date(slug=slug)
            print(f'slug: {slug}, created_date: {created_date}, timestamp: {arrow.get(created_date).timestamp()}')
            start_block = self.__find_nearest_block_by_estimate(
                input_timestamp=created_date,
                verbose=False)
            collections_dict[slug] = start_block

        return collections_dict






