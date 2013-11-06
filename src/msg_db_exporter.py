#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'Daniel Zhang (張道博)'
__copyright__ = 'Copyright (c) 2013, University of Hawaii Smart Energy Project'
__license__ = 'https://raw.github' \
              '.com/Hawaii-Smart-Energy-Project/Maui-Smart-Grid/master/BSD' \
              '-LICENSE.txt'

from msg_logger import MSGLogger
from msg_time_util import MSGTimeUtil
import subprocess
from msg_configer import MSGConfiger
import gzip
import os
import httplib2
#import pprint
from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.file import Storage
from apiclient import errors
from msg_notifier import MSGNotifier
import time
import datetime
import argparse
import hashlib
from functools import partial

commandLineArgs = None


def processCommandLineArguments():
    """
    Generate command-line arguments. Load them into global variable
    commandLineArgs.
    """

    global parser, commandLineArgs
    parser = argparse.ArgumentParser(description = '')
    parser.add_argument('--dbname', help = 'Database file to be uploaded.')
    parser.add_argument('--fullpath',
                        help = 'Full path to database file to be uploaded.')
    parser.add_argument('--testing', action = 'store_true', default = False)

    commandLineArgs = parser.parse_args()


class MSGDBExporter(object):
    """
    Export MSG DBs as SQL scripts.

    Supports export to local storage and to cloud storage.
    """

    @property
    def cloudFiles(self):
        self._cloudFiles = self.driveService.files().list().execute()
        return self._cloudFiles

    @property
    def driveService(self):
        if self._driveService:
            return self._driveService

        if not self.credentialPath:
            raise Exception("Credential path is required.")
        storage = Storage('%s/google_api_credentials' % self.credentialPath)

        #self.logger.log("Retrieving credentials.")
        #self.retrieveCredentials()
        #storage.put(self.googleAPICredentials)

        self.googleAPICredentials = storage.get()

        self.logger.log("Authorizing credentials.", 'info')
        http = httplib2.Http()
        http = self.googleAPICredentials.authorize(http)

        self.logger.log("Authorized.", 'info')

        self._driveService = build('drive', 'v2', http = http)
        return self._driveService


    def __init__(self):
        """
        Constructor.
        """

        self.logger = MSGLogger(__name__, 'debug')
        self.timeUtil = MSGTimeUtil()
        self.configer = MSGConfiger()

        # Google Drive parameters.
        self.clientID = self.configer.configOptionValue('Export',
                                                        'google_api_client_id')
        self.clientSecret = self.configer.configOptionValue('Export',
                                                            'google_api_client_secret')
        self.oauthScope = 'https://www.googleapis.com/auth/drive'
        self.oauthConsent = 'urn:ietf:wg:oauth:2.0:oob'
        self.googleAPICredentials = ''
        self.exportPath = self.configer.configOptionValue('Export',
                                                          'db_export_path')
        self.credentialPath = self.exportPath
        self.credentialStorage = Storage(
            '%s/google_api_credentials' % self.credentialPath)

        self._driveService = None
        self._cloudFiles = None


    def exportDB(self, databases = None, toCloud = False, testing = False):
        """
        Export a set of DBs to local storage.

        Uses

        pg_dump -s -h ${HOST} ${DB_NAME} > ${DUMP_TIMESTAMP}_{DB_NAME}.sql

        :param databases: List of database names.
        :param toCloud: If set to True, then export will also be copied to
        cloud storage.
        """

        host = self.configer.configOptionValue('Database', 'db_host')

        for db in databases:
            self.logger.log('Exporting %s.' % db, 'info')
            conciseNow = self.timeUtil.conciseNow()
            dumpName = "%s_%s" % (conciseNow, db)
            command = """pg_dump -h %s %s > %s/%s.sql""" % (host, db,
                                                            self.configer
                                                            .configOptionValue(
                                                                'Export',
                                                                'db_export_path'),
                                                            dumpName)
            fullPath = '%s/%s' % (
                self.configer.configOptionValue('Export', 'db_export_path'),
                dumpName)

            try:
                if not testing:
                    subprocess.check_call(command, shell = True)
            except subprocess.CalledProcessError, e:
                self.logger.log("An exception occurred: %s" % e)

            self.logger.log("Compressing %s using gzip." % db, 'info')
            if not testing:
                self.gzipCompressFile(fullPath)

            if toCloud:
                self.uploadDBToCloudStorage('%s.sql.gz' % fullPath,
                                            testing = commandLineArgs.testing)

            # Remove the uncompressed file.
            try:
                os.remove('%s.sql' % fullPath)
            except OSError, e:
                self.logger.log(
                    'Exception while removing %s.sql: %s.' % (fullPath, e))


    def uploadDBToCloudStorage(self, fullPath = '', testing = False):
        """
        Export a DB to cloud storage.

        :param fullPath of DB file to be exported.
        """

        success = True
        dbName = os.path.basename(fullPath)

        self.logger.log('full path %s' % os.path.dirname(fullPath), 'debug')
        #self.startDriveService(os.path.dirname(fullPath))

        self.logger.log("Uploading %s." % dbName)

        try:

            if not testing:
                media_body = MediaFileUpload(fullPath,
                                             mimetype =
                                             'application/gzip-compressed',
                                             resumable = True)
                body = {'title': dbName,
                        'description': 'Hawaii Smart Energy Project gzip '
                                       'compressed DB export.',
                        'mimeType': 'application/gzip-compressed'}

                file = self.driveService.files().insert(body = body,
                                                        media_body =
                                                        media_body).execute()

                #pprint.pprint(file)
            else:
                self.logger.log("Called upload with testing flag on.")

        except (errors.ResumableUploadError):
            self.logger.log("Cannot initiate upload of %s." % dbName, 'error')
            success = False

        if not self.verifyMD5Sum(fullPath, self.fileIDForFileName(dbName)):
            self.logger.log('Failed MD5 checksum verification.', 'INFO')
            success = False

        if success:
            self.logger.log("Finished.")


    def retrieveCredentials(self):
        """
        Perform authorization at the server.
        """

        flow = OAuth2WebServerFlow(self.clientID, self.clientSecret,
                                   self.oauthScope, self.oauthConsent)
        authorize_url = flow.step1_get_authorize_url()
        print 'Go to the following link in your browser: ' + authorize_url
        code = raw_input('Enter verification code: ').strip()
        self.googleAPICredentials = flow.step2_exchange(code)

        print "refresh_token = %s" % self.googleAPICredentials.refresh_token
        print "expiry = %s" % self.googleAPICredentials.token_expiry


    def gzipCompressFile(self, fullPath):
        """
        @todo Test valid compression.
        @todo Move to file utils.

        :param fullPath: Full path of the file to be compressed.
        """

        f_in = open('%s.sql' % fullPath, 'rb')
        f_out = gzip.open('%s.sql.gz' % fullPath, 'wb')
        f_out.writelines(f_in)
        f_out.close()
        f_in.close()


    def freeSpace(self):
        """
        Get free space from the drive service.

        :param driveService: Object for the drive service.
        :returns: Free space on the drive service.
        """

        aboutData = self.driveService.about().get().execute()
        return int(aboutData['quotaBytesTotal']) - int(
            aboutData['quotaBytesUsed']) - int(
            aboutData['quotaBytesUsedInTrash'])


    def uploadWasSuccessful(self, file):
        """
        Determine upload success.
        """
        success = False
        return success


    def deleteFile(self, fileID = ''):
        """
        Delete the file with ID fileID.

        :param fileID: Googe API file ID.
        """

        #self.logger.log('http: %s', self.driveService._http)
        self.logger.log('Deleting File ID: %s' % fileID, 'debug')

        try:
            self.driveService.files().delete(fileId = fileID).execute()

        except errors.HttpError, error:
            self.logger.log('An error occurred: %s' % error, 'error')


    def deleteOutdatedFiles(self):
        for item in self.cloudFiles['items']:
            t1 = datetime.datetime.strptime(item['createdDate'],
                                            "%Y-%m-%dT%H:%M:%S.%fZ")
            t2 = datetime.datetime.now()
            tdelta = t2 - t1

            if tdelta > datetime.timedelta(days = 1):
                self.deleteFile(fileID = item['id'])


    def sendNotificationOfFiles(self):
        pass


    def verifyMD5Sum(self, localFilePath, remoteFileID):

        self.logger.log('local file path: %s' % localFilePath)
        # Get the md5sum for the local file.
        f = open(localFilePath, mode = 'rb')
        fContent = hashlib.md5()
        for buf in iter(partial(f.read, 128), b''):
            fContent.update(buf)
        localMD5Sum = fContent.hexdigest()
        f.close()

        self.logger.log('local md5: %s' % localMD5Sum, 'DEBUG')

        # Get the md5sum for the remote file.
        for item in self.cloudFiles['items']:
            if (item['id'] == remoteFileID):
                self.logger.log('remote md5: %s' % item['md5Checksum'], 'DEBUG')
                if localMD5Sum == item['md5Checksum']:
                    return True
                else:
                    return False
        return False


    def fileIDForFileName(self, filename):
        """
        Get the file ID for the given filename.
        """

        for item in self.cloudFiles['items']:
            self.logger.log('title: %s' % item['title'], 'DEBUG')
            if (item['title'] == filename):
                return item['id']
        return None


if __name__ == '__main__':
    processCommandLineArguments()

    exporter = MSGDBExporter()
    notifier = MSGNotifier()
    exporter.logger.shouldRecord = True

    startTime = time.time()
    exporter.exportDB(
        [exporter.configer.configOptionValue('Export', 'dbs_to_export')],
        toCloud = True, testing = commandLineArgs.testing)
    wallTime = time.time() - startTime
    wallTimeMin = int(wallTime / 60.0)
    wallTimeSec = (wallTime - wallTimeMin * 60.0)

    exporter.logger.log('Free space remaining: %d' % exporter.freeSpace(),
                        'info')

    exporter.logger.log(
        'Wall time: {:d} min {:.2f} s.'.format(wallTimeMin, wallTimeSec),
        'info')

    #print 'Recording:\n%s' % exporter.logger.recording


