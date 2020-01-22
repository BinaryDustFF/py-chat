from threading import Thread
import socket
import json

HOST = "127.0.0.1"
PORT = "1234"

# Keywords
ERR = "ERR"
LOGIN = "LOGIN"
MSG = "MSG"
STOP = "STOP"

REJECTED = "REJECTED"
REQUEST = "REQUEST"
SUCCESSFUL = "SUCCESSFUL"


class CltThread(Thread):

    def __init__(self, connexion):
        Thread.__init__(self)
        self.channel = connexion[0]
        self.ip = connexion[1][0]
        self.port = connexion[1][1]
        print(self.ip, ":", self.port, "> Demande de connection acceptée. Connexion en cours...")

    def run(self):
        self.channel.send(
            (toJSONString({"key": "LOGIN", "arg": None, "state": REQUEST}) + "\n").encode("utf-8", "ignore"))

        while True:  # Ask user to log in
            try:
                runner = self.channel.recv(1024).decode("utf-8", "ignore")
                runner = loadJSON(runner)
            except:
                print("User Disconnected")
                return

            if runner["key"] != "LOGIN":
                continue

            if validateUserName(runner["arg"]) is not None:
                self.channel.send((toJSONString(
                    {"key": "LOGIN", "arg": "Le nom d'utilisateur est déjà prit", "state": REJECTED}) + "\n").encode(
                    "utf-8", "ignore"))
                print(self.ip, ":", self.port, "> %s pseudo non disponible" % (runner["arg"]))
                continue
            elif len(runner["arg"]) > 15:
                self.channel.send((toJSONString(
                    {"key": "LOGIN", "arg": "Nom d'utilisateur trop long", "state": REJECTED}) + "\n").encode("utf-8",
                                                                                                              "ignore"))
                print(self.ip, ":", self.port, "> %s pseudo trop long" % (runner["arg"]))
                continue

            break

        # Add user to userList
        addUser(runner["arg"], (self.channel, (self.ip, self.port)))
        self.channel.send(
            (toJSONString({"key": "LOGIN", "arg": None, "state": SUCCESSFUL}) + "\n").encode("utf-8", "ignore"))
        print(self.ip, ":", self.port,
              "> Utilisateur connecté avec le nom d'utilisateur: " + getUserName("%s:%s" % (self.ip, self.port)))

        while True:  # Listen for user request
            try:
                runner = rcvMsg(self.channel.recvfrom(2048))
            except:
                print("%s : %s > Utilisateur déconnecté" % (self.ip, self.port))
                remUser(getUserName("%s:%s" % (self.ip, self.port)))
                return

            if runner is None:
                print("%s : %s > Utilisateur déconnecté" % (self.ip, self.port))
                remUser(getUserName("%s:%s" % (self.ip, self.port)))
                return

            if runner["key"] == "STOP":  # End connexion
                break
            elif runner["key"] == "MSG":
                if runner["src"] is not getUserName("%s:%s" % (self.ip, self.port)):
                    sendError(getUserName("%s:%s" % (self.ip, self.port)), "Source username doesn't match")
                elif getUserName(runner["dest"]) is None:
                    sendError(getUserName("%s:%s" % (self.ip, self.port)), "Destination not found")
                else:
                    sendMsg(getUserName("%s:%s" % (self.ip, self.port)), runner["dest"], runner["arg"])

        remUser(getUserName("%s:%s" % (self.ip, self.port)))
        self.channel.shutdown()
        self.channel.close()


def loadJSON(jsonString):  # Load incoming messages as JSON objects
    return json.loads(jsonString)


def toJSONString(dict):  # Dumps JSON objects to String before sending message
    return json.dumps(dict)


def sendError(dest, cause):
    if getUserName(dest) is None:
        return
    dest = getUserName(dest)

    userList[dest][0].send((toJSONString({"key": "ERR", "arg": cause}) + "\n").encode("utf-8", "ignore"))
    return


def sendMsg(src, dest, msg):  # Send the message @msg from @src to @dest
    if getUserName(src) is None:
        return  # Invalid source user
    src = getUserName(src)

    # Talking to everyone
    if dest == "everyone":
        for user, userChannel in userList:
            userChannel[0].send((toJSONString(
                {"key": "MSG", "src": src, "dest": "everyone", "arg": src + " -> EVERYONE: " + msg}) + "\n").encode(
                "utf-8", "ignore"))

    elif getUserName(dest) is not None:
        userList[getUserName(dest)][0].send((toJSONString({"key": "MSG", "src": src, "dest": getUserName(dest),
                                                           "arg": src + " -> " + getUserName(
                                                               dest) + " : " + msg + "\n"})).encode("utf-8", "ignore"))

    return


def rcvMsg(rcvPacket):  # Process incoming rcvPackets to JSON Objects
    if rcvPacket[0].decode("utf-8", "ignore") == "":
        return None
    return loadJSON(rcvPacket[0].decode("utf-8", "ignore"))


def validateUserName(userName):  # Check if user still exist in the user list
    for userNameIter in userList:
        if userNameIter == userName:
            return userNameIter
    return None


def getUserIPV4(userName):  # Get IPV4 address of a user from its username
    if ":" in userName:
        return None

    for userNameIter in userList:
        if userNameIter == userName:
            userChannel = userList[userNameIter]
            return userChannel[1][0] + ":" + userChannel[1][1]

    return None


def getUserName(userIPV4):  # Validate a username or get username from IPV4 address
    if ":" not in userIPV4:
        return validateUserName(userIPV4)

    for userName in userList:
        if "%s:%s" % (userList[userName][1][0], userList[userName][1][1]) == userIPV4:
            return userName

    return None


def addUser(userName, cnxPacket):  # Add a user to the user list
    userList[userName] = cnxPacket  # cnxPacket (Channel, (ip, port))
    return


def remUser(userName):  # Remove a user from the user list
    userList.pop(userName)
    return


serverRunning = True

userList = {}
bannedList = []  # List of banned IPs

tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcpSocket.bind((HOST, int(PORT)))

while serverRunning:
    tcpSocket.listen(10)
    print("%s : %s > En attente de demande de connection" % (HOST, PORT))
    cltConnexion = tcpSocket.accept()
    if cltConnexion[1][0] in bannedList:
        print(cltConnexion[1][0] + " > Connexion refusée, ip bannie")
        cltConnexion[0].shutdown(socket.SHUT_RDWR)
        cltConnexion[0].close()
        continue
    cltConnection = CltThread(cltConnexion)
    cltConnection.start()
