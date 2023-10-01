import socket
import sqlite3
import signal

### GLOBAL VARIABLES ###
# Host and Port info
HOST = '127.0.0.1'
PORT = 65432

# For zipping select results to reference in messages relayed to client
USER_KEYS = ('id', 'email', 'first_name', 'last_name', 'user_name', 'password', 'usd_balance')
CARD_KEYS = ('id', 'card_name', 'card_type', 'rarity', 'count', 'owner_id')

#Error codes
OK = '200 OK'
INVALID = '400 invalid command'
FORMAT = '403 message format order'

# Create tables
def createTables(con, c):
    # No AUTO_INCREMENT support like w/ example table in sqlite3 for python
    #   Still auto increments for each entry added, so it does the same thing
    # Users Table
    c.execute("""CREATE TABLE IF NOT EXISTS Users (
            ID INTEGER PRIMARY KEY,
            email TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            user_name INTEGER NOT NULL,
            password INTEGER,
            usd_balance DOUBLE NOT NULL
    );""")
    con.commit() # Commit changes to DB

    # Pokemon Cards Table
    c.execute("""CREATE TABLE IF NOT EXISTS Pokemon_cards (
            ID INTEGER PRIMARY KEY,
            card_name TEXT NOT NULL,
            card_type TEXT NOT NULL,
            rarity TEXT NOT NULL,
            count INTEGER,
            owner_id INTEGER,
            FOREIGN KEY (owner_id) REFERENCES Users (ID)
    );""")
    con.commit() # Commit changes to DB

# Test insert query
def testInsert(con, c):
    c.execute("""INSERT INTO Users (email, first_name, last_name, user_name, usd_balance) VALUES
            ('jhwisnie@umich.edu', 'Jacob', 'Wisniewski', 1, 100),
            ('jsmith@hotmail.com', 'John', 'Smith', 2, 100),
            ('jdoe@gmail.com', 'Jane', 'Doe', 3, 100),
            ('njspence@umich.edu', 'Nick', 'Spencer', 4, 100);""")
    con.commit() # Commit changes to DB
    
    # Test insert query
    c.execute("""INSERT INTO Pokemon_cards (card_name, card_type, rarity) VALUES
            ('Pikachu', 'Electric', 'Common'),
            ('Charizard', 'Fire', 'Rare'),
            ('Jiggglypuff', 'Normal', 'Common'),
            ('Bulbasaur', 'Grass', 'Common');""")
    con.commit() # Commit changes to DB

# Test select query
def testSelect(c):
    res = c.execute("SELECT * FROM Users;")
    results = res.fetchall()
    # If no results tell so
    if not results:
        print('nothing found')
    for item in results: # Print query result, results in list form
        print(item)
    print()

    res = c.execute("SELECT * FROM Pokemon_cards")
    results = res.fetchall()
    # If no results tell so
    if not results:
        print('nothing found')
    for item in results: # Print query result, results in list form
        print(item)
    print()

# Ctrl-C handler for graceful interrupt exit
def handler(signum, frame):
    res = input('\nCtrl-c was pressed. Do you really want to exit? y/n ')
    if res.lower() == 'y':
        exit(1)

def getUser(user_id, c):
    res = c.execute(f"SELECT * FROM Users WHERE ID = '{user_id}'")
    results = res.fetchone()
    selected_user = dict(zip(USER_KEYS, results))
    return selected_user

# User buys a card
# Deduct card 
def buyCard(data):
    pass

def sellCard(data):
    pass

def listCardsForOwner(data):
    pass

def listBalanceForOwner(data, c):
    id = data.pop(0)
    if not id.isnumeric():
        return FORMAT + '\nBalance requires a user to be specified'
    user = getUser(id, c)
    if not user:
        return INVALID + f'\nNo user {id} exists'
    pass

def tokenizer(data, con, c):
    tokens = data.split()
    token = tokens.pop(0)
        
    if token.upper() == 'BUY':
        return buyCard(tokens, con, c)
    elif token.upper() == 'SELL':
        return sellCard(tokens, con, c)
    elif token.upper() == 'LIST':
        return listCardsForOwner(tokens, c)
    elif token.upper() == 'BALANCE':
        return listBalanceForOwner(tokens, c)
    else:
        return INVALID

def main():
    con = sqlite3.connect('database.db') # Open/create and connect to database
    c = con.cursor()                     # Create a cursor

    # Create Tables
    createTables(con, c)

    # Test insert query
    testInsert(con, c)

    # Test select query
    testSelect(c)

    # Tied to Ctrl-C handler, run before connection loop
    signal.signal(signal.SIGINT, handler)

    # Looped socket connection
    # Where I put what I need to happen with data entered
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen()
            conn, addr = s.accept()
            with conn:
                print(f'Connected by {addr}')
                while True:
                    data = conn.recv(1024).decode()                # Data received from client
                    print(f'Received: {data}\n')

                    # Client wishes to log off
                    if data == 'QUIT':
                        conn.sendall(bytes(OK, encoding='ASCII'))
                        break
                    # No data received, client is not connected, wait for new client
                    elif not data:
                        break
                    # Client wishes to shutdown server
                    elif data == 'SHUTDOWN':                       
                        conn.sendall(bytes(OK, encoding='ASCII'))
                        print('SERVER SHUTDOWN INITIATED BY USER...')
                        break
                    
                    message = tokenizer(data, con, c)

                    conn.sendall(bytes(message, encoding='ASCII'))
                if data == 'SHUTDOWN':                             # Only triggered via SHUTDOWN command, otherwise loop for new connections
                    break

if __name__ == '__main__':
    main()

# Misc functions
"""
if not results:
    print('nothing found')
# Print query result
for item in results:
    print(item)
"""

# Notes for program structure
"""
def getUser()

def getCard()

def updateUser()

def updateCard()

def insert()
    builds query from tokenized string
    performs query

def buy()
    builds query from tokenized string

def sell()
    builds query from tokenized string

def tokenizer()
    tokenize string
    pass along to relevant function

def main()
    runs server
    builds db
    takes prompts from client

try catch, 
    if error
    print error, continue
"""