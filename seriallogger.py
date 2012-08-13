#!/usr/bin/env python
"""
Script to monitor a XO's serial port and log the data
seen into timestamped files.

A new file is made each time the XO is booted/rebooted.

Known issues:
- The program will delete logfiles which are too short to help
avoid leaving unncessary files if a XO is manually rebooted or
a XO is powered off while early in the process of rebooting.
But if a XO does a quick mostly OFW reboot on its own this could
be deleted as well.
The number of lines OFW will show during a normal boot varies
by XO/firmware between approximately 10-16.

Author: Samuel Greenfeld
Copyright 2012 One Laptop per Child
"""

import re
import os
import serial
import sys
import time

DESTDIR = "/tmp/logs"
LOG_LENGTH_UNKEEPABLE = 10
OFW_BANNER_MAX_LENGTH = 50
SERIAL_DEFAULT_TIMEOUT = 1800  # 30 Minutes


def log_until_next_boot(sourcedata, serialnum='Unknown',
                        initiallines=None):
    """
    Log data from a XO to a file named after its serial number
    until the string "Forthmacs" or "CForth built" is seen (XO boot/reboot)

    The first string seen varies by XO model.

    Returns True if either string is seen, False otherwise
    """
    starttime = time.gmtime()
    destfile = DESTDIR + "/" + time.strftime("%Y%m%d_%H%M%S", starttime) \
        + "-" + serialnum
    logfile = open(destfile, "w")
    logfile.write("--- Logfile started for '" + serialnum + "' at "
                  + time.asctime(starttime) + " GMT ---\n")

    datalinecount = 0

    if initiallines:
        logfile.writelines(initiallines)
        datalinecount += len(initiallines)

    for line in sourcedata:
        if line.find("Forthmacs") >= 0 or line.find("CForth built") >= 0:
            logfile.write(line)
            logfile.write("--- Logfile closed for '" + serialnum + "' at "
                          + time.asctime(time.gmtime())
                          + " GMT (Reboot detected) ---\n")
            logfile.close()
            if datalinecount <= LOG_LENGTH_UNKEEPABLE:
                os.unlink(destfile)
            return True

        logfile.write(line)
        datalinecount += 1

    # EOF reached or timeout occurred
    logfile.write("--- Logfile closed for '" + serialnum + "' at "
                  + time.asctime(time.gmtime()) + " GMT (EOF/timeout) ---\n")
    logfile.close()
    if datalinecount <= LOG_LENGTH_UNKEEPABLE:
        os.unlink(destfile)
    return False


def get_sn_banner(sourcedata):
    """
    Gets the serial number of a XO from the source file{-like} specified by
    sourcedata (which should already be open)

    Returns the touple (None, None) if the OFW banner is not seen prior to
    a EOF/Timeout condition.

    Returns a touple with the (1) serial number or 'Unknown' and
    (2) the OFW banner lines seen up to that point if successful

    Raises an exception if too many lines are seen for the data processed to be
    an OFW banner.
    """
    failsafe = 0
    for line in sourcedata:
        bannerlines = []

        bannerlines.append(line)

        serialmatch = re.search('S/N ([SC][HS][CN]\w{8}|Unknown)', line)
        if serialmatch:
            serialnum = serialmatch.group(1)
            return(serialnum, bannerlines)

        failsafe += 1
        if failsafe > OFW_BANNER_MAX_LENGTH:
            raise Exception('OFW banner > 50 lines; unexpected')


def main():
    """
    Main function to start the logger & close it when finished

    A serial port to open (such as /dev/ttyUSB0) should be specified
    on the command line.

    The main function closes the datasource when the log_until_next_boot
    function times out for data, hits EOF, or otherwise signals
    no additional run is necessary.
    """
    #datasource = open("/tmp/testfile", "r")
    datasource = serial.Serial(sys.argv[1], baudrate=115200,
                               timeout=SERIAL_DEFAULT_TIMEOUT)
    need_another_run = log_until_next_boot(datasource)
    while need_another_run:
        (serialnum, logdata) = get_sn_banner(datasource)
        need_another_run = log_until_next_boot(datasource, serialnum, logdata)
        # time.sleep(2)  # For file Testing

    datasource.close()
    exit(0)


if __name__ == '__main__':
    main()
