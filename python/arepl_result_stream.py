"""
File for storing result stream so it can be accessed by dump.
Once you close a stream you can't reopen, hence why this file just has a open method
"""

result_stream = None


def get_result_stream():
    return result_stream


def open_result_stream():
    global result_stream
    result_stream = open(3, "w")
