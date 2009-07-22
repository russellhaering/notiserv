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
        self.putChild('post', NotificationPoster(manager))
        self.putChild('listen', NotificationRequester(manager))
        self.putChild('checkpasswd', PasswordCheckerResource(manager))
    
### Post Notification ####################################################

class NotificationPoster(resource.Resource):
    isLeaf = True

    def __init__(self, manager):
        resource.Resource.__init__(self)
        self.manager = manager

    def render_POST(self, request):
        if not self.manager.checkCredentials(request):
            return "{'success': false, 'message': 'Invalid Credentials'}"
        if 'notificationText' not in request.args:
            return "{'success': false, 'message': 'Blank notifications are not allowed'}"
        text = request.args['notificationText']
        print "Notifying clients for user", request.getUser()
        self.manager.notifyDelegates(request.getUser(), '({ "success" : "true", "message" : "' + text[0] + '" })')
        return "{'success': 'true', 'message': 'Notification Sent Successfully'}"


### Listen for Notification #####################################################

class NotificationRequester(resource.Resource):
    isLeaf = True

    def __init__(self, manager):
        resource.Resource.__init__(self)
        self.manager = manager
    
    def render_GET(self, request):
        print "Delegate Request Received"
        if not self.manager.checkCredentials(request):
            return "{'success': false, 'message': 'Invalid Credentials'}"
        self.manager.addDelegate(request.getUser(), ClientDelegate(request))
        return server.NOT_DONE_YET

### Verify Credentials #####################################################

class PasswordCheckerResource(resource.Resource):
    isLeaf = True

    def __init__(self, manager):
        resource.Resource.__init__(self)
        self.manager = manager
    
    def render_GET(self, request):
        if self.manager.checkCredentials(request):
            return "{'success': true}"
        else:
            return "{'success': false}"

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
        if user in self._clients:
            for delegate in self._clients[user]:
                delegate.notify(notification)
                print "Delegate Notified"
            del self._clients[user]
        else:
            print "No delegates for user", user

    def checkCredentials(self, request):
        user, passwd = request.getUser(), request.getPassword()
        if user in self._authDB and self._authDB[user] == passwd:
            return True
        else:
            request.setHeader('WWW-Authenticate', 'Basic realm="NotiServ API"')
            request.setResponseCode(http.UNAUTHORIZED)
            return False

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
        self.request.finish()


### main #################################################################

manager = ClientManager()
site = server.Site(RootResource(manager))
application = service.Application('notiserv') 

siteServer = internet.TCPServer(9100, site)
#cleanupServer = internet.TimerService(180, cancelConnections, internalRequester)

siteServer.setServiceParent(application)
#cleanupServer.setServiceParent(application)
