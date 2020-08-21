#This file will run on startup and update card data.
#All vintage legal, non token, non rear facing creature cards will be loaded.
#All card data is pulled from the Scryfall API Oracle Card data set found here https://scryfall.com/docs/api/bulk-data
#Images come from the Scryfall Imagery API for art_crop found here https://scryfall.com/docs/api/images

import urllib3
import json

def get_oracle_cards():
    http = urllib3.PoolManager()
    bulkrequest = http.request('GET', 'https://api.scryfall.com/bulk-data')
    bulkdata = json.loads(bulkrequest.data)

    #this is the most recent url for the bulk oracle data
    oracleurl = [obj for obj in bulkdata['data'] if obj['name']=='Oracle Cards'][0]['download_uri']
    oraclerequest = http.request('GET', oracleurl)

    ret = json.loads(oraclerequest.data)
    return  ret

def get_oracle_cards_test():
    f = open('oracle-cards-20200820090701.json',encoding='utf-8')
    ret = json.load(f)
    return  ret

def process_image(url):
    pass    

oracle = get_oracle_cards_test()

image_url = oracle[0]['image_uris']['art_crop']

print(image_url)