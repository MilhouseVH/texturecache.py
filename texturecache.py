#!/usr/bin/python
# -*- coding: utf-8 -*-

################################################################################
#
#  Copyright (C) 2013 Neil MacLeod (texturecache@nmacleod.com)
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# Simple utility to query, validate, clean and refresh the XBMC texture cache.
#
# https://github.com/MilhouseVH/texturecache.py
#
# Usage:
#
#  x) Extract - dump - all or filtered cached textures information. Default
#  field separator can be overridden by specifying an alternate value in
#  properties file (see below). Filter expression must be valid WHERE clause.
#  Option X will extract only those rows that have missing cached artwork.
#
#  s) Search texture cache for specific partial url names, dumping results.
#  Option S will return only results for those items that no longer have a
#  matching cached artwork.
#
#  d) Delete one or more rows from the texture cache database, along with
#  any associated cached artwork.
#
#  r) Walk the Thumbnails folder, identifying those cached items that are no
#  longer referenced in the SQL db, with option (R) to automatically purge
#  the orphaned files.
#
#  c) Refresh cache with all artwork. Specify one of the following as an
#  optional parameter, otherwise all but songs will be refreshed:
#
#       albums, artists, movies, tags, sets, tvshows, songs
#
#  When specifying a class to refresh, a third optional argument can be provided
#  to restrict (filter) the movie/show/album etc. that are processed.
#
#  C) Similar to (c), but will remove artwork from the cache to ensure
#  artwork is always refreshed. Mandatory class and filter required to limit
#  accidental processing, though a filter of ".*" will match everything.
#
#  j) Query media library by class with optional filter, returning JSON results.
#
#  J) As per j), but include additional JSON audio/video query fields as specified
#  in the properties file, using comma-delimited lists. Additional fields can have
#  a significant impact on performance.
#
#  qa) Locate movies/tags/tvshows with missing artwork, plot, mpaa certificates, that
#  have been added within qaperiod days. Add qa.rating=yes to properties file for
#  rating property to be included in QA tests.
#
#  qax) Same as (qa), but will perform remove/rescan of media for items that fail QA.
#
#  p/P) Prune Cache: Identify items in the texture cache that don't exist in the media
#  library. These items are typically artwork image previews and other non-essential
#  assets downloaded by addons that can be safely removed from the texture cache.
#  The p option will display the items that could be removed, while the P option will
#  perform the same checks but then also physically remove qualifying items from the
#  texture cache. Due to the amount of processing involved this is quite a slow process.
#
#  To refresh the cache the Webserver service must be enabled without a
#  username or password.
#
#  To allow JSON access, you must enable "Allow programs on this system to control XBMC"
#  in System -> Services -> Remote control. Also enable "Allow other programs..." if
#  accessing JSON functions of a remote XBMC client (ie. xbmc.host is not localhost).
#
# Properties File:
#
#  A properties file, texturecache.cfg, will be read if found in the same
#  folder as this script. It can be used to override the default field
#  separator, the location of the XBMC userdata folder, the location and name
#  of the Texture db (relative to the XBMC userdata folder), and the Thumbnails
#  folder (also relative to the XBMC userdata folder).
#
#  Example texturecache.cfg (showing default values):
#
#    sep = |
#    userdata = ~/.xbmc/userdata
#    dbfile = Database/Textures13.db
#    thumbnails = Thumbnails
#    xbmc_host = localhost
#    webserver.port = 8080
#    webserver.singleshot = no
#    rpc_port = 9090
#    extrajson.albums  = None
#    extrajson.artists = None
#    extrajson.songs   = file
#    extrajson.movies  = trailer, streamdetails, file
#    extrajson.sets    = None
#    extrajson.tvshows.tvshow = None
#    extrajson.tvshows.season = None
#    extrajson.tvshows.episode= streamdetails, file
#    qaperiod = 30
#    qa.rating = false
#    cache.castthumb = false
#    cache.ignore.types = image://video, image://music
#    logfile = None
#
# Dumped data format:
#
#  rowid, cachedurl, height, width, usecount, lastusetime, lasthashcheck, url
#
# Changelog:
#
#  Version 0.3.2 - 29/03/2013
#  * Return large data objects for garbage collection
#  * Disabled logging of "Duplicate" items - can be
#    excessive, and rarely useful.
#
#  Version 0.3.1 - 28/03/2013
#  * Changed cache options (c and C) to be muli-threaded.
#    Increase number of download threads by modifying
#    download.threads in properties. Default is 2.
#  * Added "nc" option, dry-run version of c.
#  * Better error detection - will determine at startup what
#    resources are required by each option, and abort when
#    not available.
#  * Move to github.
#
#  Version 0.3.0 - 26/03/2013
#  * Added support for multiple tags, combine with "and"/"or".
#    Example: c tags "comedy and standup"
#    Example: c tags "action or adventure"
#
#    Combinations of "and" and "or" will be accepted, but may or may not
#    return valid results.
#
#  Version 0.2.9 - 26/03/2013
#  * Added tag support..
#    Tag supporting options: j, J, jd, Jd, c, C, qa and qax.
#    For example "c tags live-comedy", to re-cache movies with the
#    "live-comedy" tag. Partial tag matches will also succeed.
#
#  Version 0.2.8 - 25/03/2013
#  * Add url decode functionality (jd, Jd)
#
#  Version 0.2.7 - 25/03/2013
#  * Add "Duplicate" statistic for images that are cached
#    more than once - only first cache attempt will succeed,
#    subsequent attempts will be ignored and account for as
#    a duplicate.
#  * Use classes for configuration and logging.
#  * Allow absolute paths to be used for thumbnails and dbfile properties.
#  * Add qa.file = yes/no (default:no) property, to verify existence of
#    media file (will not initiate remove/rescan in qax option, obviously).
#
#  Version 0.2.6 - 24/03/2013
#  * Remove media items (movies, episodes) that fail QA when
#    during qax operation - this should result in the items being
#    correctly re-scraped.
#
#  Version 0.2.5 - 24/03/2013
#  * Fix hash calculation error in R option (sorry charrua!)
#  * Apply 5% limit when identifying orphaned files (option R). Abort
#    file orphaned file removal if limit is exceeded.
#
#  Version 0.2.4 - 24/03/2013
#  * Added cache.ignore.types property, to ignore (don't delete,
#    don't cache) certain image types, such as image://video and
#    image://music (both the default).
#    Use comma delimited patterns, eg. "image://video, ^nfs.*". Set
#    to None to process all URLs. Matches anywhere within URL.
#  * Added extra QA rule, "[artwork] (uncached)", which is a warning
#    only, and won't cause a directory re-scan by itself, mostly
#    because it's usually pointless.
#
#  Version 0.2.3 - 24/03/2013
#  * Add logfile property, eg. logfile=/tmp/cache.log
#
#  Version 0.2.2 - 24/03/2013
#  * Fix pre-Python 2.7.3 incompatibility.
#
#  Version 0.2.1 - 23/03/2013
#  * Added webserver.username/webserver.password authentication.
#  * Summary of processing for c/C options
#
#  Version 0.2.0 - 23/03/2013
#  * Auto-detect webserver.singleshot - unless already enabled
#    in properties, will be automatically enabled when first web
#    connection request fails, with the request being attempted a
#    second time. Best to leave disabled, and only used when required.
#
#  Version 0.1.9 - 23/03/2013
#  * Add webserver.singleshot = yes/no property to prevent web server
#    connection from being reused, as this seems to cause a problem for
#    some users. Default behaviour is to reuse the connection.
#
#  Version 0.1.8 - 22/03/2013
#  * Optionally cache cast thumbnails - add cache.castthumb = yes/no/true/false
#    to properties file. Default is no/false.
#
#  Version 0.1.7 - 21/03/2013
#  * When pruning the texture cache, don't consider files that are
#    stored in the local filesystem as these are most likely add-on
#    related.
#
#  Version 0.1.6 - 20/03/2013
#  * Add support for season-all-(fanart|banner).
#
#  Version 0.1.5 - 17/03/2013
#  * Add prune (p) option.
#  * Significantly improved performance of r/R option
#
#  Version 0.1.4 - 16/03/2013
#  * Refactor connection code
#  * Add keyboard interrupt exception handler
#
#  Version 0.1.3 - 15/03/2013
#  * Switch JSON to use tcp sockets.
#  * Add xbmc_host (localhost) and rpc_port (9090) properties
#
#  Version 0.1.2 - 13/03/2013
#  * Restrict qa to consider only movies/tvshows added within qaperiod days.
#
#  Version 0.1.1 - 13/03/2013
#  * Add qa option to identify missing artwork and plots (movies and tvshows only)
#
#  Version 0.1.0 - 13/03/2013
#  * Add JSON additional field support
#  * Use File.PrepareDownload method to obtain correct image download URL
#
#  Version 0.0.9 - 10/03/2013
#  * Add JSON query option (j)
#
#  Version 0.0.8 - 10/03/2013
#  * Clarify licensing with addition of GPLv2 license
#
#  Version 0.0.7 - 10/03/2013
#  * Default value of userdata property changed to ~/.xbmc/userdata, with user expansion
#
#  Version 0.0.6 - 09/03/2013
#  * Add function to forcibly cache artwork, even when already present in texture cache (C)
#  * Add season-all.[tbn|png|jpg] TV Sshow poster support
#
#  Version 0.0.5 - 08/03/2013
#  * Add function to cache artwork missing from texture cache (c)
#
#  Version 0.0.4 - 06/03/2013
#  * Improve unicode handling
#
#  Version 0.0.3 - 06/03/2013
#  * Add file summary option (f)
#
#  Version 0.0.2 - 05/03/2013
#  * Add support for older Dharma version 6 database
#  * Fix unicode conversion
#
#  Version 0.0.1 - 05/03/2013
#  * First release
#
################################################################################

import sqlite3 as lite
import os, sys, ConfigParser, StringIO, json, re, datetime, time
import httplib, urllib, socket, base64
import Queue, threading

#
# Config class. Will be a global object.
#
class MyConfiguration(object):
  def __init__( self ):

    self.VERSION="0.3.2"

    config = ConfigParser.SafeConfigParser(defaults={
                                            "format": "%%06d",
                                            "sep": "|",
                                            "userdata": "~/.xbmc/userdata",
                                            "dbfile": "Database/Textures13.db",
                                            "thumbnails": "Thumbnails",
                                            "xbmc.host": "localhost",
                                            "webserver.port": "8080",
                                            "webserver.singleshot": "no",
                                            "webserver.username": None,
                                            "webserver.password": None,
                                            "rpc.port": "9090",
                                            "download.threads": "2",
                                            "extrajson.albums": None,
                                            "extrajson.artists": None,
                                            "extrajson.songs": None,
                                            "extrajson.movies": None,
                                            "extrajson.sets": None,
                                            "extrajson.tvshows.tvshow": None,
                                            "extrajson.tvshows.season": None,
                                            "extrajson.tvshows.episode": None,
                                            "qaperiod": "30",
                                            "qa.rating": "no",
                                            "qa.file": "no",
                                            "cache.castthumb": "no",
                                            "cache.ignore.types": "image://video, image://music",
                                            "logfile": None,
                                            "allow.recacheall": "no"
                                            }
                                          )

    self.DEBUG = True if "PYTHONDEBUG" in os.environ and os.environ["PYTHONDEBUG"].lower()=="y" else False

    self.CONFIG_NAME = "texturecache.cfg"

    # Try and find a config file in current directory, else look in
    # same directory as script itself
    self.FILENAME = "%s%s%s" % (os.getcwd(), os.sep, self.CONFIG_NAME)
    if not os.path.exists(self.FILENAME):
      self.FILENAME = "%s%s%s" % (os.path.dirname(__file__), os.sep, self.CONFIG_NAME)

    cfg = StringIO.StringIO()
    cfg.write("[xbmc]\n")
    if os.path.exists(self.FILENAME): cfg.write(open(self.FILENAME, "r").read())
    cfg.seek(0, os.SEEK_SET)
    config.readfp(cfg)

    self.IDFORMAT = config.get("xbmc", "format")
    self.FSEP = config.get("xbmc", "sep")

    self.XBMC_BASE = os.path.expanduser(config.get("xbmc", "userdata"))
    self.TEXTUREDB = config.get("xbmc", "dbfile")
    self.THUMBNAILS = config.get("xbmc", "thumbnails")

    if self.XBMC_BASE[-1:] != "/": self.XBMC_BASE += "/"
    if self.THUMBNAILS[-1:] != "/": self.THUMBNAILS += "/"

    self.XBMC_BASE = self.XBMC_BASE.replace("/", os.sep)
    self.TEXTUREDB = self.TEXTUREDB.replace("/", os.sep)
    self.THUMBNAILS = self.THUMBNAILS.replace("/", os.sep)

    self.XBMC_HOST = config.get("xbmc", "xbmc.host")
    self.WEB_PORT = config.get("xbmc", "webserver.port")
    self.RPC_PORT = config.get("xbmc", "rpc.port")

    self.DOWNLOAD_THREADS_DEFAULT = int(config.get("xbmc", "download.threads"))

    self.DOWNLOAD_THREADS = {}
    for x in ["albums", "artists", "songs", "movies", "sets", "tags", "tvshows"]:
      temp = self.DOWNLOAD_THREADS_DEFAULT
      try:
        temp = int(config.get("xbmc", "download.threads.%s" % x))
      except ConfigParser.NoOptionError:
        pass
      self.DOWNLOAD_THREADS["download.threads.%s" % x] = temp

    self.XTRAJSON = {}
    for x in ["extrajson.albums", "extrajson.artists", "extrajson.songs",
              "extrajson.movies", "extrajson.sets",
              "extrajson.tvshows.tvshow", "extrajson.tvshows.season", "extrajson.tvshows.episode"]:
      temp = config.get("xbmc", x)
      self.XTRAJSON[x] = temp if temp != "" else None

    self.QAPERIOD = int(config.get("xbmc", "qaperiod"))
    adate = datetime.date.today() - datetime.timedelta(days=self.QAPERIOD)
    self.QADATE = adate.strftime("%Y-%m-%d")

    temp = config.get("xbmc", "qa.rating").lower() if config.get("xbmc", "qa.rating") else "yes"
    self.QA_RATING = True if (temp == "yes" or temp == "true") else False

    temp = config.get("xbmc", "qa.file").lower() if config.get("xbmc", "qa.file") else "yes"
    self.QA_FILE = True if (temp == "yes" or temp == "true") else False

    temp = config.get("xbmc", "cache.castthumb").lower() if config.get("xbmc", "cache.castthumb") else "yes"
    self.CACHE_CAST_THUMB = True if (temp == "yes" or temp == "true") else False

    temp = config.get("xbmc", "webserver.singleshot").lower() if config.get("xbmc", "webserver.singleshot") else "yes"
    self.WEB_SINGLESHOT = True if (temp == "yes" or temp == "true") else False

    web_user = config.get("xbmc", "webserver.username")
    web_pass = config.get("xbmc", "webserver.password")
    if (web_user and web_pass): self.WEB_AUTH_TOKEN = base64.encodestring('%s:%s' % (web_user, web_pass)).replace('\n', '')
    else: self.WEB_AUTH_TOKEN = None

    self.LOGFILE = config.get("xbmc", "logfile")

    temp = config.get("xbmc", "cache.ignore.types")
    if temp != None and temp.lower() == "none": temp = None
    self.CACHE_IGNORE_TYPES = [re.compile(x.strip()) for x in temp.split(',')] if temp else None

    temp = config.get("xbmc", "allow.recacheall").lower()
    self.RECACHEALL = True if (temp == "yes" or temp == "true") else False


  def getFilePath( self, filename = "" ):
    # Absolute path, or colon (likely Windows drive ref)
    if self.THUMBNAILS.startswith(os.sep) or self.THUMBNAILS.find(":") != -1:
      return "%s%s" % (self.THUMBNAILS, filename)
    else:
      return "%s%s%s" % (self.XBMC_BASE, self.THUMBNAILS, filename)

  def getDBPath( self ):
    # Absolute path, or colon (likely Windows drive ref)
    if self.TEXTUREDB.startswith(os.sep) or self.TEXTUREDB.find(":") != -1:
      return self.TEXTUREDB
    else:
      return "%s%s" % (self.XBMC_BASE, self.TEXTUREDB)

#
# Very simple logging class. Will be a global object, also passed to threads
# hence the Lock() methods..
#
# Writes progress information to stderr so that
# information can still be grepp'ed easily (stdout).
#
# Prefix logfilename with + to enable flushing after each write.
#
class MyLogger():
  def __init__( self ):
    self.lastlen = 0
    self.now = 0
    self.LOG = False
    self.LOGFILE = None
    self.LOGFLUSH = False
    self.DEBUG = False

  def __del__( self ):
    if self.LOGFILE: self.LOGFILE.close()

  def errout(self, data, every=0, newLine=False):
    with threading.Lock():
      if every != 0:
        self.now += 1
        if self.now != 1:
          if self.now <= every: return
          else: self.reset(initialValue=1)
      else:
        self.reset(initialValue=0)

      udata = self.removeNonAscii(data, "?")
      spaces = self.lastlen - len(udata)
      self.lastlen = len(udata)
      if spaces > 0:
        sys.stderr.write("%-s%*s\r" % (udata, spaces, " "))
      else:
        sys.stderr.write("%-s\r" % udata)
      if newLine:
        sys.stderr.write("\n")
        self.last = 0
      sys.stderr.flush()

  def reset(self, initialValue=0):
    self.now = initialValue

  def stdout( self, data):
    with threading.Lock():
      udata = self.removeNonAscii(data, "?")
      spaces = self.lastlen - len(udata)
      self.lastlen = len(udata)
      if spaces > 0:
        sys.stdout.write("%-s%*s" % (udata, spaces, " "))
      else:
        sys.stdout.write("%-s" % udata)
      sys.stdout.flush()

  def debug(self, data, jsonrequest=None, every=0, newLine=False, newLineBefore=False):
    if self.DEBUG:
      with threading.Lock():
        if newLineBefore: sys.stderr.write("\n")
        self.errout("%s: %s" % (datetime.datetime.now(), data), every, newLine)
    self.log(data, jsonrequest=jsonrequest)

  def setLogFile(self, filename):
    with threading.Lock():
      if filename:
        self.LOG = True
        self.LOGFLUSH = filename.startswith("+")
        if self.LOGFLUSH: filename = filename[1:]

        self.LOGFILE = open(filename, "w")
      else:
        self.LOG = False
        if self.LOGFILE:
          self.LOGFILE.close()
          self.LOGFILE = None

  def log(self, data, jsonrequest = None):
    if self.LOG:
      with threading.Lock():
        t = threading.current_thread().name
        if jsonrequest == None:
          self.LOGFILE.write("%s:%-10s: %s\n" % (datetime.datetime.now(), t, data.encode("utf-8")))
        else:
          self.LOGFILE.write("%s:%-10s: %s [%s]\n" % (datetime.datetime.now(), t,
            data.encode("utf-8"), json.dumps(jsonrequest).encode("utf-8")))
        if self.DEBUG or self.LOGFLUSH: self.LOGFILE.flush()

  def removeNonAscii(self, s, replaceWith = ""):
    if replaceWith == "":
      return  "".join([x if ord(x) < 128 else ("%%%02x" % ord(x)) for x in s])
    else:
      return  "".join([x if ord(x) < 128 else replaceWith for x in s])

#
# Image loader thread class.
#
class MyImageLoader(threading.Thread):
  def __init__(self, work_queue, error_queue, maxItems, config, progress, totals, force=False, retry=10):
    threading.Thread.__init__(self)
    self.work_queue = work_queue
    self.error_queue = error_queue
    self.maxItems = maxItems

    self.config = config
    self.progress = progress
    self.database = MyDB(config, progress)
    self.json = MyJSONComms(config, progress)
    self.totals = totals

    self.force = force
    self.retry = retry

    self.LAST_URL = None

  def run(self):

    while not stopped.is_set():
      item = self.work_queue.get()

      if not self.loadImage(item.itype, item.filename, item.dbid, item.cachedurl, self.retry, self.force, item.missingOK):
        if not item.missingOK:
          self.error_queue.put(item)

      self.work_queue.task_done()

      if not stopped.is_set():
        wqs = self.work_queue.qsize()
        eqs = self.error_queue.qsize()
        tac = threading.activeCount() - 1
        self.progress.errout("Caching artwork: %d item%s remaining of %d, %d error%s, %d thread%s active" % \
                          (wqs, "s"[wqs==1:],
                           self.maxItems,
                           eqs, "s"[eqs==1:],
                           tac, "s"[tac==1:]))

      if self.work_queue.empty(): break

  def loadImage(self, imgtype, filename, rowid, cachedurl, retry, force, missingOK = False):

    self.LAST_URL = self.json.getDownloadURL(filename)

    if self.LAST_URL != None:
      self.progress.log("Proceeding with download of URL [%s]" % self.LAST_URL)
      ATTEMPT = retry
      if rowid != 0 and force:
        self.progress.log("Deleting old image from cache with id [%d], cachedurl [%s] for filename [%s]" % (rowid, cachedurl, filename))
        self.database.deleteItem(rowid, cachedurl)
        self.totals.bump("Deleted", imgtype)
    else:
      self.progress.log("Image not available for download - uncacheable (embedded?), or doesn't exist.Filename [%s]" % filename)
      ATTEMPT = 0

    while ATTEMPT > 0:
      try:
        PAYLOAD = self.json.sendWeb("GET", self.LAST_URL)
        if self.json.WEB_LAST_STATUS == httplib.OK:
          self.progress.log("Succesfully downloaded image with size [%d] bytes, attempts required [%d]. Filename [%s]" \
                        % (len(PAYLOAD), (retry - ATTEMPT + 1), filename))
          self.totals.bump("Cached", imgtype)
          break
      except:
        pass
      ATTEMPT -= 1
      self.progress.log("Failed to download image URL [%s], status [%d], " \
                   "attempts remaining [%d]" % (self.LAST_URL, self.json.WEB_LAST_STATUS, ATTEMPT))
      if stopped.is_set(): ATTEMPT = 0

    if ATTEMPT == 0:
      if not missingOK: self.totals.bump("Error", imgtype)

    return ATTEMPT != 0

#
# Simple database wrapper class.
#
class MyDB(object):
  def __init__(self, config, progress):
    self.config = config
    self.progress = progress

    self.mydb = None
    self.DBVERSION = None
    self.cursor = None

  def __enter__(self):
    self.getDB()
    return self

  def __exit__(self, atype, avalue, traceback):
    if self.cursor: self.cursor.close()
    if self.mydb: self.mydb.close()

  def getDB(self):
    if not self.mydb:
      if not os.path.exists(self.config.getDBPath()):
        raise lite.OperationalError("Database [%s] does not exist" % self.config.getDBPath())
      self.mydb = lite.connect(self.config.getDBPath())
      self.DBVERSION = self.execute("SELECT idVersion FROM version").fetchone()[0]
    return self.mydb

  def execute(self, SQL):
    self.cursor = self.getDB().cursor()
    self.progress.log("EXECUTING SQL: %s" % SQL)
    self.cursor.execute(SQL)
    return self.cursor

  def fetchone(self): return self.cursor.fetchone()
  def fetchall(self): return self.cursor.fetchall()
  def commit(self): return self.getDB().commit()

  def getAllColumns(self, extraSQL=None):
    if self.DBVERSION >= 13:
      SQL = "SELECT t.id, t.cachedurl, t.lasthashcheck, t.url, s.height, s.width, s.usecount, s.lastusetime " \
            "FROM texture t JOIN sizes s ON (t.id = s.idtexture) "
    else:
      SQL = "SELECT t.id, t.cachedurl, t.lasthashcheck, t.url, 0 as height, 0 as width, t.usecount, t.lastusetime " \
            "FROM texture t "

    if extraSQL: SQL += extraSQL

    return self.execute(SQL)

  def deleteItem(self, id, cachedURL = None):
    if not cachedURL:
      SQL = "SELECT id, cachedurl, lasthashcheck, url FROM texture WHERE id=%d" % id
      row = self.execute(SQL).fetchone()

      if row == None:
        print "id " + self.config.IDFORMAT % int(id) + " is not valid"
        return
      else:
        localFile = row[1]
    else:
      localFile = cachedURL

    if os.path.exists(self.config.getFilePath(localFile)):
      os.remove(self.config.getFilePath(localFile))
    else:
      print "WARNING: id %s, cached thumbnail file %s not found" % ((self.config.IDFORMAT % id), localFile)

    self.execute("DELETE FROM texture WHERE id=%d" % id)
    self.commit()

  def getRowByFilename(self, filename):
  # Strip image:// prefix, trailing / suffix, and unquote...
    row = self.getRowByFilename_Impl(filename[8:-1], unquote=True)

  # Didn't find anyhing so try again, this time leave filename quoted, and don't truncate
    if not row:
      self.progress.log("Failed to find row by filename with the expected formatting, trying again (with prefix, quoted)")
      row = self.getRowByFilename_Impl(filename, unquote=False)

    return row

  def getRowByFilename_Impl(self, filename, unquote=True):
    ufilename = urllib.unquote(filename) if unquote else filename

    # If string contains unicode, replace unicode chars with % and
    # use LIKE instead of equality
    if ufilename.encode("ascii", "ignore") == ufilename.encode("utf-8"):
      SQL = "SELECT id, cachedurl from texture where url = \"%s\"" % ufilename
    else:
      self.progress.log("Removing ASCII from filename: [%s]" % ufilename)
      SQL = "SELECT id, cachedurl from texture where url like \"%s\"" % removeNonAscii(ufilename, "%")

    self.progress.log("SQL EXECUTE: [%s]" % SQL)
    row = self.execute(SQL).fetchone()
    self.progress.log("SQL RESULT : [%s]" % (row,))

    return row if row else None

  def removeNonAscii(self, s, replaceWith = ""):
    if replaceWith == "":
      return  "".join([x if ord(x) < 128 else ("%%%02x" % ord(x)) for x in s])
    else:
      return  "".join([x if ord(x) < 128 else replaceWith for x in s])

  def dumpRow(self, row):
    print (self.config.IDFORMAT % row[0] + "%s%14s%s%04d%s%04d%s%04d%s%19s%s%19s%s" % \
          (self.config.FSEP, row[1], self.config.FSEP, row[4], self.config.FSEP, row[5],
           self.config.FSEP, row[6], self.config.FSEP, row[7], self.config.FSEP, row[2],
           self.config.FSEP)).encode("utf-8") + \
          row[3].encode("utf-8")

#
# Handle all JSON RPC communication.
#
# Mostly uses sockets, etc. for those methods (Files.*) that must
# use HTTP.
#
class MyJSONComms(object):
  def __init__(self, config, progress):
    self.config = config
    self.progress = progress
    self.mysocket = None
    self.myweb = None
    self.WEB_LAST_STATUS = -1
    self.config.WEB_SINGLESHOT = True

  def __enter__(self):
    return self

  def __exit__(self, atype, avalue, traceback):
    return

  def __del__(self):
    if self.mysocket: self.mysocket.close()
    if self.myweb: self.myweb.close()

  def getSocket(self):
    if not self.mysocket:
      self.mysocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.mysocket.connect((self.config.XBMC_HOST, int(self.config.RPC_PORT)))
    return self.mysocket

  def getWeb(self):
    if not self.myweb or self.config.WEB_SINGLESHOT:
      if self.myweb: self.myweb.close()
      self.myweb = httplib.HTTPConnection("%s:%s" % (self.config.XBMC_HOST, self.config.WEB_PORT))
      self.WEB_LAST_STATUS = -1
      if self.config.DEBUG: self.myweb.set_debuglevel(1)
    return self.myweb

  def sendWeb(self, request_type, url, request=None, headers={}, readAmount = 0, timeout=15.0):
    if self.config.WEB_AUTH_TOKEN:
      headers.update({"Authorization": "Basic %s" % self.config.WEB_AUTH_TOKEN})

    web = self.getWeb()

    web.request(request_type, url, request, headers)

    if timeout == None: web.sock.setblocking(1)
    else: web.sock.settimeout(timeout)

    try:
      response = web.getresponse()
      self.WEB_LAST_STATUS = response.status
      if self.WEB_LAST_STATUS == httplib.UNAUTHORIZED:
        raise httplib.HTTPException("Remote web host requires webserver.username/webserver.password properties")
      if readAmount == 0: return response.read()
      else: return response.read(readAmount)
    except socket.timeout:
      self.progress.log("** iotimeout occurred during web request **")
      self.WEB_LAST_STATUS = httplib.REQUEST_TIMEOUT
      self.myweb.close()
      self.myweb = None
      return ""
    except:
      if self.config.WEB_SINGLESHOT == False:
        self.progress.debug("SWITCHING TO WEBSERVER.SINGLESHOT MODE", newLine=True)
        self.config.WEB_SINGLESHOT = True
        return self.sendWeb(request_type, url, request, headers)
      raise

  def sendJSON(self, request, id, callback=None, timeout=2, checkResult=True):
    BUFFER_SIZE = 32768

    request["jsonrpc"] = "2.0"
    request["id"] =  id

    # Following methods don't work over sockets - by design.
    if request["method"] in ["Files.PrepareDownload", "Files.Download"]:
      self.progress.debug("SENDING JSON WEB REQUEST", jsonrequest=request, newLine=True, newLineBefore=True)
      data = self.sendWeb("POST", "/jsonrpc", json.dumps(request), {"Content-Type": "application/json"})
      if self.progress.LOGFILE:
        self.progress.log("RESPONSE%s: %s" % (" (truncated)" if len(data)>256 else "", self.removeNonAscii(data[:256])))
      return json.loads(data) if data != "" else ""

    s = self.getSocket()
    self.progress.debug("SENDING JSON SOCKET REQUEST", jsonrequest=request, newLine=True, newLineBefore=True)
    START_TIME=time.time()
    s.send(json.dumps(request))

    ENDOFDATA = True
    jdata = {}

    while True:
      if ENDOFDATA:
        ENDOFDATA = False
        s.setblocking(1)
        data = []

      try:
        newdata = s.recv(BUFFER_SIZE)
        if data == []: s.setblocking(0)
        data.append(newdata)
        LASTIO=time.time()
        self.progress.debug("BUFFER RECEIVED (len %d)" % len(newdata), newLine=True)
      except socket.error:
        if newdata[-1:] == "}" or newdata[-2:] == "}\n":
          try:
            self.progress.debug("CONVERTING RESPONSE", newLine=True)
            jdata = json.loads("".join(data))
            self.progress.debug("CONVERSION COMPLETE, elapsed time: %f seconds" % (time.time() - START_TIME), newLine=True)
            if ("result" in jdata and "limits" in jdata["result"]):
              self.progress.debug("RECEIVED LIMITS: %s" % jdata["result"]["limits"], newLine=True)
            if self.progress.LOGFILE:
              self.progress.log("RESPONSE%s: %s" % (" (truncated)" if len(data[0]) > 256 else "", removeNonAscii(data[0][:256])))
            ENDOFDATA = True
          except ValueError:
            pass

        if not ENDOFDATA:
          if (time.time() - LASTIO) > timeout:
            raise socket.error("Socket IO timeout exceeded")
            break
          else:
            time.sleep(0.1)

      if ENDOFDATA:
        id = jdata["id"] if "id" in jdata else None

  # If we've got a callback defined, call it
  # If no callback, return response if it has an id
  # Responses without ids are notification, ignore and continue reading
        if callback:
          method = jdata["method"] if "method" in jdata else jdata["result"]
          params = jdata["params"] if "params" in jdata else None
          self.progress.log("Calling callback function: [%s] notification with params [%s]" % (method, params))
          if callback(id, method, params): break
        elif id: break

    if checkResult and not "result" in jdata: print "ERROR: JSON response has no result!\n%s" % jdata

    return jdata

  def jsonWaitForScanFinished(self, id, method, params):
    if method == "VideoLibrary.OnUpdate" and "data" in params:
      if "item" in params["data"]:
        item = params["data"]["item"]
        self.progress.errout("Updating Library: %s id %d" % (item["type"], item["id"]), newLine=True)
      return False

    if method.endswith("Library.OnScanFinished"): return True

    return False

  def appendFields(self, aList, fields):
    if fields != None:
      for f in fields.split():
        newField = f.replace(",", "")
        if not newField in aList:
          aList.append(newField)

  def addFilter(self, filter, newFilter, condition="and"):
    if "filter" in filter:
       filter["filter"] = { condition: [ filter["filter"], newFilter ] }
    else:
       filter["filter"] = newFilter

  def removeNonAscii(self, s, replaceWith = ""):
    if replaceWith == "":
      return  "".join([x if ord(x) < 128 else ("%%%02x" % ord(x)) for x in s])
    else:
      return  "".join([x if ord(x) < 128 else replaceWith for x in s])

  def rescanDirectories(self, mediatype, libraryids, directories):
    if libraryids == [] or directories == {}: return

    if mediatype == "movies":
      scanMethod = "VideoLibrary.Scan"
      removeMethod = "VideoLibrary.RemoveMovie"
      idName = "movieid"
    elif mediatype == "tvshows":
      scanMethod = "VideoLibrary.Scan"
      removeMethod = "VideoLibrary.RemoveTVShow"
      idName = "tvshowid"
    elif mediatype == "episodes":
      scanMethod = "VideoLibrary.Scan"
      removeMethod = "VideoLibrary.RemoveEpisode"
      idName = "episodeid"
    else:
      raise ValueError("mediatype [%s] not yet implemented" % mediatype)

    for libraryid in libraryids:
      self.progress.log("Removing %s %d from media library." % (idName, libraryid))
      REQUEST = {"method": removeMethod, "params":{idName: libraryid}}
      self.sendJSON(REQUEST, "libRemove")

    for directory in directories:
      self.progress.stdout("Rescanning directory: %s...\n" % directory)
      REQUEST = {"method": scanMethod, "params":{"directory": directory}}
      self.sendJSON(REQUEST, "libRescan", callback=self.jsonWaitForScanFinished, checkResult=False)

  def getSeasonAll(self, filename):

    # Not able to get a directory for remote files...
    if filename.find("image://http") != -1: return (None, None, None)

    directory = urllib.unquote(filename[8:-1])

    # Remove filename, leaving just directory...
    ADD_BACK=""
    if directory.rfind("/") != -1:
      directory = directory[:directory.rfind("/")]
      ADD_BACK="/"
    if directory.rfind("\\") != -1:
      directory = directory[:directory.rfind("\\")]
      ADD_BACK="\\"

    REQUEST = {"method":"Files.GetDirectory", "params":{"directory": directory}}

    data = self.sendJSON(REQUEST, "libDirectory", checkResult=False)

    if "result" in data and "files" in data["result"]:
      poster_url = fanart_url = banner_url = None
      for f in data["result"]["files"]:
        if f["filetype"] == "file":
          fname = f["label"].lower()
          if fname.find("season-all.") != -1: poster_url = "image://%s%s" % (urllib.quote(f["file"], "()"),ADD_BACK)
          elif fname.find("season-all-poster.") != -1: poster_url = "image://%s%s" % (urllib.quote(f["file"], "()"),ADD_BACK)
          elif fname.find("season-all-banner.") != -1: banner_url = "image://%s%s" % (urllib.quote(f["file"], "()"),ADD_BACK)
          elif fname.find("season-all-fanart.") != -1: fanart_url = "image://%s%s" % (urllib.quote(f["file"], "()"),ADD_BACK)
      return (poster_url, fanart_url, banner_url)

    return (None, None, None)

  def getDownloadURL(self, filename):
    REQUEST = {"method":"Files.PrepareDownload",
               "params":{"path": filename }}

    data = self.sendJSON(REQUEST, "1")

    if "result" in data:
      return "/%s" % data["result"]["details"]["path"]
    else:
      if filename[8:12].lower() != "http":
        self.progress.log("Files.PrepareDownload failed. It's a local file, what the heck... trying anyway.")
        return "/image/%s" % urllib.quote(filename, "()")
      return None

  def getFileDetails(self, filename):
    REQUEST = {"method":"Files.GetFileDetails",
               "params":{"file": filename,
                         "properties": ["streamdetails", "lastmodified", "dateadded", "size", "mimetype", "tag", "file"]}}

    data = self.sendJSON(REQUEST, "1", checkResult=False)

    if "result" in data:
      return data["result"]["filedetails"]
    else:
      return None

  def dumpJSON(self, data, decode=False):
    if decode:
      self.progress.errout("Decoding URLs...")
      self.unquoteArtwork(data)

    self.progress.errout("")

    print json.dumps(data, indent=2, ensure_ascii=True, sort_keys=False)

  def unquoteArtwork(self, items):
    for item in items:
      for field in item:
        if field in ["seasons", "episodes"]: self.unquoteArtwork(item[field])

        if field in ["fanart", "thumbnail"]: item[field] = urllib.unquote(item[field])

        if field == "art":
          art = item["art"]
          for image in art:
            art[image] = urllib.unquote(art[image])

        if field == "cast":
          for cast in item["cast"]:
            if "thumbnail" in cast:
              cast["thumbnail"] = urllib.unquote(cast["thumbnail"])

  def getData(self, action, mediatype,
              filter = None, useExtraFields = False, secondaryFields = None,
              showid = None, seasonid = None):

    XTRA = mediatype
    SECTION = mediatype
    FILTER = "title"
    TITLE = "title"
    IDENTIFIER = "%sid" % re.sub("(.*)s$", "\\1", mediatype)

    if mediatype == "albums":
      REQUEST = {"method":"AudioLibrary.GetAlbums",
                 "params":{"sort": {"order": "ascending", "method": "label"},
                           "properties":["title", "artist", "fanart", "thumbnail"]}}
      FILTER = "album"
    elif mediatype == "artists":
      REQUEST = {"method":"AudioLibrary.GetArtists",
                 "params":{"sort": {"order": "ascending", "method": "artist"},
                           "albumartistsonly": False,
                           "properties":["fanart", "thumbnail"]}}
      FILTER = "artist"
      TITLE = "artist"
    elif mediatype == "songs":
      REQUEST = {"method":"AudioLibrary.GetSongs",
                 "params":{"sort": {"order": "ascending", "method": "title"},
                           "properties":["title", "artist", "fanart", "thumbnail"]}}
    elif mediatype in ["movies", "tags"]:
      REQUEST = {"method":"VideoLibrary.GetMovies",
                 "params":{"sort": {"order": "ascending", "method": "title"},
                           "properties":["title", "art"]}}
      XTRA = "movies"
      SECTION = "movies"
      IDENTIFIER = "movieid"
    elif mediatype == "sets":
      REQUEST = {"method":"VideoLibrary.GetMovieSets",
                 "params":{"sort": {"order": "ascending", "method": "title"},
                           "properties":["title", "art"]}}
      FILTER = ""
    elif mediatype == "tvshows":
      REQUEST = {"method":"VideoLibrary.GetTVShows",
                 "params":{"sort": {"order": "ascending", "method": "title"},
                           "properties":["title", "art"]}}
      XTRA = "tvshows.tvshow"
    elif mediatype == "seasons":
      REQUEST = {"method":"VideoLibrary.GetSeasons",
                 "params":{"sort": {"order": "ascending", "method": "season"},
                           "tvshowid": showid, "properties":["season", "art"]}}
      FILTER = ""
      TITLE = "label"
      XTRA = "tvshows.season"
      IDENTIFIER = "season"
    elif mediatype == "episodes":
      REQUEST = {"method":"VideoLibrary.GetEpisodes",
                 "params":{"sort": {"order": "ascending", "method": "label"},
                           "tvshowid": showid, "season": seasonid, "properties":["art"]}}
      FILTER = ""
      TITLE = "label"
      XTRA = "tvshows.episode"
    else:
      raise ValueError("Invalid mediatype: [%s]" % mediatype)

    qaSinceDate = self.config.QADATE if action == "qa" else None
    xtraFields = self.config.XTRAJSON["extrajson.%s" % XTRA] if XTRA != "" else None

    if qaSinceDate and mediatype in ["movies", "tags", "episodes"]:
      self.addFilter(REQUEST["params"], {"field": "dateadded", "operator": "after", "value": qaSinceDate })

    if useExtraFields and xtraFields:
      self.appendFields(REQUEST["params"]["properties"], xtraFields)
    if secondaryFields:
      self.appendFields(REQUEST["params"]["properties"], secondaryFields)

    if mediatype == "tags":
        if not filter or filter.strip() == "":
          self.addFilter(REQUEST["params"], {"field": "tag", "operator": "contains", "value": "%"})
        else:
          word = 0
          filterBoolean = "and"
          for tag in [x.strip() for x in re.split("( and | or )", filter)]:
            word += 1
            if (word%2 == 0) and tag in ["and","or"]: filterBoolean = tag
            else: self.addFilter(REQUEST["params"], {"field": "tag", "operator": "contains", "value": tag}, filterBoolean)
    elif filter and filter.strip() != "" and not mediatype in ["sets", "seasons", "episodes"]:
        self.addFilter(REQUEST["params"], {"field": FILTER, "operator": "contains", "value": filter})

    return (SECTION, TITLE, IDENTIFIER, self.sendJSON(REQUEST, "lib%s" % mediatype.capitalize()))

#
# Hold and print some pretty totals.
#
class MyTotals(object):
  def __init__(self):
    self.TOTALS = {}
    self.TOTALS["Skipped"] = {}
    self.TOTALS["Deleted"] = {}
    self.TOTALS["Duplicate"] = {}
    self.TOTALS["Error"] = {}
    self.TOTALS["Cached"] = {}
    self.TOTALS["Ignored"] = {}

  def addSeasonAll(self):
    self.TOTALS["Season-all"] = {}

  def addNotCached(self):
    self.TOTALS["Not in Cache"] = {}

  def bump(self, action, imgtype):
    # Strip off any numerics, ie. "cast 01" -> "cast"
    itype = re.sub(r" [0-9]*$", "", imgtype)

    with threading.Lock():
      if not action in self.TOTALS: self.TOTALS[action] = {}
      if not itype in self.TOTALS[action]: self.TOTALS[action][itype ] = 0
      self.TOTALS[action][itype ] += 1

  def libraryStats(self, item="", filter=""):
    items = {}
    for a in self.TOTALS:
      for c in self.TOTALS[a]:
        if not c in items: items[c] = None

  # Ensure some basic items are included in the summary
    if not "fanart" in items: items["fanart"] = None
    if item.find("movies") != -1:
      if not "poster" in items: items["poster"] = None
    if item.find("tvshows") != -1:
      if not "thumb" in items: items["thumb"] = None
    if item.find("artists") != -1 or \
       item.find("albums") != -1 or \
       item.find("songs") != -1:
      if not "thumbnail" in items: items["thumbnail"] = None

    sortedItems = sorted(items.items())
    sortedItems.append(("TOTAL", None))
    items["TOTAL"] = 0

    sortedTOTALS = sorted(self.TOTALS.items())
    sortedTOTALS.append(("TOTAL", {}))
    self.TOTALS["TOTAL"] = {}

    line0 = "Cache pre-load activity summary for \"%s\"" % item
    if filter != "": line0 = "%s, filtered by \"%s\"" % (line0, filter)
    line0 = "%s:" % line0

    line1 = "%-13s" % " "
    line2 = "-" * 13
    for i in sortedItems:
      i = i[0]
      width = 10 if len(i) < 10 else len(i)+1
      line1 = "%s| %s" % (line1, i.center(width))
      line2 = "%s+-%s" % (line2, "-" * width)

    print
    print line0
    print
    print line1
    print line2

    for a in sortedTOTALS:
      a = a[0]
      self.TOTALS[a]["TOTAL"] = 0
      if a == "TOTAL": print line2.replace("-","=").replace("+","=")
      line = "%-12s " % a
      for i in sortedItems:
        i = i[0]
        if a == "TOTAL":
          value = "%d" % items[i] if items[i] != None else "-"
        elif i in self.TOTALS[a]:
          ivalue = self.TOTALS[a][i]
          value = "%d" % ivalue
          if items[i] == None: items[i] = 0
          items[i] += ivalue
          self.TOTALS[a]["TOTAL"] += ivalue
        else:
          value = "-"
        width = 10 if len(i) < 10 else len(i)+1
        line = "%s| %s" % (line, value.center(width))
      print line

#
# Simple container for media items under consideration for processing
#
# status is 0 (not to be loaded) or 1 (to be loaded).
#
# missingOK is used to specify that if an image cannot be loaded,
# don't complain (ie. speculative loading, eg. season-all.tbn)
#
class MyMediaItem(object):
  def __init__(self, mediaType, imageType, name, season, episode, filename, dbid, cachedurl, libraryid, missingOK):
    self.status = 1 # 0=OK, 0=Ignore
    self.mtype = mediaType
    self.itype = imageType
    self.name = name
    self.season = season
    self.episode = episode
    self.filename = filename
    self.dbid = dbid
    self.cachedurl = cachedurl
    self.libraryid = libraryid
    self.missingOK = missingOK

  def __str__(self):
    return "{%d, %s, %s, %s, %s, %s, %s, %d, %s, %d, %s}" % \
      (self.status, self.mtype, self.itype, self.name, self.season, \
       self.episode, self.filename,  self.dbid, self.cachedurl, \
       self.libraryid, self.missingOK)

  def getFullName(self):
    if self.episode:
      return "%s, %s Episode %s" % (self.name, self.season, self.episode)
    elif self.season:
      if self.itype == "cast.thumb":
        return "Cast Member %s in %s" % (self.name, self.season)
      elif self.mtype == "tvshows":
        return "%s, %s" % (self.name, self.season)
      else:
        return "%s by %s" % (self.name, " & ".join(self.season))
    else:
      return "%s" % (self.name)

def removeNonAscii(s, replaceWith = ""):
  if replaceWith == "":
    return  "".join([x if ord(x) < 128 else ("%%%02x" % ord(x)) for x in s])
  else:
    return  "".join([x if ord(x) < 128 else replaceWith for x in s])

#
# Load data using JSON-RPC. In the case of TV Shows, also load Seasons
# and Episodes into a single data structure.
#
# Sets doesn't support filters, so filter this list after retrieval.
#
def processData(action, mediatype, filter, force, extraFields=False, nodownload=False):
  jcomms = MyJSONComms(gConfig, gProgress)
  database = MyDB(gConfig, gProgress)

  if mediatype in ["movies", "tags", "tvshows", "episodes"] and gConfig.CACHE_CAST_THUMB:
    secondaryFields= "cast"
  else:
    secondaryFields = None

  if mediatype == "tvshows": TOTALS.addSeasonAll()

  gProgress.errout("Loading %s..." % mediatype, every = 1)

  (section_name, title_name, id_name, data) = jcomms.getData(action, mediatype, filter, extraFields, secondaryFields)

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  if mediatype == "sets" and filter:
    filteredSets = []
    for set in data["result"]["sets"]:
      if re.search(filter, set["title"], re.IGNORECASE):
        filteredSets.append(set)
    data["result"]["sets"] = filteredSets

  if mediatype == "tvshows":
    for tvshow in data["result"][section_name]:
      title = tvshow["title"]
      gProgress.errout("Loading TV Show: [%s]..." % title.encode("utf-8"), every = 1)
      (s2, t2, i2, data2) = jcomms.getData(action, "seasons", filter, extraFields, showid=tvshow[id_name])
      limits = data2["result"]["limits"]
      if limits["total"] == 0: return
      tvshow[s2] = data2["result"]
      for season in data2["result"][s2]:
        seasonid = season["season"]
        gProgress.errout("Loading TV Show: [%s, Season %d]..." % (title.encode("utf-8"), seasonid), every = 1)
        (s3, t3, i3, data3) = jcomms.getData(action, "episodes", filter, extraFields, secondaryFields, showid=tvshow[id_name], seasonid=season[i2])
        limits = data3["result"]["limits"]
        if limits["total"] == 0: return
        season[s3] = data3["result"]

  cacheImages(mediatype, jcomms, database, force, nodownload, data, section_name, title_name, id_name)

#
# Parse the supplied JSON data, turning it into a list of artwork urls
# (mediaitems) that should be matched against the database (cached files)
# to determine which should be skipped (those in the cache, unless
# force update is true).
#
# Those that are not skipped will be added to a queueu for processing by
# 1..n threads. Errors will be added to an error queue by the threads, and
# subsueqently displayed to the user at the end.
#
def cacheImages(mediatype, jcomms, database, force, nodownload, data, section_name, title_name, id_name):

  mediaitems = []
  imagecache = {}

  parseURLData(jcomms, mediatype, mediaitems, imagecache, data["result"][section_name], title_name, id_name)

  # Don't need this data anymore, make it available for garbage collection
  del data
  del imagecache

  gProgress.errout("Loading database items...")
  dbfiles = {}
  with database:
    rows = database.getAllColumns().fetchall()
    for r in rows:
      dbfiles[r[3].encode("ascii", "ignore")] = r

  gProgress.log("Loaded %d items from texture cache database" % len(dbfiles))

  gProgress.errout("Matching database items...")

  ITEMLIMIT = 1e9 if nodownload else 100

  itemCount = 0
  for item in mediaitems:
    filename = urllib.unquote(item.filename[8:-1]).encode("ascii", "ignore")
    if not filename in dbfiles:
      filename = item.filename[:-1].encode("ascii", "ignore")

    if item.mtype == "tvshows" and item.season == "Season All": TOTALS.bump("Season-all", item.itype)

    # Don't need to cache it if it's already in the cache, unless forced...
    # Assign the texture cache database id and cachedurl so that removal will be quicker.
    if filename in dbfiles:
      if force:
        db = dbfiles[filename]
        itemCount += 1
        item.status = 1
        item.dbid = db[0]
        item.cachedurl = db[1]
      else:
        gProgress.log("ITEM SKIPPED: %s" % item)
        TOTALS.bump("Skipped", item.itype)
        item.status = 0
    # These items we are missing from the cache...
    else:
      itemCount += 1
      item.status = 1
      if itemCount < ITEMLIMIT:
        MSG = "Need to cache: [%-10s] for %s: %s" % (item.itype.center(10), re.sub("(.*)s$", "\\1", item.mtype), item.getFullName())
        gProgress.errout(MSG, newLine=True)
      elif itemCount == ITEMLIMIT:
        gProgress.errout("...and many more! (First %d items shown)" % ITEMLIMIT, newLine=True)

  # Don't need this data anymore, make it available for garbage collection
  del dbfiles

  if nodownload:
    TOTALS.addNotCached()
    for item in mediaitems:
      if item.status == 1: TOTALS.bump("Not in Cache", item.itype)

  gProgress.errout("")

  if itemCount > 0 and not nodownload:
    work_queue = Queue.Queue()
    error_queue = Queue.Queue()

    gProgress.errout("", newLine=True)
    gProgress.errout("Caching artwork: %d item%s remaining of %d, 0 errors" % \
                      (itemCount, "s"[itemCount==1:], itemCount))

    for item in mediaitems:
      if item.status == 1:
        gProgress.log("QUEUE ITEM: %s" % item)
        work_queue.put(item)

    # Don't need this data anymore, make it available for garbage collection
    del mediaitems

    tCount = gConfig.DOWNLOAD_THREADS["download.threads.%s" % mediatype]
    THREADCOUNT = tCount if tCount <= itemCount else itemCount
    gProgress.log("Creating %d image download threads" % THREADCOUNT)

    THREADS = []
    for i in range(THREADCOUNT):
      t = MyImageLoader(work_queue, error_queue, itemCount, gConfig, gProgress, TOTALS, force, 10)
      THREADS.append(t)
      t.setDaemon(True)
      t.start()

    try:
      ALIVE = True
      while ALIVE:
        ALIVE = False
        for t in THREADS: ALIVE = True if t.isAlive() else ALIVE
        if ALIVE: time.sleep(1.0)
    except (KeyboardInterrupt, SystemExit):
      stopped.set()
      gProgress.errout("Please wait while threads terminate...")
      ALIVE = True
      while ALIVE:
        ALIVE = False
        for t in THREADS: ALIVE = True if t.isAlive() else ALIVE
        if ALIVE: time.sleep(0.1)

    gProgress.errout("\n")

    if not error_queue.empty():
      gProgress.errout("\n")
      gProgress.errout("The following items could not be downloaded:\n", newLine=True)
      while not error_queue.empty():
        item = error_queue.get()
        name = item.getFullName()[:40]
        gProgress.errout("[%-10s] [%-40s] %s" % (item.itype, name, urllib.unquote(item.filename)), newLine=True)
        gProgress.log("ERROR ITEM: %s" % item)
        error_queue.task_done()

#
# Iterate over all the elements, seeking out artwork to be stored in a list.
# Use recursion to process season and episode sub-elements.
#
def parseURLData(jcomms, mediatype, mediaitems, imagecache, data, title_name, id_name, showName = None, season = None):
  gProgress.reset()

  SEASON_ALL = True

  for item in data:
    if title_name in item: title = item[title_name]

    if showName:
      name = showName
      if season:
        episode = re.sub("([0-9]*x[0-9]*)\..*", "\\1", title)
      else:
        season = title
        episode = None
      mediatype = "tvshows"
    else:
      name = title
      if title_name != "artist" and "artist" in item:
        season = item["artist"]
      else:
        season = None
      episode = None

    gProgress.errout("Parsing [%s]..." % name, every = 25)

    for a in ["fanart", "poster", "thumb", "thumbnail"]:
      if a in item and evaluateURL(a, item[a], imagecache):
        mediaitems.append(MyMediaItem(mediatype, a, name, season, episode, item[a], 0, None, item[id_name], False))

    if "art" in item:
      if season and SEASON_ALL and "poster" in item["art"]:
        SEASON_ALL = False
#        poster_url = re.sub(r"season(-specials|[ 0-9]*)(.*)\.(.*)", r"season-all\2.\3", item["art"]["poster"])
#        banner_url = re.sub(r"season(-specials|[ 0-9]*)(.*)\.(.*)", r"season-all-fanart.\3", item["art"]["poster"])
#        fanart_url = re.sub(r"season(-specials|[ 0-9]*)(.*)\.(.*)", r"season-all-banner.\3", item["art"]["poster"])
        (poster_url, fanart_url, banner_url) = jcomms.getSeasonAll(item["art"]["poster"])
        if poster_url and evaluateURL("poster", poster_url, imagecache):
          mediaitems.append(MyMediaItem(mediatype, "poster", name, "Season All", None, poster_url, 0, None, item[id_name], False))
        if fanart_url and evaluateURL("fanart", fanart_url, imagecache):
          mediaitems.append(MyMediaItem(mediatype, "fanart", name, "Season All", None, fanart_url, 0, None, item[id_name], False))
        if banner_url and evaluateURL("banner", banner_url, imagecache):
          mediaitems.append(MyMediaItem(mediatype, "banner", name, "Season All", None, banner_url, 0, None, item[id_name], False))
      for a in item["art"]:
        imgtype_short = a.replace("tvshow.","")
        if evaluateURL(imgtype_short, item["art"][a], imagecache):
          mediaitems.append(MyMediaItem(mediatype, imgtype_short, name, season, episode, item["art"][a], 0, None, item[id_name], False))

    if "cast" in item:
      for a in item["cast"]:
        if "thumbnail" in a and evaluateURL("thumbnail", a["thumbnail"], imagecache):
          mediaitems.append(MyMediaItem(mediatype, "cast.thumb", a["name"], name, None, a["thumbnail"], 0, None, item[id_name], False))

    if "seasons" in item:
      parseURLData(jcomms, "seasons", mediaitems, imagecache, item["seasons"]["seasons"], "label", "season", showName = title)
    if "episodes" in item:
      parseURLData(jcomms, "episodes", mediaitems, imagecache, item["episodes"]["episodes"], "label", "episodeid", showName = showName, season = title)
      season = None

# Include or exclude url depending on basic properties - has it
# been "seen" before (in which case, discard as no point caching
# it twice. Or discard if matches an "ignore" rule.
#
# Otherwise include it, and add it to the "seen" cache so it can
# be excluded in future if seen again.
#
def evaluateURL(imgtype, url, imagecache):
  if url == "": return False

  if url in imagecache:
    TOTALS.bump("Duplicate", imgtype)
    imagecache[url] += 1
    return False

  if gConfig.CACHE_IGNORE_TYPES:
    for ignore in gConfig.CACHE_IGNORE_TYPES:
      if re.search(ignore, url):
        gProgress.log("Ignored image due to rule [%s]" % ignore)
        TOTALS.bump("Ignored", imgtype)
        imagecache[url] = 1
        return False

  imagecache[url] = 0
  return True

def libraryQuery(action, item, filter="", force=False, extraFields=False, rescan=False, decode=False, nodownload=False):
  if action == "cache":
    processData(action, item, filter, force, extraFields, nodownload)
  elif item == "albums":
    libraryAllAlbums(action, filter, force, extraFields, rescan, decode)
  elif item == "artists":
    libraryAllArtists(action, filter, force, extraFields, rescan, decode)
  elif item == "songs":
    libraryAllSongs(action, filter, force, extraFields, rescan, decode)
  elif item == "movies":
    libraryAllMovies(action, filter, force, extraFields, rescan, decode, isTag=False)
  elif item == "tags":
    libraryAllMovies(action, filter, force, extraFields, rescan, decode, isTag=True)
  elif item == "sets":
    libraryAllMovieSets(action, filter, force, extraFields, rescan, decode)
  elif item == "tvshows":
    libraryAllTVShows(action, filter, force, extraFields, rescan, decode)
  else:
    print "item [%s] is not a valid library class to be queried" % item
    sys.exit(2)

  gProgress.errout("")

def libraryAllAlbums(action, filter, force, extraFields, rescan, decode):

  jcomms = MyJSONComms(gConfig, gProgress)
  database = MyDB(gConfig, gProgress)

  (section_name, title_name, id_name, data) = jcomms.getData(action, "albums", filter, extraFields)

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  albums = data["result"]["albums"]

  for album in albums:
    title = album["title"]
    artist = album["artist"]

    if action in ["qa", "dump"]: gProgress.errout("Parsing Album: [%s]..." % title.encode("utf-8"), every = 1)

  if action == "dump": jcomms.dumpJSON(albums, decode)

def libraryAllArtists(action, filter, force, extraFields, rescan, decode):

  jcomms = MyJSONComms(gConfig, gProgress)
  database = MyDB(gConfig, gProgress)

  (section_name, title_name, id_name, data) = jcomms.getData(action, "artists", filter, extraFields)

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  artists = data["result"]["artists"]

  for artist in artists:
    name = artist["artist"]

    if action in ["qa", "dump"]: gProgress.errout("Parsing Artist: [%s]..." % name.encode("utf-8"), every = 1)

  if action == "dump": jcomms.dumpJSON(artists, decode)

def libraryAllSongs(action, filter, force, extraFields, rescan, decode):

  jcomms = MyJSONComms(gConfig, gProgress)
  database = MyDB(gConfig, gProgress)

  (section_name, title_name, id_name, data) = jcomms.getData(action, "songs", filter, extraFields)

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  songs = data["result"]["songs"]

  for song in songs:

    title = song["title"]

    if action in ["qa", "dump"]: gProgress.errout("Parsing Song: [%s]..." % title.encode("utf-8"), every = 1)

  if action == "dump": jcomms.dumpJSON(songs, decode)

def libraryAllMovies(action, filter, force, extraFields, rescan, decode, isTag=False):
  mediaType = "Tag" if isTag else "Movie"

  jcomms = MyJSONComms(gConfig, gProgress)
  database = MyDB(gConfig, gProgress)

  secondaryFields = None

  if action == "qa": secondaryFields = "file, plot, rating, mpaa"
  if action == "cache" and gConfig.CACHE_CAST_THUMB: secondaryFields= "cast"

  if isTag:
    (section_name, title_name, id_name, data) = jcomms.getData(action, "tags", filter, extraFields, secondaryFields)
  else:
    (section_name, title_name, id_name, data) = jcomms.getData(action, "movies", filter, extraFields, secondaryFields)

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  movies = data["result"]["movies"]

  directories = {}
  libraryids = []

  for movie in movies:
    title = movie["title"]
    movieid = movie["movieid"]

    if action in ["qa","dump"]: gProgress.errout("Parsing %s: [%s]..." % (mediaType, title.encode("utf-8")), every = 1)

    if action == "qa":
      missing = {}

      if gConfig.QA_RATING and not ("rating" in movie and movie["rating"] != 0): missing["rating"] = True
      if not "plot" in movie or movie["plot"] == "": missing["plot"] = True
      if not "mpaa" in movie or movie["mpaa"] == "": missing["mpaa"] = True

      if not "fanart" in movie["art"] or movie["art"]["fanart"] == "": missing["fanart"] = True
      elif database.getRowByFilename(movie["art"]["fanart"]) == None: missing["fanart (uncached)"] = False

      if not "poster" in movie["art"] or movie["art"]["poster"] == "": missing["poster"] = True
      elif database.getRowByFilename(movie["art"]["poster"]) == None: missing["poster (uncached)"] = False

      if gConfig.QA_FILE and not ("file" in movie and jcomms.getFileDetails(movie["file"])): missing["file"] = False

      if missing != {}:
        gProgress.stdout("%s [%-50s]: Missing %s\n" % (mediaType, title.encode("utf-8")[0:50], ", ".join(missing)))
        if "".join(["Y" if missing[m] else "" for m in missing]) != "":
          libraryids.append(movieid)
          dir = os.path.dirname(movie["file"])
          directories[dir] = dir

  if rescan: jcomms.rescanDirectories("movies", libraryids, directories)

  if action == "dump": jcomms.dumpJSON(movies, decode)

def libraryAllMovieSets(action, filter, force, extraFields, rescan, decode):

  jcomms = MyJSONComms(gConfig, gProgress)
  database = MyDB(gConfig, gProgress)

  (section_name, title_name, id_name, data) = jcomms.getData(action, "sets", filter, extraFields)

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  sets = data["result"]["sets"]

  filteredSets = []

  if action == "dump": gProgress.errout("Filtering Sets...")

  for set in sets:
    title = set["title"]
    if filter == "" or re.search(filter, title, re.IGNORECASE):
      filteredSets.append(set)

  for set in filteredSets:
    if action in ["qa", "dump"]: gProgress.errout("Parsing Set: [%s]..." % title.encode("utf-8"), every = 1)

  if action == "dump": jcomms.dumpJSON(filteredSets, decode)

def libraryAllTVShows(action, filter, force, extraFields, rescan, decode):

  jcomms = MyJSONComms(gConfig, gProgress)
  database = MyDB(gConfig, gProgress)

  secondaryFields = None
  if action == "qa": secondaryFields = "plot, rating"
  if action == "cache" and gConfig.CACHE_CAST_THUMB: secondaryFields = "cast"

  (section_name, title_name, id_name, data) = jcomms.getData(action, "tvshows", filter, extraFields, secondaryFields)

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  tvshows = data["result"]["tvshows"]

  for tvshow in tvshows:
    title = tvshow["title"]
    tvshowid = tvshow["tvshowid"]

    if action in ["qa", "dump"]: gProgress.errout("Parsing TV Show: [%s]..." % title.encode("utf-8"), every = 1)

    if action == "qa":
      missing = {}

      if gConfig.QA_RATING and not ("rating" in tvshow and tvshow["rating"] != 0): missing["rating"] = True
      if not "plot" in tvshow or tvshow["plot"] == "": missing["plot"] = True

      if not "fanart" in tvshow["art"] or tvshow["art"]["fanart"] == "": missing["fanart"] = True
      elif database.getRowByFilename(tvshow["art"]["fanart"]) == None: missing["fanart (uncached)"] = False

      if not "banner" in tvshow["art"] or tvshow["art"]["banner"] == "": missing["banner"] = True
      elif database.getRowByFilename(tvshow["art"]["banner"]) == None: missing["banner (uncached)"] = False

      if not "poster" in tvshow["art"] or tvshow["art"]["poster"] == "":
        if not "thumb" in tvshow["art"] or tvshow["art"]["thumb"] == "": missing["poster"] = True
        elif database.getRowByFilename(tvshow["art"]["thumb"]) == None: missing["thumb (uncached)"] = False
      elif database.getRowByFilename(tvshow["art"]["poster"]) == None: missing["poster (uncached)"] = False

      if missing != {}:
        gProgress.stdout("TVShow  [%-38s]: Missing %s" % (title.encode("utf-8")[0:38], ", ".join(missing)))

    seasons = libraryTVShow(jcomms, database, action, force, extraFields, rescan, title, tvshowid)

    if action == "dump": tvshow["seasons"] = seasons

  if action == "dump": jcomms.dumpJSON(tvshows, decode)

def libraryTVShow(jcomms, database, action, force, extraFields, rescan, showName, showid):

  (section_name, title_name, id_name, data) = jcomms.getData(action, "seasons", None, extraFields, showid = showid)

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  seasons = data["result"]["seasons"]

  for season in seasons:
    seasonid = season["season"]

    if action in ["qa", "dump"]: gProgress.errout("Parsing TV Show: [%s, Season %d]..." % (showName.encode("utf-8"), seasonid), every = 1)

    episodes = libraryTVSeason(jcomms, database, action, force, extraFields, rescan, showName, showid, seasonid)

    if action == "dump": season["episodes"] = episodes

  return seasons

def libraryTVSeason(jcomms, database, action, force, extraFields, rescan, showName, showid, seasonid):

  secondaryFields = None
  if action == "qa": secondaryFields = "plot, rating, file"
  if action == "cache" and gConfig.CACHE_CAST_THUMB: secondaryFields= "cast"

  (section_name, title_name, id_name, data) = jcomms.getData(action, "episodes", None, extraFields, \
                                                              secondaryFields, showid = showid, seasonid = seasonid)

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  episodes = data["result"]["episodes"]

  directories = {}
  libraryids = []

  for episode in episodes:
    label = episode["label"].partition(".")[0]
    episodeid = episode["episodeid"]

    if action == "qa":
      missing = {}

      if gConfig.QA_RATING and not ("rating" in episode and episode["rating"] != 0): missing["rating"] = True
      if not "plot" in episode or episode["plot"] == "": missing["plot"] = True

      if not "thumb" in episode["art"] or episode["art"]["thumb"] == "": missing["thumb"] = True
      elif database.getRowByFilename(episode["art"]["thumb"]) == None: missing["thumb (uncached)"] = False

      if gConfig.QA_FILE and not ("file" in episode and jcomms.getFileDetails(episode["file"])): missing["file"] = False

      if missing != {}:
        gProgress.stdout("Episode [%-32s] %5s: Missing %s\n" % (showName[0:32], label, ", ".join(missing)))
        if "".join(["Y" if missing[m] else "" for m in missing]) != "":
          libraryids.append(episodeid)
          dir = os.path.dirname(episode["file"])
          directories[dir] = dir

  if rescan: jcomms.rescanDirectories("episodes", libraryids, directories)

  return episodes

# Extract data, using optional simple search, or complex SQL filter.
def sqlExtract(ACTION="NONE", search="", filter=""):
  database = MyDB(gConfig, gProgress)

  with database:
    SQL = ""
    if (search != "" or filter != ""):
      if search != "": SQL = "WHERE t.url LIKE '%" + search + "%' ORDER BY t.id ASC"
      if filter != "": SQL = filter + " "

    IDS=""
    FSIZE=0
    FCOUNT=0

    database.getAllColumns(SQL)

    while True:
      row = database.fetchone()
      if row == None: break

      IDS += " " + str(row[0])
      FCOUNT+=1

      if ACTION == "NONE":
        database.dumpRow(row)
      elif not os.path.exists(gConfig.getFilePath(row[1])):
        if ACTION == "EXISTS":
          database.dumpRow(row)
      elif ACTION == "STATS":
        FSIZE += os.path.getsize(gConfig.getFilePath(row[1]))
        database.dumpRow(row)

    if ACTION == "STATS": print "\nFile Summary: %s files; Total size: %s Kbytes\n" % (format(FCOUNT, ",d"), format(FSIZE/1024, ",d"))

    sys.stdout.flush()

    if (search != "" or filter != ""): gProgress.errout("Matching row ids:%s\n" % IDS)

# Delete row by id, and corresponding file item
def sqlDelete( ids=[] ):
  database = MyDB(gConfig, gProgress)
  with database:
    for id in ids:
      try:
        database.deleteItem(int(id))
      except ValueError:
        print "id " + id + " is not valid"
        continue

def dirScan(CLEAN="N", purge_nonlibrary_artwork=False, libraryFiles=None, keyIsHash=False):
  database = MyDB(gConfig, gProgress)

  with database:
    dbfiles = {}
    orphanedfiles = []
    localfiles = []

    re_search_addon = re.compile("^.*%s.xbmc%saddons%s.*" % (os.sep, os.sep, os.sep))
    re_search_mirror = re.compile("^http://mirrors.xbmc.org/addons/.*")

    gProgress.errout("Loading texture cache...")

    rows = database.getAllColumns().fetchall()
    for r in rows: dbfiles[r[1]] = r
    gProgress.log("Loaded %d rows from texture cache" % len(dbfiles))

    gProgress.errout("Scanning Thumbnails directory...")

    path = gConfig.getFilePath()

    for (p, dirs, files) in os.walk(path): break

    for dir in sorted(dirs, key=str.lower):
      for (p, d, files) in os.walk(path + dir):
        for f in sorted(files, key=str.lower):
          hash = "%s/%s" % (dir, f)

          gProgress.errout("Scanning Thumbnails directory [%s]..." % hash, every=25)

          if not hash in dbfiles:
            orphanedfiles.append(hash)
          elif libraryFiles:
            row = dbfiles[hash]
            URL = removeNonAscii(row[3].encode("utf-8"))
            # Ignore add-on/mirror related images, and files located in
            # local file system (most likely addons)
            if not re_search_addon.search(URL) and \
               not re_search_mirror.search(URL) and \
               not os.path.exists(row[3].encode("utf-8")):
              key = hash[:-4] if keyIsHash else URL

              if not key in libraryFiles:
                # Last ditch attempt to find a matching key, database might be
                # slightly mangled
                if not keyIsHash:
                  key = getKeyFromFilename(row[3])
                  if key in libraryFiles:
                    del libraryFiles[key]
                  else:
                    localfiles.append(row)
                else:
                  localfiles.append(row)
              else:
                 del libraryFiles[key]

    gProgress.errout("")

    if not libraryFiles:
      gProgress.log("Identified %d orphaned files" % len(orphanedfiles))
      if CLEAN == "Y" and len(orphanedfiles) > (len(dbfiles)/20):
        gProgress.log("Something wrong here, that's far too many orphaned files - more than 5% limit.")
        print "Found %d orphaned files for %d database files."  % (len(orphanedfiles), len(dbfiles))
        print "This is far too many orphaned files for this number of database files, something may be wrong."
        print "Check your configuration, database, and Thumbnails folder."
        return
      for ofile in orphanedfiles:
        print "Orphaned file found: Name [%s], Created [%s], Size [%d]%s" % \
          (ofile,
           time.ctime(os.path.getctime(gConfig.getFilePath(ofile))),
           os.path.getsize(gConfig.getFilePath(ofile)),
           ", REMOVING..." if CLEAN == "Y" else "")
        if CLEAN == "Y": os.remove(gConfig.getFilePath(ofile))

    if libraryFiles:
      if localfiles != []:
        if purge_nonlibrary_artwork: gProgress.errout("Pruning cached images from texture cache...", newLine=True)
        else: gProgress.errout("The following items are present in the texture cache but not the media library:", newLine=True)
      FSIZE=0
      for row in localfiles:
        database.dumpRow(row)
        FSIZE += os.path.getsize(gConfig.getFilePath(row[1]))
        if purge_nonlibrary_artwork: database.deleteItem(row[0], row[1])
      print "\nSummary: %s files; Total size: %s Kbytes\n" % (format(len(localfiles),",d"), format(FSIZE/1024, ",d"))

def getHash(string):
  string = string.lower()
  bytes = bytearray(string)
  crc = 0xffffffff;
  for b in bytes:
    crc = crc ^ (b << 24)
    for i in range(8):
      if (crc & 0x80000000): crc = (crc << 1) ^ 0x04C11DB7
      else: crc = crc << 1;
    crc = crc & 0xFFFFFFFF
  return '%08x' % crc

# The following method is extremely slow on a Raspberry Pi, and
# doesn't work well with unicode strings (returns wrong hash).
# Fortunately, using the encoded url/filename as the key (next
# function) is sufficient for our needs and also about twice
# as fast on a Pi.
def getKeyFromHash(filename):
  url = re.sub("^image://(.*)/","\\1",filename)
  url = u"" + urllib.unquote(url)
  hash = getHash(url.encode("utf-8"))
  return "%s%s%s" % (hash[0:1], os.sep, hash)

def getKeyFromFilename(filename):
  return removeNonAscii(urllib.unquote(re.sub("^image://(.*)/","\\1",filename)))

def getAllFiles(keyFunction):

  jcomms = MyJSONComms(gConfig, gProgress)

  files = {}

  REQUEST = [
              {"method":"AudioLibrary.GetAlbums",
                "params":{"sort": {"order": "ascending", "method": "label"},
                          "properties":["title", "fanart", "thumbnail"]}},

              {"method":"AudioLibrary.GetArtists",
               "params":{"sort": {"order": "ascending", "method": "artist"},
                         "properties":["fanart", "thumbnail"], "albumartistsonly": False}},

              {"method":"AudioLibrary.GetSongs",
               "params":{"sort": {"order": "ascending", "method": "title"},
                         "properties":["title", "fanart", "thumbnail"]}},

              {"method":"VideoLibrary.GetMusicVideos",
               "params":{"sort": {"order": "ascending", "method": "title"},
                         "properties":["title", "art"]}},

              {"method":"VideoLibrary.GetMovies",
               "params":{"sort": {"order": "ascending", "method": "title"},
                         "properties":["title", "cast", "art"]}},

              {"method":"VideoLibrary.GetMovieSets",
               "params":{"sort": {"order": "ascending", "method": "title"},
                         "properties":["title", "art"]}}
             ]

  for r in REQUEST:
    mediatype = re.sub(".*Library\.Get(.*)","\\1",r["method"])
    interval = 0 if mediatype == "MovieSets" else 50

    gProgress.errout("Loading: %s..." % mediatype)
    data = jcomms.sendJSON(r, "libFiles")

    for items in data["result"]:
      if items != "limits":
        title = ""
        for i in data["result"][items]:
          title = i["title"] if "title" in i else i["artist"]
          gProgress.errout("Parsing: %s [%s]..." % (mediatype, title), every = interval)
          if "fanart" in i: files[keyFunction(i["fanart"])] = "fanart"
          if "thumbnail" in i: files[keyFunction(i["thumbnail"])] = "thumbnail"
          if "art" in i:
            for a in i["art"]:
              files[keyFunction(i["art"][a])] = a
          if "cast" in i:
            for c in i["cast"]:
              if "thumbnail" in c:
                files[keyFunction(c["thumbnail"])] = "cast.thumbnail"
        if title != "": gProgress.errout("Parsing: %s [%s]..." % (mediatype, title))

  gProgress.errout("Loading: TVShows...")

  REQUEST = {"method":"VideoLibrary.GetTVShows",
             "params": {"sort": {"order": "ascending", "method": "title"},
                        "properties":["title", "cast", "art"]}}

  tvdata = jcomms.sendJSON(REQUEST, "libTV")

  for tvshow in tvdata["result"]["tvshows"]:
    gProgress.errout("Parsing: TVShows [%s]..." % tvshow["title"])
    tvshowid = tvshow["tvshowid"]
    for a in tvshow["art"]:
      files[keyFunction(tvshow["art"][a])] = a
    if "cast" in tvshow:
      for c in tvshow["cast"]:
        if "thumbnail" in c:
          files[keyFunction(c["thumbnail"])] = "cast.thumbnail"

    REQUEST = {"method":"VideoLibrary.GetSeasons",
               "params":{"tvshowid": tvshowid,
                         "properties":["season", "art"]}}

    seasondata = jcomms.sendJSON(REQUEST, "libTV")

    if "seasons" in seasondata["result"]:
      SEASON_ALL = True
      for season in seasondata["result"]["seasons"]:
        seasonid = season["season"]
        for a in season["art"]:
          if SEASON_ALL and a in ["poster", "tvshow.poster", "tvshow.fanart", "tvshow.banner"]:
            SEASON_ALL = False
#            filename = keyFunction(season["art"][a])
#            files[re.sub(r"season(-specials|[ 0-9]*)(.*)\.(.*)", r"season-all\2.\3", filename)] = a
#            files[re.sub(r"season(-specials|[ 0-9]*)(.*)\.(.*)", r"season-all-fanart.\3", filename)] = "fanart"
#            files[re.sub(r"season(-specials|[ 0-9]*)(.*)\.(.*)", r"season-all-banner.\3", filename)] = "banner"
            (poster_url, fanart_url, banner_url) = jcomms.getSeasonAll(season["art"][a])
            if poster_url: files[keyFunction(poster_url)] = "poster"
            if fanart_url: files[keyFunction(fanart_url)] = "fanart"
            if banner_url: files[keyFunction(banner_url)] = "banner"
          files[keyFunction(season["art"][a])] = a

        REQUEST = {"method":"VideoLibrary.GetEpisodes",
                   "params":{"tvshowid": tvshowid, "season": seasonid,
                             "properties":["cast", "art"]}}

        episodedata = jcomms.sendJSON(REQUEST, "libTV")

        for episode in episodedata["result"]["episodes"]:
          episodeid = episode["episodeid"]
          for a in episode["art"]:
            files[keyFunction(episode["art"][a])] = a
          if "cast" in episode:
            for c in episode["cast"]:
              if "thumbnail" in c:
                files[keyFunction(c["thumbnail"])] = "cast.thumbnail"

  return files

def pruneCache( purge_nonlibrary_artwork=False ):

  files = getAllFiles(keyFunction=getKeyFromFilename)

  dirScan("N", purge_nonlibrary_artwork, libraryFiles=files, keyIsHash=False)

def usage(EXIT_CODE):

  print "Version: %s" % gConfig.VERSION
  print
  print "Usage: " + os.path.basename(__file__) + " sS <string> | xXf [sql-filter] | dD <id[id id]>] |" \
        "rR | c [class [filter]] | nc [class [filter]] | C class filter | jJ class [filter] | qa class [filter] | qax class [filter] | pP | config"
  print
  print "  s       Search url column for partial movie or tvshow title. Case-insensitive."
  print "  S       Same as \"s\" (search) but will validate cachedurl file exists, displaying only those that fail validation"
  print "  x       Extract details, using optional SQL filter"
  print "  X       Same as \"x\" (extract) but will validate cachedurl file exists, displaying only those that fail validation"
  print "  f       Same as x, but include file summary (file count, accumulated file size)"
  print "  d       Delete rows with matching ids, along with associated cached images"
  print "  r       Reverse search to identify \"orphaned\" Thumbnail files not present in texture cache"
  print "  R       Same as \"r\" (reverse search) but automatically deletes \"orphaned\" Thumbnail files"
  print "  c       Re-cache missing artwork. Class can be movies, tags, sets, tvshows, artists, albums or songs."
  print "  C       Re-cache artwork even when it exists. Class can be movies, tags, sets, tvshows, artists, albums or songs. Filter mandatory."
  print "  nc      Same as c, but don't actually cache anything (ie. see what is missing). Class can be movies, tags, sets, tvshows, artists, albums or songs."
  print "  j       Query library by class (movies, tags, sets, tvshows, artists, albums or songs) with optional filter, return JSON results."
  print "  J       Same as \"j\", but includes extra JSON audio/video fields as defined in properties file."
  print "  jd, Jd  Functionality equivalent to j/J, but all urls are decoded"
  print "  qa      Run QA check on movies, tags and tvshows, identifying media with missing artwork or plots"
  print "  qax     Same as qa, but remove and rescan those media items with missing details. Optional tests: qa.rating, qa.file."
  print "  p       Display files present in texture cache that don't exist in the media library"
  print "  P       Prune (automatically remove) cached items that don't exist in the media library"
  print "  config  Show current configuration"
  print
  print "SQL Filter fields:"
  print "  id, cachedurl, height, width, usecount, lastusetime, lasthashcheck, url"

  sys.exit(EXIT_CODE)

def showConfig(EXIT_CODE):
  if not gConfig.CACHE_IGNORE_TYPES:
    ignore_types = None
  else:
    t = []
    for i in gConfig.CACHE_IGNORE_TYPES: t.append(i.pattern)
    ignore_types = ", ".join(t)

  print "Current properties (if exists, read from %s%s%s):" % (os.path.dirname(__file__), os.sep, gConfig.CONFIG_NAME)
  print
  print "  sep = %s" % gConfig.FSEP
  print "  userdata = %s " % gConfig.XBMC_BASE
  print "  dbfile = %s" % gConfig.TEXTUREDB
  print "  thumbnails = %s " % gConfig.THUMBNAILS
  print "  xbmc.host = %s" % gConfig.XBMC_HOST
  print "  webserver.port = %s" % gConfig.WEB_PORT
  print "  webserver.singleshot = %s" % gConfig.WEB_SINGLESHOT
  print "  rpc.port = %s" % gConfig.RPC_PORT
  print "  download.threads = %d" % gConfig.DOWNLOAD_THREADS_DEFAULT
  print "  extrajson.albums  = %s" % gConfig.XTRAJSON["extrajson.albums"]
  print "  extrajson.artists = %s" % gConfig.XTRAJSON["extrajson.artists"]
  print "  extrajson.songs   = %s" % gConfig.XTRAJSON["extrajson.songs"]
  print "  extrajson.movies  = %s" % gConfig.XTRAJSON["extrajson.movies"]
  print "  extrajson.sets    = %s" % gConfig.XTRAJSON["extrajson.sets"]
  print "  extrajson.tvshows.tvshow = %s" % gConfig.XTRAJSON["extrajson.tvshows.tvshow"]
  print "  extrajson.tvshows.season = %s" % gConfig.XTRAJSON["extrajson.tvshows.season"]
  print "  extrajson.tvshows.episode= %s" % gConfig.XTRAJSON["extrajson.tvshows.episode"]
  print "  qaperiod = %d (added after %s)" % (gConfig.QAPERIOD, gConfig.QADATE)
  print "  qa.rating = %s" % gConfig.QA_RATING
  print "  qa.file = %s" % gConfig.QA_FILE
  print "  cache.castthumb = %s" % gConfig.CACHE_CAST_THUMB
  print "  cache.ignore.types = %s" % ignore_types
  print "  logfile = %s" % gConfig.LOGFILE
  if gConfig.RECACHEALL:
    print "  allow.recacheall = yes"
  print
  print "See http://wiki.xbmc.org/index.php?title=JSON-RPC_API/v6 for details of available audio/video fields."

  sys.exit(EXIT_CODE)

def loadConfig():
  global DBVERSION, MYWEB, MYSOCKET, MYDB
  global TOTALS
  global gConfig, gProgress

  DBVERSION = MYWEB = MYSOCKET = MYDB = None

  TOTALS = MyTotals()

  gConfig = MyConfiguration()
  gProgress = MyLogger()
  gProgress.DEBUG = gConfig.DEBUG
  gProgress.setLogFile(gConfig.LOGFILE)

def checkConfig(option):

  jsonNeedVersion = 6

  if option in ["c","C"]:
    needWeb = True
  else:
    needWeb = False

  if option in ["c","C","nc","j","jd","J","Jd","qa","qax","p","P" ]:
    needSocket = True
  else:
    needSocket = False

  if option in ["s","S","x","X","f","c","C","nc","qa","qax","d","r","R","p","P" ]:
    needDb = True
  else:
    needDb = False

  gotWeb = gotSocket = gotDb = False
  jsonGotVersion = 0

  if needWeb:
    try:
      defaultTimeout = socket.getdefaulttimeout()
      socket.setdefaulttimeout(7.5)
      jcomms = MyJSONComms(gConfig, gProgress)
      REQUEST = {}
      REQUEST["jsonrpc"] = "2.0"
      REQUEST["method"] = "JSONRPC.Ping"
      REQUEST["id"] =  "libPing"
      data = json.loads(jcomms.sendWeb("POST", "/jsonrpc", json.dumps(REQUEST), timeout=5))
      if "result" in data and data["result"] == "pong":
        gotWeb = True

      socket.setdefaulttimeout(defaultTimeout)
    except socket.error:
      pass

  if needWeb and not gotWeb:
    MSG = "FATAL: The task you wish to perform requires that the web server is\n" \
          "       enabled and running on the XBMC system you wish to connect.\n\n" \
          "       A connection cannot be established to the following webserver:\n" \
          "       %s:%s\n\n" \
          "       Check settings in properties file %s" % (gConfig.XBMC_HOST, gConfig.WEB_PORT, gConfig.CONFIG_NAME)
    gProgress.errout(MSG, newLine=True)
    sys.exit(2)

  if needSocket:
    try:
      jcomms = MyJSONComms(gConfig, gProgress)
      REQUEST = {"method": "JSONRPC.Ping"}
      data = jcomms.sendJSON(REQUEST, "libPing", timeout=7.5, checkResult=False)
      if "result" in data and data["result"] == "pong":
        gotSocket = True

      REQUEST = {"method": "JSONRPC.Version"}
      data = jcomms.sendJSON(REQUEST, "libVersion", timeout=7.5, checkResult=False)
      if "result" in data:
        if "version" in data["result"]:
          jsonGotVersion = data["result"]["version"]
          if type(jsonGotVersion) is dict and "major" in jsonGotVersion:
            jsonGotVersion = jsonGotVersion["major"]
    except socket.error:
      pass

  if needSocket and not gotSocket:
    MSG = "FATAL: The task you wish to perform requires that the JSON-RPC server is\n" \
          "       enabled and running on the XBMC system you wish to connect.\n\n" \
          "       A connection cannot be established to the following JSON-RPC server:\n" \
          "       %s:%s\n\n" \
          "       Check settings in properties file %s" % (gConfig.XBMC_HOST, gConfig.RPC_PORT, gConfig.CONFIG_NAME)
    gProgress.errout(MSG, newLine=True)
    return False

  if needSocket and jsonGotVersion  < jsonNeedVersion :
    MSG = "FATAL: The task you wish to perform requires that a JSON-RPC server with\n" \
          "       version %d or above of the XBMC JSON-RPC API is provided.\n\n" \
          "       The JSON-RPC API version of the connected server is: %d (0 means unknown)\n\n" \
          "       Check settings in properties file %s" % (jsonNeedVersion, jsonGotVersion, gConfig.CONFIG_NAME)
    gProgress.errout(MSG, newLine=True)
    return False

  if needDb:
    try:
      database = MyDB(gConfig, gProgress)
      con = database.getDB()
      if database.DBVERSION < 13:
        MSG = "WARNING: The sqlite3 database pre-dates Frodo (v12), some problems may be encountered!"
        gProgress.errout(MSG, newLine=True)
        gProgress.log(MSG)
      gotDb = True
    except lite.OperationalError:
      pass

  if needDb and not gotDb:
    MSG = "FATAL: The task you wish to perform requires read/write file\n" \
          "       access to the XBMC sqlite3 Texture Cache database.\n\n" \
          "       The following sqlite3 database could not be opened:\n" \
          "       %s\n\n" \
          "       Check settings in properties file %s" % (gConfig.getDBPath(), gConfig.CONFIG_NAME)
    gProgress.errout(MSG, newLine=True)
    return False

  return True

def main(argv):

  loadConfig()

  if len(argv) == 0: usage(1)

  if not checkConfig(argv[0]): sys.exit(2)

  if argv[0] == "s" and len(argv) == 2:
    sqlExtract("NONE", argv[1], "")
  elif argv[0] == "S" and len(argv) == 2:
    sqlExtract("EXISTS", argv[1], "")

  elif argv[0] == "x" and len(argv) == 1:
    sqlExtract("NONE")
  elif argv[0] == "x" and len(argv) == 2:
    sqlExtract("NONE", "", argv[1])
  elif argv[0] == "X" and len(argv) == 1:
    sqlExtract("EXISTS")

  elif argv[0] == "f" and len(argv) == 1:
    sqlExtract("STATS")
  elif argv[0] == "f" and len(argv) == 2:
    sqlExtract("STATS", "", argv[1])

  elif argv[0] == "c" and len(argv) == 1:
    libraryQuery("cache", "albums")
    libraryQuery("cache", "artists")
    libraryQuery("cache", "movies")
    libraryQuery("cache", "sets")
    libraryQuery("cache", "tvshows")
    TOTALS.libraryStats("albums/artists/movies/sets/tvshows")
  elif argv[0] == "c" and len(argv) == 2:
    libraryQuery("cache", argv[1])
    TOTALS.libraryStats(argv[1])
  elif argv[0] == "c" and len(argv) == 3:
    libraryQuery("cache", argv[1], argv[2])
    TOTALS.libraryStats(argv[1], argv[2])

  elif argv[0] == "nc" and len(argv) == 1:
    libraryQuery("cache", "albums", nodownload=True)
    libraryQuery("cache", "artists", nodownload=True)
    libraryQuery("cache", "movies", nodownload=True)
    libraryQuery("cache", "sets", nodownload=True)
    libraryQuery("cache", "tvshows", nodownload=True)
    TOTALS.libraryStats("albums/artists/movies/sets/tvshows")
  elif argv[0] == "nc" and len(argv) == 2:
    libraryQuery("cache", argv[1], nodownload=True)
    TOTALS.libraryStats(argv[1])
  elif argv[0] == "nc" and len(argv) == 3:
    libraryQuery("cache", argv[1], argv[2], nodownload=True)
    TOTALS.libraryStats(argv[1], argv[2])

  elif argv[0] == "C" and len(argv) == 2:
    if gConfig.RECACHEALL:
      libraryQuery("cache", argv[1], force=True)
      TOTALS.libraryStats(argv[1])
    else:
      print "Forcing re-cache of all items is disabled. Enable by setting \"allow.recacheall=yes\" in property file."
      sys.exit(2)
  elif argv[0] == "C" and len(argv) == 3:
    libraryQuery("cache", argv[1], argv[2], force=True)
    TOTALS.libraryStats(argv[1], argv[2])

  elif argv[0] == "j" and len(argv) == 2:
    libraryQuery("dump", argv[1])
  elif argv[0] == "j" and len(argv) == 3:
    libraryQuery("dump", argv[1], argv[2])

  elif argv[0] == "jd" and len(argv) == 2:
    libraryQuery("dump", argv[1], decode=True)
  elif argv[0] == "jd" and len(argv) == 3:
    libraryQuery("dump", argv[1], argv[2], decode=True)

  elif argv[0] == "J" and len(argv) == 2:
    libraryQuery("dump", argv[1], extraFields=True)
  elif argv[0] == "J" and len(argv) == 3:
    libraryQuery("dump", argv[1], argv[2], extraFields=True)

  elif argv[0] == "Jd" and len(argv) == 2:
    libraryQuery("dump", argv[1], extraFields=True, decode=True)
  elif argv[0] == "Jd" and len(argv) == 3:
    libraryQuery("dump", argv[1], argv[2], extraFields=True, decode=True)

  elif argv[0] == "qa" and len(argv) == 2:
    libraryQuery("qa", argv[1])
  elif argv[0] == "qa" and len(argv) == 3:
    libraryQuery("qa", argv[1], argv[2])

  elif argv[0] == "qax" and len(argv) == 2:
    libraryQuery("qa", argv[1], rescan=True)
  elif argv[0] == "qax" and len(argv) == 3:
    libraryQuery("qa", argv[1], argv[2], rescan=True)

  elif argv[0] == "d" and len(argv) >= 2:
    sqlDelete(argv[1:])

  elif argv[0] == "r":
    dirScan("N")

  elif argv[0] == "R":
    dirScan("Y")

  elif argv[0] == "p" and len(argv) == 1:
    pruneCache(purge_nonlibrary_artwork=False)

  elif argv[0] == "P" and len(argv) == 1:
    pruneCache(purge_nonlibrary_artwork=True)

  elif argv[0] == "version":
    print "Version: v%s" % gConfig.VERSION

  elif argv[0] == "config":
    showConfig(1)

  else:
    usage(1)

  sys.exit(0)

if __name__ == "__main__":
  try:
    stopped = threading.Event()
    main(sys.argv[1:])
  except (KeyboardInterrupt, SystemExit):
    pass