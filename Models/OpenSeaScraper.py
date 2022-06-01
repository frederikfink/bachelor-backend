import json
import time
from selenium import webdriver
import requests
from selenium.webdriver.common.by import By
from colorama import Fore, Style
from Models import DatabaseModel as dbm
from Models import CollectionService

Db_Model, Transfer = dbm.DatabaseModel, dbm.Transfer.Transfer

Collection, Slug = dbm.Collection.Collection, dbm.Slug.Slug

# buffers for letting the browser load in next elements
# if the scraper fails, try increasing the load timers
SCROLL_PAUSE_TIME = 1
NEXT_PAGE_PAUSE_TIME = 3

class OpenSeaScraper:
    def __init__(self,
                 db: Db_Model = None,
                 etherscan_api_key: str = "",
                 collection_service: CollectionService.CollectionService = None):
        self.document_height = None
        self.collection_service = collection_service
        self.etherscan_api_key = etherscan_api_key
        self.db = db
        self.current_scroll_height = None
        self.options = None
        self.url = "https://opensea.io/rankings"
        self.slugs = set()
        self.driver = None
        self.window_height = None
        self.count = 0


    def setup(self):
        self.options = webdriver.FirefoxOptions()
        self.options.add_argument("window-size=800,800")
        self.driver = webdriver.Firefox()
        self.driver.get(self.url)
        self.window_height = 800
        self.current_scroll_height = 0
        self.driver.set_window_size(800, self.window_height)
        self.document_height = self.driver.execute_script("return document.body.scrollHeight")

        return self

    # call after any method that scrapes data
    def teardown(self):
        self.driver.close()

    # adds elems found to a set, removing dublicates that
    # might have been added twice since the scroll function
    # cannot guarantee no dublicates.
    # substrings the link for the slug only
    def add_elems(self, elems):
        for elem in elems:
            slug = elem.get_attribute('href')[30:]
            self.slugs.add(slug)

    # scroll function to scroll through opensea dealing with lazy loading
    # scrolls @self.window_height pixels at a time
    # updates @self.document_height as document height increases when more lines are loaded
    # sleeps for @SCROLL_PAUSE_TIME to let the page load in
    def scroll(self):
        self.current_scroll_height += self.window_height
        self.driver.execute_script(f"window.scrollTo(0, {self.current_scroll_height});")
        self.document_height = self.driver.execute_script("return document.body.scrollHeight")

        time.sleep(SCROLL_PAUSE_TIME)

    # goes to next page using navigation buttons at the bottom
    # resets values to start scraping from the top again
    def next_page(self):
        self.current_scroll_height = 0
        self.document_height = self.driver.execute_script("return document.body.scrollHeight")
        self.driver.execute_script(f"window.scrollTo(0, {self.current_scroll_height});")
        self.driver.find_element(By.XPATH, '//*[@id="main"]/div/div[3]/button[2]').click()

        self.slugs = set()
        time.sleep(NEXT_PAGE_PAUSE_TIME)

    # finds all elements with specified XPATH and scrolls
    # to next section until document end
    def scrape_page(self):
        while self.current_scroll_height <= self.document_height:
            elems = self.driver.find_elements(By.XPATH, "//a[@role = 'row']")
            self.add_elems(elems)
            self.scroll()

    # status printer helper function
    def print_status(self, message, emoji, slug, index):
        print(f"{emoji} ({index} / {len(self.slugs)})\t{slug} " + Fore.LIGHTRED_EX + f"{message}" + Style.RESET_ALL)

    # uses opensea api to fetch data associated with found slug
    def fetch_contract_addr(self, slug, index):
        url = "https://api.opensea.io/api/v1/collection/" + slug
        response = requests.request("GET", url)
        data = json.loads(response.text)
        collection = data['collection']

        primary_asset_contracts = collection['primary_asset_contracts']

        # happens when a collection is created through opensea using their smart contract
        if len(primary_asset_contracts) == 0:
            self.print_status("NO PRIMARY ASSET CONTRACT FOUND", "❗️", slug, index)
            return None

        # happens when a collection is using multi contract address
        # this might be because the contract is using the @EIP-1155 Multi token standard
        # https://eips.ethereum.org/EIPS/eip-1155
        if len(primary_asset_contracts) > 1:
            self.print_status("MORE THAN ONE PRIMARY ASSET CONTRACT FOUND", "❗️", slug, index)
            return None

        # happens when the contract is associated with one well defined contract address
        if len(primary_asset_contracts) == 1:
            return primary_asset_contracts[0]['address']

    # asd
    def export_collections(self):
        i = 0
        with self.db.start_session() as session:
            validator = self.db.slugs.is_empty(session)
            for slug in self.slugs:
                i += 1
                contract_address = self.fetch_contract_addr(slug, i)
                if contract_address:
                    eth_url = f"https://api.etherscan.io/api?module=account&action=txlist&address={contract_address}" \
                              f"&startblock=0" \
                              f"&endblock=99999999" \
                              f"&page=1" \
                              f"&offset=1" \
                              f"&sort=asc" \
                              f"&apikey={self.etherscan_api_key}"

                    headers = {"Accept": "application/json"}
                    # this request fetches the start block. Might replace this with Block estimation?
                    response = requests.request("GET", eth_url, headers=headers)

                    data = json.loads(response.text)
                    try:
                        start_block = int(data['result'][0]['blockNumber'])
                        ent = Slug(contract_address=contract_address, slug=slug, start_block=start_block)
                        self.db.slugs.add_slug_to_db(db_session=session, slug=ent, validator=validator)
                        self.count += 1
                        self.print_status("", "✅", slug, i)
                    except Exception as e:
                        print(e)
                        self.print_status("COULD NOT ADD COLLECTION", "❗️", slug, i)

    # limit default value determines the number of collections that are added to the db. Reset count when done.
    def scrape(self, limit: int = 200):
        try:
            while True and limit > self.count:
                if self.driver is not None:
                    print("🔎 Scraping page ...")
                    self.scrape_page()
                    print("📦 Exporting data found ...")
                    self.export_collections()
                    print("📖 waiting for next page to load ...")
                    print()
                    self.next_page()
            self.count = 0
        except KeyboardInterrupt:
            print("Program exited successfully 🔨")
            raise