#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Insert Meter Location History data into the database from a tab-separated
data file.

Usage:
insertMECOMeterLocationHistoryData.py --filename ${FILENAME} [--email] [
--testing]
"""

__author__ = 'Daniel Zhang (張道博)'
__copyright__ = 'Copyright (c) 2013, University of Hawaii Smart Energy Project'
__license__ = 'https://raw.github' \
              '.com/Hawaii-Smart-Energy-Project/Maui-Smart-Grid/master/BSD' \
              '-LICENSE.txt'

import csv
import sys
from msg_db_connector import MSGDBConnector
from msg_db_util import MSGDBUtil
from msg_notifier import MSGNotifier
from msg_configer import MSGConfiger
from sek.logger import SEKLogger
import argparse

COMMAND_LINE_ARGS = None
logger = SEKLogger(__name__, 'debug')

def processCommandLineArguments():
    global argParser, COMMAND_LINE_ARGS, filename
    argParser = argparse.ArgumentParser(
        description = 'Perform insertion of Meter Location History contained '
                      'in the file given by --filename to the MECO database '
                      'specified in the configuration file.')
    argParser.add_argument('filename', metavar = '${FILENAME}', type = str,
                           default = '',
                           help = 'Name of file containing Meter Location '
                                  'History data.')
    argParser.add_argument('--email', action = 'store_true', default = False,
                           help = 'Send email notification if this flag is '
                                  'specified.')
    argParser.add_argument('--testing', action = 'store_true', default = False,
                           help = 'If this flag is on, '
                                  'insert data to the testing database as '
                                  'specified in the local configuration file.')
    commandLineArgs = argParser.parse_args()

if __name__ == '__main__':

    processCommandLineArguments()

    filename = COMMAND_LINE_ARGS.filename

    success = True
    anyFailure = False
    connector = MSGDBConnector(testing = COMMAND_LINE_ARGS.testing)
    conn = connector.connectDB()
    cur = conn.cursor()
    dbUtil = MSGDBUtil()
    notifier = MSGNotifier()
    msgBody = ''
    configer = MSGConfiger()

    if COMMAND_LINE_ARGS.testing:
        dbName = configer.configOptionValue("Database", "testing_db_name")
    else:
        dbName = configer.configOptionValue("Database", "db_name")

    msg = ("Loading Meter Location History data in file %s to database %s.\n" % (
        filename, dbName))
    sys.stderr.write(msg)
    msgBody += msg

    f = open(filename, "r")
    reader = csv.reader(f)

    data = []
    cols = ["meter_name", "mac_address", "installed", "uninstalled", "location",
            "address", "city", "latitude", "longitude", "service_point_id",
            "service_point_height", "service_point_latitude",
            "service_point_longitude", "notes"]

    lineCnt = 0

    with open(filename, "rU") as csvFile:
        for line in csv.reader(csvFile, delimiter = ","):
            if lineCnt != 0: # Skip header.
                data = line[0:len(cols)] # Overshoot columns to get the last column.

                for i in range(0, len(cols)):
                    if len(data[i]) == 0:
                        data[i] = 'NULL'
                    else:
                        # Escape single quotes with double single quotes in
                        # PostgreSQL.
                        data[i] = data[i].replace("'", "\'\'")
                        data[i] = "'" + data[i] + "'"

                sql = """INSERT INTO "MeterLocationHistory" (%s) VALUES (%s)""" % (
                    ','.join(cols), ','.join(data))
                logger.log("SQL: %s" % sql, 'debug')
                success = dbUtil.executeSQL(cur, sql)
                if not success:
                    anyFailure = True

            lineCnt += 1

    conn.commit()

    msg = ("Processed %s lines.\n" % lineCnt)
    sys.stderr.write(msg)
    msgBody += msg

    if not anyFailure:
        msg = "Finished inserting Meter Location History records.\n"
        sys.stderr.write(msg)
        msgBody += msg
    else:
        msg = "Meter Location History records were NOT successfully loaded.\n"
        sys.stderr.write(msg)
        msgBody += msg

    if COMMAND_LINE_ARGS.email:
        notifier.sendNotificationEmail(msgBody, testing = COMMAND_LINE_ARGS.testing)
