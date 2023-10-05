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
BUY_ARG_LEN = 6
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
            ('Pikachu', 'Electric', 'Common', 2, 1),
            ('Charizard', 'Fire', 'Rare', 2, 1),
            ('Jigglypuff', 'Normal', 'Common', 1, 2),
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

# HELPER FUNCTIONS
########################

# Ctrl-C handler for graceful interrupt exit
def keyboardInterruptHandler(signum, frame):
    res = input("\nCtrl-c was pressed. Do you really want to exit? y/n ")
    if res.lower() == 'y':
        exit(1)

def isFloat(string):
    try:
        float(string)
        return True
    except:
        return False

def insertCard(c_name, c_type, c_rarity, c_quantity, c_owner, con, c):
    c.execute(f"INSERT INTO Pokemon_cards (card_name, card_type, rarity, count, owner_id) VALUES ('{c_name}', '{c_rarity}', '{c_type}', {c_quantity}, {c_owner});")
    con.commit()

def getCardByOwnerNameRarity(c_name, c_rarity, c_owner, c):
    selected_card = {}

    res = c.execute(f"SELECT * FROM Pokemon_cards WHERE (card_name, rarity, owner_id) = ('{c_name}', '{c_rarity}', '{c_owner}');")
    result = res.fetchone()
    if result:
        selected_card = dict(zip(CARD_KEYS, result))               # Map associated user fields to results in a dict for easier formatting of return message later on

    return selected_card

def updateUserBalance(user, con, c):
    c.execute(f"UPDATE Users SET usd_balance = {user['usd_balance']:.2f} WHERE id = {user['id']};")
    con.commit()

def updateCardCount(card, con, c):
    c.execute(f"UPDATE Pokemon_cards SET count = {card['count']} WHERE id = {card['id']};")
    con.commit()

def deleteCard(card, c_owner, con, c):
    c.execute(f"DELETE FROM Pokemon_cards WHERE (card_name, owner_id) = ('{card['card_name']}', {c_owner});")
    con.commit()

def getCardByOwnerName(owner_id, c_name, c):
    selected_card = {}

    res = c.execute(f"SELECT * FROM Pokemon_cards WHERE (card_name, owner_id) = ('{c_name}', {owner_id});")
    result = res.fetchone()
    if result:
        selected_card = dict(zip(CARD_KEYS, result))               # Map associated user fields to results in a dict for easier formatting of return message later on

    return selected_card

def getCardByOwner(owner_id, c):
    selected_cards = []

    res = c.execute(f"SELECT * FROM Pokemon_cards WHERE owner_id = {owner_id};") # db query for selected card
    results = res.fetchall()                                                      # Tuples of results
    # Result of query is not an empty tuple
    if results:
        for item in results:
            selected_cards.append(item)                                           # Map associated card fields to results in a duct for easier formatting of return message later on, add it into selected_cards list

    return selected_cards

def numberOfArgs(data, arg_len):
    if len(data) < arg_len:
        message = FORMAT + "\nNot enough args"
        return message
    elif len(data) > arg_len:
        message = FORMAT + "\nToo many args"
        return message
    
    return None

def getUser(user_id, c):
    selected_user = None

    res = c.execute(f"SELECT * FROM Users WHERE id = {user_id};") # db query for selected user
    result = res.fetchone()                                       # Tuple for result
    # Result of query is not an empty tuple
    if result:
        selected_user = dict(zip(USER_KEYS, result))              # Map associated user fields to results in a dict for easier formatting of return message later on

    return selected_user

########################


# BALANCE FUNCTIONS
########################

# Summary: Takes parameters following "BALANCE" and returns an appropriate reponse for both errors and legitimate requests
# Pre-conditions : "BALANCE" was the first token determined
# Post-conditions: Error message or success message both w/ appropriate details returned to user
#Process Balance command
def balanceForOwner(user_id, c):
    #Get User Information
    user = getUser(user_id, c)
    if not user:    #Return if no user was found in the database
        message = NOT_FOUND + f"\nNo user {user_id} exists"                                                   # Error 404, selected user does not exist
        return message
    
    #Create and return message
    message = OK + f"\nBalance for user {user['first_name']} {user['last_name']}: ${user['usd_balance']:.2f}" # Success w/ appropriate first name, last name, and balance
    return message

#Validate BALANCE command args
def balance(data, c):
    message = numberOfArgs(data, BALANCE_ARG_LEN) #Check if command has correct number of args
    if message:                                   #Return if too many or too few args
        return message
    
    #Validate Owner ID Arg
    id = data.pop(0)                      # Store next argument
    if not id.isnumeric() or int(id) < 1: #Return if owner id is non-int or non-positive
        message = FORMAT + "\nBALANCE requires non-zero, positive integer for user"
        return message
    
    #Run BALANCE command
    message = balanceForOwner(id, c)   # Hand off to message builder

    return message
########################


# LIST FUNCTIONS
########################
#Process LIST command
def listCardsForOwner(owner_id, c):
    #Get User's Cards
    cards = getCardByOwner(owner_id, c)

    if not cards:   #Return if user owns no cards or the ID is not in the database
        message = NOT_FOUND + f"\nNo cards owned by {owner_id}, user may not exist"                         # Error 404, selected user does not exist
        return message
    
    #Print list of cards
    message = OK + f"\nThe list of records in the Pokemon cards table for current user, user {owner_id}:\n"
    for item in CARD_KEYS:
        message += f"{item.ljust(LONGEST_POKEMON_NAME, ' ')}"
    message += '\n'
    for card in cards:
        for field in card:
            message += f"{str(field).ljust(LONGEST_POKEMON_NAME, ' ')}"
        message += '\n'

    return message

#Validate LIST command args
def listC(data, c):
    message = numberOfArgs(data, LIST_ARG_LEN) #Check if command has correct number of args
    if message:                                #Return if too many or too few args
        return message
    
    #Validate Owner ID Arg
    id = data.pop(0)                      #Store next argument
    if not id.isnumeric() or int(id) < 1: #Return if owner id is non-int or non-positive
        message = FORMAT + "\nLIST requires non-zero, positive integer for user"
        return message
    
    #Run LIST Command
    message = listCardsForOwner(id, c)                          # Hand off to message builder
    return message
########################


# SELL FUNCTIONS
########################
#Process SELL command
def sellCard(c_name, c_quantity, c_price, c_owner, con, c):
    #Get User and User's Card Information
    user = getUser(c_owner, c)
    card = getCardByOwnerName(c_owner, c_name, c)

    if not user:                        #Return if user id was not in list
        message = NOT_FOUND + f"\nNo user {c_owner}"
        return message
    if not card:                        #Return if user does not own any of the card
        message = NOT_FOUND + f"\nNo Pokemon '{c_name}' owned by user {c_owner}"
        return message
    if int(c_quantity) > card['count']: #Return if the quantity is more than the card count in database
        message = INVALID + "\nSELL quantity more than card count"
        return message
    
    #Adds balance to the user, subtracts card quantity
    user['usd_balance'] += int(c_quantity)*float(c_price)
    card['count'] -= int(c_quantity)

    if card['count'] == 0: #If card count is zero, remove the card from the database
        deleteCard(card, c_owner, con, c)
    else:                  #Else, update the value in the database
        updateCardCount(card, con, c)
    updateUserBalance(user, con, c)

    return OK + f"\nSOLD: New balance: {card['count']} Pikachu. User’s balance USD ${user['usd_balance']:.2f}"

#Validate SELL command args
def sell(data, con, c):
    message = numberOfArgs(data, SELL_ARG_LEN) #Check if command has correct number of args
    if message:                                #Return if too many or too few args
        return message
    
    #Split command args
    c_name = data.pop(0)
    
    #Validate Quantity Arg
    c_quantity = data.pop(0)
    if not c_quantity.isnumeric() or int(c_quantity) < 1: #Return if quantity is non-int or non-positive
        message = FORMAT + "\nSELL requires positive, non-zero integer for quantity"
        return message
    
    #Validate Price Arg
    c_price = data.pop(0)
    if not isFloat(c_price): #Return if price is non-float type
        message = FORMAT + "\nSELL requires a float for price"
        return message
    elif float(c_price) < 0: #Return if price is non-positive
        message = INVALID + "\nSELL requires a positive float for price"
        return message
    
    #Validate Owner ID Arg
    c_owner = data.pop(0)
    if not c_owner.isnumeric() or int(c_owner) < 1: #Return if owner id is non-int or non-positive
        message = FORMAT + "\nSELL requires positive, non-zero integer for user"
        return message
    
    #Run SELL command
    message = sellCard(c_name, c_quantity, c_price, c_owner, con, c)
    return message
########################


# BUY FUNCTIONS
########################
#Proccess BUY command
def buyCard(c_name, c_type, c_rarity, c_price, c_quantity, c_owner, con, c):
    #Get User and User's Card Information
    user = getUser(c_owner, c)
    card = getCardByOwnerNameRarity(c_name, c_rarity, c_owner, c)

    if not user:                #Return if user id was not in list
        message = NOT_FOUND + f"\nNo user {c_owner}"
        return message
    
    user['usd_balance'] -= int(c_quantity) * float(c_price)
    if user['usd_balance'] < 0: #Return if selected user does not have enough funds
        message = INVALID + f"\nUser {c_owner} does not have enough funds to purchase {c_quantity} {c_name}s"
        return message
    
    if card:                    #If the card is already in the card database, increase count
        card['count'] += int(c_quantity)
        updateCardCount(card, con, c)
    else:                       #Else, add it to the card database
        insertCard(c_name, c_type, c_rarity, c_quantity, c_owner, con, c)
    updateUserBalance(user, con, c) #Update user database

    return OK + f"\nBOUGHT: New balance: {c_quantity} {c_name}. User USD balance ${user['usd_balance']:.2f}"

#Validate BUY command args
def buy(data, con, c):
    message = numberOfArgs(data, BUY_ARG_LEN) #Check if command has correct number of args
    if message:                               #Return if too many or too few args
        return message
    
    #Split command args
    c_name = data.pop(0)
    c_type = data.pop(0)
    c_rarity = data.pop(0)
    
    #Validate Price Arg
    c_price = data.pop(0)
    if not isFloat(c_price): #Return if price is non-float type
        message = FORMAT + "\nBUY requires a float for price"
        return message
    elif float(c_price) < 0: #Return if price is non-positive
        message = INVALID + "\nBUY requires a positive float for price"
        return message
    
    #Validate Quantity Arg
    c_quantity = data.pop(0)
    if not c_quantity.isnumeric() or int(c_quantity) < 1: #Return if quantity is non-int or non-positive
        message = FORMAT + "\nBUY requires positive, non-zero integer for quantity"
        return message
    
    #Validate Owner ID Arg
    c_owner = data.pop(0)
    if not c_owner.isnumeric() or int(c_owner) < 1: #Return if owner id is non-int or non-positive
        message = FORMAT + "\nBUY requires positive, non-zero integer for user"
        return message
    
    #Run BUY command
    message = buyCard(c_name, c_type, c_rarity, c_price, c_quantity, c_owner, con, c)
    return message
########################

# Summary: Splits user-entered messages into tokens by a delimiter ' ', checks for valid commands of the server, pushes remaining arguments into appropriate
#          functions w/ db related APIs.  Returns a message relayed back from the related functions (valid or error), or an error for an INVALID command
# Pre-conditions : Message entered into the server by a user
# Post-conditions: Appropriate response from related functions or an error for invalid command
def tokenizer(data, con, c):
    tokens = data.split() # Split Input Into Strings
    if not tokens:        # If No Input Given
        message = INVALID + "\nNo valid command received"
        return message
    firstToken = tokens.pop(0)
    
    # Function Selection
    if firstToken.upper() == "BUY":
        return buy(tokens, con, c)
    elif firstToken.upper() == "SELL":
        return sell(tokens, con, c)
    elif firstToken.upper() == "LIST":
        return listC(tokens, c)
    elif firstToken.upper() == "BALANCE":
        return balance(tokens, c)
    else:
        return INVALID + "\nNo valid command received"

def main():
    con = sqlite3.connect('database.db') # Open/create and connect to database
    c = con.cursor()                     # Create a cursor

    # Create Tables
    createTables(con, c)

    # Keyboard Interrupt Handler for graceful exit with Ctrl-C
    signal.signal(signal.SIGINT, keyboardInterruptHandler)

    ###############
    # Testing without socket environment needed, will be removed later
    data = ["BUY Pikachu Electric Common 19.99 2 1"]

    for item in data:
        print("###############")
        testInsert(con, c)
        testSelect(c)

        print(f"Received: {item}\n")
        message = tokenizer(item, con, c)
        print(f"To send to user:\n{message}\n")

        testSelect(c)
        print("###############\n")
        c.execute("DELETE FROM Pokemon_cards;")
        c.execute("DELETE FROM Users;")
        con.commit()

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

if __name__ == "__main__":
    main()

# Test Data
"""
data = ["SHUTDOWN"]                                                                                                                                                       # Testing SHUTDOWN - DONE

data = ["QUIT"]                                                                                                                                                           # Testing QUIT - DONE

data = ["BALANCE 3", "balance 3", "BALANCE 0", "BALANCE -1", "BALANCE 5", "BALANCE E", "BALANCE", "BALANCE 3 4"] # Testing BALANCE - DONE

data = ["list 1", "list 2", "list 0", "list -1", "list 5", "list e", "list", "list 2 3", "LIST 1", "LIST 2", "LIST 0", "LIST -1", "LIST 5", "LIST e", "LIST", "LIST 2 3"] # Testing LIST - DONE

data = [] # Testing BUY

data = ["SELL Pikachu 1 34.99 1", "sell Pikachu 1 34.99 1", "SELL Jigglypuff 1 35.00 2",
        "SELL Pikac 1 34.99 1", "SELL 1 1 34.99 1",
        "SELL Pikachu 2 34.99 1", "SELL Pikachu 3 34.99 1", "SELL Pikachu e 34.99 1", "SELL Pikachu 0 34.99 1", "SELL Pikachu -1 34.99 1",
        "SELL Pikachu 1 b 1", "SELL Pikachu 1 0 1", "SELL Pikachu 1 -1 1",
        "SELL Pikachu 1 34.99 0", "SELL Pikachu 1 34.99 -1", "SELL Pikachu 1 34.99 5", "SELL Pikachu 1 34.99 e",
        "SELL", "SELL 1 2 3 4 5"]                                                                                                                                         # Testing SELL - DONE

data = ["BUY Pikachu Electric Common 19.99 2 1"]
"""