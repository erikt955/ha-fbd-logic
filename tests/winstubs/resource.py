"""Minimal resource stub so Home Assistant test harness imports on Windows."""
RLIMIT_NOFILE = 7
RLIM_INFINITY = -1


def getrlimit(res):
    return (8192, 8192)


def setrlimit(res, limits):
    return None
