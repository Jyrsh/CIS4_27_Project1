import sys
import os
import socket
import sqlite3
import signal
from multiprocessing import Process
from _thread import *
import threading
from math import isinf

# GLOBAL VARIABLES
########################
# Port info
PORT = 65432
MaxThreads = 10
ThreadIDs = [False] * MaxThreads
ServerRunning = True

# For zipping with SELECT results for easier data handling
USER_KEYS = ('id', 'email', 'first_name', 'last_name', 'user_name', 'password', 'usd_balance')
CARD_KEYS = ('id', 'card_name', 'card_type', 'rarity', 'count', 'owner_id')
USER_SESSION_KEYS = ('id', 'user_id', 'user_name', 'IP_address')

# Error codes
OVERFLOW = "006 Overflow error"
OK = "200 OK"
INVALID = "400 invalid command"
ACCESS = "401 security refusal"
LOGIN_FAIL = "403 Wrong UserID or Password"
NOT_FOUND = "404 no record found"
FORMAT = "405 message format order"
INF = "420 price is 'inf'"

# Length variables
LONGEST_POKEMON_NAME = len("Crabominable") + 1 # Longest pokemon name at project time
LIST_ARG_LEN = 0
WHO_ARG_LEN = 0
BALANCE_ARG_LEN = 1
DEPOSIT_ARG_LEN = 1
LOOKUP_ARG_LEN = 1
LOGIN_ARG_LEN = 2
SELL_ARG_LEN = 4
BUY_ARG_LEN = 6
########################

# Helper to determine if a string is in float format
def isFloat(string):
    try:
        float(string)
        return True
    except:
        return False

# Helper to insert card into Pokemon_cards table
def insertCard(c_name, c_type, c_rarity, c_quantity, c_owner, con, c):
    c.execute(f"INSERT INTO Pokemon_cards (card_name, card_type, rarity, count, owner_id) VALUES ('{c_name}', '{c_type}', '{c_rarity}', {c_quantity}, {c_owner});")
    con.commit()

# Helper to get card by owner id, owner name and card rarity
def getCardByOwnerNameRarity(c_name, c_rarity, c_owner, c):
    selected_card = {}

    res = c.execute(f"SELECT * FROM Pokemon_cards WHERE (card_name, rarity, owner_id) = ('{c_name}', '{c_rarity}', '{c_owner}');")
    result = res.fetchone()
    if result:
        selected_card = dict(zip(CARD_KEYS, result))               # Map associated user fields to results in a dict for easier formatting of return message later on

    return selected_card

# Helper to update a user's balance
def updateUserBalance(user, con, c):
    c.execute(f"UPDATE Users SET usd_balance = {user['usd_balance']:.2f} WHERE id = {user['id']};")
    con.commit()

# Helepr to update a card's quantity
def updateCardCount(card, con, c):
    c.execute(f"UPDATE Pokemon_cards SET count = {card['count']} WHERE id = {card['id']};")
    con.commit()

# Helper to remove card from Pokemon_cards table
def deleteCard(card, c_owner, con, c):
    c.execute(f"DELETE FROM Pokemon_cards WHERE (card_name, owner_id) = ('{card['card_name']}', {c_owner});")
    con.commit()

# Helper to get card dict by owner id and card name
def getCardByOwnerName(owner_id, c_name, c):
    selected_card = {}

    res = c.execute(f"SELECT * FROM Pokemon_cards WHERE (card_name, owner_id) = ('{c_name}', {owner_id});") # db query for selected card
    result = res.fetchone() # tuple result
    if result:
        selected_card = dict(zip(CARD_KEYS, result)) # map associated user fields to results in a dict for easier formatting of return message later on

    return selected_card

# Helper to get card dict by owner id
def getCardByOwner(owner_id, c):
    selected_cards = []

    res = c.execute(f"SELECT * FROM Pokemon_cards WHERE owner_id = {owner_id};") # db query for selected card
    results = res.fetchall() # tuples results
    if results: # result of query is not an empty tuple
        for item in results:
            selected_cards.append(item)

    return selected_cards

# Helper to determin if command is valid based on argument list length
def numberOfArgs(data, arg_len):
    if len(data) < arg_len:
        message = FORMAT + "\nNot enough args" # 405 message format order
        return message
    
    elif len(data) > arg_len:
        message = FORMAT + "\nToo many args" # 405 message format order
        return message
    
    return None

# Helper to get a User in a dict
def getUser(user_id, c):
    selected_user = None

    res = c.execute(f"SELECT * FROM Users WHERE id = {user_id};")
    result = res.fetchone()
    if result:
        selected_user = dict(zip(USER_KEYS, result))

    return selected_user

# Helper to insert default users
def insertDefaultUser(con, c):
    c.execute("""INSERT INTO Users (email, first_name, last_name, user_name, password, usd_balance) VALUES
            ('root@umich.edu',     'Root', 'User',        'Root', 'Root01', 100.00),
            ('mpoppins@umich.edu', 'Mary', 'PoppinsYall', 'Mary', 'Mary01', 100.00),
            ('jdoe@umich.edu',     'John', 'Doe',         'John', 'John01', 100.00),
            ('mschmoe@umich.edu',  'Moe',  'Schmoe',      'Moe',  'Moe01',  100.00)
            ;""")
    con.commit()

# Helper to check if Users table is empty
def isUserTableEmpty(c):
    res = c.execute("SELECT * FROM Users;")
    results = res.fetchall()

    if not results:
        return True
    
    return False

# Helper for creating tables
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

# Helper for printing a table
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

# Validate and process LOOKUP command
def lookup(data, user, c):
    target = []
    message = numberOfArgs(data, LOOKUP_ARG_LEN) # argument check

    if message:
        return message
    
    message = ''
    substring = data.pop(0)
    res = c.execute(f"SELECT * FROM Pokemon_cards WHERE owner_id = {user['id']};") # get cards for the active user
    result = res.fetchall()
    
    for card in result:
        for i in range(len(card)):
            if substring in str(card[i]): # if substring matches or is a substring of a specific card field
                target.append(card) # add card to target

    if not target: # target is empty, no cards have substring
        message = NOT_FOUND + f"\nYour search did not match any records" # 404 NOT FOUND
        return message
    
    message += f"Found {len(target)} match(es)\n\n"
    for field in CARD_KEYS:
        message += f"{str(field).ljust(LONGEST_POKEMON_NAME, ' ')}" # add card categories to return message

    message += '\n'
    for item in target:
        for i in range(len(item)):
            message += f"{str(item[i]).ljust(LONGEST_POKEMON_NAME, ' ')}" # add card fields to return message

        message += '\n'

    message = OK + '\n' + message # 200 OK
    return message

# Validate and process DEPOSIT command
def deposit(data, user, con, c):
    message = numberOfArgs(data, DEPOSIT_ARG_LEN)
    if message:
        return message
    
    money_to_add = data.pop(0)
    if not isFloat(money_to_add):
        message = FORMAT + "\nDEPOSIT requires a float for money to add" # 405 message format order
        return message
    
    elif float(money_to_add) < 0:
        message = INVALID + "\nDEPOSIT requires a positive float for money to add" # 400 invalid command
        return message

    user['usd_balance'] += float(money_to_add)
    if isinf(user['usd_balance']):
        message = INVALID + "\nResulting balance too high" # 400 invalid command
        return message
    
    updateUserBalance(user, con, c)

    return OK + f"\nDeposit successful. New User Balance ${user['usd_balance']:.2f}"

# Validate and process WHO command
def who(data, user, c):
    message = numberOfArgs(data, WHO_ARG_LEN) # argument check

    if message:
        return message
    
    if user['user_name'] != "Root": # only Root can run this command
        message = INVALID + "\nOnly user Root can execute this command"
        return message
    
    message = ''
    res = c.execute(f"SELECT * FROM User_sessions")
    result = list(res.fetchall())
    message += "The list of active users:\n"
    for value in result:
        for i in range(len(value)):
            if i > 1: # get rid of primary key field in User_session table
                message += f"{value[i].ljust(LONGEST_POKEMON_NAME, ' ')}"

        message += '\n'
    
    message = OK + '\n' + message # 200 OK
    return message

# Process Balance command
def balanceForOwner(user_id, c):
    user = getUser(user_id, c)
    if not user:
        message = NOT_FOUND + f"\nNo user {user_id} exists" # 404 no record found
        return message
    
    message = OK + f"\nBalance for user {user['first_name']} {user['last_name']}: ${user['usd_balance']:.2f}"

    return message

# Validate BALANCE command args
def balance(data, c):
    message = numberOfArgs(data, BALANCE_ARG_LEN)

    if message:
        return message
    
    id = data.pop(0)
    if not id.isnumeric() or int(id) < 1: # if owner id is non-int or non-positive
        message = FORMAT + "\nBALANCE requires non-zero, positive integer for user" # 405 message format order
        return message
    
    message = balanceForOwner(id, c)

    return message

# Process LIST command for active user
def listCardsForOwner(user, c):
    cards = getCardByOwner(user['id'], c)
    if not cards:   #Return if user owns no cards or the ID is not in the database
        message = NOT_FOUND + f"\nNo cards owned by {user['user_name']}, user may not exist" # 
        return message
    
    #Print list of cards
    message = OK + f"\nThe list of records in the Pokemon cards table for current user, {user['user_name']}:\n"
    message += printTable(CARD_KEYS, cards)

    return message

# Process LIST command for Root user
def listAllCards(c):
    res = c.execute(f"SELECT * FROM Pokemon_cards")
    result = res.fetchall()
    message = OK + f"\nThe list of records in the Pokemon cards table:\n"

    message += printTable(CARD_KEYS, result)

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

# Process SELL command
def sellCard(c_name, c_quantity, c_price, c_owner, con, c):
    user = getUser(c_owner, c)
    card = getCardByOwnerName(c_owner, c_name, c)

    if not user:
        message = NOT_FOUND + f"\nNo user {c_owner}" # 404 no record found
        return message
    
    if not card:
        message = NOT_FOUND + f"\nNo Pokemon '{c_name}' owned by user {c_owner}" # 404 no record found
        return message
    
    if int(c_quantity) > card['count']:
        message = INVALID + "\nSELL quantity more than card count" # 400 invalid command
        return message

    user['usd_balance'] += int(c_quantity) * float(c_price)
    if isinf(user['usd_balance']):
        message = INVALID + "\nResulting balance too high" # 400 invalid command
        return message
    
    card['count'] -= int(c_quantity)
    if card['count'] == 0:
        deleteCard(card, c_owner, con, c)

    else:
        updateCardCount(card, con, c)

    updateUserBalance(user, con, c)

    return OK + f"\nSOLD: New balance: {card['count']} {card['card_name']}. User's balance USD ${user['usd_balance']:.2f}"

# Validate SELL command args
def sell(data, con, c):
    message = numberOfArgs(data, SELL_ARG_LEN)

    if message:
        return message
    
    c_name = data.pop(0) 
    c_quantity = data.pop(0)
    if not c_quantity.isnumeric() or int(c_quantity) < 1:
        message = FORMAT + "\nSELL requires positive, non-zero integer for quantity"
        return message
    
    c_price = data.pop(0)
    if not isFloat(c_price):
        message = FORMAT + "\nSELL requires a float for price"
        return message
    
    elif float(c_price) < 0:
        message = INVALID + "\nSELL requires a positive float for price" # 400 invalid command
        return message
    
    elif isinf(float(c_price)):
        message = INVALID + "\nSELL price is too high" # 400 invalid command
        return message
    
    c_owner = data.pop(0)
    if not c_owner.isnumeric() or int(c_owner) < 1:
        message = FORMAT + "\nSELL requires positive, non-zero integer for user"
        return message
    
    message = sellCard(c_name, c_quantity, c_price, c_owner, con, c)

    return message

# Proccess BUY command
def buyCard(c_name, c_type, c_rarity, c_price, c_quantity, c_owner, con, c):
    user = getUser(c_owner, c)
    card = getCardByOwnerNameRarity(c_name, c_rarity, c_owner, c)

    if not user:
        message = NOT_FOUND + f"\nNo user {c_owner}" # 404 no record found
        return message
    
    try:
        user['usd_balance'] -= int(c_quantity) * float(c_price)
    except OverflowError:
        message = OVERFLOW + "\nQuantity is too large"
        return message
    
    if user['usd_balance'] < 0:
        message = INVALID + f"\nUser {c_owner} does not have enough funds to purchase {c_quantity} {c_name}(s)"
        return message
    
    if card:
        card['count'] += int(c_quantity)
        updateCardCount(card, con, c)
    else:
        insertCard(c_name, c_type, c_rarity, c_quantity, c_owner, con, c)
    updateUserBalance(user, con, c)

    return OK + f"\nBOUGHT: New balance: {c_quantity} {c_name}. User's USD balance ${user['usd_balance']:.2f}"

# Validate BUY command args
def buy(data, con, c):
    message = numberOfArgs(data, BUY_ARG_LEN)

    if message:
        return message
    
    c_name = data.pop(0)
    c_type = data.pop(0)
    c_rarity = data.pop(0)
    c_price = data.pop(0)
    if not isFloat(c_price):
        message = FORMAT + "\nBUY requires a float for price" # 405 message format order
        return message
    
    elif float(c_price) < 0:
        message = INVALID + "\nBUY requires a positive float for price" # 400 invalid command
        return message
    
    elif isinf(float(c_price)):
        message = INF + "\nPrice is 'inf'" # 420 price is 'inf'
    
    c_quantity = data.pop(0)
    if not c_quantity.isnumeric() or int(c_quantity) < 1:
        message = FORMAT + "\nBUY requires positive, non-zero integer for quantity" # 405 message format order
        return message
    
    c_owner = data.pop(0)
    if not c_owner.isnumeric() or int(c_owner) < 1:
        message = FORMAT + "\nBUY requires positive, non-zero integer for user" # 405 message format order
        return message
    
    message = buyCard(c_name, c_type, c_rarity, c_price, c_quantity, c_owner, con, c)

    return message

# handle login
def login(data, host, con, c):
    active_user = None
    message = numberOfArgs(data, LOGIN_ARG_LEN)

    if message:
        return active_user, message
    
    u_name = data.pop(0)
    u_pass = data.pop(0)
    res = c.execute(f"SELECT * FROM Users WHERE (user_name, password) = ('{u_name}', '{u_pass}');") # get user by user_name and u_pass
    result = res.fetchone()
    if not result:
        message = LOGIN_FAIL + "\nUser does not exist or password incorrect" # 403 Wrong UserID or Password
        return active_user, message
    
    active_user = dict(zip(USER_KEYS, result))
    res = c.execute(f"SELECT * FROM User_sessions WHERE user_id = {active_user['id']};") # check against user_session table
    result = res.fetchone()
    if result:
        active_user = None
        message = LOGIN_FAIL + "\nUser already logged in" # 403 Wrong UserID or Password
        return active_user, message

    c.execute(f"INSERT INTO User_sessions (user_id, user_name, IP_address) VALUES ({active_user['id']}, '{active_user['user_name']}', '{host}');") # user not currently active and valid login info
    con.commit()
    message = OK + f"\nUser {active_user['user_name']} successfully signed in"

    return active_user, message

# Command processing start for logged in clients
def tokenizerLoggedIn(data, user, con, c):
    tokens = data.split() # split input into strings
    if not tokens:
        message = INVALID + "\nNo valid command received" # 400 invalid command
        return message
    
    commandToken = tokens.pop(0)

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
    
    return INVALID + "\nNo valid command received" # 400 invalid command

# Command processing start for non-logged in clients
def tokenizer(data, client, con, c):
    tokens = data.split() # split input into strings
    if not tokens:
        message = INVALID + "\nNo valid command received" # 400 invalid command
        return message
    commandToken = tokens.pop(0)
    
    # Function Selection
    if commandToken == 'LOGIN':
        return login(tokens, client, con, c)
    
    return INVALID + "\nNo valid command received" # 400 invalid command

def client_handler(connection, address, tID):
    global ServerRunning

    active_user = None
    con = sqlite3.connect('database.db') # Open/create and connect to database, for each thread
    c = con.cursor()                     # Create a cursor

    while True:
        data = connection.recv(1024).decode()
        print(f"C{tID}: {data}\n")

        if data == 'QUIT' and active_user: # QUIT command w/ login
            c.execute(f"DELETE FROM User_sessions WHERE user_id = {active_user['id']};") # delete user session
            con.commit()
            active_user = None
            connection.sendall(bytes("Quitting", encoding="ASCII"))
            break

        elif data == 'QUIT' and not active_user: # QUIT command w/o login
            connection.sendall(bytes("Quitting", encoding="ASCII"))
            break

        elif data == 'LOGOUT' and active_user: # LOGOUT command
            c.execute(f"DELETE FROM User_sessions WHERE user_id = {active_user['id']};") # delete user session
            con.commit()
            active_user = None
            connection.sendall(bytes("Logging out", encoding="ASCII"))
            continue

        elif data == 'SHUTDOWN' and active_user and active_user['user_name'] == 'Root': # SHUTDOWN command
            connection.sendall(bytes("Shutting Down Server...", encoding="ASCII"))
            pid = os.getpid() # get pid of server
            os.kill(pid, signal.SIGTERM) # kill with terminate signal

        elif data == 'SHUTDOWN' and active_user and active_user['user_name'] != 'Root': # SHUTDOWN command error, not Root
            connection.sendall(bytes(ACCESS + "\nNot Root User", encoding="ASCII"))
            continue

        elif data == 'SHUTDOWN' and not active_user: # SHUTDOWN command error, no user
            connection.sendall(bytes(ACCESS + "\nNot Root User", encoding="ASCII"))
            continue

        elif not active_user: # if no active user, only valid command at this point is LOGIN
            message = tokenizer(data, address, con, c)
            if type(message) != str: # message is a tuple, expected with a valid login; otherwise pass along error
                active_user = message[0]
                message = message[1]
        else:
            message = tokenizerLoggedIn(data, active_user, con, c)

        print(f"S: {message}\n")
        connection.sendall(bytes(message, encoding="ASCII"))

    connection.close()
    ThreadIDs[tID] = False
    

def accept_connections(server):
    client, address = server.accept()
    print(f"Connected to: {address}")
    start_new_thread(client_handler, (client, address[0], find_open_thread()))
    ThreadIDs[find_open_thread()] = True

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
    exit()

def main():
    if len(sys.argv) == 2:
        HOST = sys.argv[1]
    else:
        HOST = "127.0.0.1"

    # Ctrl-C handler for graceful interrupt exit
    def keyboardInterruptHandler(signum, frame):
        res = input("\nCtrl-c was pressed. Do you really want to exit? y/n ")
        if res.lower() == 'y':
            exit()

    # Keyboard Interrupt Handler for graceful exit with Ctrl-C
    signal.signal(signal.SIGINT, keyboardInterruptHandler)

    con = sqlite3.connect('database.db') # Open/create and connect to database, for original queries on server startup
    c = con.cursor()                     # Create a cursor

    createTables(con, c)                 # Create Tables
    if isUserTableEmpty(c):
        insertDefaultUser(con, c)

    c.execute(f"DELETE FROM User_sessions;") # always start with a fresh User_sessions table
    con.commit()
    start_server(HOST, PORT)

if __name__ == "__main__":
    main()

#LIST done
#LOGIN done
#LOOKUP done
#WHO done
#DEPOSIT done
#LOGOUT done
#SHUTDOWN ???