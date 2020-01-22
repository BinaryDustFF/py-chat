import json
import socket
from tkinter import *
from threading import Thread

# Keywords
ERR = "ERR"
LOGIN = "LOGIN"
MSG = "MSG"
STOP = "STOP"

REJECTED = "REJECTED"
REQUEST = "REQUEST"
SUCCESSFUL = "SUCCESSFUL"

# Chat display box
chatDisp = None
# Chat writing box
chatWrite = None

HOST = None
PORT = None

tcpSocket = None

askHOST = None
HOSTEntry = None
askLOGIN = None
LOGINEntry = None

userName = None


class CltThread(Thread):

    def __init__(self):
        global tcpSocket
        Thread.__init__(self)
        tcpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while HOST is None or PORT is None:
            askForHOST()
        succeed = tcpSocket.connect_ex((HOST, PORT))
        if succeed != 0:
            print("%s : %s > La connexion avec le serveur a échouée (code d'erreur: %s)" % (HOST, PORT, succeed))
            exit(-1)
        print("%s : %s > Demande de connection. Connexion en cours..." % (HOST, PORT))
        if userName is None:
            askForLOGIN()

    def run(self):
        global userName
        while True:
            try:
                runner = rcvMsg(tcpSocket.recv(2048).decode("utf-8", "ignore"))
            except:
                print("%s : %s > Perte de connexion avec le serveur (Arrêt Critique)" % (HOST, PORT))
                return

            if runner is None:
                print("%s : %s > Perte de connexion avec le serveur" % (HOST, PORT))
                return

            if runner["key"] == "STOP":  # End connexion
                break
            elif runner["key"] == "MSG":
                insertMsg("%s -> %s : %s" % (runner["src"], runner["dest"], runner["arg"]))
            elif runner["key"] == "LOGIN":
                if runner["state"] == SUCCESSFUL:
                    insertMsg("Utilisateur connecté en tant que %s!" % userName)
                    continue

                userName = None
                while userName is None:
                    askForLOGIN()
                    tcpSocket.send((toJSONString(
                        {"key": "LOGIN", "arg": userName, "state": REQUEST}) + "\n").encode("utf-8",
                                                                                            "ignore"))

        tcpSocket.shutdown()
        tcpSocket.close()


def askForLOGIN():
    global LOGINEntry, askLOGIN, userName
    askLOGIN = Tk()
    askLOGIN.title("USER Config")
    askLOGIN.geometry("250x100")

    Label(askLOGIN, text="Entrez votre pseudo:").pack(side=TOP)

    LOGINEntry = Entry(askLOGIN, width=22)
    LOGINEntry.pack(side=LEFT)
    val = Button(askLOGIN, text="Valider", command=askLOGIN.quit)
    val.pack(side=RIGHT)

    askLOGIN.mainloop()

    userName = LOGINEntry.get()

    if len(userName) > 15 or len(userName) == 0:
        userName = None
        askLOGIN.destroy()
        return

    if ":" in userName:
        userName = None

    askLOGIN.destroy()


def askForHOST():
    global HOSTEntry, askHOST, HOST, PORT
    askHOST = Tk()
    askHOST.title("HOST Config")
    askHOST.geometry("250x100")

    Label(askHOST, text="Entrez l'ip du serveur:").pack(side=TOP)

    HOSTEntry = Entry(askHOST, width=22)
    HOSTEntry.pack(side=LEFT)
    val = Button(askHOST, text="Valider", command=askHOST.quit)
    val.pack(side=RIGHT)

    askHOST.mainloop()

    ipVerif = HOSTEntry.get().split(":")
    if len(ipVerif) != 2:
        PORT = None
        HOST = None
        askHOST.destroy()
        return
    if len(ipVerif[0].split(".")) != 4:
        PORT = None
        HOST = None
        askHOST.destroy()
        return

    try:
        PORT = int(ipVerif[1])
    except:
        PORT = None
        HOST = None
        askHOST.destroy()
        return

    HOST = ipVerif[0]
    askHOST.destroy()


def rcvMsg(rcvPacket):  # Process incoming rcvPackets to JSON Objects
    print(rcvPacket)
    if rcvPacket == "":
        return None
    return loadJSON(rcvPacket)


def loadJSON(jsonString):  # Load incoming messages as JSON objects
    return json.loads(jsonString)


def toJSONString(dict):  # Dumps JSON objects to String before sending message
    return json.dumps(dict)


def insertMsg(msg):
    if chatDisp is Text:
        return False

    chatDisp.configure(state="normal")
    chatDisp.insert(END, msg)
    chatDisp.configure(state="disabled")


def chatWriteEvent(event):
    if chatWrite is None:
        return

    print(event)

    insertMsg(chatWrite.get("1.0", END))
    chatWrite.delete("1.0", END)

    return "break"


mainWindow = Tk()
mainWindow.title("Py-chat - TCP chatting server")
mainWindow.geometry("800x600")
mainWindow.resizable(True, False)
mainWindow.configure(background='grey')

chatWrite = Text(mainWindow, height=3)
chatWrite.bind('<Return>', chatWriteEvent)
chatWrite.pack(side=BOTTOM, fill=X)
chatWrite.focus()

chatDisp = Text(mainWindow, height=33)
chatDisp.pack(side=TOP, fill=X)
chatDisp.configure(state="disabled")

thread = CltThread()
thread.start()

mainWindow.mainloop()
