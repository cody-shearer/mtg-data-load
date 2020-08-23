import mysql.connector

connection = mysql.connector.connect(host='localhost', user ='root', password = 'pass', db='mtg', port=3307)

query = 'select * from test'

cursor = connection.cursor()
cursor.execute(query)

print(cursor.description)

