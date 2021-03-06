#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Daniel Zhang (張道博)'
__copyright__ = 'Copyright (c) 2013, University of Hawaii Smart Energy Project'
__license__ = 'https://raw.github' \
              '.com/Hawaii-Smart-Energy-Project/Maui-Smart-Grid/master/BSD' \
              '-LICENSE.txt'


class MECOMapper(object):
    """
    Map attribute names to db column names.
    """

    # DB col names are differentiated from source data column names.
    # Source data column names are capitalized.
    # All DB col names are lowercase only.

    def __init__(self):
        """
        Constructor.

        This class provides mappings between XML names and database names. The
        table names correspond directly to the DB table names.

        It is used by the columns and values dictionary in the parser class to
        map the tags in the source XML to the correct database column names.

        The following are special mapping cases:
        * _fkey
        * _pkey
        * Event_Content
        """

        self.dbColsMeterData = {'_pkey': 'meter_data_id', 'MacID': 'mac_id',
                                'MeterName': 'meter_name',
                                'UtilDeviceID': 'util_device_id'}

        self.dbColsRegisterData = {'_fkey': 'meter_data_id',
                                   '_pkey': 'register_data_id',
                                   'EndTime': 'end_time',
                                   'NumberReads': 'number_reads',
                                   'StartTime': 'start_time'}

        self.dbColsRegisterRead = {'_fkey': 'register_data_id',
                                   '_pkey': 'register_read_id',
                                   'GatewayCollectedTime':
                                       'gateway_collected_time',
                                   'ReadTime': 'read_time',
                                   'RegisterReadSource': 'register_read_source',
                                   'Season': 'season'}

        self.dbColsRegister = {'_fkey': 'tier_id', '_pkey': 'register_id',
                               'CumulativeDemand': 'cumulative_demand',
                               'DemandUOM': 'demand_uom',
                               'Number': 'number', 'Summation': 'summation',
                               'SummationUOM': 'summation_uom'}

        self.dbColsIntervalReadData = {'_pkey': 'interval_read_data_id',
                                       '_fkey': 'meter_data_id',
                                       'EndTime': 'end_time',
                                       'IntervalLength': 'interval_length',
                                       'NumberIntervals': 'number_intervals',
                                       'StartTime': 'start_time'}

        self.dbColsInterval = {'_fkey': 'interval_read_data_id',
                               '_pkey': 'interval_id',
                               'BlockSequenceNumber': 'block_sequence_number',
                               'EndTime': 'end_time',
                               'GatewayCollectedTime': 'gateway_collected_time',
                               'IntervalSequenceNumber':
                                   'interval_sequence_number'}

        self.dbColsReading = {'_fkey': 'interval_id', '_pkey': 'reading_id',
                              'BlockEndValue': 'block_end_value',
                              'Channel': 'channel',
                              'RawValue': 'raw_value', 'UOM': 'uom',
                              'Value': 'value'}

        self.dbColsTier = {'_fkey': 'register_read_id', '_pkey': 'tier_id',
                           'Number': 'number'}

        self.dbColsEventData = {'_fkey': 'meter_data_id',
                                '_pkey': 'event_data_id', 'EndTime': 'end_time',
                                'NumberEvents': 'number_events',
                                'StartTime': 'start_time'}

        self.dbColsEvent = {'_fkey': 'event_data_id', '_pkey': 'event_id',
                            'EventName': 'event_name',
                            'EventTime': 'event_time',
                            'Event_Content': 'event_text'}


    def dbColumnsForTable(self, table):
        """
        Return DB mapping dict for a given table.

        :param table DB table name
        :returns: dict
        """

        dictName = 'self.dbCols' + table
        return eval(dictName)

    def mapColumnsToDB(self, tableName):
        """
        Return a list of comma-separated DB columns for a given table name.

        :param tableName: name in db
        :returns: list of database columns separated by commas
        """

        dictName = 'self.dbCols' + tableName

        try:
            result = ','.join(eval(dictName).values())
            return result
        except:
            return ()

    def getDBColNameDict(self, tableName):
        """
        Return a dictionary containing DB col names with keys of source data
        labels.

        :param DB tableName
        :return: dictionary keyed with DB column names.
        """

        dictName = 'self.dbCols' + tableName

        try:
            result = eval(dictName)
            return result
        except:
            return {}
