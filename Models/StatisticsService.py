from dataclasses import dataclass
import math
from Models import DatabaseModel, GraphService, Session, Utils
from Entities import Token, Collection, Statistics, Transfer
Token = Token.Token
tokenStats = Statistics.TokenStatistics
utils = Utils.Utils
collectionStats = Statistics.CollectionStatistics

@dataclass
class StatisticsService:
    graph_service: GraphService
    db: DatabaseModel.DatabaseModel

    '''
    This method is used to go through all of the collections in the database and then calculating and inserting the
    statistics for each of them.
    '''
    def populate_collection_stats(self):
        with self.db.start_session() as session:
            collections = self.db.collections.get_all_collections(db_session=session)
            for col in collections:
                collection = col[0]
                self.insert_collections_stats(db_session=session, collection=collection)

    '''
    This method calculates the statistics for a single collection using two different methods. When the calculations are
    finished, it saves the results to the database.
    '''
    def insert_collections_stats(self,*, db_session: Session, collection: Collection):
        transfers = self.db.transfers. \
            get_ordered_transfers_from_collection(db_session=db_session,
                                                  contract_address=collection.contract_address)
        if len(transfers) != 0:
            (collection_block_stats, token_block_dict) = StatisticsService.calculate_statistics_collection(
                transfers=transfers)
            (collection_cycle_stats, token_cycle_dict) = self.graph_service.calculate_token_graph_statistics(
                transfers=transfers)
            if collection_block_stats is None or token_block_dict is None:
                print(f"something went wrong 0 - {collection.name}")
                return
            if collection_cycle_stats is None or token_cycle_dict is None:
                print(f"something went wrong 1 - {collection.name}")
                return

            self.db.collections.set_collection_statistics(db_session=db_session, collection=collection,
                                                      cycle_stats=collection_cycle_stats,
                                                      block_stats=collection_block_stats)

            for k, v in token_block_dict.items():
                items = len(v)
                token = Token(token_id=k, contract_address=collection.contract_address,
                              cycle_count=token_cycle_dict[k], block_diff_average=v["stats"].avg,
                              block_diff_std=v["stats"].std_deviation, transfer_count=items)
                self.db.tokens.add_token(db_session=db_session, token=token)
            print("done inserting tokens into db.")

    '''
    This function calculates the statistics for a given token in a collection and prints the results.
    '''
    def get_statistics(self, db_session: Session, collection: Collection, token_id: int = None):
        transfers = self.db.transfers. \
            get_ordered_transfers_from_collection(db_session=db_session,
                                                  contract_address=collection.contract_address)
        (collection_block_stats, token_block_dict) = self.db.transfers.calculate_statistics_collection(
            transfers=transfers)
        print("finished calculating block stats")
        (collection_cycle_stats, token_cycle_dict) = self.graph_service.calculate_token_graph_statistics(
            transfers=transfers)

        if token_id is None:
            print(f'cycles dict {token_cycle_dict}')
            print(f'block dict {token_block_dict}')
        else:
            print(f'cycles dict {token_cycle_dict[token_id]}')
            print(f'block dict {token_block_dict[token_id]["stats"]}')


    '''
    function that creates a dictionary with k 0 tokenid and v = list of transfer.block of token and a statistics object.
    '''
    @staticmethod
    def create_block_dict_grouped_by_token(*, list_of_transfers: list) -> dict:
        token_dict = {}

        for row in list_of_transfers:
            token = row[0]
            token_dict.setdefault(token.token_id, {
                "blocks": [],
                "stats": tokenStats()
            })
            # remove mint because it generally takes very short time
            if token.from_address != "0000000000000000000000000000000000000000":
                token_dict[token.token_id]['blocks'].append(token.block)
        return token_dict

    # TODO: if the there are no transfers, don't run this :)
    '''
    function that calls the other functions that are related to statistics. Returns a statistics object for the collection
    as a whole and a dict with statistics objects for each token in the collection.
    '''
    @staticmethod
    def calculate_statistics_collection(*, transfers, min_nr_of_transfers: int = 3) -> (Statistics.CollectionStatistics, dict):

        # init object for keeping track of statistics of collection
        collection_stats = collectionStats()

        # create dictionary of tokens with token.blocks and a stats obj
        tk_dict = StatisticsService.create_block_dict_grouped_by_token(list_of_transfers=transfers)

        # go through tokens in dict and calculate averages for block time diff
        valid_tk_dict = StatisticsService._calc_average_time_diff(coll_stats=collection_stats, token_dict=tk_dict,
                                         min_nr_of_transfers=min_nr_of_transfers)
        # use previously calculated average to calc standard deviation
        StatisticsService._calc_standard_deviation_collection(stats_obj=collection_stats, token_dict=valid_tk_dict)

        # return stats of collection and the dict containing stats object for each token
        return collection_stats, valid_tk_dict

    '''
    function that calculates the standard deviation for a given statistics object given that it has a list_of_diffs.
    https://www.cuemath.com/data/standard-deviation/
    '''
    @staticmethod
    def _calc_standard_deviation_token(*, stats_obj: Statistics.StatisticsBase):
        diff_sum = 0
        for item in stats_obj.list_of_diffs:
            diff_sum += math.pow(item - stats_obj.avg, 2)
        if diff_sum  != 0 and len(stats_obj.list_of_diffs) != 0:
            stats_obj.std_deviation = math.sqrt(diff_sum / len(stats_obj.list_of_diffs))

    '''
    function that calculates the standard deviation for collection using the standard deviation of all tokens.
    https://www.statology.org/averaging-standard-deviations/
    '''
    @staticmethod
    def _calc_standard_deviation_collection(*, stats_obj: Statistics.CollectionStatistics, token_dict):
        diff_sum = 0
        n_sum = 0
        len_tokens = len(token_dict)
        for k, v in token_dict.items():
            sd = v['stats'].std_deviation
            n = v['stats'].total_count
            n_sum += n
            diff_sum += math.pow(sd, 2) * n - 1

        if diff_sum != 0 and n_sum != 0:
            stats_obj.std_deviation = math.sqrt(diff_sum / (n_sum - len_tokens))

    '''
    function that calculates different statistics regarding transfer speeds for a collection and its tokens.
    It mutates the statistics object that is given as a param.
    ONLY CALCULATES AVERAGES FOR TOKENS THAT HAVE MORE THAN 3 TRANSFERS
    https://www.statisticshowto.com/grand-mean/ 
    '''
    @staticmethod
    def _calc_average_time_diff(*, token_dict: dict, coll_stats, min_nr_of_transfers: int):

        acc_valid = 0  # value is not saved in statistics object since it has no use other than calculating average.
        valid_token_dict = {}

        for k, v in token_dict.items():
            blocks = v['blocks']
            token_stats = v['stats']
            items = len(blocks)
            coll_stats.total_count += 1

            if items > min_nr_of_transfers:  # sort out the token that have only been minted and nothing else
                temp_acc = 0  # accumulator for block differences
                temp_list_of_diffs = []
                coll_stats.count_valid += items

                for i in range(items - 1):
                    diff = blocks[i + 1] - blocks[i]  # calculate difference in block for transfers
                    temp_acc += diff
                    temp_list_of_diffs.append(diff)

                    StatisticsService._check_extremes_token(stats_obj=token_stats, val=diff)
                    StatisticsService._check_extremes_collection(stats_obj=coll_stats,  val=diff, k=k)

                token_stats.avg = temp_acc / items
                token_stats.total_count = items
                token_stats.list_of_diffs = temp_list_of_diffs
                StatisticsService._calc_standard_deviation_token(stats_obj=token_stats)

                for l in temp_list_of_diffs:
                    coll_stats.list_of_diffs.append(l)

                acc_valid += temp_acc
                v['block'] = None  # no reason to store blocks in token_dict anymore
                valid_token_dict[k] = v

        if coll_stats.count_valid != 0 and acc_valid != 0:
            coll_stats.avg = acc_valid / coll_stats.count_valid

        return valid_token_dict

    '''
    function that checks whether the high, low attributes of the CollectionStatistics object should be changed with the
    new val.
    '''
    @staticmethod
    def _check_extremes_collection(stats_obj: Statistics.CollectionStatistics, val, k):
        if val > stats_obj.high[1]:
            stats_obj.high = (k, val)
        if val < stats_obj.low[1] and val != 0:
            stats_obj.low = (k, val)

    '''
    function that checks whether the high, low attributes of the CollectionStatistics object should be changed with the
    new val.
    '''
    @staticmethod
    def _check_extremes_token(stats_obj: Statistics.TokenStatistics, val):
        if val < stats_obj.fastest:
            stats_obj.fastest = val
        if val > stats_obj.slowest and val != 0:
            stats_obj.slowest = val
