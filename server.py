import socket
import sqlite3
import signal

# GLOBAL VARIABLES
########################
# Host and Port info
HOST = "127.0.0.1"
PORT = 65432

# For zipping select results to reference in messages relayed to client
USER_KEYS = ('id', 'email', 'first_name', 'last_name', 'user_name', 'password', 'usd_balance')
CARD_KEYS = ('id', 'card_name', 'card_type', 'rarity', 'count', 'owner_id')

# Error codes
OK = "200 OK"
INVALID = "400 invalid command"
FORMAT = "403 message format order"
NOT_FOUND = "404 no record found"

# Length variables
LONGEST_POKEMON_NAME = len("Crabominable") + 1 # Longest pokemon name at project time
LIST_ARG_LEN = 1
BALANCE_ARG_LEN = 1
SELL_ARG_LEN = 4
BUY_ARG_LEN = 5
########################

# Create tables
def createTables(con, c):
    # No AUTO_INCREMENT support like w/ example table in sqlite3 for python
    #   Still auto increments for each entry added, so it does the same thing
    # Users Table, checks if no users table exists and will create one, else carries on
    c.execute("""CREATE TABLE IF NOT EXISTS Users (
            ID INTEGER PRIMARY KEY,
            email TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            user_name INTEGER NOT NULL,
            password INTEGER,
            usd_balance DOUBLE NOT NULL
    );""")
    con.commit() # Commit changes to db

    # Pokemon cards Table, checks if no pokemon cards table exists and will create one, else carries on
    c.execute("""CREATE TABLE IF NOT EXISTS Pokemon_cards (
            ID INTEGER PRIMARY KEY,
            card_name TEXT NOT NULL,
            card_type TEXT NOT NULL,
            rarity TEXT NOT NULL,
            count INTEGER,
            owner_id INTEGER,
            FOREIGN KEY (owner_id) REFERENCES Users (ID)
    );""")
    con.commit() # Commit changes to db

# Test insert query
def testInsert(con, c):
    c.execute("""INSERT INTO Users (email, first_name, last_name, user_name, usd_balance) VALUES
            ('jhwisnie@umich.edu', 'Jacob', 'Wisniewski', 1, 100.00),
            ('jsmith@hotmail.com', 'John', 'Smith', 2, 100.00),
            ('jdoe@gmail.com', 'Jane', 'Doe', 3, 100.00),
            ('njspence@umich.edu', 'Nick', 'Spencer', 4, 100.00);""")
    con.commit() # Commit changes to db
    
    # Test insert query
    c.execute("""INSERT INTO Pokemon_cards (card_name, card_type, rarity, count, owner_id) VALUES
            ('Pikachu', 'Electric', 'Common', 3, 1),
            ('Charizard', 'Fire', 'Rare', 2, 1),
            ('Jiggglypuff', 'Normal', 'Common', 1, 2),
            ('Bulbasaur', 'Grass', 'Common', 1, 1);""")
    con.commit() # Commit changes to db

# Test select query
def testSelect(c):
    res = c.execute("SELECT * FROM Users;")
    results = res.fetchall()
    # No results? Tell so
    if not results:
        print("nothing found")
    for item in results: # Print query result, results in list form
        print(item)
    print()

    res = c.execute("SELECT * FROM Pokemon_cards")
    results = res.fetchall()
    # No results? Tell so
    if not results:
        print("nothing found")
    for item in results: # Print query result, results in list form
        print(item)
    print()

# Ctrl-C handler for graceful interrupt exit
def keyboardInterruptHandler(signum, frame):
    res = input("\nCtrl-c was pressed. Do you really want to exit? y/n ")
    if res.lower() == 'y':
        exit(1)

def getUser(user_id, c):
    selected_user = None

    res = c.execute(f"SELECT * FROM Users WHERE ID = '{user_id}'") # db query for selected user
    result = res.fetchone()                                        # Tuple for result
    # Result of query is not an empty tuple
    if result:
        selected_user = dict(zip(USER_KEYS, result))               # Map associated user fields to results in a dict for easier formatting of return message later on
    return selected_user

def getCardByOwnerAndName(owner_id, c_name, c):
    selected_card = {}

    res = c.execute(f"SELECT * FROM Pokemon_cards WHERE owner_id = '{owner_id}' AND card_name = '{c_name}'")
    result = res.fetchone()
    if result:
        selected_card = dict(zip(CARD_KEYS, result))               # Map associated user fields to results in a dict for easier formatting of return message later on
    return selected_card

def getCardByOwner(owner_id, c):
    selected_cards = []

    res = c.execute(f"SELECT * FROM Pokemon_cards WHERE owner_id = '{owner_id}'") # db query for selected card
    results = res.fetchall()                                                      # Tuples of results
    # Result of query is not an empty tuple
    if results:
        for item in results:
            selected_cards.append(item)                                           # Map associated card fields to results in a duct for easier formatting of return message later on, add it into selected_cards list
    return selected_cards

def is_float(string):
    try:
        float(string)
        return True
    except:
        return False

def updateUser(user, con, c):
    c.execute(f"UPDATE Users SET 'usd_balance' = {user['usd_balance']} WHERE id = {user['id']};")
    con.commit()    

def updateCard(card, con, c):
    c.execute(f"UPDATE Pokemon_cards SET 'count' = {card['count']} WHERE id = {card['id']};")
    con.commit()

def buyCard(data):
    pass

# User buys a card
def buy(data):
    pass

def sellCard(c_name, c_quantity, c_price, c_owner, con, c):
    user = getUser(c_owner, c)
    card = getCardByOwnerAndName(c_owner, c_name, c)

    if int(c_quantity) > card['count']:
        message = INVALID + "\nCard quantity too low"
        return message
    
    user['usd_balance'] += float(c_price)
    card['count'] -= int(c_quantity)
    if card['count'] == 0:
        # remove card
        pass
    
    updateUser(user, con, c)
    updateCard(card, con, c)
    testSelect(c)

    return OK + f"\nSOLD: New balance: {card['count']} Pikachu. User’s balance USD ${user['usd_balance']}"

# User sells a card
def sell(data, con, c):
    if len(data) < SELL_ARG_LEN:
        message = FORMAT + "\nNot enough SELL args"
        return message
    elif len(data) > SELL_ARG_LEN:
        message = FORMAT + "\nToo many SELL args"
        return message
    
    c_name = data.pop(0)
    c_quantity = data.pop(0)
    if not c_quantity.isnumeric():
        message = FORMAT + "\nSELL quantity is not an integer"
        return message
    
    c_price = data.pop(0)
    if not is_float(c_price):
        message = FORMAT + "\nSELL price is not a double"
        return message
    
    c_owner = data.pop(0)
    if not c_owner.isnumeric():
        message = FORMAT + "\nSELL owner is not an integer"
        return message

    message = sellCard(c_name, c_quantity, c_price, c_owner, con, c)

    return message

# List cards by owner
def listCardsForOwner(owner_id, c):
    cards = getCardByOwner(owner_id, c)

    if not cards:
        message = NOT_FOUND + f"\nNo cards owned by {owner_id}, user may not exist"                         # Error 404, selected user does not exist
        return message
    
    message = OK + f"\nThe list of records in the Pokemon cards table for current user, user {owner_id}:\n"
    for item in CARD_KEYS:
        message += f"{item.ljust(LONGEST_POKEMON_NAME, ' ')}"
    message += '\n'
    for card in cards:
        for field in card:
            message += f"{str(field).ljust(LONGEST_POKEMON_NAME, ' ')}"
        message += '\n'

    return message

def listC(data, c):
    # If there is no argument
    if len(data) == 0:
        message = FORMAT + "\nLIST requires a user to be specified" # Error 403, no user argument received
        return message
    id = data.pop(0)                                                # Store next argument
    # If next argument is not an integer
    if not id.isnumeric():
        message = FORMAT + "\nLIST requires integer for lookup"     # Error 403, need number for lookup
        return message
    # If there is more than one argument
    if data:
        message = FORMAT + "\nLIST only takes one argument"         # Error 403, more than one argument
        return message
    message = listCardsForOwner(id, c)                              # Hand off to message builder
    return message

# Summary: Takes parameters following "BALANCE" and returns an appropriate reponse for both errors and legitimate requests
# Pre-conditions : "BALANCE" was the first token determined
# Post-conditions: Error message or success message both w/ appropriate details returned to user
def balanceForOwner(user_id, c):
    user = getUser(user_id, c)                                                                                # Find correlated user, returns empty dict if non-existent
    # getUser() returns an empty dict
    if not user:
        message = NOT_FOUND + f"\nNo user {user_id} exists"                                                   # Error 404, selected user does not exist
        return message
    
    message = OK + f"\nBalance for user {user['first_name']} {user['last_name']}: ${user['usd_balance']:.2f}" # Success w/ appropriate first name, last name, and balance
    return message

def balance(data, c):
    # If there is no argument
    if len(data) == 0:
        message = FORMAT + "\nBALANCE requires a user to be specified" # Error 403, no user argument received
        return message
    
    id = data.pop(0)                                                   # Store next argument
    # If next argument is not an integer
    if not id.isnumeric():
        message = FORMAT + "\nBALANCE requires integer for lookup"     # Error 403, need number for lookup
        return message
    # If there is more than one argument
    if data:
        message = FORMAT + "\nBALANCE only takes one argument"         # Error 403, more than one argument
        return message
    
    message = balanceForOwner(id, c)                                   # Hand off to message builder
    return message

# Summary: Splits user-entered messages into tokens by a delimiter ' ', checks for valid commands of the server, pushes remaining arguments into appropriate
#          functions w/ db related APIs.  Returns a message relayed back from the related functions (valid or error), or an error for an INVALID command
# Pre-conditions : Message entered into the server by a user
# Post-conditions: Appropriate response from related functions or an error for invalid command
def tokenizer(data, con, c):
    tokens = data.split()
    token = tokens.pop(0)
        
    if token.upper() == "BUY":
        return buyCard(tokens, con, c)
    elif token.upper() == "SELL":
        return sell(tokens, con, c)
    elif token.upper() == "LIST":
        return listC(tokens, c)
    elif token.upper() == "BALANCE":
        return balance(tokens, c)
    else:
        return INVALID

def main():
    con = sqlite3.connect('database.db') # Open/create and connect to database
    c = con.cursor()                     # Create a cursor

    # Create Tables
    createTables(con, c)

    # Test insert query, only need to run this to regen database if deleted locally.
    #testInsert(con, c)

    # Test select query, just some fun with the select query to ensure it and insert worked properly
    #testSelect(c)

    # Keyboard Interrupt Handler for graceful exit with Ctrl-C
    signal.signal(signal.SIGINT, keyboardInterruptHandler)
    
    ###############
    # Testing without socket environment needed, will be removed later
    data = ["SELL Pikachu 1 34.99 1"]
    for item in data:
        print(f"###############\nReceived: {item}\n")
        message = tokenizer(item, con, c)
        print(f"To send to user:\n{message}\n###############\n")
    return
    ###############

    # Looped socket connection - DONE
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen()
            conn, addr = s.accept()
            with conn:
                print(f"Connected by {addr}")
                while True:
                    data = conn.recv(1024).decode()                # Data received from client
                    print(f"Received: {data}\n")

                    # Client wishes to log off
                    if data == "QUIT":
                        conn.sendall(bytes(OK, encoding="ASCII"))
                        break
                    # No data received, client is not connected, wait for new client
                    elif not data:
                        break
                    # Client wishes to shutdown server
                    elif data == "SHUTDOWN":                       
                        conn.sendall(bytes(OK, encoding="ASCII"))
                        print('SERVER SHUTDOWN INITIATED BY USER...')
                        break
                    
                    message = tokenizer(data, con, c)              # Process message received if not "SHUTDOWN" or "QUIT"

                    conn.sendall(bytes(message, encoding="ASCII"))
                if data == "SHUTDOWN":                             # Only triggered via SHUTDOWN command, otherwise loop for new connections
                    break

                # take loop and put it in function and then let it be handler for cmd line data locally

if __name__ == "__main__":
    main()

# Test Data
"""
data = ["SHUTDOWN"]                                                                                                                                                 # Testing SHUTDOWN - DONE

data = ["QUIT"]                                                                                                                                                     # Testing QUIT - DONE

data = ["balance 3", "balance 0", "balance 5", "balance e", "balance", "balance 3 4", "BALANCE 3", "BALANCE 0", "BALANCE 5", "BALANCE E", "BALANCE", "BALANCE 3 4"] # Testing BALANCE - DONE

data = ["list 1", "list 2", "list 0", "list 5", "list e", "list", "list 2 3", "LIST 1", "LIST 2", "LIST 0", "LIST 5", "LIST e", "LIST", "LIST 2 3"]                 # Testing LIST - DONE

data = [] # Testing BUY

data = ["SELL Pikachu 1 34.99 1"] # Testing SELL
"""