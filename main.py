import urllib.request
import logging
import yaml
import json
from urllib.error import URLError, HTTPError
from os import getenv
from prometheus_client import start_http_server, Gauge, REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR 
from time import sleep
from pycoingecko import CoinGeckoAPI
from cryptotools import Xpub

[REGISTRY.unregister(c) for c in [PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR ]]


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s — %(message)s',
                    datefmt='%Y-%m-%d_%H:%M:%S',
                    handlers=[logging.StreamHandler()])

def loadConfig():
    with open("./config.yml", "r") as stream:
        try:
            CONFIG = yaml.safe_load(stream)
            return CONFIG
        except yaml.YAMLError as exc:
            logging.error(exc)
            exit(1)


CONFIG = loadConfig()
cg = CoinGeckoAPI()

WALLET_BALANCE = Gauge('crypto_wallet_balance','wallet_balance', ['currency','wallet'])

EXCHANGE_RATE = Gauge('crypto_exchange_rate','Current exchange rates', ['currency', 'reference_currency'])



def request(url, additional_headers = {}, data = None):
    if data:
        data = json.dumps(data)
        data = data.encode('utf-8')   # needs to be bytes

    try:
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36',
                'Content-Type': 'application/json; charset=utf-8',
                **additional_headers
            }
        )
        with urllib.request.urlopen(req) as url:
            data = json.loads(url.read())
            return data
    except HTTPError as e:
        # do something
        logging.info(e.code)
        logging.info('Error code: ', e.read().decode())
    except URLError as e:
        # do something
        logging.info('Reason: ', e.reason)                

def ubiquity_request(path, data = None, api_version='v2'):
    data = request('https://ubiquity.api.blockdaemon.com/'+api_version+'/'+ path, 
                    additional_headers= {'Authorization': 'Bearer '+ CONFIG.get('blockdaemon_api_key')},
                    data = data
                    )
    return data

def get_xpub_wallets(xpub, start = 1, end = 20, wallets = []):
    logging.info('xpub wallet detected')
    key = Xpub.decode(xpub)
    zero_counter = 0
    total_balance = 0
    for first_path in range(0,2):
        for i in range(start, end):
            wallet = key/first_path/i
            address = wallet.address('P2WPKH')
            data = ubiquity_request('bitcoin/mainnet/account/'+ address)
            chain = next(iter(data))
            balance = int(data.get(chain).get('balance', 0))
            total_balance += balance
            if balance == 0:
                zero_counter += 1
            else:
                #print('m/'+str(first_path)+'/'+str(i) +' '+ address +' '+ str(balance))
                zero_counter = 0

            if zero_counter == 10:
                break
    logging.info('Total balance:', total_balance/100000000)

def get_wallet_info(coin, wallet):
    balance = 0
    if coin == 'nimiq-2':
        data = request('https://api.nimiq.watch/account/'+ wallet.replace(' ','+'))
        balance = data.get('balance')
    else:   
        if 'xpub'in wallet:
           #get_xpub_wallets(wallet)
           logging.info('xpub not supported')
        else:
            data = ubiquity_request(coin + '/mainnet/account/'+ wallet)
            chain = next(iter(data))
            balance = data.get(chain).get('balance', 0)

    display_name = CONFIG.get('coins', {}).get(coin, {}).get('display_name', coin).capitalize()
    WALLET_BALANCE.labels(currency=display_name, wallet=wallet).set(balance)


def coins_info(coins=[]):
    enabled_coins =  { key:value for (key,value) in coins.items() if value.get('enabled')}
    coins_string = ','.join(map(str, enabled_coins.keys()))
    logging.info('Fetching info for {} from CoinGecko'.format(coins_string))

    reference_currency = CONFIG.get('currencies')
    price_data = cg.get_price(ids=coins_string, vs_currencies=reference_currency)    
    
    for coin in enabled_coins.keys():
        coin_price = price_data.get(coin, None)
        
        if not coin_price:
            logging.info(coin + ' not found ')
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
    logging.info(40 * '-')
    logging.info('Crypto Exporter')
    logging.info(40 * '-')
   
    port = CONFIG.get('port')
    start_http_server(port)
    logging.info('Prometheus exporter running at port {}'.format(port))
    logging.info(40 * '-')

    while True:
        coins_info(CONFIG.get('coins', []))
        sleep(60)
