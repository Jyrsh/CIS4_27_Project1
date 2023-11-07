import sys
import socket
import sqlite3
import signal
from _thread import *
import threading
from math import isinf
import asyncio

# GLOBAL VARIABLES
########################
# Port info
PORT = 65432
MaxThreads = 10
ThreadIDs = [False] * MaxThreads
ServerRunning = True

# For zipping select results to reference in messages relayed to client
USER_KEYS = ('id', 'email', 'first_name', 'last_name', 'user_name', 'password', 'usd_balance')
CARD_KEYS = ('id', 'card_name', 'card_type', 'rarity', 'count', 'owner_id')
USER_SESSION_KEYS = ('id', 'user_id', 'user_name', 'IP_address')

# Error codes
OK = "200 OK"
INVALID = "400 invalid command"
LOGIN_FAIL = "403 Wrong UserID or Password"
FORMAT = "405 message format order"
NOT_FOUND = "404 no record found"
OVERFLOW = "006 Overflow error"
INF = "420 price is 'inf'"
LOG = "403 Wrong UserID or Password"

# Length variables
LONGEST_POKEMON_NAME = len("Crabominable") + 1 # Longest pokemon name at project time
LIST_ARG_LEN = 0
BALANCE_ARG_LEN = 1
SELL_ARG_LEN = 4
BUY_ARG_LEN = 6
LOGIN_ARG_LEN = 2
WHO_ARG_LEN = 0
DEPOSIT_ARG_LEN = 1
LOOKUP_ARG_LEN = 1

print_lock = threading.Lock()
########################


# HELPER FUNCTIONS
########################
def isFloat(string):
    try:
        float(string)
        return True
    except:
        return False

def insertCard(c_name, c_type, c_rarity, c_quantity, c_owner, con, c):
    c.execute(f"INSERT INTO Pokemon_cards (card_name, card_type, rarity, count, owner_id) VALUES ('{c_name}', '{c_type}', '{c_rarity}', {c_quantity}, {c_owner});")
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
    results = res.fetchall()                                                     # Tuples of results
    # Result of query is not an empty tuple
    if results:
        for item in results:
            selected_cards.append(item)

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

def insertDefaultUser(con, c):
    c.execute("""INSERT INTO Users (email, first_name, last_name, user_name, password, usd_balance) VALUES
            ('root@umich.edu',    'Root',    'User', 'Root',        'Root01', 100.00),
            ('default@umich.edu', 'Default', 'User', 'DefaultUser', 'Root01', 100.00),
            ('blamo@umich.edu',   'Blam',    'o',    'blamo',       'Root01', 100.00)
            ;""")
    con.commit()

def isUserTableEmpty(c):
    res = c.execute("SELECT * FROM Users;")
    results = res.fetchall()

    if not results:
        return True
    return False

def createTables(con, c):
    # No AUTO_INCREMENT support like w/ example table in sqlite3 for python
    #   Still auto increments for each entry added, so it does the same thing
    # Users Table, checks if no users table exists and will create one, else carries on
    c.execute("""CREATE TABLE IF NOT EXISTS Users (
            ID INTEGER PRIMARY KEY,
            email TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            user_name TEXT NOT NULL,
            password TEXT,
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
            FOREIGN KEY (owner_id) REFERENCES Users(ID)
    );""")
    con.commit() # Commit changes to db

    # User sessions Table
    c.execute("""CREATE TABLE IF NOT EXISTS User_sessions (
            ID INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            user_name TEXT NOT NULL,
            IP_address TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES Users(ID)
    );""")
    con.commit() # Commit changes to db

    c.execute("""INSERT INTO Pokemon_cards (card_name, card_type, rarity, count, owner_id) VALUES
            ('Pikachu', 'Electric', 'Common', 2, 1),
            ('Diglet', 'Electric', 'Common', 3, 2),
            ('idgaf', 'Electric', 'Common', 1, 1),
            ('Pikachu', 'Electric', 'Rare', 6, 1),
            ('Pi', 'Electric', 'Rare', 4, 1),
            ('Pik', 'Electric', 'Rare', 8, 1),
            ('idgaf', 'Electric', 'Common', 1, 3)
    ;""")
    con.commit()

def printTable(fields, data):
    message = ''
    for item in fields:
        message += f"{item.ljust(LONGEST_POKEMON_NAME, ' ')}"

    message += '\n'
    for card in data:
        for field in card:
            message += f"{str(field).ljust(LONGEST_POKEMON_NAME, ' ')}"

        message += '\n'
    
    return message

########################

# LOOKUP FUNCTION
def lookup(data, user, c):
    target = []
    
    message = numberOfArgs(data, LOOKUP_ARG_LEN)
    if message:
        return message
    
    message = ''
    
    c_name = data.pop(0)

    res = c.execute(f"SELECT * FROM Pokemon_cards WHERE owner_id = {user['id']};")
    result = res.fetchall()
    
    for card in result:
        for i in range(len(card)):
            if c_name in str(card[i]):
                target.append(card)

    if not target:
        message = NOT_FOUND + f"\nNo cards of {c_name} found for {user['user_name']}"
        return message
    
    for field in CARD_KEYS:
        message += f"{str(field).ljust(LONGEST_POKEMON_NAME, ' ')}"

    message += '\n'
    for item in target:
        for i in range(len(item)):
            message += f"{str(item[i]).ljust(LONGEST_POKEMON_NAME, ' ')}"

        message += '\n'

    return OK + '\n' + message

# WHO FUNCTION
def who(data, user, c):
    message = numberOfArgs(data, WHO_ARG_LEN)
    if message:
        return message
    
    if user['user_name'] != "Root":
        message = INVALID + "\nOnly user Root can execute this command"
        return message
    
    message = ''
    res = c.execute(f"SELECT * FROM User_sessions")
    result = list(res.fetchall())
    field_names = list(USER_SESSION_KEYS)

    for field in field_names:
        if field == 'user_name':
            message += f"{field.ljust(LONGEST_POKEMON_NAME, ' ')}"
        elif field == 'IP_address':
            message += f"{field.ljust(LONGEST_POKEMON_NAME, ' ')}"

    message += '\n'
    for value in result:
        for i in range(len(value)):
            if i > 1:
                message += f"{value[i].ljust(LONGEST_POKEMON_NAME, ' ')}"

        message += '\n'


    message = OK + '\n' + message
    return message

# DEPOSIT FUNCTION
def deposit(data, user, con, c):
    message = numberOfArgs(data, DEPOSIT_ARG_LEN)
    if message:
        return message
    
    money_to_add = data.pop(0)
    if not isFloat(money_to_add): #Return if price is non-float type
        message = FORMAT + "\nDEPOSIT requires a float for money to add"
        return message
    elif float(money_to_add) < 0: #Return if price is non-positive
        message = INVALID + "\nDEPOSIT requires a positive float for money to add"
        return message

    user['usd_balance'] += float(money_to_add)
    if isinf(user['usd_balance']):
        message = INVALID + "\nResulting balance too high"
        return message
    
    updateUserBalance(user, con, c)

    return OK + f"\nDeposit successful. New User Balance ${user['usd_balance']:.2f}"

# LOGIN FUNCTION
def login(data, host, con, c):
    active_user = None
    
    message = numberOfArgs(data, LOGIN_ARG_LEN)
    if message:
        return active_user, message
    
    #Get command args
    u_name = data.pop(0)
    u_pass = data.pop(0)
    
    # check against user table for correct info
    res = c.execute(f"SELECT * FROM Users WHERE (user_name, password) = ('{u_name}', '{u_pass}');")
    result = res.fetchone()
    if not result:
        message = LOGIN_FAIL + "\nUser does not exist or password incorrect"
        return active_user, message
    active_user = dict(zip(USER_KEYS, result))

    # check against user_session table
    res = c.execute(f"SELECT * FROM User_sessions WHERE user_id = {active_user['id']};")
    result = res.fetchone()
    if result:
        active_user = None
        message = LOGIN_FAIL + "\nUser already logged in"
        return active_user, message

    # user not currently active and valid login info
    c.execute(f"INSERT INTO User_sessions (user_id, user_name, IP_address) VALUES ({active_user['id']}, '{active_user['user_name']}', '{host}');")
    con.commit()
    message = OK + f"\nUser {active_user['user_name']} successfully signed in"

    return active_user, message

# BALANCE FUNCTIONS
########################

# Process Balance command
def balanceForOwner(user_id, c):
    #Get User Information
    user = getUser(user_id, c)
    if not user:    #Return if no user was found in the database
        message = NOT_FOUND + f"\nNo user {user_id} exists"                                                   # Error 404, selected user does not exist
        return message
    
    #Create and return message
    message = OK + f"\nBalance for user {user['first_name']} {user['last_name']}: ${user['usd_balance']:.2f}" # Success w/ appropriate first name, last name, and balance

    return message

# Validate BALANCE command args
def balance(data, c):
    message = numberOfArgs(data, BALANCE_ARG_LEN) #Check if command has correct number of args
    if message:                                   #Return if too many or too few args
        return message
    
    #Get and validate Owner ID Arg
    id = data.pop(0)                      # Store next argument
    if not id.isnumeric() or int(id) < 1: # Return if owner id is non-int or non-positive
        message = FORMAT + "\nBALANCE requires non-zero, positive integer for user"
        return message
    
    #Run BALANCE command
    message = balanceForOwner(id, c)   # Hand off to message builder

    return message

########################


# LIST FUNCTIONS
########################

# Process LIST command for Root user
def listAllCards(c):
    res = c.execute(f"SELECT * FROM Pokemon_cards")
    result = res.fetchall()
    message = OK + f"\nThe list of records in the Pokemon cards table:\n"

    message += printTable(CARD_KEYS, result)

    return message

# Process LIST command for active user
def listCardsForOwner(user, c):
    #Get User's Cards
    cards = getCardByOwner(user['id'], c)

    if not cards:   #Return if user owns no cards or the ID is not in the database
        message = NOT_FOUND + f"\nNo cards owned by {user['user_name']}, user may not exist"                         # Error 404, selected user does not exist
        return message
    
    #Print list of cards
    message = OK + f"\nThe list of records in the Pokemon cards table for current user, {user['user_name']}:\n"
    message += printTable(CARD_KEYS, cards)

    return message

# Direct LIST command based on user
def listC(data, user, c):
    message = numberOfArgs(data, LIST_ARG_LEN)
    if message:
        return message
    
    if user['user_name'] == "Root":
        message = listAllCards(c)

    else:
        message = listCardsForOwner(user, c)

    return message

########################


# SELL FUNCTIONS
########################

# Process SELL command
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
    user['usd_balance'] += int(c_quantity) * float(c_price)
    if isinf(user['usd_balance']):
        message = INVALID + "\nResulting balance too high"
        return message
    card['count'] -= int(c_quantity)

    if card['count'] == 0: #If card count is zero, remove the card from the database
        deleteCard(card, c_owner, con, c)
    else:                  #Else, update the value in the database
        updateCardCount(card, con, c)
    updateUserBalance(user, con, c)

    return OK + f"\nSOLD: New balance: {card['count']} {card['card_name']}. User's balance USD ${user['usd_balance']:.2f}"

# Validate SELL command args
def sell(data, con, c):
    message = numberOfArgs(data, SELL_ARG_LEN) #Check if command has correct number of args
    if message:                                #Return if too many or too few args
        return message
    
    #Get command args
    c_name = data.pop(0)
    
    #Get and validate Quantity Arg 
    c_quantity = data.pop(0)
    if not c_quantity.isnumeric() or int(c_quantity) < 1: #Return if quantity is non-int or non-positive
        message = FORMAT + "\nSELL requires positive, non-zero integer for quantity"
        return message
    
    #Get and validate Price Arg
    c_price = data.pop(0)
    if not isFloat(c_price): #Return if price is non-float type
        message = FORMAT + "\nSELL requires a float for price"
        return message
    elif float(c_price) < 0: #Return if price is non-positive
        message = INVALID + "\nSELL requires a positive float for price"
        return message
    elif isinf(float(c_price)):
        message = INVALID + "\nSELL price is too high"
        return message
    
    #Get and validate Owner ID Arg
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

# Proccess BUY command
def buyCard(c_name, c_type, c_rarity, c_price, c_quantity, c_owner, con, c):
    #Get User and User's Card Information
    user = getUser(c_owner, c)
    card = getCardByOwnerNameRarity(c_name, c_rarity, c_owner, c)

    if not user:                #Return if user id was not in list
        message = NOT_FOUND + f"\nNo user {c_owner}"
        return message
    
    #To determine overflow with quantity
    try:
        user['usd_balance'] -= int(c_quantity) * float(c_price)
    except OverflowError:
        message = OVERFLOW + "\nQuantity is too large"
        return message
    
    if user['usd_balance'] < 0: #Return if selected user does not have enough funds
        message = INVALID + f"\nUser {c_owner} does not have enough funds to purchase {c_quantity} {c_name}(s)"
        return message
    
    if card:                    #If the card is already in the card database, increase count
        card['count'] += int(c_quantity)
        updateCardCount(card, con, c)
    else:                       #Else, add it to the card database
        insertCard(c_name, c_type, c_rarity, c_quantity, c_owner, con, c)
    updateUserBalance(user, con, c) #Update user database

    return OK + f"\nBOUGHT: New balance: {c_quantity} {c_name}. User's USD balance ${user['usd_balance']:.2f}"

# Validate BUY command args
def buy(data, con, c):
    message = numberOfArgs(data, BUY_ARG_LEN) #Check if command has correct number of args
    if message:                               #Return if too many or too few args
        return message
    
    #Get command args
    c_name = data.pop(0)
    c_type = data.pop(0)
    c_rarity = data.pop(0)
    
    #Get and validate Price Arg
    c_price = data.pop(0)
    if not isFloat(c_price): #Return if price is non-float type
        message = FORMAT + "\nBUY requires a float for price"
        return message
    elif float(c_price) < 0: #Return if price is non-positive
        message = INVALID + "\nBUY requires a positive float for price"
        return message
    elif isinf(float(c_price)):
        message = INF + "\nPrice is 'inf'"
    
    #Get and validate Quantity Arg
    c_quantity = data.pop(0)
    if not c_quantity.isnumeric() or int(c_quantity) < 1: #Return if quantity is non-int or non-positive
        message = FORMAT + "\nBUY requires positive, non-zero integer for quantity"
        return message
    
    #Get and validate Owner ID Arg
    c_owner = data.pop(0)
    if not c_owner.isnumeric() or int(c_owner) < 1: #Return if owner id is non-int or non-positive
        message = FORMAT + "\nBUY requires positive, non-zero integer for user"
        return message
    
    #Run BUY command
    message = buyCard(c_name, c_type, c_rarity, c_price, c_quantity, c_owner, con, c)

    return message

########################

def tokenizerLoggedIn(data, user, con, c):
    tokens = data.split() # Split Input Into Strings
    if not tokens:        # If No Input Given
        message = INVALID + "\nNo valid command received"
        return message
    commandToken = tokens.pop(0)
    
    # Function Selection
    if commandToken == "BUY":
        return buy(tokens, con, c)
    elif commandToken == "SELL":
        return sell(tokens, con, c)
    elif commandToken == "LIST":
        return listC(tokens, user, c)
    elif commandToken == "BALANCE":
        return balance(tokens, c)
    elif commandToken == "WHO":
        return who(tokens, user, c)
    elif commandToken == "DEPOSIT":
        return deposit(tokens, user, con, c)
    elif commandToken == "LOOKUP":
        return lookup(tokens, user, c)
    return INVALID + "\nNo valid command received"

def tokenizer(data, client, con, c):
    tokens = data.split() # Split Input Into Strings
    if not tokens:        # If No Input Given
        message = INVALID + "\nNo valid command received"
        return message
    commandToken = tokens.pop(0)
    
    # Function Selection
    if commandToken == 'LOGIN':
        return login(tokens, client, con, c)
    
    return INVALID + "\nNo valid command received"

def client_handler(connection, address, tID):
    global ServerRunning
    while True:
        active_user = None
        con = sqlite3.connect('database.db') # Open/create and connect to database
        c = con.cursor()                     # Create a cursor
        #:p
        #connection.sendall(bytes("Connected to Server!", encoding="ASCII"))
        while True:
            data = connection.recv(1024).decode()
            print(f"C{tID}: {data}")

            if data == 'QUIT':
                c.execute(f"DELETE FROM User_sessions WHERE user_id = {active_user['id']};")
                con.commit()
                break

            elif data == 'LOGOUT':
                c.execute(f"DELETE FROM User_sessions WHERE user_id = {active_user['id']};")
                con.commit()
                active_user = None
                connection.sendall(bytes("Logging out", encoding="ASCII"))
                continue

            elif data == 'SHUTDOWN':
                if active_user and active_user['user_name'] == 'Root': 
                    connection.sendall(bytes("Shutting Down Server... OwO", encoding="ASCII"))
                    ServerRunning = False
                    break

                else:    
                    connection.sendall(bytes("Not Root User", encoding="ASCII"))

            if not active_user:
                message = tokenizer(data, address, con, c)
                if type(message) != str:
                    active_user = message[0]
                    message = message[1]
            else:
                message = tokenizerLoggedIn(data, active_user, con, c)

            print(f"S: {message}")
            connection.sendall(bytes(message, encoding="ASCII"))
            #print_lock.release()
        if data == "QUIT":
            break

    message = f"CLOSE"
    connection.sendall(bytes(message, encoding="ASCII"))
    connection.close()
    ThreadIDs[tID] = False

def accept_connections(server):
    #print_lock.acquire()
    client, address = server.accept()
    print(f"Connected to: {address}")
    start_new_thread(client_handler, (client, address[0], find_open_thread()))
    ThreadIDs[find_open_thread()] = True
    #print_lock.release()

def find_open_thread():
    for i in range(MaxThreads):
        if ThreadIDs[i] == False:
            return i
        
    return None

def start_server(HOST, PORT):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print("Starting Server")

    try:
        server.bind((HOST, PORT))
        print("Server Started!")
        print("Waiting for clients...")
    except socket.error:
        print(str(socket.error))

    #if find_open_thread() != None:
    server.listen()

    while ServerRunning:
        if find_open_thread() != None:
            accept_connections(server)

def main():
    if len(sys.argv) == 2:
        HOST = sys.argv[1]
    else:
        HOST = "127.0.0.1"

    con = sqlite3.connect('database.db') # Open/create and connect to database
    c = con.cursor()                     # Create a cursor

    c.execute(f"DELETE FROM Pokemon_cards;")
    con.commit()    
    createTables(con, c)                 # Create Tables

    if isUserTableEmpty(c):
        insertDefaultUser(con, c)

    # Ctrl-C handler for graceful interrupt exit
    def keyboardInterruptHandler(signum, frame):
        res = input("\nCtrl-c was pressed. Do you really want to exit? y/n ")
        if res.lower() == 'y':
            exit(1)

    # Keyboard Interrupt Handler for graceful exit with Ctrl-C
    signal.signal(signal.SIGINT, keyboardInterruptHandler)

    c.execute(f"DELETE FROM User_sessions;")
    con.commit()
    start_server(HOST, PORT)

if __name__ == "__main__":
    main()

""" 
# Client wishes to shutdown server
elif data == "SHUTDOWN":                       
    conn.sendall(bytes(OK, encoding="ASCII"))
    print('SERVER SHUTDOWN INITIATED BY USER...')
    break 
    
if data == "SHUTDOWN":                                # Only triggered via SHUTDOWN command, otherwise loop for new connections                            
    break
"""

#GIL may pose a problem later

#LIST done
#LOGIN done
#LOOKUP done
#WHO done
#DEPOSIT done
#LOGOUT
#SHUTDOWN

"""
# TEST IN MAIN
########################

# get active user for threaded session
res = c.execute(f"SELECT * FROM Users;")
result = res.fetchall()
print(printTable(USER_KEYS, result))

# process non-threaded commands
input = "LOGIN Root Root01"
print(input)
message = tokenizerNotThreaded(input, host, con, c) # in non-threaded loop
print(message + '\n')

res = c.execute("SELECT * FROM User_sessions;")
result = res.fetchall()
print(printTable(USER_SESSION_KEYS, result))

print("Active User: " + str(ACTIVE_USERID) + '\n')

# get active user for threaded session
res = c.execute(f"SELECT * FROM Users WHERE (id) = {ACTIVE_USERID};")
result = res.fetchone()
active_user = dict(zip(USER_KEYS, result))

# process threaded commands
input = "LOOKUP klhjadfgjhqawnfsdg"
print(input)
message = tokenizerThreaded(input, active_user, con, c) # in threaded loop once threads implemented
print(message + '\n')

res = c.execute(f"SELECT * FROM Users;")
result = res.fetchall()
print(printTable(USER_KEYS, result))
printTable(USER_KEYS, result)

return
########################
"""

"""
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, PORT))
            s.listen()
            conn, addr = s.accept()

            with conn:
                print(f"Connected by {addr}")
                while True:
                    data = conn.recv(1024).decode()                   # Data received from client
                    print(f"Received: {data}\n")

                    # Client wishes to log off
                    if data == "QUIT":
                        conn.sendall(bytes(OK, encoding="ASCII"))
                        break
                    # No data received, client is not connected, wait for new client
                    elif not data:
                        break
                    
                    message = tokenizerNotThreaded(data, host, threads, conn, con, c)                 # Process message received if not "SHUTDOWN" or "QUIT"

                    conn.sendall(bytes(message, encoding="ASCII"))
"""

"""
def threaded(conn, message, active_user):
    con = sqlite3.connect('database.db') # Open/create and connect to database
    c = con.cursor()                     # Create a cursor
    
    conn.sendall(bytes(message, encoding="ASCII")) # Return successful login
    while True:
        data = conn.recv(1024).decode() # Data received from client
        print(f"Received: {data}\n")

        # Client wishes to log off
        if data == "LOGOUT":
            conn.sendall(bytes(OK, encoding="ASCII"))
            break
        # No data received, client is not connected, wait for new client
        elif active_user['user_name'] == 'Root' and data == "SHUTDOWN":
            pass
        elif not data:
            break
        
        message = tokenizerLogin(data, active_user, con, c)

        conn.sendall(bytes(message, encoding="ASCII"))
    return
"""