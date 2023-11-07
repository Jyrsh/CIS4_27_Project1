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
reply = client.recv(2048).decode('utf-8')
print("Connected!")

while reply != "CLOSE":
    message = input('Your message: ')
    client.send(str.encode(message))
    reply = client.recv(2048).decode('utf-8')
    print(reply)
client.close()