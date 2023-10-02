import socket
import sqlite3
import signal

# GLOBAL VARIABLES
########################
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
def keyboardInterruptHandler(signum, frame):
    res = input('\nCtrl-c was pressed. Do you really want to exit? y/n ')
    if res.lower() == 'y':
        exit(1)

def getUser(user_id, c):
    selected_user = None

    res = c.execute(f"SELECT * FROM Users WHERE ID = '{user_id}'") # db query for selected user
    result = res.fetchone()                                        # Tuple for result
    # If result of query is no an empty tuple
    if result:
        selected_user = dict(zip(USER_KEYS, result))              # Zip associated user fields to results in a dict for easier formatting of return message later on
    return selected_user

def getCard(user_id, c):
    selected_cards = None

    res = c.execute(f"SELECT * FROM Pokemon_cards WHERE owner_id = '{user_id}'") # db query for selected card
    results = res.fetchall()                                                     # Tuples of results
    if results:
        for item in results:
            selected_cards = dict(zip(CARD_KEYS, item))                          # Zip associated card fields to results in a duct for easier formatting of return message later on
    return selected_cards

def updateOwner(user, card):
    pass

def deductFunds(user, funds):
    pass

def addFunds(user, funds):
    pass

# User buys a card
def buyCard(data):
    pass

# User sells a card
def sellCard(data):
    pass

# List cards by owner
def listCardsForOwner(data, C):
    pass

# Summary: Takes parameters following "BALANCE" and returns an appropriate reponse for both errors and legitimate requests
# Pre-conditions : "BALANCE" was the first token determined
# Post-conditions: Error message or success message both w/ appropriate details returned to user
def listBalanceForOwner(data, c):
    # No additional arguments
    if len(data) == 0:
        message = FORMAT + "\nBALANCE requires a user to be specified" # Error 403, no user argument received
        return message
    id = data.pop(0)                                                   # Get the next argument
    # If next argument is not an integer
    if not id.isnumeric():
        message = FORMAT + "\nBALANCE requires integer for lookup"     # Error 403, need number for lookup
        return message
    user = getUser(id, c) # Find correlated user, returns None if non-existent
    # getUser() returns an empty dict
    if not user:
        message = FORMAT + f"\nNo user {id} exists"                    # Error 403, selected user does not exist
        return message
    message = OK + f"\nBalance for user {user['first_name']} {user['last_name']}: ${user['usd_balance']:.2f}" # Success w/ appropriate first name, last name, and balance
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
        return sellCard(tokens, con, c)
    elif token.upper() == "LIST":
        return listCardsForOwner(tokens, c)
    elif token.upper() == "BALANCE":
        return listBalanceForOwner(tokens, c)
    else:
        return INVALID

def main():
    con = sqlite3.connect('database.db') # Open/create and connect to database
    c = con.cursor()                     # Create a cursor

    # Create Tables
    createTables(con, c)

    # Test insert query
    #testInsert(con, c)

    # Test select query
    #testSelect(c)

    # Keyboard Interrupt Handler for graceful exit with Ctrl-C
    signal.signal(signal.SIGINT, keyboardInterruptHandler)
    
    ###############
    # Testing without socket environment needed, will be removed later
    data = ["balance 3", "balance 0", "balance 5", "balance e", "balance"]
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
data = ["SHUTDOWN"]                                                    # Testing SHUTDOWN - DONE

data = ["QUIT"]                                                        # Testing QUIT - DONE

data = ["balance 3", "balance 0", "balance 5", "balance e", "balance"] # Testing BALANCE - DONE

data = [] # Testing LIST

data = [] # Testing BUY

data = [] # Testing SELL
"""