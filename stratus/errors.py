class BaseException(Exception):
    def __init__(self, reason="", fail_trace=False):
        super(BaseException, self).__init__()
        self.reason = reason
        self.fail_trace = fail_trace

    def __str__(self):
        return self.reason

class ServiceCallFailed(BaseException):
    pass

class RecvDisconnected(BaseException):
    pass
