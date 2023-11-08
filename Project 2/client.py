import sys
import socket

# GLOBAL VARIABLES
########################
# Port info
PORT = 65432

# Error codes
OK = "200 OK"
INVALID = "400 invalid command"
########################

def main():
    print(str(sys.argv))
    if len(sys.argv) == 2:
        HOST = sys.argv[0]
    else:
        HOST = "127.0.0.1"
    message = ''

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        while message !=  "QUIT":
            message = input("c: ")
            if message.isspace() or len(message) == 0:
                print(f"{INVALID}\nNo valid command received\n")
                continue
            s.sendall(bytes(message, encoding="ASCII"))
            data = s.recv(1024).decode("ASCII")
            print(f"{data}\n")

if __name__ == "__main__":
    main()