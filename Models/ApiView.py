from contextvars import Token
from flask import Flask, request, jsonify
from Models import DatabaseModel, GraphService, TransferScanner, StatisticsService
from flask_cors import CORS


class Api:

    def __init__(self,
                 db_model: DatabaseModel.DatabaseModel,
                 graph_service: GraphService.GraphService,
                 transfer_scanner: TransferScanner.TransferScanner,
                 statistics_service: StatisticsService.StatisticsService):
        self.app = Flask(__name__)
        self.db = db_model
        self.statistics_service = statistics_service
        self.graph_service = graph_service
        self.scanner = transfer_scanner
        self.app.config['DEBUG'] = True
        self.app.config['JSON_SORT_KEYS'] = False
        CORS(self.app, resources={r"*": {"origins": "*"}})

    # add endpoints here
    def setup(self):
        self._add_endpoint('/', self.index)
        self._add_endpoint('/collection/add', self.add_collection, methods=['POST'])
        self._add_endpoint('/collection/all', self.get_all_collections)
        # self._add_endpoint('/collection/status/<string:collectionID>', self.get_collection_status)
        self._add_endpoint('/collection/<string:collectionID>', self.get_contract_token_transfers)
        self._add_endpoint('/collection/<string:collectionID>/stats', self.get_collection_stats)
        self._add_endpoint('/collection/<string:collectionID>/token/<int:tokenID>', self.token_list)
        self._add_endpoint('/collection/<string:collectionID>/token/<int:tokenID>/stats', self.get_token_statistics)
        self._add_endpoint('/group/<collectionID>', self.collectionGroup)

    def index(self):
        return 'Index Page'

    def add_collection(self):

        contract_address = request.json['collection']
        if len(contract_address) != 42:
            return {
                'exception': 'collection string length does not fit'
            }

        res = self.scanner.scan_with_progressbar(contract_address=contract_address)
        
        with self.db.start_session() as session:
            collection = self.db.collections.get_collection(db_session=session, contract_address=contract_address)
            self.statistics_service.insert_collections_stats(db_session=session, collection=collection)

        response = jsonify({"collection" : request.json['collection']})
        response.headers.add('Access-Control-Allow-Origin', '*')

        return response

    def get_all_collections(self):

        with self.db.start_session() as session:
            result = self.db.collections.get_all_collections(db_session=session)

            response = jsonify([((row[0].to_dict())) for row in result])
            response.headers.add('Access-Control-Allow-Origin', '*')

        return response

    def get_contract_token_transfers(self, collectionID):

        with self.db.start_session() as session:
            tokens = self.db.tokens.get_tokens_in_collection(db_session=session, contract_address=collectionID)
        
            response = jsonify([t.to_dict() for t in tokens])

            response.headers.add('Access-Control-Allow-Origin', '*')

        return response


    # @app.route('/collection/<string:collectionID>')
    # def collection(collectionID):

    #     db = DatabaseModel.DatabaseModel()

    #     with db.start_session() as session:
    #         transfers = db.get_grouped_transfers(db_session=session, contract_address=collectionID)

    #         transfer_count = len(transfers)

    #     return jsonify({"transfers" : transfer_count})

    def get_collection_stats(self, collectionID):
        with self.db.start_session() as session:

            result = self.db.collections.get_collection(db_session=session, contract_address=collectionID)

            response = jsonify(result.to_dict())

        return response

    def token_list(self, collectionID, tokenID):
        # starts a session
        with self.db.start_session() as session:
            # gets transfers for a certain token
            result = self.db.get_token_transfers(db_session=session, contract_address=collectionID, token_id=tokenID)

            # creates a graph from those transfers
            graph = self.graph_service.create_token_graph(result)

            # exports to format readable by the frontend
            json_graph = self.graph_service.export_json(graph)

            # convert to json and
            response = jsonify(json_graph)
            response.headers.add('Access-Control-Allow-Origin', '*')

        return response

    def get_token_statistics(self, collectionID, tokenID):
        with self.db.start_session() as session:
            res = self.db.tokens.get_token(db_session=session, contract_address=collectionID, token_id=tokenID)
            
            response = jsonify(res[0].to_dict())
            response.headers.add('Access-Control-Allow-Origin', '*')

        return response


    def token(self, collectionID, tokenID):
        raise NotImplementedError("Not yet implemented");

    def collectionAddress(self, collectionID, addressID):
        raise NotImplementedError("Not yet implemented");

    def collectionGroup(self, collectionID):
        db = DatabaseModel.DatabaseModel()
        with db.start_session() as session:
            result = db.get_grouped_transfers(db_session=session, contract_address=collectionID)

            list = [((db.group_to_dict(row))) for row in result]

        return jsonify(list)

    def address(self, addressID):
        raise NotImplementedError("Not yet implemented");

    def start_api(self):
        self.app.run(debug=True)

    def _add_endpoint(self, endpoint, method, methods: list = ['GET']):
        self.app.add_url_rule(rule=endpoint, endpoint=method.__name__, view_func=method, methods=methods)
