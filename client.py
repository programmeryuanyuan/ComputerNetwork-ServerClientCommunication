"""
    client.py
    Python 3.7
    Usage: python client.py server_IP server_port
    coding: utf-8
    
    Author: Yuanyuan Luo
"""

from socket import *
from threading import *
import sys
import re as regular


if (len(sys.argv) != 3):
    print("\n===== Error usage, python client.py server_IP server_port ======\n");
    exit(0);


serverIP = sys.argv[1]
serverPort = int(sys.argv[2])
serverAddress = (serverIP, serverPort)

privateConnections = {}

username = ''


def solve():

    # create the client socket
    clientSocket = socket(AF_INET, SOCK_STREAM)
    clientSocket.connect(serverAddress)

    # create a thread responsible for sendalling messages to the server
    Thread(target = sendallThread, args=[clientSocket], daemon = True).start()

    # create a thread for the welcoming socket for private connections
    Thread(target = privateThread, args = [clientSocket], daemon = True).start()


    # start receiving messages from the server
    recvThread(clientSocket)

def getMessage():
    
    msg = input()
    return msg
    
def sendallThread(client):

    while 1:

        # get the user's input
        message = getMessage()

        # check the private <user> <message> command
        # ^: the regular expression match starts
        # \s+: matches multiple characters except whitespace
        # .*: take any character of 0 to infinite length
        # $: the regular expression match ends
        command = regular.search(r'^private (\S+) (.*)$', message)
        if command:

            # intercept string by group to get the user and message from the command
            user = command.group(1)
            message = command.group(2)

            # no setup a private connection with this client
            if user in privateConnections:
                try:
                    formattedMessage = '%s(private): %s\n'%(username, message)
                    privateConnections[user].sendall(formattedMessage.encode())
                # the user is no longer online, throw an exception
                except:
                    del privateConnections[user]
                    print('Error. %s is no longer available through this connection'%(user))
            else:
                print('Error. Private messaging to %s not enabled'%(user))
        # no private message command, sendall to the server
        else:
            client.sendall(message.encode())


def recvThread(client):

    global username
    while True:

        response = client.recv(1024)

        if response:

            response = response.decode()
            if response.find('password')!=-1:
                command = regular.search(r'^password: (\S*) msg: (.*)$', response)
                if command:

                    username = command.group(1)
                    response = command.group(2)
            elif response.find('startprivate')!=-1:
                # receive a startprivate message
                command = regular.search(r'^startprivate: (\S+) (\S+) (\S+) msg: (.*)$', response)
                if command:

                    privateIP,privatePort,user,response=command.group(1),int(command.group(2)),command.group(3),command.group(4) + '\n'

                    # create the private socket
                    p2pSocket = socket(AF_INET, SOCK_STREAM)

                    # next the TCP connection with the other client must be established using a three-way handshake
                    p2pSocket.connect((privateIP, privatePort))

                    # let the other client know our username
                    p2pSocket.sendall(username.encode())

                    # associate this user with the socket connected to their machine
                    privateConnections[user] = p2pSocket

                    # create a thread to handle messages receieved from the other client
                    Thread(target = recvThread, args=[p2pSocket], daemon = True).start()

            elif response.find('stopprivate')!=-1:
                # receive a stopprivate message
                command = regular.search(r'^stopprivate: (\S+) msg: (.*)$', response)
                if command:

                    user,response = command.group(1),command.group(2) + '\n'

                    # close connection
                    if user in privateConnections:
                        # sendall a message to the other client noticing that the private messaging has finished
                        privateConnections[user].sendall(response.encode())
                        
                        # close the private connection with the client
                        privateConnections[user].close()
                        del privateConnections[user]
                        continue
                    # no active p2p messaging session with the user
                    else:
                        response = 'Error. Cannot stop private messaging as an active connection with {} does not exist\n'.format(user)
                        
            elif response.find('Private messaging with')!=-1:
                # if another client close the private connection
                command = regular.search(r'^Private messaging with (\S+) has ended$', response)
                if command:
                    user = command.group(1)
                    del privateConnections[user]
            
            # display this received message to the client
            print(response)
        else: break

    # close the client socket
    client.close()

    # when logging out, close all private connections
    for user in privateConnections:
        privateConnections[user].close()


def privateThread(clientSocket):

    privateSocket = socket(AF_INET, SOCK_STREAM)

    # options for TCP socket
    privateSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

    privateSocket.bind(('', 0))

    # set the welcoming socket to listen for any client connection requests
    privateSocket.listen(5)

    # sendall the welcoming socket's port number to the server
    message = '{0}'.format(privateSocket.getsockname()[1])
    clientSocket.sendall(message.encode())

    while True:

        # when a client knocks on this door, a new socket is created that is dedicated to this particular client
        client, address = privateSocket.accept()

        # associate this socket with the user setting up this private connection
        response = client.recv(2048)
        response = response.decode()
        privateConnections[response] = client

        # create a thread to handle messages receieved from the other client
        Thread(target = recvThread, args=[client], daemon = True).start()

if __name__=="__main__":
    solve()