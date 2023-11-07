import socket
from _thread import *

HOST = "127.0.0.1"
PORT = 65432
MaxThreads = 1
ThreadIDs = [False] * MaxThreads

def client_handler(connection, tID):
    connection.send(str.encode('Connected to server!'))
    while True:
        data = connection.recv(2048)
        message = data.decode('utf-8')
        print(f"C{tID}: {message}")
        if message == 'BYE':
            break
        reply = f'Server: {message}'
        print(f"S: {reply}")
        connection.sendall(str.encode(reply))
    reply = f"CLOSE"

    connection.sendall(str.encode(reply))
    connection.close()
    ThreadIDs[tID] = False


def accept_connections(server):
    client, address = server.accept()
    print(f"Connected to: {address[0]:{address[1]}}")
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