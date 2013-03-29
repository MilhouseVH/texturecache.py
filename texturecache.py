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
#  any associated cached artwork. Option (D) will perform a dry run.
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
#    cache.ignore.types = image://video
#    logfile = None
#
# Dumped data format:
#
#  rowid, cachedurl, height, width, usecount, lastusetime, lasthashcheck, url
#
# Changelog:
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
#    don't cache) certain image types, such as image://video (default).
#    Comma delimited patterns, eg. "image://video, image://nfs". Set
#    to None to process all urls. Matches beginning of url.
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

class MyConfiguration(object):
  def __init__( self ):

    self.VERSION="0.3.0"

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
                                            "cache.ignore.types": "image://video",
                                            "logfile": None
                                            }
                                          )

    self.DEBUG = True if "PYTHONDEBUG" in os.environ and os.environ["PYTHONDEBUG"].lower()=="y" else False

    self.FILENAME = os.path.dirname(__file__) + "/texturecache.cfg"

    cfg = StringIO.StringIO()
    cfg.write("[xbmc]\n")
    if os.path.exists(self.FILENAME): cfg.write(open(self.FILENAME, "r").read())
    cfg.seek(0, os.SEEK_SET)
    config.readfp(cfg)

    self.IDFORMAT = config.get("xbmc", "format")
    self.FSEP = config.get("xbmc", "sep")

    self.XBMC_BASE = os.path.expanduser(config.get("xbmc", "userdata")) + "/"
    self.TEXTUREDB = config.get("xbmc", "dbfile")
    self.THUMBNAILS = config.get("xbmc", "thumbnails") + "/"

    self.XBMC_BASE = self.XBMC_BASE.replace("/", os.sep)
    self.TEXTUREDB = self.TEXTUREDB.replace("/", os.sep)
    self.THUMBNAILS = self.THUMBNAILS.replace("/", os.sep)

    self.XBMC_HOST = config.get("xbmc", "xbmc.host")
    self.WEB_PORT = config.get("xbmc", "webserver.port")
    self.RPC_PORT = config.get("xbmc", "rpc.port")
    self.XTRAJSON_ALBUMS  = config.get("xbmc", "extrajson.albums")
    self.XTRAJSON_ARTISTS = config.get("xbmc", "extrajson.artists")
    self.XTRAJSON_SONGS   = config.get("xbmc", "extrajson.songs")
    self.XTRAJSON_MOVIES  = config.get("xbmc", "extrajson.movies")
    self.XTRAJSON_SETS    = config.get("xbmc", "extrajson.sets")
    self.XTRAJSON_TVSHOWS_TVSHOW = config.get("xbmc", "extrajson.tvshows.tvshow")
    self.XTRAJSON_TVSHOWS_SEASON = config.get("xbmc", "extrajson.tvshows.season")
    self.XTRAJSON_TVSHOWS_EPISODE= config.get("xbmc", "extrajson.tvshows.episode")

    if self.XTRAJSON_ALBUMS  == "": self.XTRAJSON_ALBUMS = None
    if self.XTRAJSON_ARTISTS == "": self.XTRAJSON_ARTISTS = None
    if self.XTRAJSON_SONGS   == "": self.XTRAJSON_SONGS = None
    if self.XTRAJSON_MOVIES  == "": self.XTRAJSON_MOVIES = None
    if self.XTRAJSON_SETS    == "": self.XTRAJSON_SETS = None
    if self.XTRAJSON_TVSHOWS_TVSHOW == "": self.XTRAJSON_TVSHOWS = None
    if self.XTRAJSON_TVSHOWS_SEASON == "": self.XTRAJSON_SEASON  = None
    if self.XTRAJSON_TVSHOWS_EPISODE== "": self.XTRAJSON_EPISODE = None

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
    self.CACHE_IGNORE_TYPES = [x.strip() for x in temp.split(',')] if temp else None

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

class MyLogger():
  def __init__( self ):
    self.lastlen = 0
    self.now = 0
    self.LOG = False
    self.LOGFILE = None

  def __del__( self ):
    if self.LOGFILE: self.LOGFILE.close()

  def errout(self, data, every=0, newLine=False):
    if every != 0:
      self.now += 1
      if self.now != 1:
        if self.now <= every: return
        else: self.reset(initialValue=1)
    else:
      self.reset(initialValue=0)

    udata = removeNonAscii(data, "?")
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
    sys.stdout.write(data)
    sys.stdout.flush()

  def debug(self, data, jsonrequest=None, every=0, newLine=False, newlineBefore=False):
    if self.DEBUG:
      if newlineBefore: sys.stderr.write("\n")
      self.errout("%s: %s" % (datetime.datetime.now(), data), every, newLine)
    self.log(data, jsonrequest=jsonrequest)

  def setLogFile(self, filename):
    if filename:
      self.LOG = True
      self.LOGFILE = open(filename, "w")
    else:
      self.LOG = False
      if self.LOGFILE:
        self.LOGFILE.close()
        self.LOGFILE = None

  def log(self, data, jsonrequest = None):
    if self.LOG:
      if jsonrequest == None:
        self.LOGFILE.write("%s: %s\n" % (datetime.datetime.now(), data.encode("utf-8")))
      else:
        self.LOGFILE.write("%s: %s [%s]\n" % (datetime.datetime.now(),
            data.encode("utf-8"), json.dumps(jsonrequest).encode("utf-8")))

def getGlobalDB():
  global MYDB, DBVERSION
  if not MYDB:
    if not os.path.exists(gConfig.getDBPath()):
      print "\n*** Local texture database does not exist: %s ***\n" % (gConfig.getDBPath())
      sys.exit(2)
    MYDB = lite.connect(gConfig.getDBPath())
    DBVERSION = MYDB.execute("SELECT idVersion FROM version").fetchone()[0]
  return MYDB

def getGlobalWeb():
  global MYWEB, WEB_LAST_STATUS
  if not MYWEB or gConfig.WEB_SINGLESHOT:
    if MYWEB: MYWEB.close()
    MYWEB = httplib.HTTPConnection("%s:%s" % (gConfig.XBMC_HOST, gConfig.WEB_PORT))
    WEB_LAST_STATUS = -1
    if gConfig.DEBUG: MYWEB.set_debuglevel(1)
  return MYWEB

def getGlobalSocket():
  global MYSOCKET
  if not MYSOCKET:
    MYSOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    MYSOCKET.connect((gConfig.XBMC_HOST, int(gConfig.RPC_PORT)))
  return MYSOCKET

def sendWeb(request_type, url, request=None, headers={}, readAmount = 0):
  global WEB_LAST_STATUS

  if gConfig.WEB_AUTH_TOKEN:
    headers.update({"Authorization": "Basic %s" % gConfig.WEB_AUTH_TOKEN})

  web = getGlobalWeb()
  web.request(request_type, url, request, headers)
  web.sock.setblocking(1)
  try:
    response = web.getresponse()
    WEB_LAST_STATUS = response.status
    if WEB_LAST_STATUS == httplib.UNAUTHORIZED:
      raise httplib.HTTPException("Remote web host requires webserver.username/webserver.password properties")
    if readAmount == 0: return response.read()
    else: return response.read(readAmount)
  except:
    if gConfig.WEB_SINGLESHOT == False:
      gProgress.debug("SWITCHING TO WEBSERVER.SINGLESHOT MODE", newLine=True)
      gConfig.WEB_SINGLESHOT = True
      return sendWeb(request_type, url, request, headers)
    raise

def sendJSON(request, id, callback=None, timeout=2, checkResult=True):
  BUFFER_SIZE = 32768

  request["jsonrpc"] = "2.0"
  request["id"] =  id

  # Following methods don't work over sockets - by design.
  if request["method"] in ["Files.PrepareDownload", "Files.Download"]:
    gProgress.debug("SENDING JSON WEB REQUEST", jsonrequest=request, newLine=True, newlineBefore=True)
    data = sendWeb("POST", "/jsonrpc", json.dumps(request), {"Content-Type": "application/json"})
    if gProgress.LOGFILE:
      gProgress.log("RESPONSE%s: %s" % (" (truncated)" if len(data)>256 else "", removeNonAscii(data[:256])))
    return json.loads(data)

  s = getGlobalSocket()
  gProgress.debug("SENDING JSON SOCKET REQUEST", jsonrequest=request, newLine=True, newlineBefore=True)
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
      gProgress.debug("BUFFER RECEIVED (len %d)" % len(newdata), newLine=True)
    except socket.error:
      if newdata[-1:] == "}" or newdata[-2:] == "}\n":
        try:
          gProgress.debug("CONVERTING RESPONSE", newLine=True)
          jdata = json.loads("".join(data))
          gProgress.debug("CONVERSION COMPLETE, elapsed time: %f seconds" % (time.time() - START_TIME), newLine=True)
          if ("result" in jdata and "limits" in jdata["result"]):
            gProgress.debug("RECEIVED LIMITS: %s" % jdata["result"]["limits"], newLine=True)
          if gProgress.LOGFILE:
            gProgress.log("RESPONSE%s: %s" % (" (truncated)" if len(data[0]) > 256 else "", removeNonAscii(data[0][:256])))
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
        if not callback(id, method, params): break
      elif id: break

  if checkResult and not "result" in jdata: print "ERROR: JSON response has no result!\n%s" % jdata

  return jdata

def jsonWaitForScanFinished(id, method, params):
  if method.endswith("Library.OnScanFinished"): return False
  return True

def dumpJSON(data, decode=False):
  if decode:
    gProgress.errout("Decoding URLs...")
    unquoteArtwork(data)

  gProgress.errout("")

  print json.dumps(data, indent=2, ensure_ascii=True, sort_keys=False)

def dumpRow(row):
  print (gConfig.IDFORMAT % row[0] + "%s%14s%s%04d%s%04d%s%04d%s%19s%s%19s%s" % \
        (gConfig.FSEP, row[1], gConfig.FSEP, row[4], gConfig.FSEP, row[5],
         gConfig.FSEP, row[6], gConfig.FSEP, row[7], gConfig.FSEP, row[2],
         gConfig.FSEP)).encode("utf-8") + \
        row[3].encode("utf-8")

def removeNonAscii(s, replaceWith = ""):
  if replaceWith == "":
    return  "".join([x if ord(x) < 128 else ("%%%02x" % ord(x)) for x in s])
  else:
    return  "".join([x if ord(x) < 128 else replaceWith for x in s])

def appendFields(aList, fields):
  if fields != None:
    for f in fields.split():
      newField = f.replace(",", "")
      if not newField in aList:
        aList.append(newField)

def addFilter(filter, newFilter, condition="and"):
  if "filter" in filter:
     filter["filter"] = { condition: [ filter["filter"], newFilter ] }
  else:
     filter["filter"] = newFilter

def unquoteArtwork(items):
  for item in items:
    for field in item:
      if field in ["seasons", "episodes"]: unquoteArtwork(item[field])

      if field in ["fanart", "thumbnail"]: item[field] = urllib.unquote(item[field])

      if field == "art":
        art = item["art"]
        for image in art:
          art[image] = urllib.unquote(art[image])

      if field == "cast":
        for cast in item["cast"]:
          if "thumbnail" in cast:
            cast["thumbnail"] = urllib.unquote(cast["thumbnail"])

def libraryQuery(action, item, filter="", force=False, extraFields=False, rescan=False, decode=False):
  if item == "albums":
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

def libraryStats(item="", filter=""):
  items = {}
  for a in TOTALS:
    for c in TOTALS[a]:
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

  sortedTOTALS = sorted(TOTALS.items())
  sortedTOTALS.append(("TOTAL", {}))
  TOTALS["TOTAL"] = {}

  KEYS = {"Deleted":   "#",
          "Duplicate": "*",
          "Error":     "!",
          "Ignored":   "-",
          "Skipped":   ".",
          "Updated":   "+",
          "TOTAL":     " "}

  line0 = "Cache pre-load activity summary for \"%s\"" % item
  if filter != "": line0 = "%s, filtered by \"%s\"" % (line0, filter)
  line0 = "%s:" % line0

  line1 = "%-12s" % " "
  line2 = "-" * 12
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
    TOTALS[a]["TOTAL"] = 0
    if a == "TOTAL": print line2.replace("-","=").replace("+","=")
    line = "%-9s %s " % (a, KEYS[a])
    for i in sortedItems:
      i = i[0]
      if a == "TOTAL":
        value = "%d" % items[i] if items[i] != None else "-"
      elif i in TOTALS[a]:
        ivalue = TOTALS[a][i]
        value = "%d" % ivalue
        if items[i] == None: items[i] = 0
        items[i] += ivalue
        TOTALS[a]["TOTAL"] += ivalue
      else:
        value = "-"
      width = 10 if len(i) < 10 else len(i)+1
      line = "%s| %s" % (line, value.center(width))
    print line

def libraryAllAlbums(action, filter, force, extraFields, rescan, decode):
  if action == "dump":
    gProgress.errout("Loading Albums...")
  else:
    print "Querying %s:%s for all Music Albums..." % (gConfig.XBMC_HOST, gConfig.RPC_PORT)

  REQUEST = {"method":"AudioLibrary.GetAlbums",
             "params":{"sort": {"order": "ascending", "method": "label"},
                       "properties":["title", "artist", "fanart", "thumbnail"]}}

  if filter != "": addFilter(REQUEST["params"], {"field": "album", "operator": "contains", "value": filter})
  if extraFields: appendFields(REQUEST["params"]["properties"], gConfig.XTRAJSON_ALBUMS)

  data = sendJSON(REQUEST, "libAlbums")

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  albums = data["result"]["albums"]

  imagesCache = {}

  for album in albums:
    title = album["title"]
    artist = album["artist"]

    if action == "dump": gProgress.errout("Parsing Album: [%s]..." % title.encode("utf-8"), every = 1)

    if action == "cache":
      gProgress.stdout("Album: %-40s" % title.encode("utf-8")[0:40])
      gProgress.log("=== Music Albums: Title [%s], Artist [%s] ===" % (title, artist))
      imgErrors = {}
      for art in album:
        if art in ["fanart", "thumbnail"]:
          loadImage(force, art, album[art], imagesCache, imgErrors)

      processImageErrors(imgErrors)

  if action == "dump": dumpJSON(albums, decode)

def libraryAllArtists(action, filter, force, extraFields, rescan, decode):
  if action == "dump":
    gProgress.errout("Loading Artists...")
  else:
    print "Querying %s:%s for all Music Artists..." % (gConfig.XBMC_HOST, gConfig.RPC_PORT)

  REQUEST = {"method":"AudioLibrary.GetArtists",
             "params":{"sort": {"order": "ascending", "method": "artist"},
                       "albumartistsonly": False,
                       "properties":["fanart", "thumbnail"]}}

  if filter != "": addFilter(REQUEST["params"], {"field": "artist", "operator": "contains", "value": filter})
  if extraFields: appendFields(REQUEST["params"]["properties"], gConfig.XTRAJSON_ARTISTS)

  data = sendJSON(REQUEST, "libArtists")

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  artists = data["result"]["artists"]

  imagesCache = {}

  for artist in artists:
    name = artist["artist"]

    if action == "dump": gProgress.errout("Parsing Artist: [%s]..." % name.encode("utf-8"), every = 1)

    if action == "cache":
      gProgress.stdout("Artist: %-40s" % name.encode("utf-8")[0:40])
      gProgress.log("=== Music Artists: Artist [%s] ===" % name)
      imgErrors = {}
      for art in artist:
        if art in ["fanart", "thumbnail"]:
          loadImage(force, art, artist[art], imagesCache, imgErrors)

      processImageErrors(imgErrors)

  if action == "dump": dumpJSON(artists, decode)

def libraryAllSongs(action, filter, force, extraFields, rescan, decode):
  if action == "dump":
    gProgress.errout("Loading Songs...")
  else:
    print "Querying %s:%s for all Music Songs..." % (gConfig.XBMC_HOST, gConfig.RPC_PORT)

  REQUEST = {"method":"AudioLibrary.GetSongs",
             "params":{"sort": {"order": "ascending", "method": "title"},
                       "properties":["title", "fanart", "thumbnail"]}}

  if filter != "": addFilter(REQUEST["params"], {"field": "title", "operator": "contains", "value": filter})
  if extraFields: appendFields(REQUEST["params"]["properties"], gConfig.XTRAJSON_SONGS)

  data = sendJSON(REQUEST, "libSongs")

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  songs = data["result"]["songs"]

  imagesCache = {}

  for song in songs:
    title = song["title"]

    if action == "dump": gProgress.errout("Parsing Song: [%s]..." % title.encode("utf-8"), every = 1)

    if action == "cache":
      gProgress.stdout("Song: %-40s" % title.encode("utf-8")[0:40])
      gProgress.log("=== Music Songs: Title [%s] ===" % title)
      imgErrors = {}
      for art in song:
        if art in ["fanart", "thumbnail"]:
          loadImage(force, art, song[art], imagesCache, imgErrors)

      processImageErrors(imgErrors)

  if action == "dump": dumpJSON(songs, decode)

def libraryAllMovies(action, filter, force, extraFields, rescan, decode, isTag=False):
  mediaType = "Tag" if isTag else "Movie"

  if action == "dump":
    gProgress.errout("Loading %ss..." % mediaType)
  else:
    print "Querying %s:%s for all %ss..." % (gConfig.XBMC_HOST, gConfig.RPC_PORT, mediaType)

  REQUEST = {"method":"VideoLibrary.GetMovies",
             "params":{"sort": {"order": "ascending", "method": "title"},
                       "properties":["title", "art"]}}

  if action == "qa": appendFields(REQUEST["params"]["properties"], "file, plot, rating, mpaa")
  if action == "qa": addFilter(REQUEST["params"], {"field": "dateadded", "operator": "after", "value": gConfig.QADATE})

  if isTag:
    if filter.strip() == "":
      addFilter(REQUEST["params"], {"field": "tag", "operator": "contains", "value": "%"})
    else:
      word = 0
      filterBoolean = "and"
      for tag in [x.strip() for x in re.split("( and | or )", filter)]:
        word += 1
        if (word%2 == 0) and tag in ["and","or"]: filterBoolean = tag
        else: addFilter(REQUEST["params"], {"field": "tag", "operator": "contains", "value": tag}, filterBoolean)
  else:
    if filter != "": addFilter(REQUEST["params"], {"field": "title", "operator": "contains", "value": filter})

  if action == "cache" and gConfig.CACHE_CAST_THUMB: appendFields(REQUEST["params"]["properties"], "cast")
  if extraFields: appendFields(REQUEST["params"]["properties"], gConfig.XTRAJSON_MOVIES)

  data = sendJSON(REQUEST, "libMovies")

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  movies = data["result"]["movies"]

  imagesCache = {}

  for movie in movies:
    title = movie["title"]
    movieid = movie["movieid"]

    if action == "dump": gProgress.errout("Parsing %s: [%s]..." % (mediaType, title.encode("utf-8")), every = 1)

    if action == "cache":
      gProgress.stdout("%s: %-40s" % (mediaType, title.encode("utf-8")[0:40]))
      gProgress.log("=== Video %ss: Title [%s] ===" % (mediaType, title))
      imgErrors = {}
      art = movie["art"]
      for artwork in art:
        loadImage(force, artwork, art[artwork], imagesCache, imgErrors)

      if "cast" in movie:
        cast = movie["cast"]
        n = 0
        for actor in cast:
          if "thumbnail" in actor:
            n += 1
            loadImage(force, "cast %02d" % n, actor["thumbnail"], imagesCache, imgErrors)

      processImageErrors(imgErrors)

    if action == "qa":
      directories = {}
      libraryids = []

      missing = {}

      if gConfig.QA_RATING and not ("rating" in movie and movie["rating"] != 0): missing["rating"] = True
      if not "plot" in movie or movie["plot"] == "": missing["plot"] = True
      if not "mpaa" in movie or movie["mpaa"] == "": missing["mpaa"] = True

      if not "fanart" in movie["art"] or movie["art"]["fanart"] == "": missing["fanart"] = True
      elif getRowByFilename(movie["art"]["fanart"]) == None: missing["fanart (uncached)"] = False

      if not "poster" in movie["art"] or movie["art"]["poster"] == "": missing["poster"] = True
      elif getRowByFilename(movie["art"]["poster"]) == None: missing["poster (uncached)"] = False

      if gConfig.QA_FILE and not ("file" in movie and getFileDetails(movie["file"])): missing["file"] = False

      if missing != {}:
        print "%s [%-50s]: Missing %s" % (mediaType, title.encode("utf-8")[0:50], ", ".join(missing))
        if "".join(["Y" if missing[m] else "" for m in missing]) != "":
          libraryids.append(movieid)
          dir = os.path.dirname(movie["file"])
          directories[dir] = dir

    if rescan: rescanDirectories("movies", libraryids, directories)

  if action == "dump": dumpJSON(movies, decode)

def libraryAllMovieSets(action, filter, force, extraFields, rescan, decode):
  if action == "dump":
    gProgress.errout("Loading Sets...")
  else:
    print "Querying %s:%s for all Movie Sets..." % (gConfig.XBMC_HOST, gConfig.RPC_PORT)

  REQUEST = {"method":"VideoLibrary.GetMovieSets",
             "params":{"sort": {"order": "ascending", "method": "title"},
                       "properties":["title", "art"]}}

  if extraFields: appendFields(REQUEST["params"]["properties"], gConfig.XTRAJSON_SETS)

  data = sendJSON(REQUEST, "libMovies")

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  sets = data["result"]["sets"]

  filteredSets = []
  imagesCache = {}

  if action == "dump": gProgress.errout("Filtering Sets...")

  for set in sets:
    title = set["title"]
    if filter == "" or re.search(filter, title, re.IGNORECASE):
      filteredSets.append(set)

  for set in filteredSets:
    if action == "dump": gProgress.errout("Parsing Set: [%s]..." % title.encode("utf-8"), every = 1)

    if action == "cache":
      gProgress.stdout("Movie Set: %-40s" % title.encode("utf-8")[0:40])
      gProgress.log("=== Video Sets: Title [%s] ===" % title)
      imgErrors = {}
      art = set["art"]
      for artwork in art: loadImage(force, artwork, art[artwork], imagesCache, imgErrors)

      processImageErrors(imgErrors)

  if action == "dump": dumpJSON(filteredSets, decode)

def libraryAllTVShows(action, filter, force, extraFields, rescan, decode):
  if action == "dump":
    gProgress.errout("Loading: TV Shows...")
  else:
    print "Querying %s:%s for all TV Shows..." % (gConfig.XBMC_HOST, gConfig.RPC_PORT)


  REQUEST = {"method":"VideoLibrary.GetTVShows",
             "params":{"sort": {"order": "ascending", "method": "title"},
                       "properties":["title", "art"]}}

  if action == "qa": appendFields(REQUEST["params"]["properties"], "plot, rating")
  if filter != "": addFilter(REQUEST["params"], {"field": "title", "operator": "contains", "value": filter})
  if action == "cache" and gConfig.CACHE_CAST_THUMB: appendFields(REQUEST["params"]["properties"], "cast")
  if extraFields: appendFields(REQUEST["params"]["properties"], gConfig.XTRAJSON_TVSHOWS_TVSHOW)

  data = sendJSON(REQUEST, "libTvShows")

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  tvshows = data["result"]["tvshows"]

  imagesCache = {}

  for tvshow in tvshows:
    title = tvshow["title"]
    tvshowid = tvshow["tvshowid"]

    if action == "dump": gProgress.errout("Parsing TV Show: [%s]..." % title.encode("utf-8"), every = 1)

    if action == "cache":
      gProgress.stdout("TV Show: %s..." % title.encode("utf-8"))
      gProgress.log("=== Video TVShows: Title [%s] ===" % title)
      imgErrors = {}

      art = tvshow["art"]
      for artwork in art:
        loadImage(force, artwork, art[artwork], imagesCache, imgErrors)

      if "cast" in tvshow:
        cast = tvshow["cast"]
        n = 0
        for actor in cast:
          if "thumbnail" in actor:
            n += 1
            loadImage(force, "cast %02d" % n, actor["thumbnail"], imagesCache, imgErrors)

      processImageErrors(imgErrors)

    if action == "qa":
      missing = {}

      if gConfig.QA_RATING and not ("rating" in tvshow and tvshow["rating"] != 0): missing["rating"] = True
      if not "plot" in tvshow or tvshow["plot"] == "": missing["plot"] = True

      if not "fanart" in tvshow["art"] or tvshow["art"]["fanart"] == "": missing["fanart"] = True
      elif getRowByFilename(tvshow["art"]["fanart"]) == None: missing["fanart (uncached)"] = False

      if not "banner" in tvshow["art"] or tvshow["art"]["banner"] == "": missing["banner"] = True
      elif getRowByFilename(tvshow["art"]["banner"]) == None: missing["banner (uncached)"] = False

      if not "poster" in tvshow["art"] or tvshow["art"]["poster"] == "":
        if not "thumb" in tvshow["art"] or tvshow["art"]["thumb"] == "": missing["poster"] = True
        elif getRowByFilename(tvshow["art"]["thumb"]) == None: missing["thumb (uncached)"] = False
      elif getRowByFilename(tvshow["art"]["poster"]) == None: missing["poster (uncached)"] = False

      if missing != {}:
        print "TVShow  [%-38s]: Missing %s" % (title.encode("utf-8")[0:38], ", ".join(missing))

    seasons = libraryTVShow(action, force, extraFields, rescan, imagesCache, title, tvshowid)

    if action == "dump": tvshow["seasons"] = seasons

  if action == "dump": dumpJSON(tvshows, decode)

def libraryTVShow(action, force, extraFields, rescan, imagesCache, showName, showid):

  REQUEST = {"method":"VideoLibrary.GetSeasons",
             "params":{"sort": {"order": "ascending", "method": "season"},
                       "tvshowid": showid, "properties":["season", "art"]}}

  if extraFields: appendFields(REQUEST["params"]["properties"], gConfig.XTRAJSON_TVSHOWS_SEASON)

  data = sendJSON(REQUEST, "libTvShows")

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  seasons = data["result"]["seasons"]
  SEASON_ALL = True

  for season in seasons:
    seasonid = season["season"]

    if action == "dump": gProgress.errout("Parsing TV Show: [%s, Season %d]..." % (showName.encode("utf-8"), seasonid), every = 1)

    if action == "cache":
      if SEASON_ALL and "poster" in season["art"]:
        gProgress.log("=== Video TVShows: Title [%s], Season ALL ===" % showName)
        SEASON_ALL = False
        gProgress.stdout("  Season: ALL...")
        loadImage(force, "poster",  re.sub(r"season(-specials|[ 0-9]*)(.*)\.(.*)",
                r"season-all\2.\3", season["art"]["poster"]), imagesCache, None, retry=1)
        loadImage(force, "banner",  re.sub(r"season(-specials|[ 0-9]*)(.*)\.(.*)",
                r"season-all-fanart.\3", season["art"]["poster"]), imagesCache, None, retry=1)
        loadImage(force, "fanart",  re.sub(r"season(-specials|[ 0-9]*)(.*)\.(.*)",
                r"season-all-banner.\3", season["art"]["poster"]), imagesCache, None, retry=1)
        print

      gProgress.stdout("  Season: %02d..." % seasonid)
      gProgress.log("=== Video TVShows: Title [%s], Season %d ===" % (showName, seasonid))
      imgErrors = {}
      art = season["art"]
      for artwork in art:
        loadImage(force, artwork, art[artwork], imagesCache, imgErrors)

      processImageErrors(imgErrors)

    episodes = libraryTVSeason(action, force, extraFields, rescan, imagesCache, showName, showid, seasonid)

    if action == "dump": season["episodes"] = episodes

  return seasons

def libraryTVSeason(action, force, extraFields, rescan, imagesCache, showName, showid, seasonid):

  REQUEST = {"method":"VideoLibrary.GetEpisodes",
             "params":{"sort": {"order": "ascending", "method": "label"},
                       "tvshowid": showid, "season": seasonid, "properties":["art"]}}

  if action == "qa":
    appendFields(REQUEST["params"]["properties"], "plot, rating, file")
    addFilter(REQUEST["params"], {"field": "dateadded", "operator": "after", "value": gConfig.QADATE})
  if action == "cache" and gConfig.CACHE_CAST_THUMB: appendFields(REQUEST["params"]["properties"], "cast")
  if extraFields: appendFields(REQUEST["params"]["properties"], gConfig.XTRAJSON_TVSHOWS_EPISODE)

  data = sendJSON(REQUEST, "libTvShows")

  limits = data["result"]["limits"]
  if limits["total"] == 0: return

  episodes = data["result"]["episodes"]

  for episode in episodes:
    label = episode["label"].partition(".")[0]
    episodeid = episode["episodeid"]

    if action == "cache":
      gProgress.stdout("    Episode: %s..." % label)
      gProgress.log("=== Video TVShows: Title [%s], Season [%d], Episode [%s] ===" % (showName, seasonid, label))
      imgErrors = {}

      art = episode["art"]
      for artwork in art:
        loadImage(force, artwork, art[artwork], imagesCache, imgErrors)

      if "cast" in episode:
        cast = episode["cast"]
        n = 0
        for actor in cast:
          if "thumbnail" in actor:
            n += 1
            loadImage(force, "cast %02d" % n, actor["thumbnail"], imagesCache, imgErrors)

      processImageErrors(imgErrors)

    if action == "qa":
      directories = {}
      libraryids = []

      missing = {}

      if gConfig.QA_RATING and not ("rating" in episode and episode["rating"] != 0): missing["rating"] = True
      if not "plot" in episode or episode["plot"] == "": missing["plot"] = True

      if not "thumb" in episode["art"] or episode["art"]["thumb"] == "": missing["thumb"] = True
      elif getRowByFilename(episode["art"]["thumb"]) == None: missing["thumb (uncached)"] = False

      if gConfig.QA_FILE and not ("file" in episode and getFileDetails(episode["file"])): missing["file"] = False

      if missing != {}:
        print "Episode [%-32s] %5s: Missing %s" % (showName[0:32], label, ", ".join(missing))
        if "".join(["Y" if missing[m] else "" for m in missing]) != "":
          libraryids.append(episodeid)
          dir = os.path.dirname(episode["file"])
          directories[dir] = dir

    if rescan: rescanDirectories("episodes", libraryids, directories)

  return episodes

def rescanDirectories(mediatype, libraryids, directories):
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
    gProgress.log("Removing %s %d from media library." % (idName, libraryid))
    REQUEST = {"method": removeMethod, "params":{idName: libraryid}}
    sendJSON(REQUEST, "1")

  for directory in directories:
    print "Rescanning directory: %s..." % directory
    REQUEST = {"method": scanMethod, "params":{"directory": directory}}
    sendJSON(REQUEST, "1", callback=jsonWaitForScanFinished, checkResult=False)

def getRowByFilename(filename):
  row = getRowByFilename_Impl(filename[8:-1], unquote=True)

# Try again, this time leave filename quoted, and with image:// prefix
  if not row:
    gProgress.log("Failed to find row by filename with the expected formatting, trying again (with prefix, quoted)")
    row = getRowByFilename_Impl(filename, unquote=False)

  return row

def getRowByFilename_Impl(filename, unquote=True):
  con = getGlobalDB()

  cur = con.cursor()

  ufilename = urllib.unquote(filename) if unquote else filename

  # If string contains unicode, replace unicode chars with % and
  # use LIKE instead of equality
  if ufilename.encode("ascii", "ignore") == ufilename.encode("utf-8"):
    SQL = "SELECT id, cachedurl from texture where url = \"%s\"" % ufilename
  else:
    gProgress.log("Removing ASCII from filename: [%s]" % ufilename)
    SQL = "SELECT id, cachedurl from texture where url like \"%s\"" % removeNonAscii(ufilename, "%")

  gProgress.log("SQL EXECUTE: [%s]" % SQL)
  row = cur.execute(SQL).fetchone()
  gProgress.log("SQL RESULT : [%s]" % (row,))

  return row if row else None

def deleteItem(id, cachedURL = None):
  con = getGlobalDB()

  cur = con.cursor()

  if not cachedURL:
    SQL = "SELECT id, cachedurl, lasthashcheck, url FROM texture WHERE id=%d" % id
    row = cur.execute(SQL).fetchone()

    if row == None:
      print "id " + gConfig.IDFORMAT % int(id) + " is not valid"
      return
    else:
      localFile = row[1]
  else:
    localFile = cachedURL

  if os.path.exists(gConfig.getFilePath(localFile)):
    os.remove(gConfig.getFilePath(localFile))
  else:
    print "WARNING: id %s, cached thumbnail file %s not found" % ((gConfig.IDFORMAT % id), localFile)

  cur.execute("DELETE FROM texture WHERE id=%d" % id)

  con.commit()

def getFileDetails(filename):

  REQUEST = {"method":"Files.GetFileDetails",
             "params":{"file": filename,
                       "properties": ["streamdetails", "lastmodified", "dateadded", "size", "mimetype", "tag", "file"]}}

  data = sendJSON(REQUEST, "1", checkResult=False)

  if "result" in data:
    return data["result"]["filedetails"]
  else:
    return None

def getDownloadURL(filename):

  REQUEST = {"method":"Files.PrepareDownload",
             "params":{"path": filename }}

  data = sendJSON(REQUEST, "1")

  if "result" in data:
    return "/%s" % data["result"]["details"]["path"]
  else:
    return None

def bumpTotals(action, imgtype):
  # Strip off any numerics, ie. "cast 01" -> "cast"
  itype = re.sub(r" [0-9]*$", "", imgtype)
  if not action in TOTALS: TOTALS[action] = {}
  if not itype in TOTALS[action]: TOTALS[action][itype ] = 0
  TOTALS[action][itype ] += 1

def loadImage(force, imgtype, filename, imagesCache, imgErrors, silent=False, retry=10):
  if filename == "": return True

  imgtype_short = imgtype.replace("tvshow.","")

  gProgress.log("Loading image with type [%s], filename [%s]" % (imgtype, filename))

  if imgtype.find("cast") != -1 and imgtype != "cast 01":
    gProgress.stdout("\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b\b")

  if filename in imagesCache:
    (o1, o2) = imagesCache[filename].split(":")
    gProgress.log("Duplicate image - previously processed as type [%s] with cachedurl [%s]" % (o1, o2))
    gProgress.stdout( "  [ * %-10s ]" % imgtype_short)
    bumpTotals("Duplicate", imgtype_short)
    return True

  if gConfig.CACHE_IGNORE_TYPES:
    for ignore in gConfig.CACHE_IGNORE_TYPES:
      if re.match(ignore, filename):
        gProgress.log("Ignored image due to rule [%s]" % ignore)
        gProgress.stdout( "  [ - %-10s ]" % imgtype_short)
        bumpTotals("Ignored", imgtype_short)
        imagesCache[filename] = ("%s:%s" % (imgtype_short, "*ignored*"))
        return True

  row = getRowByFilename(filename)

  if row: (rowid, cachedurl) = row
  else: (rowid, cachedurl) = (0, None)

  if rowid != 0 and not force:
    gProgress.log("Skipping image - cache update not required, id [%d], cachedurl [%s]" % (rowid, cachedurl))
    gProgress.stdout( "  [ . %-10s ]" % imgtype_short)
    bumpTotals("Skipped", imgtype_short)
    imagesCache[filename] = ("%s:%s" % (imgtype_short, cachedurl))
    return True

  #URL = "/image/%s" % urllib.quote(filename, "()")
  URL = getDownloadURL(filename)

  if URL != None:
    gProgress.log("Proceeding with download of URL [%s]" % URL)
    ATTEMPT = retry
    if rowid != 0 and force:
      gProgress.log("Deleting old image from cache with id [%d], cachedurl [%s]" % (rowid, cachedurl))
      deleteItem(rowid, cachedurl)
      bumpTotals("Deleted", imgtype_short)
  else:
    gProgress.log("Image not available for download - uncacheable (embedded?), or doesn't exist")
    ATTEMPT = 0
#    URL = "/image/%s" % urllib.quote(filename, "()")
#    gProgress.log("Look up failed, downloading with alternate url: type [%s], url [%s]" % (imgtype, URL))
#    ATTEMPT = 2

  while ATTEMPT > 0:
    PAYLOAD = sendWeb("GET", URL)
    if WEB_LAST_STATUS == httplib.OK:
      gProgress.log("Succesfully downloaded image with size [%d] bytes, attempts required [%d]" \
                    % (len(PAYLOAD), (retry - ATTEMPT + 1)))
      break
    ATTEMPT -= 1
    gProgress.log("Failed to download image URL [%s], status [%d], " \
                 "attempts remaining [%d]" % (URL, WEB_LAST_STATUS, ATTEMPT))

  if ATTEMPT == 0:
    if imgErrors == None: # not interested in errors, so optional load
      STATUS = "o"
    else:
      STATUS = "!"
      bumpTotals("Error", imgtype_short)
      imgErrors[imgtype_short] = URL if URL != None else filename
  else:
    STATUS = "+" if not force else "#"
    bumpTotals("Updated", imgtype_short)
    imagesCache[filename] = ("%s:%s" % (imgtype_short, cachedurl))

  gProgress.stdout( "  [ %s %-10s ]" % (STATUS, imgtype_short))

  return True if ATTEMPT != 0 else False

def processImageErrors(imgErrors):
  print
  for i in imgErrors:
    print "ERROR: Unable to load artwork [%-10s]: %s" % (i, imgErrors[i])

def sqlExtract(ACTION="NONE", search="", filter=""):
  con = getGlobalDB()

  cur = con.cursor()

  if DBVERSION >= 13:
    SQL="SELECT t.id, t.cachedurl, t.lasthashcheck, t.url, s.height, s.width, s.usecount, s.lastusetime \
         FROM texture t JOIN sizes s ON (t.id = s.idtexture) "
  else:
    SQL="SELECT t.id, t.cachedurl, t.lasthashcheck, t.url, 0 as height, 0 as width, t.usecount, t.lastusetime \
         FROM texture t "

  if (search != "" or filter != ""):
    if search != "": SQL += "WHERE t.url LIKE '%" + search + "%' ORDER BY t.id ASC"
    if filter != "": SQL += filter + " "

  IDS=""
  FSIZE=0
  FCOUNT=0

  cur.execute(SQL)

  while True:
    row = cur.fetchone()
    if row == None: break

    IDS += " " + str(row[0])
    FCOUNT+=1

    if ACTION == "NONE": dumpRow(row)
    elif not os.path.exists(gConfig.getFilePath(row[1])):
      if ACTION == "EXISTS": dumpRow(row)
    elif ACTION == "STATS":
      FSIZE += os.path.getsize(gConfig.getFilePath(row[1]))
      dumpRow(row)

  if ACTION == "STATS": print "\nFile Summary: %s files; Total size: %s Kbytes\n" % (format(FCOUNT, ",d"), format(FSIZE/1024, ",d"))

  sys.stdout.flush()

  if (search != "" or filter != ""): gProgress.errout("Matching row ids:%s\n" % IDS)

def sqlDelete(DRYRUN="Y", ids=[]):
  if DRYRUN == "Y": print "*** DRY RUN ***"

  con = getGlobalDB()

  cur = con.cursor()

  for id in ids:
    try:
      SQL="SELECT id, cachedurl, lasthashcheck, url FROM texture WHERE id=" + str(int(id))
    except ValueError:
      print "id " + id + " is not valid"
      continue

    row = cur.execute(SQL).fetchone()

    if row == None:
      print "id " + gConfig.IDFORMAT % int(id) + " is not valid"
    else:
      if os.path.exists(gConfig.getFilePath(row[1])):
        if DRYRUN == "N": os.remove(gConfig.getFilePath(row[1]))
      else:
        print "id " + gConfig.IDFORMAT % row[0] + ": Cached thumbnail file " + row[1] + " not found"

      if DRYRUN == "N":
        cur.execute("DELETE FROM texture WHERE id=" + id)

  con.commit()

def dirScan(CLEAN="N", purgenonlibraryartwork=False, libraryFiles=None, keyIsHash=False):
  con = getGlobalDB()

  cur = con.cursor()

  if DBVERSION >= 13:
    SQL="SELECT t.id, t.cachedurl, t.lasthashcheck, t.url, s.height, s.width, s.usecount, s.lastusetime \
         FROM texture t JOIN sizes s ON (t.id = s.idtexture)"
  else:
    SQL="SELECT t.id, t.cachedurl, t.lasthashcheck, t.url, 0 as height, 0 as width, t.usecount, t.lastusetime \
         FROM texture t"

  dbfiles = {}
  orphanedfiles = []
  localfiles = []

  re_search_addon = re.compile("^.*%s.xbmc%saddons%s.*" % (os.sep, os.sep, os.sep))
  re_search_mirror = re.compile("^http://mirrors.xbmc.org/addons/.*")

  gProgress.errout("Loading texture cache...")

  rows = cur.execute(SQL).fetchall()
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
      if purgenonlibraryartwork: gProgress.errout("Pruning cached images from texture cache...", newLine=True)
      else: gProgress.errout("The following items are present in the texture cache but not the media library:", newLine=True)
    FSIZE=0
    for row in localfiles:
      dumpRow(row)
      FSIZE += os.path.getsize(gConfig.getFilePath(row[1]))
      if purgenonlibraryartwork: deleteItem(row[0], row[1])
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

def getKeyFromFilename(filename):
  return removeNonAscii(urllib.unquote(re.sub("^image://(.*)/","\\1",filename)))

# The following method is extremely slow on a Raspberry Pi, and
# doesn't work well with unicode strings (returns wrong hash).
# Fortunately, using the encoded url/filename as the key (above
# function) is sufficient for our needs and also about twice
# as fast on a Pi.
def getKeyFromHash(filename):
  url = re.sub("^image://(.*)/","\\1",filename)
  url = u"" + urllib.unquote(url)
  hash = getHash(url.encode("utf-8"))
  return "%s%s%s" % (hash[0:1], os.sep, hash)

def getAllFiles(keyFunction):
  files = {}

  REQUEST = [
              {"method":"AudioLibrary.GetAlbums", "params":{"sort": {"order": "ascending", "method": "label"},
                                                            "properties":["title", "fanart", "thumbnail"]}},
              {"method":"AudioLibrary.GetArtists", "params":{"sort": {"order": "ascending", "method": "artist"},
                                                             "properties":["fanart", "thumbnail"], "albumartistsonly": False}},
              {"method":"AudioLibrary.GetSongs", "params":{"sort": {"order": "ascending", "method": "title"},
                                                           "properties":["title", "fanart", "thumbnail"]}},
              {"method":"VideoLibrary.GetMusicVideos", "params":{"sort": {"order": "ascending", "method": "title"},
                                                                 "properties":["title", "art"]}},
              {"method":"VideoLibrary.GetMovies", "params":{"sort": {"order": "ascending", "method": "title"},
                                                            "properties":["title", "cast", "art"]}},
              {"method":"VideoLibrary.GetMovieSets", "params":{"sort": {"order": "ascending", "method": "title"},
                                                               "properties":["title", "art"]}}
             ]

  for r in REQUEST:
    mediatype = re.sub(".*Library\.Get(.*)","\\1",r["method"])
    interval = 0 if mediatype == "MovieSets" else 50

    gProgress.errout("Loading: %s..." % mediatype)
    data = sendJSON(r, "libFiles")

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

  REQUEST = {"method":"VideoLibrary.GetTVShows", "params": {"sort": {"order": "ascending", "method": "title"},
                                                            "properties":["title", "cast", "art"]}}

  gProgress.errout("Loading: TVShows...")
  tvdata = sendJSON(REQUEST, "libTV")

  for tvshow in tvdata["result"]["tvshows"]:
    gProgress.errout("Parsing: TVShows [%s]..." % tvshow["title"])
    tvshowid = tvshow["tvshowid"]
    for a in tvshow["art"]:
      files[keyFunction(tvshow["art"][a])] = a
    if "cast" in tvshow:
      for c in tvshow["cast"]:
        if "thumbnail" in c:
          files[keyFunction(c["thumbnail"])] = "cast.thumbnail"

    REQUEST = {"method":"VideoLibrary.GetSeasons","params":{"tvshowid": tvshowid, "properties":["season", "art"]}}
    seasondata = sendJSON(REQUEST, "libTV")

    if "seasons" in seasondata["result"]:
      SEASON_ALL = True
      for season in seasondata["result"]["seasons"]:
        seasonid = season["season"]
        for a in season["art"]:
          if SEASON_ALL and a == "poster":
            SEASON_ALL = False
            filename = keyFunction(season["art"][a])
            files[re.sub(r"season(-specials|[ 0-9]*)(.*)\.(.*)", r"season-all\2.\3", filename)] = a
            files[re.sub(r"season(-specials|[ 0-9]*)(.*)\.(.*)", r"season-all-fanart.\3", filename)] = "fanart"
            files[re.sub(r"season(-specials|[ 0-9]*)(.*)\.(.*)", r"season-all-banner.\3", filename)] = "banner"
          files[keyFunction(season["art"][a])] = a

        REQUEST = {"method":"VideoLibrary.GetEpisodes","params":{"tvshowid": tvshowid, "season": seasonid, "properties":["cast", "art"]}}
        episodedata = sendJSON(REQUEST, "libTV")

        for episode in episodedata["result"]["episodes"]:
          episodeid = episode["episodeid"]
          for a in episode["art"]:
            files[keyFunction(episode["art"][a])] = a
          if "cast" in episode:
            for c in episode["cast"]:
              if "thumbnail" in c:
                files[keyFunction(c["thumbnail"])] = "cast.thumbnail"

  return files

def pruneCache(purgenonlibraryartwork=False):
  files = getAllFiles(keyFunction = getKeyFromFilename)
  dirScan("N", purgenonlibraryartwork, libraryFiles=files, keyIsHash=False)

def libraryGetDetailsByID(media_class, libraryid):

  if media_class == "movie":
    method = "VideoLibrary.GetMovieDetails"
    identifier = "movieid"
  elif media_class == "tvshow":
    method = "VideoLibrary.GetTVShowDetails"
    identifier = "tvshowid"
  elif media_class == "episode":
    method = "VideoLibrary.GetEpisodeDetails"
    identifier = "episodeid"
  elif media_class == "artist":
    method = "AudioLibrary.GetArtistDetails"
    identifier = "artistid"
  elif media_class == "album":
    method = "AudioLibrary.GetAlbumDetails"
    identifier = "albumid"
  elif media_class == "song":
    method = "AudioLibrary.GetSongDetails"
    identifier = "songid"
  else:
    raise Exception("invalid class for Get<type>Details: artist, album, song, movie, tvshow, episode")

  REQUEST = {"method": method,
             "params": {identifier: libraryid,
                        "properties":["streamdetails", "runtime", "resume"]}}
  print REQUEST
  data = sendJSON(REQUEST, "libMovies")
  print data

# eg. libraryModify("movie", 661, "playcount", "", "0")
# eg. libraryModify("movie", 661, "art", "clearlogo", "nfs://192.168.0.3/mnt/share/media/Video/Movies HD/Senna (2010) [BDRip]-clearlogo.png")
def libraryModify(media_class, id, item, subitem, value):
  if media_class == "movie":
    method = "VideoLibrary.SetMovieDetails"
    identifier = "movieid"
  elif media_class == "tvshow":
    method = "VideoLibrary.SetTVShowDetails"
    identifier = "tvshowid"
  elif media_class == "episode":
    method = "VideoLibrary.SetEpisodeDetails"
    identifier = "episodeid"
  elif media_class == "artist":
    method = "AudioLibrary.SetArtistDetails"
    identifier = "artistid"
  elif media_class == "album":
    method = "AudioLibrary.SetAlbumDetails"
    identifier = "albumid"
  elif media_class == "song":
    method = "AudioLibrary.SetSongDetails"
    identifier = "songid"
  else:
    raise Exception("invalid class for modification: artist, album, song, movie, tvshow, episode")

  REQUEST = {"method": method}

  if item == "art":
    newvalue = URL="image://%s/" % urllib.quote(value, "()")
  else:
    newvalue = int(value) if re.match("[0-9]*", value) else value

  if subitem == "":
    REQUEST["params"] = {identifier: id, item: newvalue}
  else:
    REQUEST["params"] = {identifier: id, item:{ subitem: newvalue }}

  print REQUEST
  data = sendJSON(REQUEST, "libMovies", timeout=10)
  print data

def usage(EXIT_CODE):

  print "Version: %s" % gConfig.VERSION
  print
  print "Usage: " + os.path.basename(__file__) + " sS <string> | xXf [sql-filter] | dD <id[id id]>] |" \
        "rR | c [class [filter]] | C class filter | jJ class [filter] | qa class [filter] | qax class [filter] | pP | config"
  print
  print "  s       Search url column for partial movie or tvshow title. Case-insensitive."
  print "  S       Same as \"s\" (search) but will validate cachedurl file exists, displaying only those that fail validation"
  print "  x       Extract details, using optional SQL filter"
  print "  X       Same as \"x\" (extract) but will validate cachedurl file exists, displaying only those that fail validation"
  print "  f       Same as x, but include file summary (file count, accumulated file size)"
  print "  d       Delete rows with matching ids, along with associated cached images"
  print "  D       Same as \"d\" (delete) but performs a DRY RUN with no db or filesystem changes"
  print "  r       Reverse search to identify \"orphaned\" Thumbnail files not present in texture cache"
  print "  R       Same as \"r\" (reverse search) but automatically deletes \"orphaned\" Thumbnail files"
  print "  c       Re-cache missing artwork. Class can be movies, tags, sets, tvshows, artists, albums or songs."
  print "  C       Re-cache artwork even when it exists. Class can be movies, tags, sets, tvshows, artists, albums or songs. Filter mandatory."
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
  ignore_types = gConfig.CACHE_IGNORE_TYPES if not gConfig.CACHE_IGNORE_TYPES else ", ".join(gConfig.CACHE_IGNORE_TYPES)

  print "Current properties (if exists, read from %s%stexturecache.cfg):" % (os.path.dirname(__file__), os.sep)
  print
  print "  sep = %s" % gConfig.FSEP
  print "  userdata = %s " % gConfig.XBMC_BASE
  print "  dbfile = %s" % gConfig.TEXTUREDB
  print "  thumbnails = %s " % gConfig.THUMBNAILS
  print "  xbmc.host = %s" % gConfig.XBMC_HOST
  print "  webserver.port = %s" % gConfig.WEB_PORT
  print "  webserver.singleshot = %s" % gConfig.WEB_SINGLESHOT
  print "  rpc.port = %s" % gConfig.RPC_PORT
  print "  extrajson.albums  = %s" % gConfig.XTRAJSON_ALBUMS
  print "  extrajson.artists = %s" % gConfig.XTRAJSON_ARTISTS
  print "  extrajson.songs   = %s" % gConfig.XTRAJSON_SONGS
  print "  extrajson.movies  = %s" % gConfig.XTRAJSON_MOVIES
  print "  extrajson.sets    = %s" % gConfig.XTRAJSON_SETS
  print "  extrajson.tvshows.tvshow = %s" % gConfig.XTRAJSON_TVSHOWS_TVSHOW
  print "  extrajson.tvshows.season = %s" % gConfig.XTRAJSON_TVSHOWS_SEASON
  print "  extrajson.tvshows.episode= %s" % gConfig.XTRAJSON_TVSHOWS_EPISODE
  print "  qaperiod = %d (added after %s)" % (gConfig.QAPERIOD, gConfig.QADATE)
  print "  qa.rating = %s" % gConfig.QA_RATING
  print "  qa.file = %s" % gConfig.QA_FILE
  print "  cache.castthumb = %s" % gConfig.CACHE_CAST_THUMB
  print "  cache.ignore.types = %s" % ignore_types
  print "  logfile = %s" % gConfig.LOGFILE
  print
  print "See http://wiki.xbmc.org/index.php?title=JSON-RPC_API/v6 for details of available audio/video fields."

  sys.exit(EXIT_CODE)

def doInit():
  global DBVERSION, MYWEB, MYSOCKET, MYDB
  global TOTALS
  global gConfig, gProgress

  DBVERSION = MYWEB = MYSOCKET = MYDB = None

  TOTALS = {}
  TOTALS["Skipped"] = {}
  TOTALS["Deleted"] = {}
  TOTALS["Duplicate"] = {}
  TOTALS["Error"] = {}
  TOTALS["Updated"] = {}
  TOTALS["Ignored"] = {}

  gConfig = MyConfiguration()

  gProgress = MyLogger()
  gProgress.DEBUG = gConfig.DEBUG
  gProgress.setLogFile(gConfig.LOGFILE)

def main(argv):

  doInit()

  if len(argv) == 0: usage(1)

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
    libraryStats("albums/artists/movies/sets/tvshows")
  elif argv[0] == "c" and len(argv) == 2:
    libraryQuery("cache", argv[1])
    libraryStats(argv[1])
  elif argv[0] == "c" and len(argv) == 3:
    libraryQuery("cache", argv[1], argv[2])
    libraryStats(argv[1], argv[2])
  elif argv[0] == "C" and len(argv) == 3:
    libraryQuery("cache", argv[1], argv[2], force=True)
    libraryStats(argv[1], argv[2])
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
    sqlDelete("N", argv[1:])
  elif argv[0] == "D" and len(argv) >= 2:
    sqlDelete("Y", argv[1:])
  elif argv[0] == "r":
    dirScan("N")
  elif argv[0] == "R":
    dirScan("Y")
  elif argv[0] == "p" and len(argv) == 1:
    pruneCache(purgenonlibraryartwork=False)
  elif argv[0] == "P" and len(argv) == 1:
    pruneCache(purgenonlibraryartwork=True)
  elif argv[0] == "version":
    print "Version: v%s" % gConfig.VERSION
  elif argv[0] == "config":
    showConfig(1)
  else:
    usage(1)

  sys.exit(0)

try:
  main(sys.argv[1:])
except (KeyboardInterrupt, SystemExit):
  if MYWEB: MYWEB.close()
  if MYSOCKET: MYSOCKET.close()
  if MYDB: MYDB.close()
