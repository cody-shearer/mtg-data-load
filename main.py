# This file will run on startup and update card data.
# All vintage legal, non token, non rear facing creature cards will be loaded.
# Data is stored in a local MariaDB instance and in the file system. 
# All card data is pulled from the Scryfall API Oracle Card data set found here https://scryfall.com/docs/api/bulk-data
# Images come from the Scryfall Imagery API for art_crop found here https://scryfall.com/docs/api/images

import json
import mariadb
import os
import requests
import time
import urllib3
import uuid
from io import BytesIO
from PIL import Image

def main():
    cards = []

    # stop mysql, pi zero cannot handle parsing ~70 MB of json with mysql running
    os.system('/etc/init.d/mysql stop')

    for card in get_oracle_cards():
        cmc = card['cmc']
        legality = card['legalities']['vintage']
        if 'image_uris' in card:
            art_uri = card['image_uris']['art_crop']

        # only select the front face of 2 faced cards
        if 'card_faces' in card:  
            card = card['card_faces'][0]
            if 'image_uris' in card:
                # dual faced cards sometimes have card art and front face art, front face is preferred
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

    os.system('/etc/init.d/mysql start')

    conn = mariadb.connect(host='127.0.0.1', user='root', password= 'pass', db='mtg')

    create_temp_table(conn)

    insert_cards(conn, cards)
    print('Data loaded to MySql')

    del cards

    upsert(conn)
    print('Data merged')

    # make folders as needed
    path = '/home/pi/card_images/'
    if not os.path.exists(path):
        os.mkdir(path)

    for i in range(0, 21):
        cmc_path = path + str(i)
        if not os.path.exists(cmc_path):
            os.mkdir(cmc_path)

    print('File structure created')

    for card in get_cards_missing_images(conn):
        # wait as requested by API. needed to prevent IP ban.
        time.sleep(0.05)

        try:
            response = requests.get(card[2])
            img = Image.open(BytesIO(response.content))
        except:
            pass
        else:
            file_path = '/home/pi/card_images/' + \
                str(card[1]) + '/' + str(uuid.uuid1()) + '.png'

            img = img.convert(mode='L')
            img = img.resize((304, 245))
            img.save(file_path)

            update_card_image(conn, card[0], file_path)

            print(card[0])

    print('Done!')

def get_oracle_cards():
    http = urllib3.PoolManager()
    bulkrequest = http.request('GET', 'https://api.scryfall.com/bulk-data')
    bulkdata = json.loads(bulkrequest.data)

    oracleurl = [obj for obj in bulkdata['data']
        if obj['name'] == 'Oracle Cards'][0]['download_uri']

    return json.loads(http.request('GET', oracleurl).data)


def create_temp_table(connection):
    cursor = connection.cursor()
    sql = (
        'create temporary table \
            mtg.oracle_staging \
        select \
            name, mana_cost, type, rules, artist, power, toughness, cmc, art_uri \
        from \
            mtg.oracle_cards \
        limit 0')
    cursor.execute(sql)
    connection.commit()


def insert_cards(connection, cards):
    cursor = connection.cursor()
    sql = (
        'insert into mtg.oracle_staging \
            (name, mana_cost, type, rules, artist, power, toughness, cmc, art_uri) \
        values \
            (%s, %s, %s, %s, %s, %s, %s, %s, %s)')
    cursor.executemany(sql, cards)
    connection.commit()


def upsert(connection):
    cursor = connection.cursor()
    sql = (
        'insert into \
            mtg.oracle_cards ( \
                name, mana_cost, type, rules, artist, power, toughness, cmc, art_uri) \
        select \
            os.name, os.mana_cost, os.type, os.rules, os.artist, os.power, os.toughness, os.cmc, os.art_uri \
        from \
            mtg.oracle_staging os \
        on duplicate key update \
            name = os.name, mana_cost = os.mana_cost, type = os.type, rules = os.rules, artist = os.artist, power = os.power, toughness = os.toughness, cmc = os.cmc, art_uri = os.art_uri')
    cursor.execute(sql)
    connection.commit()


def get_cards_missing_images(connection):
    cursor = connection.cursor()
    sql = (
        'select \
            id, cmc, art_uri, art_file \
        from \
            mtg.oracle_cards \
        where \
            art_file is null \
            and not art_uri is null')
    cursor.execute(sql)
    return cursor.fetchall()


def update_card_image(connection, card_id, art_file):
    cursor = connection.cursor()
    sql = (
        'update \
            mtg.oracle_cards \
        set \
            art_file = %s \
        where \
            id = %s')
    cursor.execute(sql, (art_file, card_id))
    connection.commit()


if __name__ == '__main__':
    main()
