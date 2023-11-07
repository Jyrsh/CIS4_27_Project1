import socket
from _thread import *

HOST = "127.0.0.1"
PORT = 65432
MaxThreads = 1
ThreadIDs = [False] * MaxThreads

def client_handler(connection, tID):
    connection.sendall(bytes("Connected to Server!", encoding="ASCII"))
    while True:
        data = connection.recv(1024).decode()
        print(f"C{tID}: {data}")
        if data == 'BYE':
            break

        message = data
        print(f"S: {message}")
        connection.sendall(bytes(message, encoding="ASCII"))

    message = f"CLOSE"
    connection.sendall(bytes(message, encoding="ASCII"))
    connection.close()
    ThreadIDs[tID] = False

def accept_connections(server):
    client, address = server.accept()
    print(f"Connected to: {address}")
    threadID = find_open_thread()
    if threadID != None:        
        start_new_thread(client_handler, (client, threadID))
        ThreadIDs[threadID] = True

    else:
        print("Threads are filled")
        client.close()
        accept_connections(server)

def find_open_thread():
    for i in range(MaxThreads):
        if ThreadIDs[i] == False:
            return i
        
    return None

def start_server(HOST, PORT):
    server = socket.socket()
    print("Starting Server")

    try:
        server.bind((HOST, PORT))
        print("Server Started!")
        print("Waiting for clients...")
    except socket.error:
        print(str(socket.error))

    #if find_open_thread() != None:
    server.listen()

    while True:
        if find_open_thread() != None:
            accept_connections(server)

start_server(HOST, PORT)