
from random import randint

def entropy(length):
    return "".join(chr(randint(0, 255)) for _ in xrange(length))
