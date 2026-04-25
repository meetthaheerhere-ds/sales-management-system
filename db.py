import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Thaheer@1609",
        database="sales_management_system"
    )