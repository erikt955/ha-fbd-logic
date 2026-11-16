"""Minimal fcntl stub so Home Assistant test harness imports on Windows."""
LOCK_EX = 2
LOCK_NB = 4
LOCK_UN = 8
LOCK_SH = 1
F_GETFL = 3
F_SETFL = 4


def flock(fd, op):
    return None


def lockf(fd, op, *args):
    return None


def fcntl(fd, op, arg=0):
    return 0


def ioctl(fd, op, arg=0, mutate_flag=True):
    return 0
