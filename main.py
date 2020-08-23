#This file will run on startup and update card data.
#All vintage legal, non token, non rear facing creature cards will be loaded.
#All card data is pulled from the Scryfall API Oracle Card data set found here https://scryfall.com/docs/api/bulk-data
#Images come from the Scryfall Imagery API for art_crop found here https://scryfall.com/docs/api/images

import urllib3
import json
import mysql.connector
import uuid
import os
import time
from PIL import Image
import requests
from io import BytesIO

def get_oracle_cards():
    http = urllib3.PoolManager()
    bulkrequest = http.request('GET', 'https://api.scryfall.com/bulk-data')
    bulkdata = json.loads(bulkrequest.data)

    #this is the most recent url for the bulk oracle data
    oracleurl = [obj for obj in bulkdata['data'] if obj['name']=='Oracle Cards'][0]['download_uri']
    oraclerequest = http.request('GET', oracleurl)

    ret = json.loads(oraclerequest.data)
    return  ret

def process_image(url):
    pass    

def create_temp_table(connection):
    cursor = connection.cursor()
    sql = (
        'create temporary table mtg.oracle_staging \
        select name, mana_cost, type, rules, artist, power, toughness, cmc, art_uri \
        from mtg.oracle_cards limit 0')
    cursor.execute(sql)
    connection.commit()

def insert_cards(connection, cards):
    cursor = connection.cursor()
    sql = (
        'insert into mtg.oracle_staging(name, mana_cost, type, rules, artist, power, toughness, cmc, art_uri) \
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s)')
    cursor.executemany(sql, cards)    
    connection.commit()

def upsert(connection):
    cursor = connection.cursor()
    sql = (
        'insert into \
            mtg.oracle_cards (\
            name, mana_cost, type, rules, artist, power, toughness, cmc, art_uri)\
        select\
            os.name, os.mana_cost, os.type, os.rules, os.artist, os.power, os.toughness, os.cmc, os.art_uri\
        from\
            mtg.oracle_staging os\
        left join\
            mtg.oracle_cards oc\
                on os.name = oc.name\
        where\
            oc.name is null\
        on duplicate key update\
            name = os.name, mana_cost = os.mana_cost, type = os.type, rules = os.rules, artist = os.artist, power = os.power, toughness = os.toughness, cmc = os.cmc, art_uri = os.art_uri')
    cursor.execute(sql)
    connection.commit()

def get_cards_missing_images(connection):
    cursor = connection.cursor()
    sql = (
        'select\
            id, cmc, art_uri, art_file\
        from\
            mtg.oracle_cards\
        where\
            art_file is null\
            and not art_uri is null')
    cursor.execute(sql)
    return cursor.fetchall()

def update_card_image(connection, name, art_file):
    cursor = connection.cursor()
    sql = (
        'update\
            mtg.oracle_cards\
        set\
            art_file = %s\
        where\
            id = %s')
    cursor.execute(sql, (art_file, name))
    connection.commit()

cards = []

for card in get_oracle_cards():
    cmc = card['cmc']
    legality = card['legalities']['vintage']
    if 'image_uris' in card:
        art_uri = card['image_uris']['art_crop']

    if 'card_faces' in card: #only selecting the front face of 2 faced cards
        card = card['card_faces'][0]
        if 'image_uris' in card:
            art_uri = card['image_uris']['art_crop'] 

    if 'Creature' in card['type_line'] and legality != 'not_legal':
        cards.append([
            card['name'],
            card['mana_cost'].replace('{', '').replace('}', ''),
            card['type_line'],
            card['oracle_text'],
            card['artist'],
            card['power'],
            card['toughness'],
            cmc,
            art_uri])

conn = mysql.connector.connect(host='localhost', user ='root', password = 'pass', db='mtg', port=3306)

create_temp_table(conn)

insert_cards(conn, cards)

del cards

upsert(conn)

#make folders as needed
for i in range(0, 21):
    path = '/home/pi/card_images/' + str(i)
    if not os.path.exists(path):
        os.mkdir(path)

for card in get_cards_missing_images(conn)[0]:
    #wait as requested by API. needed to prevent IP ban. 
    time.sleep(0.1)

    try:
        response = requests.get(card[2])
        img = Image.open(BytesIO(response.content))
    except:
        pass
    else:
        file_path = '/home/pi/card_images/' + str(card[1]) + '/' + str(uuid.uuid1()) + '.png'

        img = img.convert(mode='L')
        img = img.resize((304, 245))
        img.save(file_path)

        update_card_image(conn, card[0], file_path)

        print(card)

print('Done!')
        





