class BaseException(Exception):
    def __init__(self, reason="", fail_trace=False):
        super(BaseException, self).__init__()
        self.reason = reason
        self.fail_trace = fail_trace

    def __str__(self):
        reason = self.reason
        if self.fail_trace:
            reason = "Remote Trace\r\n\r\n{0}".format(self.fail_trace)
        return reason

class ServiceCallFailed(BaseException):
    pass

class RecvDisconnected(BaseException):
    pass
