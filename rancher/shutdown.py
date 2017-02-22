"""Shutdown wrapper for cli"""

def err(text):
    """Shutdown with error"""

    print 'Error: ' + text
    exit(2)


def info(text):
    """Normal shutdown"""

    print text
    exit(0)
