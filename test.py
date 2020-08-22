import mysql.connector

connection = mysql.connector.connect(host='localhost', user ='root', password = 'pass')

query = 'create database mtgdb'

cursor = connection.cursor()
result = cursor.execute(query)

a=1

