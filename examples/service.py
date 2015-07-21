import sys
import uuid
import time
import stratus

NUM_SERVICES = 1
SERVICE_NAME = "db"

class service(stratus.stratus):

    def query(self, obj):
        return obj

    def uuid(self):
        return self.name

    def say_hello(self, name):
        return u"Hello " + unicode(name)

def main():
    for i in xrange(0 ,NUM_SERVICES):
        # Create the service
        to_launch = service()
        # Name the service
        name = SERVICE_NAME + "_" + str(i)
        # Connect service to cluster
        to_launch.connect(name=name, host=sys.argv[1], service=SERVICE_NAME)
    # Host services
    while True:
        time.sleep(300)

if __name__ == '__main__':
    main()
