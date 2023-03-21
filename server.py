"""
    Multi-Threaded Server
    Python 3.7
    Usage: python server.py server_port block_duration timeout
    coding: utf-8
    
    Author: Yuanyuan Luo
"""
from socket import *
from threading import *
from datetime import datetime
import sys, select
import re as regular
import time
import datetime as dt


if len(sys.argv) != 4:
    print("\n===== Error usage, python server.py server_port block_duration timeout ======\n");
    exit(0);

serverPort,blockDuration,timeout=int(sys.argv[1]),int(sys.argv[2]),int(sys.argv[3])

blacklistedUsers = {}
addresses = {}
loginHistory = {}
connections = {}
offlineDeliveries = {}
blockedUsers = []

def main():
    # socket family: AF_INET, socket type: SOCK_STREAM (connection-oriented)
    serverSocket = socket(AF_INET, SOCK_STREAM)
    # bind the port to listen on
    serverSocket.bind(('', serverPort))
    # start listening, can queue up five links
    serverSocket.listen(5)

    while True:
        client, address = serverSocket.accept()

        privatePort = int(client.recv(1024).decode())

        Thread(target = verifyUsername, args = (client, address, privatePort)).start()


def verifyUsername(client, address, privatePort):

    message = 'Username: '

    client.sendall(message.encode())

    response = client.recv(1024)
    response = response.decode()

    file = open('credentials.txt', 'r')

    isValid = False
    for line in file:

        command = regular.search('^(%s) (.*)$'%(response), line)
        
        if command:
            isValid = True

            username = command.group(1)
            password = command.group(2)

    
    file.close()

    if isValid==False:
        message = 'Invalid Username. Please try again\n'
        client.sendall(message.encode())

        verifyUsername(client, address, privatePort)
    else:
        verifyPassword(client, address, username, password, privatePort)
    return

def verifyPassword(client, address, username, password, privatePort):

    loginStatus = False
    maxAttempts = 3
    for i in range(1,maxAttempts+1):

        message = 'password: {0} msg: Password: '.format(username)

        client.sendall(message.encode())

        response = client.recv(1024)
        response = response.decode()

        if (response == password):

            if username in blockedUsers:
                message = 'Your account is blocked due to multiple login failures. Please try again later\n'
                break
            
            elif username in connections:
                message = 'This account is already logged in elsewhere. Please logout and try again\n'    
                break

            else:
                message = 'Welcome to the greatest messaging application ever!\n'
                client.sendall(message.encode())
                loginStatus = True
                break
        else:

            if (i < maxAttempts):
                message = 'Invalid Password. Please try again\n'
                client.sendall(message.encode())
            
            else:
                message = 'Invalid Password. Your account has been blocked. Please try again later\n'

                blockedUsers.append(username)
                Timer(blockDuration, lambda block: blockedUsers.remove(username), args = [username]).start()
                break
    
    if loginStatus:
        serverOperate(client, address, username, password, privatePort)
    
    else:
        client.sendall(message.encode())

        client.close()

def serverOperate(client, address, username, password, privatePort):

    loginHistory[username] = True
    flag=1
    presenceBroadcast = '%s logged in\n'%(username)
    for user in connections:
        if not(user in blacklistedUsers and username in blacklistedUsers[user]):

            connections[user].sendall(presenceBroadcast.encode())
    
    connections[username] = client
    
    if username in offlineDeliveries:
        for message in offlineDeliveries[username]:
            client.sendall(message.encode())
        del offlineDeliveries[username]

    addresses[username] = (address[0], privatePort)
    
    try:

        client.settimeout(timeout)

        while True:
            
            response = client.recv(1024)
            
            if response:
                response = response.decode()

                if response == 'logout':
                    raise error('Client logout')

                if response == 'whoelse':
                    for user in connections:
                        if user != username:
                            client.sendall((user + '\n').encode())
                    continue
                
                command = regular.search(r'^message (\S+) (.*)$', response)
                if command:

                    user = command.group(1)
                    message = command.group(2)

                    formattedMessage = '{}: {}\n'.format(username, message)

                    if user == username:
                        message = 'Error. Cannot message self\n'
                        client.sendall(message.encode()) 
                    
                    elif username in blacklistedUsers and user in blacklistedUsers[username]:
                        message = 'Your message could not be delivered as the recipient has blocked you\n'
                        client.sendall(message.encode())
                    elif user in connections:
                        connections[user].sendall(formattedMessage.encode())
                    else:
                        credentials = open('credentials.txt', 'r')
                        exists = False
                        for line in credentials:
                            
                            command = regular.search('^{} .*$'.format(user), line)                         
                            if command:
                                exists = True

                        credentials.close()
                        
                        if not exists:
                            message = 'Error. Invalid user\n'
                            client.sendall(message.encode())
                        else:
                            if user in offlineDeliveries:    
                                offlineDeliveries[user].append(formattedMessage)
                            else:
                                offlineDeliveries[user] = [formattedMessage]
                        
                    continue
                
                command = regular.search('^broadcast (.*)$', response)
                if command:
                    message = command.group(1)

                    broadcast = '{}: {}\n'.format(username, message)
                    
                    someBlocked = False
                    for user in connections:
                        if username in blacklistedUsers and user in blacklistedUsers[username]:
                            someBlocked = True
                        elif user != username:
                            connections[user].sendall(broadcast.encode())
                    
                    if someBlocked:
                        message = 'Your message could not be delivered to some recipients\n'
                        client.sendall(message.encode())
                    
                    continue

                command = regular.search('^whoelsesince ([0-9]+)$', response)
                if command:
                    seconds = int(command.group(1))

                    currentTime = datetime.now()

                    for user in loginHistory:
                        if user != username and (loginHistory[user] == True or (currentTime - loginHistory[user]).total_seconds() < seconds):
                            client.sendall((user + '\n').encode())
                    continue
                
                command = regular.search(r'^block (\S+)$', response)
                if command:

                    user = command.group(1)

                    if user == username:
                        message = 'Error. Cannot block self\n'
                        client.sendall(message.encode())
                    else:

                        credentials = open('credentials.txt', 'r')
                        
                        exists = False
                        for line in credentials:
                            
                            command = regular.search('^{} .*$'.format(user), line)                         
                            if command:
                                exists = True
                                break

                        credentials.close()
                        
                        if exists:
                            if user not in blacklistedUsers:    
                                blacklistedUsers[user] = [username]
                            else:
                                blacklistedUsers[user].append(username)
                            
                            message = '%s is blocked\n'%(user)
                            client.sendall(message.encode())
                        else:
                            message = 'Error. Invalid user\n'
                            client.sendall(message.encode())
                    continue
                
                command = regular.search(r'^unblock (\S+)$', response)
                if command:

                    user = command.group(1)

                    if user == username:
                        message = 'Error. Cannot unblock self\n'
                        client.sendall(message.encode())
                    else:

                        credentials = open('credentials.txt', 'r')

                        exists = False
                        for line in credentials:
                            command = regular.search('^%s .*$'%(user), line)                         
                            if command:
                                exists = True
                                break

                        credentials.close()
                        
                        if exists:
                            if user in blacklistedUsers and username in blacklistedUsers[user]:    
                                blacklistedUsers[user].remove(username)
                                message = '%s is unblocked\n'%(user)
                                client.sendall(message.encode())
                            else:
                                message = 'Error. %s was not blocked\n'%(user)
                                client.sendall(message.encode())
                        else:
                            message = 'Error. Invalid user\n'
                            client.sendall(message.encode())
                    continue
                
                command = regular.search(r'^startprivate (\S+)$', response)
                if command:

                    user = command.group(1)

                    if user == username:
                        message = 'Error. Cannot private message self\n'
                        client.sendall(message.encode()) 
                    elif username in blacklistedUsers and user in blacklistedUsers[username]:
                        message = 'Cannot commence private messaging as the recipient has blocked you\n'
                        client.sendall(message.encode())
                    elif user in connections:

                        message = 'startprivate: {0} {1} {2} msg: Start private messaging with {2}\n'.format(addresses[user][0], addresses[user][1], user)
                        client.sendall(message.encode())

                    else:
                        credentials = open('credentials.txt', 'r')
                        
                        exists = False
                        for line in credentials:
                            
                            command = regular.search('^%s .*$'%(user), line)                         
                            if command:
                                exists = True
                                break

                        credentials.close()
                        
                        if exists:
                            message = 'Cannot start private messaging since %s is offline\n'%(user)
                        else:
                            message = 'Error. Invalid user\n' 
                        client.sendall(message.encode())
                    continue

                command = regular.search(r'^stopprivate (\S+)$', response)
                if command:

                    user = command.group(1)

                    message = 'stopprivate: %s msg: Private messaging with %s has ended\n'%(user, username)
                    client.sendall(message.encode())
                    
                    continue

                message = 'Error. Invalid command\n'
                client.sendall(message.encode())  
            else:

                raise error('Client timeout')
                            
    except:
        if flag:
            client.close()

            del connections[username]

            presenceBroadcast = '%s logged out\n'%(username)
        else:
            raise error('Client timeout')
        for user in connections:
            if(user in blacklistedUsers and username in blacklistedUsers[user]):continue
            connections[user].sendall(presenceBroadcast.encode())
    
        loginHistory[username] = datetime.now()

main()