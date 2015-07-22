import json
import string
import random

def json_numbers(thing):
    for prop in thing:
        if (isinstance(thing[prop], unicode) \
            or isinstance(thing[prop], str)):
            # Json
            try:
                thing[prop] = json.loads(thing[prop])
            except:
                pass
            # Number
            try:
                if thing[prop].count('.') > 0:
                    thing[prop] = float(thing[prop])
                elif thing[prop][0] != '0':
                    thing[prop] = int(thing[prop])
            except:
                pass
            # Bool
            try:
                if strtrue(thing[prop]):
                    thing[prop] = True
                elif strfalse(thing[prop]):
                    thing[prop] = False
            except:
                pass
        if isinstance(thing[prop], int):
            thing[prop] = float(thing[prop])
        if isinstance(thing[prop], dict):
            thing[prop] = json_numbers(thing[prop])
    return thing

def str2bool(string):
    return strtrue(string)

def strtrue(string):
    return str(string).lower() in ("true",)

def strfalse(string):
    return str(string).lower() in ("false",)

def rand_id(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def params(webserver, files=True):
    """
    The GET argumants come as lists of one element
    This returns them as a dict
    NEEDED: type
    DEFAULTS
    GET: type=params
    """
    all_params = {}
    for param in webserver.request.arguments:
        all_params[param] = webserver.request.arguments[param][0]
    all_params = json_numbers(all_params)
    if files:
        for file in webserver.request.files:
            all_params[file] = webserver.request.files[file][0]["body"]
    return all_params
