#!/usr/bin/env python

import pynotify, base64, json
from twisted.web import client
from twisted.internet import reactor

authHeader = "Basic " + base64.encodestring("russell:testing").strip()
url = 'http://russellhaering.com:9100/listen'

def notify(data):
    fetch()
    obj = json.loads(data)
    notification = pynotify.Notification("Notification", obj['message'])
    notification.set_urgency(pynotify.URGENCY_NORMAL)
    notification.set_timeout(2000)
    notification.show()

def onError(error):
    print error.getErrorMessage()
    reactor.stop()

def fetch():
    client.getPage(url, headers={'Authorization': authHeader}).addCallback(notify).addErrback(onError)

def run():
    pynotify.init("NotiServ Example Notifier")
    fetch()
    reactor.run()

if __name__ == '__main__':
    run()
