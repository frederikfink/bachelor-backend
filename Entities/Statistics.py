from __future__ import annotations
from Models import Utils
utils = Utils.Utils


'''
base class that contains attributes that are relevant for most types of stats.
'''
class StatisticsBase:

    def __init__(self):
        self.avg = 0
        self.std_deviation = 0
        self.total_count = 0  # total count of tokens including ones with no more than one transfer
        self.list_of_diffs = []  # list that contains the block differences between transfers.

    def __repr__(self):
        return f'Avg in blocks: {self.avg} -> {utils.blocks_to_days(self.avg)}\n' \
               f'Std_dev in blocks: {self.std_deviation} -> {utils.blocks_to_days(self.std_deviation)}\n' \
               f'Count Tokens/Transfers: {self.total_count}\n'

class CollectionStatistics(StatisticsBase):

    def __init__(self):
        super().__init__()
        self.high = (0, float('-inf'))  # id and value of largest time between sale
        self.low = (0, float('inf'))  # id and value of largest time between sale
        self.count_valid = 0  # count of tokens with more than one transfer. This will be used to calc average.

    def __repr__(self):
        return "Collection:\n"+super().__repr__() + \
               f'Tokens with at least one sale: {self.count_valid}\n' \
               f'Highest val and id: {self.high}\n' \
               f'Lowest val and id: {self.low}\n' \

class TokenStatistics(StatisticsBase):

    def __init__(self):
        super().__init__()
        self.fastest = float('inf')  # id and value of largest time between sale
        self.slowest = float('-inf')  # id and value of largest time between sale

    def __repr__(self):
        return "Token:\n"+super().__repr__() + \
            f'Fastest tx and val: {self.fastest}\n' \
            f'Slowest tx and val: {self.slowest}\n' \
            f'Std_dev in blocks: {self.std_deviation} -> {utils.blocks_to_days(self.std_deviation)}\n'

class TokenCycleStatistic(StatisticsBase):

    def __init__(self):
        super().__init__()

    def __repr__(self):
        return f'Avg cycles: {self.avg}\n' \
               f'Std_dev: {self.std_deviation} ->\n'\
               f'Count Tokens: {self.total_count}\n'

