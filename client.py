import socket

HOST = "127.0.0.1"
PORT = 65432
OK = "200 OK"

def main():
    message = ''

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        while message != "SHUTDOWN" and message != "QUIT":
            message = input("c: ")
            s.sendall(bytes(message, encoding="ASCII"))
            #print(f'\nc: {message}')
            data = s.recv(1024).decode("ASCII")
            print(f"s: {data}\n")

    if message == "SHUTDOWN":
        print(message)
    else:
        print(OK)

if __name__ == "__main__":
    main()