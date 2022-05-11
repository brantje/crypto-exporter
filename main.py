from pprint import pprint
from pyparsing import empty

from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import urllib.request
from urllib.error import URLError, HTTPError
import json
from os import getenv
from prometheus_client import start_http_server, Gauge, REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR 
from time import sleep
import yaml
from pycoingecko import CoinGeckoAPI


[REGISTRY.unregister(c) for c in [PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR ]]


with open("./config.yml", "r") as stream:
    try:
        CONFIG = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)
        exit(1)


print('Config loaded')

cg = CoinGeckoAPI()

WALLET_BALANCE = Gauge('wallet_balance','wallet_balance', ['currency'])

EXCHANGE_RATE = Gauge('exchange_rate','Current exchange rates', ['currency', 'reference_currency'])

def request(url):
    try:
        req = urllib.request.Request(
            url, 
            data=None, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'
            }
        )
        with urllib.request.urlopen(req) as url:
            data = json.loads(url.read())
            return data
    except HTTPError as e:
        # do something
        print('Error code: ', e.read().decode())
    except URLError as e:
        # do something
        print('Reason: ', e.reason)                


def get_wallet_info(coin, wallet):
    balance = 0
    if coin == 'nimiq-2':
        data = request('https://api.nimiq.cafe/account/'+ wallet.replace(' ','+') +'?api_key=3140dff157ba307b2ea9e32df3b35c64')
        balance = data.get('balance')
    else:
        print('Using ubiquity')    
    display_name = CONFIG.get('coins', {}).get(coin, {}).get('display_name', coin).capitalize()
    WALLET_BALANCE.labels(currency=display_name).set(balance)


def coins_info(coins=[]):
    coins_string = ','.join(map(str, coins.keys()))
    print('Fetching info for', coins_string, 'from CoinGecko')

    reference_currency = CONFIG.get('currencies')
    price_data = cg.get_price(ids=coins_string, vs_currencies=reference_currency)    
    for coin in coins.keys():
        coin_price = price_data.get(coin, None)
        
        if not coin_price:
            print(coin + ' not found')
        else:     
            c = CONFIG.get('coins', {}).get(coin, {})
            display_name = c.get('display_name', coin).capitalize()
            for cur_ref in coin_price:
                EXCHANGE_RATE.labels(currency=display_name, reference_currency=cur_ref).set(coin_price.get(cur_ref))
        wallets = CONFIG.get('coins', {}).get(coin, {}).get('wallets', None)    
        if wallets:
            for wallet in wallets:
                if wallet:
                    get_wallet_info(coin, wallet)
if __name__ == '__main__':
    port = getenv('EXPORTER_PORT', 8000)
    start_http_server(port)
    print('Prometheus exporter running at port', port)
    while True:
        coins_info(CONFIG.get('coins', []))
        sleep(60)

