import math

from Models import DatabaseModel, Session
from Entities import Statistics
import networkx as nx
from networkx.readwrite import json_graph

# The nature of the transaction network allows for wallets to trade with one another multiple times.
# The trading relationship between two wallets can be seen as directed because one person sells while the other
# purchases.
# The direction of this interaction will be important to remember, therefore the graph must be directed.
# These factors lead us to use a MultiDiGraph.
class GraphService:

    def __init__(self, db: DatabaseModel.DatabaseModel):
        self.db = db

    # takes a list of transfers, which is created using DatabaseModel.get_grouped_transfers()
    def create_multigraph(self, *, transfers: list, include_mint: bool = True):
        g = nx.MultiDiGraph()
        # weights = [] # todo: find better weight than number of tokens. Should probably be price when we have that.
        for transfer in transfers:
            # weights.append(len(transfer.tokens))
            self._add_transfer_as_node(g=g, transfer=transfer, include_mint=include_mint)
        return g

    @staticmethod
    def get_subgraphs(g):
        return g.subgraph()

    @staticmethod
    def _add_transfer_as_node(*, g, transfer, include_mint: bool):
        if not include_mint:
            if transfer.from_address != "0000000000000000000000000000000000000000":
                g.add_node(transfer.from_address)
                g.add_node(transfer.to_address)
                g.add_edge(transfer.from_address, transfer.to_address, block=transfer.block, tx=transfer.tx)
            else:
                g.add_node(transfer.to_address)
        else:
            g.add_node(transfer.from_address)
            g.add_node(transfer.to_address)
            g.add_edge(transfer.from_address, transfer.to_address, block=transfer.block, tx=transfer.tx)

    @staticmethod
    def export_json(nx_graph):
        return json_graph.node_link_data(nx_graph)

    @staticmethod
    def create_token_graph(transfers: list):
        g = nx.MultiDiGraph()  # is a multiDigraph to support selfloops and parraleledges.
        for transfer in transfers:
            GraphService._add_transfer_as_node(g=g, transfer=transfer, include_mint=False)
        return g

    # noinspection PyTypeChecker
    # todo: if there are no transfers, dont run this :)
    @staticmethod
    def calculate_token_graph_statistics(*, transfers):
        if len(transfers) == 0:
            return None, None
        graph_dict = {}
        cycle_dict = {}
        collection_stats = Statistics.TokenCycleStatistic()

        # we have to create the graphs before we can calculate any sort of statistics
        GraphService._populate_dicts(cycle_dict, graph_dict, transfers)

        cycles_acc = 0
        # calculate cycles in each graph and add the result to the cycle_dict
        for k, v in graph_dict.items():
            nr_of_cycles = len(list(nx.simple_cycles(v)))
            cycle_dict[k] = nr_of_cycles
            cycles_acc += nr_of_cycles

        graph_dict = None

        tokens_count = len(cycle_dict)
        # calculate average and sd for collection
        if cycles_acc != 0 and tokens_count != 0:
            collection_stats.avg = cycles_acc / tokens_count
            diff_sum = 0
            for token, number_of_cycles in cycle_dict.items():
                if number_of_cycles > 0:
                    diff_sum += math.pow(number_of_cycles - collection_stats.avg, 2)

            collection_stats.std_deviation = math.sqrt(diff_sum / tokens_count)
            collection_stats.total_count = tokens_count

        return collection_stats, cycle_dict


    @staticmethod
    def _populate_dicts(cycle_dict, graph_dict, transfers):
        for row in transfers:
            token = row[0]  # get the TokenTransfer from the statement
            graph_dict.setdefault(token.token_id, nx.MultiDiGraph())
            cycle_dict.setdefault(token.token_id, 0)
            if token.from_address != "0000000000000000000000000000000000000000":
                graph_dict[token.token_id].add_edge(token.from_address, token.to_address, tx=token.tx)

