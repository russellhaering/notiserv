import time
import re
from twisted.application import internet, service 
from twisted.web import http, server, resource, rewrite
from twisted.web.static import File

### tools ################################################################

def cancelConnections(notificationServer):
    notificationServer.clean()

### Root Resource ########################################################

class RootResource(resource.Resource):
    def __init__(self, manager):
        resource.Resource.__init__(self)
        self.putChild('', File('index.html'))
        self.putChild('jquery-1.3.2.min.js', File('jquery-1.3.2.min.js'))
        self.putChild('jquery.corners.min.js', File('jquery.corners.min.js'))
        self.putChild('post', NotificationRequester(manager))
        self.putChild('listen', ClientRequester(manager))
        self.putChild('checkpasswd', PasswordCheckerResource(manager))
    
### Post Notification ####################################################

class NotificationRequester(resource.Resource):
    isLeaf = True

    def __init__(self, manager):
        resource.Resource.__init__(self)
        self.manager = manager

    def render_POST(self, request):
        user = request.getUser()
        if (user == ""):
            request.setResponseCode(http.UNAUTHORIZED)
            return 'Try Logging In'
        print "Notifying clients for user", user
        self.manager.notifyDelegates(user, "Notification")
        return 'Notifications Sent'


### Listen for Notification #####################################################

class ClientRequester(resource.Resource):
    isLeaf = True

    def __init__(self, manager):
        resource.Resource.__init__(self)
        self.manager = manager
    
    def render_POST(self, request):
        user = request.getUser()
        if (user == ""):
            request.setResponseCode(http.UNAUTHORIZED)
            return 'Try Logging In'
        self.manager.addDelegate(user, ClientDelegate(request))
        return server.NOT_DONE_YET

### Verify Credentials #####################################################

class PasswordCheckerResource(resource.Resource):
    isLeaf = True

    def __init__(self, manager):
        resource.Resource.__init__(self)
        self.manager = manager
    
    def render_GET(self, request):
        user = request.getUser()
        passwd = request.getPassword()
        print user, passwd
        if self.manager.checkCredentials(user, passwd):
            return "{'success': true, 'message': 'Valid Credentials'}"
        else:
            request.setResponseCode(http.UNAUTHORIZED)
            return "{'sucecss': false, 'message': 'Invalid Credentials'}"

### client connection ####################################################

class ClientManager:
    def __init__(self):
        self._clients = {}
        self._authDB = {'russell': 'testing',}

    def addDelegate(self, user, delegate):
        if (user in self._clients):
            self._clients[user].append(delegate)
        else:
            self._clients[user] = [ delegate ]
        print "New Delegate Registered for User", user

    # This logic is bad, if the client reconnects fast enough they could
    # get the same notification over and over (maybe?)
    def notifyDelegates(self, user, notification):
        for delegate in self._clients[user]:
            delegate.notify(notification)
        del self._clients[user]

    def checkCredentials(self, user, passwd):
        return user != "" and passwd != "" and passwd == self._authDB[user]

    def registerUser(self, user, passwd):
        if user in self._authDB:
            return False
        else:
            self._authDB[user] = passwd

class ClientDelegate:
    def __init__(self, request):
        self.request = request

    def notify(self, notification):
        self.request.write(notification)
        self.request.end()


### main #################################################################

manager = ClientManager()
site = server.Site(RootResource(manager))
application = service.Application('notiserv') 

siteServer = internet.TCPServer(9100, site)
#cleanupServer = internet.TimerService(180, cancelConnections, internalRequester)

siteServer.setServiceParent(application)
#cleanupServer.setServiceParent(application)
