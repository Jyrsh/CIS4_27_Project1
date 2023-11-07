import socket
HOST = "127.0.0.1"
PORT = 65432

client = socket.socket()
print('Waiting for connection')

try:
    client.connect((HOST, PORT))
    print("Connected!")
    print("Waiting for open thread")
except socket.error:
    print(str(socket.error))

reply = client.recv(1024).decode()
print("Connected!")

while reply != "CLOSE":
    message = input('Your message: ')
    client.sendall(bytes(message, encoding="ASCII"))
    reply = client.recv(1024).decode()
    print(reply)
    
client.close()