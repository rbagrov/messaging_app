import json


def get_protocol_contents(protocol_file, path=None):
    if not path:
        path = "messenger/"
    try:
        with open("{}{}.json".format(path, protocol_file), "r") as json_file:  # noqa
            return json.load(json_file)
    except Exception:
        return None
