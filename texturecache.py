#!/usr/bin/env python
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
#  See built-in help (run script without parameters), or the README file
#  on github for more details.
#
################################################################################

import os, sys, platform, re, datetime, time
import socket, base64, hashlib
import threading, random
import errno, codecs
import subprocess

try:
  import json
except:
  import simplejson as json

if sys.version_info >= (3, 0):
  import configparser as ConfigParser
  import io as StringIO
  import http.client as httplib
  import urllib.request as urllib2
  import queue as Queue
  basestring = (str, bytes)
else:
  import ConfigParser, StringIO, httplib, urllib2, Queue

#
# Config class. Will be a global object.
#
class MyConfiguration(object):
  def __init__( self, argv ):

    self.VERSION = "1.2.9"

    self.GITHUB = "https://raw.github.com/MilhouseVH/texturecache.py/master"
    self.ANALYTICS = "http://goo.gl/BjH6Lj"

    self.DEBUG = True if os.environ.get("PYTHONDEBUG", "n").lower()=="y" else False

    self.GLOBAL_SECTION = "global"
    self.THIS_SECTION = self.GLOBAL_SECTION
    self.CONFIG_NAME = "texturecache.cfg"

    self.HAS_PVR = False

    # These features become available with the respective API version
    self.JSON_VER_CAPABILITIES = {"setresume":    (6,  2, 0),
                                  "texturedb":    (6,  9, 0),
                                  "removeart":    (6,  9, 1),
                                  "setseason":    (6, 10, 0),
                                  "setmovieset":  (6, 12, 0),
                                  "filternullval":(6, 13, 1)}

    self.SetJSONVersion(0, 0, 0)

    namedSection = False
    serial_urls = "assets\.fanart\.tv"
    embedded_urls = "^video, ^music"

    config = ConfigParser.SafeConfigParser()
    self.config = config

    #Use @section argument if passed on command line
    #Use list(argv) so that a copy of argv is iterated over, making argv.remove() safe to use.
    for arg in list(argv):
      if re.search("^[ ]*@section[ ]*=", arg):
        self.THIS_SECTION = arg.split("=", 1)[1].strip()
        namedSection = True
        argv.remove(arg)

    #Use @config if passed on command line
    for arg in list(argv):
      if re.search("^[ ]*@config[ ]*=", arg):
        self.CONFIG_NAME = arg.split("=", 1)[1].strip()
        argv.remove(arg)

    # Use the default or user specified config filename.
    # If it doesn't exist and is a relative filename, try and find a config
    # file in the current directory, otherwise look in same directory as script itself.
    self.FILENAME = os.path.expanduser(self.CONFIG_NAME)
    if not os.path.exists(self.FILENAME) and not os.path.isabs(self.FILENAME):
      self.FILENAME = "%s%s%s" % (os.getcwd(), os.sep, self.CONFIG_NAME)
      if not os.path.exists(self.FILENAME):
        self.FILENAME = "%s%s%s" % (os.path.dirname(os.path.abspath(__file__)), os.sep, self.CONFIG_NAME)

    cfg = StringIO.StringIO()
    cfg.write("[%s]\n" % self.GLOBAL_SECTION)

    if os.path.exists(self.FILENAME):
      cfg.write(open(self.FILENAME, "r").read())
      cfg.write("\n")

    cfg.seek(0, os.SEEK_SET)
    config.readfp(cfg)

    # If a specific section is not passed on the command line, check the config
    # to see if there is a default section property, and if not then default to
    # the global default section.
    if not namedSection:
      self.THIS_SECTION = self.getValue(config, "section", self.GLOBAL_SECTION)

    # If the section is not present, bail
    if not config.has_section(self.THIS_SECTION):
      print("Section [%s] is not a valid section in this config file" % self.THIS_SECTION)
      sys.exit(2)

    #Add any command line settings - eg. @xbmc.host=192.168.0.8 - to the named section.
    for arg in list(argv):
      arg_match = re.match("^[ ]*@([^ ]+)[ ]*=(.*)", arg)
      if arg_match and len(arg_match.groups()) == 2:
        config.set(self.THIS_SECTION, arg_match.group(1).strip(), arg_match.group(2).strip())
        argv.remove(arg)

    if not self.DEBUG and self.getBoolean(config, "debug", ""):
      self.DEBUG = self.getBoolean(config, "debug", "no")

    self.IDFORMAT = self.getValue(config, "format", "%06d")
    self.FSEP = self.getValue(config, "sep", "|")

    _atv2_path = "/User/Library/Preferences/XBMC/userdata"
    _macosx_path = "~/Library/Application Support/XBMC/userdata"
    _android1_path = "Android/data/org.xbmc.xbmc/files/.xbmc/userdata"
    _android2_path = "/sdcard/%s" % _android1_path

    UD_SYS_DEFAULT = "~/.xbmc/userdata"

    if sys.platform == "win32":
      UD_SYS_DEFAULT = "%s\\XBMC\\userdata" % os.environ["appdata"]
    elif sys.platform == "darwin" and os.path.exists(_atv2_path):
      UD_SYS_DEFAULT = _atv2_path
    elif sys.platform == "darwin" and os.path.exists(os.path.expanduser(_macosx_path)):
      UD_SYS_DEFAULT = _macosx_path
    else:
      if os.path.exists(_android2_path):
        UD_SYS_DEFAULT = _android2_path
      elif os.path.exists(_android1_path):
        UD_SYS_DEFAULT = _android1_path

    self.XBMC_BASE = os.path.expanduser(self.getValue(config, "userdata", UD_SYS_DEFAULT))
    self.TEXTUREDB = self.getValue(config, "dbfile", "Database/Textures13.db")
    self.THUMBNAILS = self.getValue(config, "thumbnails", "Thumbnails")

    self.DBJSON = self.getValue(config, "dbjson", "auto")
    self.USEJSONDB = self.getBoolean(config, "dbjson", "yes")

    if self.XBMC_BASE[-1:] not in ["/", "\\"]: self.XBMC_BASE += "/"
    if self.THUMBNAILS[-1:] not in ["/", "\\"]: self.THUMBNAILS += "/"

    self.XBMC_BASE = self.XBMC_BASE.replace("/", os.sep)
    self.TEXTUREDB = self.TEXTUREDB.replace("/", os.sep)
    self.THUMBNAILS = self.THUMBNAILS.replace("/", os.sep)

    self.XBMC_HOST = self.getValue(config, "xbmc.host", "localhost")
    self.WEB_PORT = self.getValue(config, "webserver.port", "8080")
    self.RPC_PORT = self.getValue(config, "rpc.port", "9090")
    self.WEB_SINGLESHOT = self.getBoolean(config, "webserver.singleshot", "no")
    web_user = self.getValue(config, "webserver.username", "")
    web_pass = self.getValue(config, "webserver.password", "")

    self.WEB_CONNECTTIMEOUT = self.getValue(config, "webserver.ctimeout", 0.5, allowundefined=True)
    if self.WEB_CONNECTTIMEOUT: self.WEB_CONNECTTIMEOUT = float(self.WEB_CONNECTTIMEOUT)

    self.RPC_CONNECTTIMEOUT = self.getValue(config, "rpc.ctimeout", 0.5, allowundefined=True)
    if self.RPC_CONNECTTIMEOUT: self.RPC_CONNECTTIMEOUT = float(self.RPC_CONNECTTIMEOUT)

    if (web_user and web_pass):
      token = "%s:%s" % (web_user, web_pass)
      if sys.version_info >= (3, 0):
        self.WEB_AUTH_TOKEN = base64.encodestring(bytes(token, "utf-8")).decode()
      else:
        self.WEB_AUTH_TOKEN = base64.encodestring(token)
      self.WEB_AUTH_TOKEN = self.WEB_AUTH_TOKEN.replace("\n", "")
    else:
      self.WEB_AUTH_TOKEN = None

    self.DOWNLOAD_THREADS_DEFAULT = int(self.getValue(config, "download.threads", "2"))
    self.DOWNLOAD_RETRY = int(self.getValue(config, "download.retry", "3"))

    # It seems that Files.Preparedownload is sufficient to populate the texture cache
    # so there is no need to actually download the artwork.
    # v0.8.8: Leave enabled for now, may only be sufficient in recent builds.
    self.DOWNLOAD_PAYLOAD = self.getBoolean(config, "download.payload","yes")

    self.DOWNLOAD_THREADS = {}
    for x in ["addons", "albums", "artists", "songs", "movies", "sets", "tags", "tvshows", "pvr.tv", "pvr.radio"]:
      temp = int(self.getValue(config, "download.threads.%s" % x, self.DOWNLOAD_THREADS_DEFAULT))
      self.DOWNLOAD_THREADS["download.threads.%s" % x] = temp

    self.SINGLETHREAD_URLS = self.getPatternFromList(config, "singlethread.urls", serial_urls)

    self.XTRAJSON = {}
    self.QA_FIELDS = {}

    self.QA_FIELDS["qa.art.addons"] = "thumbnail"
    self.QA_FIELDS["qa.art.agenres"] = "thumbnail"
    self.QA_FIELDS["qa.art.vgenres"] = "thumbnail"

    self.QA_FIELDS["qa.art.artists"] = "fanart, thumbnail"
    self.QA_FIELDS["qa.art.albums"] = "fanart, thumbnail"
    self.QA_FIELDS["qa.art.songs"] = "fanart, thumbnail"

    self.QA_FIELDS["qa.blank.movies"] = "plot, mpaa"
    self.QA_FIELDS["qa.art.movies"] = "fanart, poster"

    self.QA_FIELDS["qa.art.sets"] = "fanart, poster"

    self.QA_FIELDS["qa.blank.tvshows.tvshow"] = "plot"
    self.QA_FIELDS["qa.blank.tvshows.episode"] = "plot"
    self.QA_FIELDS["qa.art.tvshows.tvshow"] = "fanart, banner, poster"
    self.QA_FIELDS["qa.art.tvshows.season"] = "poster"
    self.QA_FIELDS["qa.art.tvshows.episode"] = "thumb"

    self.QA_FIELDS["qa.art.pvr.tv.channel"] = "thumbnail"
    self.QA_FIELDS["qa.art.pvr.radio.channel"] = "thumbnail"

    for x in ["addons",
              "albums", "artists", "songs",
              "movies", "sets",
              "tvshows.tvshow", "tvshows.season", "tvshows.episode",
              "pvr.tv", "pvr.radio", "pvr.tv.channel", "pvr.radio.channel",
              "agenres", "vgenres"]:
      key = "extrajson.%s" % x
      temp = self.getValue(config, key, "")
      self.XTRAJSON[key] = temp if temp != "" else None

      for f in ["zero", "blank", "art"]:
        key = "qa.%s.%s" % (f, x)
        try:
          temp = self.getValue(config, key, None)
        except:
          temp = None
        if temp and temp.startswith("+"):
          temp = temp[1:]
          temp2 = self.QA_FIELDS.get(key, "")
          if temp2 != "": temp2 = "%s, " % temp2
          temp = "%s%s " % (temp2, temp.strip())
          self.QA_FIELDS[key] = temp
        else:
          self.QA_FIELDS[key] = temp if temp != None else self.QA_FIELDS.get(key, None)

    self.QAPERIOD = int(self.getValue(config, "qaperiod", "30"))
    adate = datetime.date.today() - datetime.timedelta(days=self.QAPERIOD)
    self.QADATE = adate.strftime("%Y-%m-%d")

    self.QA_FILE = self.getBoolean(config, "qafile", "no")
    self.QA_FAIL_TYPES = self.getPatternFromList(config, "qa.fail.urls", embedded_urls)
    self.QA_WARN_TYPES = self.getPatternFromList(config, "qa.warn.urls", "")

    self.CACHE_CAST_THUMB = self.getBoolean(config, "cache.castthumb", "no")

    yn = "yes" if self.getBoolean(config, "cache.extra", "no") else "no"
    self.CACHE_EXTRA_FANART = self.getBoolean(config, "cache.extrafanart", yn)
    self.CACHE_EXTRA_THUMBS = self.getBoolean(config, "cache.extrathumbs", yn)
    # http://wiki.xbmc.org/index.php?title=Add-on:VideoExtras
    self.CACHE_VIDEO_EXTRAS = self.getBoolean(config, "cache.videoextras", yn)
    self.CACHE_EXTRA = (self.CACHE_EXTRA_FANART or self.CACHE_EXTRA_THUMBS or self.CACHE_VIDEO_EXTRAS)

    self.LOGFILE = self.getValue(config, "logfile", "")
    self.LOGVERBOSE = self.getBoolean(config, "logfile.verbose", "yes")

    self.CACHE_ARTWORK = self.getSimpleList(config, "cache.artwork", "")
    self.CACHE_IGNORE_TYPES = self.getPatternFromList(config, "cache.ignore.types", embedded_urls)
    self.PRUNE_RETAIN_TYPES = self.getPatternFromList(config, "prune.retain.types", "")

    # Fix patterns as we now strip image:// from the urls, so we need to remove
    # this prefix from any legacy patterns that may be specified by the user
    for index, r in enumerate(self.CACHE_IGNORE_TYPES):
      self.CACHE_IGNORE_TYPES[index] = re.compile(re.sub("^\^image://", "^", r.pattern))
    for index, r in enumerate(self.PRUNE_RETAIN_TYPES):
      self.PRUNE_RETAIN_TYPES[index] = re.compile(re.sub("^\^image://", "^", r.pattern))

    self.PRUNE_RETAIN_PREVIEWS = self.getBoolean(config, "prune.retain.previews", "yes")

    self.PICTURE_FILETYPES = [".jpg", ".jpeg", ".png", ".tbn", ".gif", ".tif", ".tiff",
                               ".raw", ".dng", ".crw", ".cr2", ".mdc", ".mrw", ".orf"]
    for x in self.getSimpleList(config, "picture.filetypes", ""):
      x = x.lower()
      if not x.startswith("."):
        x = ".%s" % x
      if x not in self.PICTURE_FILETYPES:
        self.PICTURE_FILETYPES.append(x)

    self.RECACHEALL = self.getBoolean(config, "allow.recacheall","no")
    self.CHECKUPDATE = self.getBoolean(config, "checkupdate", "yes")
    self.AUTOUPDATE = self.getBoolean(config, "autoupdate", "yes")

    self.LASTRUNFILE = self.getValue(config, "lastrunfile", "")
    self.LASTRUNFILE_DATETIME = None
    if self.LASTRUNFILE and os.path.exists(self.LASTRUNFILE):
        temp = datetime.datetime.fromtimestamp(os.path.getmtime(self.LASTRUNFILE))
        self.LASTRUNFILE_DATETIME = temp.strftime("%Y-%m-%d %H:%M:%S")

    self.ORPHAN_LIMIT_CHECK = self.getBoolean(config, "orphan.limit.check", "yes")

    self.NONMEDIA_FILETYPES = []
    for x in self.getSimpleList(config, "nonmedia.filetypes", ""):
      x = x.lower()
      if not x.startswith("."):
        x = ".%s" % x
      if x not in self.NONMEDIA_FILETYPES:
        self.NONMEDIA_FILETYPES.append(x)

    self.CACHE_HIDEALLITEMS = self.getBoolean(config, "cache.hideallitems", "no")

    self.WATCHEDOVERWRITE = self.getBoolean(config, "watched.overwrite", "no")

    self.MAC_ADDRESS = self.getValue(config, "network.mac", "")

    self.ADD_SET_MEMBERS = self.getBoolean(config, "setmembers", "yes")

    self.PURGE_MIN_LEN = int(self.getValue(config, "purge.minlen", "5"))

    self.IMDB_FIELDS = "rating, votes"
    temp = self.getValue(config, "imdb.fields", "")
    if temp:
      if temp.startswith("+"):
        temp = temp[1:]
        temp2 = self.IMDB_FIELDS
        if temp2 != "": temp2 = "%s, " % temp2
        temp = "%s%s " % (temp2, temp.strip())
      self.IMDB_FIELDS = temp

    self.BIN_TVSERVICE = self.getValue(config, "bin.tvservice", "/usr/bin/tvservice")
    self.FORCE_HOTPLUG = self.getBoolean(config, "hdmi.force.hotplug", "no")

  def SetJSONVersion(self, major, minor, patch):
    self.JSON_VER = (major, minor, patch)
    self.JSON_VER_STR = "v%d.%d.%d" % (major, minor, patch)

    # Allow restoration of resume points with Gotham+
    self.JSON_HAS_SETRESUME = self.HasJSONCapability("setresume")

    # Allow null artwork items in set
    self.JSON_HAS_SETNULL = self.HasJSONCapability("removeart")

    # JSON API supports VideoLibrary.SetSeasonDetails and VideoLibrary.SetMovieSetDetails
    self.JSON_HAS_SETSEASON = self.HasJSONCapability("setseason")
    self.JSON_HAS_SETMOVIESET = self.HasJSONCapability("setmovieset")

    # JSON API has support for Textures database access
    self.JSON_HAS_TEXTUREDB = self.HasJSONCapability("texturedb")

    # Filter is/isnot operator broken for empty string value (""), use only if API is fixed
    self.JSON_HAS_FILTERNULLVALUE = self.HasJSONCapability("filternullval")

  def HasJSONCapability(self, feature):
    if feature not in self.JSON_VER_CAPABILITIES:
      raise ValueError("Invalid JSON capability request for feature [%s]" % feature)

    if self.JSON_VER_CAPABILITIES[feature] == (0, 0, 0):
      return False
    else:
      return self.JSON_VER >= self.JSON_VER_CAPABILITIES[feature]

  # Call this method once we have worked out if JSON or SQLite will be
  # used to access textures database
  def postConfig(self):
    # Pre-delete artwork if the database filesystem is mounted, as deleting artwork within threads
    # will result in database locks and inability of the remote client to query its own
    # database, resulting in invalid responses.
    if self.getValue(self.config, "download.predelete", "auto") == "auto":
      if self.USEJSONDB:
        self.DOWNLOAD_PREDELETE = False
      else:
        if self.getDBPath().startswith("/mnt") or self.getDBPath().startswith("\\\\"):
          ISMOUNT = True
        else:
          ISMOUNT = False
        self.DOWNLOAD_PREDELETE = (os.path.ismount(self.getDBPath()) or ISMOUNT)
    else:
      self.DOWNLOAD_PREDELETE = self.getBoolean(self.config, "download.predelete","no")

  def getValue(self, config, aKey, default=None, allowundefined=False):
    value = None

    try:
      value = config.get(self.THIS_SECTION, aKey)
      # If value being undefined is valid, return None for undefined values
      if not value and allowundefined: return None
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
      if self.THIS_SECTION != self.GLOBAL_SECTION:
        try:
          value = config.get(self.GLOBAL_SECTION, aKey)
          # If value being undefined is valid, return None for undefined values
          if not value and allowundefined: return None
        except ConfigParser.NoOptionError:
          if default == None and not allowNone:
            raise ConfigParser.NoOptionError(aKey, "%s (or global section)" % self.THIS_SECTION)
      else:
        if default == None and not allowNone:
          raise ConfigParser.NoOptionError(aKey, self.GLOBAL_SECTION)

    return value if value else default

  # default value will be used if key is present, but without a value
  def getBoolean(self, config, aKey, default="no"):
    temp = self.getValue(config, aKey, default).lower()
    return temp in ["yes", "true"]

  def getSimpleList(self, config, aKey, default=""):
    aStr = self.getValue(config, aKey, default)

    newlist = []

    if aStr:
      for item in [x.strip() for x in aStr.split(",") if x]:
        if item:
          newlist.append(item)

    return newlist

  def getPatternFromList(self, config, aKey, default=""):
    aList = self.getValue(config, aKey, default)

    if aList and aList.startswith("+"):
      aList = aList[1:]
      if default and default != "" and aList != "":
        aList = "%s,%s " % (default, aList.strip())

    return [re.compile(x.strip()) for x in aList.split(",") if x] if aList else []

  def getListFromPattern(self, aPattern):
    if not aPattern: return None
    t = []
    for r in aPattern: t.append(r.pattern)
    return ", ".join(t)

  def getQAFields(self, qatype, mediatype, stripModifier=True):
    if mediatype in ["tvshows", "seasons", "episodes"]:
      mediatype = "tvshows.%s" % mediatype[:-1]
    elif mediatype in ["pvr.tv", "pvr.radio", "pvr.channel"]:
      mediatype = "pvr.%s" % mediatype.split(".")[1]
    elif mediatype == "tags":
      mediatype = "movies"

    key = "qa.%s.%s" % (qatype, mediatype)

    aStr = self.QA_FIELDS.get(key, None)

    newlist = []

    if aStr:
      for item in [item.strip() for item in aStr.split(",")]:
        if item != "":
          if stripModifier and item.startswith("?"):
            newlist.append(item[1:])
          else:
            newlist.append(item)

    return newlist

  def getFilePath( self, filename = "" ):
    if os.path.isabs(self.THUMBNAILS):
      return os.path.join(self.THUMBNAILS, filename)
    else:
      return os.path.join(self.XBMC_BASE, self.THUMBNAILS, filename)

  def getDBPath( self ):
    if os.path.isabs(self.TEXTUREDB):
      return self.TEXTUREDB
    else:
      return os.path.join(self.XBMC_BASE, self.TEXTUREDB)

  def NoneIsBlank(self, x):
    return x if x else ""

  def BooleanIsYesNo(self, x):
    return "yes" if x else "no"

  def dumpJSONCapabilities(self):
    if self.JSON_VER == (0, 0, 0):
      return "Unknown, JSON version not acquired"
    else:
      caps = {}
      for feature in self.JSON_VER_CAPABILITIES:
        caps[feature] = self.HasJSONCapability(feature)
      return caps

  def dumpMemberVariables(self):
    mv = {}
    for key in self.__dict__.keys():
      if key != "config":
        value = self.__dict__[key]
        if type(value) is list:
          newlist = []
          for v in value:
            try:
              newlist.append(v.pattern)
            except:
              newlist.append(v)
          value = newlist
        mv[key] = value

    return json.dumps(mv, indent=2, sort_keys=True)

  def showConfig(self):
    print("Current properties (if exists, read from %s):" % (self.FILENAME))
    print("")
    print("  sep = %s" % self.FSEP)
    print("  userdata = %s " % self.XBMC_BASE)
    print("  dbfile = %s" % self.TEXTUREDB)
    print("  thumbnails = %s " % self.THUMBNAILS)
    print("  xbmc.host = %s" % self.XBMC_HOST)
    print("  webserver.port = %s" % self.WEB_PORT)
    print("  webserver.ctimeout = %s" % self.WEB_CONNECTTIMEOUT)
    print("  rpc.port = %s" % self.RPC_PORT)
    print("  rpc.ctimeout = %s" % self.RPC_CONNECTTIMEOUT)
    print("  download.predelete = %s" % self.BooleanIsYesNo(self.DOWNLOAD_PREDELETE))
    print("  download.payload = %s" % self.BooleanIsYesNo(self.DOWNLOAD_PAYLOAD))
    print("  download.retry = %d" % self.DOWNLOAD_RETRY)
    print("  download.threads = %d" % self.DOWNLOAD_THREADS_DEFAULT)
    if self.DOWNLOAD_THREADS != {}:
      for dt in self.DOWNLOAD_THREADS:
        if self.DOWNLOAD_THREADS[dt] != self.DOWNLOAD_THREADS_DEFAULT:
          print("  %s = %d" % (dt, self.DOWNLOAD_THREADS[dt]))
    print("  singlethread.urls = %s" % self.NoneIsBlank(self.getListFromPattern(self.SINGLETHREAD_URLS)))
    print("  extrajson.addons  = %s" % self.NoneIsBlank(self.XTRAJSON["extrajson.addons"]))
    print("  extrajson.agenres = %s" % self.NoneIsBlank(self.XTRAJSON["extrajson.agenres"]))
    print("  extrajson.vgenres = %s" % self.NoneIsBlank(self.XTRAJSON["extrajson.vgenres"]))
    print("  extrajson.albums  = %s" % self.NoneIsBlank(self.XTRAJSON["extrajson.albums"]))
    print("  extrajson.artists = %s" % self.NoneIsBlank(self.XTRAJSON["extrajson.artists"]))
    print("  extrajson.songs   = %s" % self.NoneIsBlank(self.XTRAJSON["extrajson.songs"]))
    print("  extrajson.movies  = %s" % self.NoneIsBlank(self.XTRAJSON["extrajson.movies"]))
    print("  extrajson.sets    = %s" % self.NoneIsBlank(self.XTRAJSON["extrajson.sets"]))
    print("  extrajson.tvshows.tvshow = %s" % self.NoneIsBlank(self.XTRAJSON["extrajson.tvshows.tvshow"]))
    print("  extrajson.tvshows.season = %s" % self.NoneIsBlank(self.XTRAJSON["extrajson.tvshows.season"]))
    print("  extrajson.tvshows.episode= %s" % self.NoneIsBlank(self.XTRAJSON["extrajson.tvshows.episode"]))
    print("  setmembers = %s" % self.BooleanIsYesNo(self.ADD_SET_MEMBERS))
    print("  qaperiod = %d (added after %s)" % (self.QAPERIOD, self.QADATE))
    print("  qafile = %s" % self.BooleanIsYesNo(self.QA_FILE))
    print("  qa.fail.urls = %s" % self.NoneIsBlank(self.getListFromPattern(self.QA_FAIL_TYPES)))
    print("  qa.warn.urls = %s" % self.NoneIsBlank(self.getListFromPattern(self.QA_WARN_TYPES)))

    for k in sorted(self.QA_FIELDS):
      print("  %s = %s" % (k, self.NoneIsBlank(self.QA_FIELDS[k])))

    print("  cache.castthumb = %s" % self.BooleanIsYesNo(self.CACHE_CAST_THUMB))
    print("  cache.hideallitems = %s" % self.BooleanIsYesNo(self.CACHE_HIDEALLITEMS))
    print("  cache.artwork = %s" % self.NoneIsBlank(", ".join(self.CACHE_ARTWORK)))
    print("  cache.ignore.types = %s" % self.NoneIsBlank(self.getListFromPattern(self.CACHE_IGNORE_TYPES)))
    print("  cache.extrafanart = %s" % self.BooleanIsYesNo(self.CACHE_EXTRA_FANART))
    print("  cache.extrathumbs = %s" % self.BooleanIsYesNo(self.CACHE_EXTRA_THUMBS))
    print("  cache.videoextras = %s" % self.BooleanIsYesNo(self.CACHE_VIDEO_EXTRAS))
    print("  prune.retain.types = %s" % self.NoneIsBlank(self.getListFromPattern(self.PRUNE_RETAIN_TYPES)))
    print("  prune.retain.previews = %s" % self.BooleanIsYesNo(self.PRUNE_RETAIN_PREVIEWS))
    print("  picture.filetypes = %s" % self.NoneIsBlank(", ".join(self.PICTURE_FILETYPES)))
    print("  logfile = %s" % self.NoneIsBlank(self.LOGFILE))
    print("  logfile.verbose = %s" % self.BooleanIsYesNo(self.LOGVERBOSE))
    print("  checkupdate = %s" % self.BooleanIsYesNo(self.CHECKUPDATE))
    print("  autoupdate = %s" % self.BooleanIsYesNo(self.AUTOUPDATE))
    if self.RECACHEALL:
      print("  allow.recacheall = yes")
    temp = " (%s)" % self.LASTRUNFILE_DATETIME if self.LASTRUNFILE and self.LASTRUNFILE_DATETIME else ""
    print("  lastrunfile = %s%s" % (self.NoneIsBlank(self.LASTRUNFILE), temp))
    print("  orphan.limit.check = %s" % self.BooleanIsYesNo(self.ORPHAN_LIMIT_CHECK))
    print("  purge.minlen = %s" % self.PURGE_MIN_LEN)
    print("  nonmedia.filetypes = %s" % self.NoneIsBlank(", ".join(self.NONMEDIA_FILETYPES)))
    print("  watched.overwrite = %s" % self.BooleanIsYesNo(self.WATCHEDOVERWRITE))
    print("  network.mac = %s" % self.NoneIsBlank(self.MAC_ADDRESS))
    print("  imdb.fields = %s" % self.NoneIsBlank(self.IMDB_FIELDS))
    print("  bin.tvservice = %s" % self.NoneIsBlank(self.BIN_TVSERVICE))
    print("  hdmi.force.hotplug = %s" % self.BooleanIsYesNo(self.FORCE_HOTPLUG))

    print("")
    print("See http://wiki.xbmc.org/index.php?title=JSON-RPC_API/v6 for details of available audio/video fields.")

#
# Very simple logging class. Will be a global object, also passed to threads
# hence the Lock() methods..
#
# Writes progress information to stderr so that
# information can still be grep'ed easily (stdout).
#
# Prefix logfilename with + to enable flushing after each write.
#
class MyLogger():
  def __init__( self ):
    self.lastlen = 0
    self.now = 0
    self.LOGGING = False
    self.LOGFILE = None
    self.LOGFLUSH = False
    self.DEBUG = False
    self.VERBOSE = False

    self.ISATTY = sys.stdout.isatty()

    #Ensure stdout/stderr use utf-8 encoding...
    if sys.version_info >= (3, 1):
      sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
      sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    else:
      sys.stdout = codecs.getwriter("utf-8")(sys.stdout)
      sys.stderr = codecs.getwriter("utf-8")(sys.stderr)

  def __del__( self ):
    if self.LOGFILE: self.LOGFILE.close()

  def setLogFile(self, filename):
    with threading.Lock():
      if filename:
        self.LOGFLUSH = filename.startswith("+")
        if self.LOGFLUSH: filename = filename[1:]
        try:
          self.LOGFILE = codecs.open(filename, "w", encoding="utf-8")
          self.LOGGING = True
        except:
          raise IOError("Unable to open logfile for writing!")
      else:
        self.LOGGING = False
        if self.LOGFILE:
          self.LOGFILE.close()
          self.LOGFILE = None

  def progress(self, data, every=0, finalItem = False, newLine=False, noBlank=False):
    with threading.Lock():
      if every != 0 and not finalItem:
        self.now += 1
        if self.now != 1:
          if self.now <= every: return
          else: self.reset(initialValue=1)
      else:
        self.reset(initialValue=0)

      udata = MyUtility.toUnicode(data)
      ulen = len(data)
      spaces = self.lastlen - ulen
      self.lastlen = ulen

      if spaces > 0 and not noBlank:
        sys.stderr.write("%-s%*s\r" % (udata, spaces, " "))
      else:
        sys.stderr.write("%-s\r" % udata)
      if newLine:
        sys.stderr.write("\n")
        self.lastlen = 0
      sys.stderr.flush()

  def reset(self, initialValue=0):
    self.now = initialValue

  def out(self, data, newLine=False, log=False):
    with threading.Lock():
      udata = MyUtility.toUnicode(data)
      ulen = len(data)
      spaces = self.lastlen - ulen
      self.lastlen = ulen if udata.rfind("\n") == -1 else 0

      NL = "\n" if newLine else ""

      if spaces > 0:
        sys.stdout.write("%-s%*s%s" % (udata, spaces, " ", NL))
      else:
        sys.stdout.write("%-s%s" % (udata, NL))

      if newLine:
        self.lastlen = 0

      try:
        sys.stdout.flush()
      except IOError as e:
        if e.errno == errno.EPIPE:
          pass
        else:
          raise

    if log: self.log(data)

  def debug(self, data, jsonrequest=None):
    with threading.Lock():
      if self.DEBUG:
        if self.ISATTY:
          self.out("%s: [%s] %s" % (datetime.datetime.now(), self.OPTION, data), newLine=True)
        else:
          self.out("[%s] %s" % (self.OPTION, data), newLine=True)
        if self.LOGGING:
          self.log("[DEBUG] %s" % data, jsonrequest=jsonrequest)

  def log(self, data, jsonrequest = None, maxLen=0):
    if self.LOGGING:
      with threading.Lock():
        udata = MyUtility.toUnicode(data)

        t = threading.current_thread().name
        if jsonrequest == None:
          d = udata
          if maxLen != 0 and not self.VERBOSE and len(d) > maxLen:
            d = "%s (truncated)" % d[:maxLen]
          self.LOGFILE.write("%s:%-10s: %s\n" % (datetime.datetime.now(), t, d))
        else:
          d = json.dumps(jsonrequest, ensure_ascii=True)
          if maxLen != 0 and len(d) > maxLen:
            d = "%s (truncated)" % d[:maxLen]
          self.LOGFILE.write("%s:%-10s: %s [%s]\n" % (datetime.datetime.now(), t, udata, d))
        if self.DEBUG or self.LOGFLUSH: self.LOGFILE.flush()

  # Use this method for large unicode data - tries to minimize
  # creation of additional temporary buffers through concatenation.
  def log2(self, prefix, udata, jsonrequest = None, maxLen=0):
    if self.LOGGING:
      with threading.Lock():
        t = threading.current_thread().name
        self.LOGFILE.write("%s:%-10s: %s" % (datetime.datetime.now(), t, prefix))

        if jsonrequest == None:
          if maxLen != 0 and not self.VERBOSE and len(udata) > maxLen:
            d = "%s (truncated)" % udata[:maxLen]
            self.LOGFILE.write(d)
          else:
            self.LOGFILE.write(udata)
        else:
          d = json.dumps(jsonrequest, ensure_ascii=True)
          if maxLen != 0 and len(d) > maxLen:
            d = "%s (truncated)" % d[:maxLen]
          self.LOGFILE.write("[")
          self.LOGFILE.write(d)
          self.LOGFILE.write("]")

        self.LOGFILE.write("\n")
        if self.DEBUG or self.LOGFLUSH: self.LOGFILE.flush()

  def err(self, data, newLine=False, log=False):
    with threading.Lock():
      udata = MyUtility.toUnicode(data)
      sys.stderr.write("%-s" % udata)
      if newLine:
        sys.stderr.write("\n")
      sys.stderr.flush()
    if log: self.log(data)

#
# Image loader thread class.
#
class MyImageLoader(threading.Thread):
  def __init__(self, isSingle, work_queue, other_queue, error_queue, maxItems,
                config, logger, totals, force=False, retry=0):
    threading.Thread.__init__(self)

    self.isSingle = isSingle

    self.work_queue = work_queue
    self.other_queue = other_queue
    self.error_queue = error_queue
    self.maxItems = maxItems

    self.config = config
    self.logger = logger
    self.database = MyDB(config, logger)
    self.json = MyJSONComms(config, logger)
    self.totals = totals

    self.force = force
    self.retry = retry

    self.totals.init(self.name)

  def showProgress(self, ignoreSelf=False):
    tac = threading.activeCount() - 1
    if ignoreSelf: tac = tac - 1

    if self.isSingle:
      swqs = self.work_queue.qsize()
      mwqs = self.other_queue.qsize()
    else:
      swqs = self.other_queue.qsize()
      mwqs = self.work_queue.qsize()
    wqs = swqs + mwqs
    eqs = self.error_queue.qsize()
    self.logger.progress("Caching artwork: %d item%s remaining of %d (qs: %d, qm: %d), %d error%s, %d thread%s active%s" % \
                      (wqs, "s"[wqs==1:],
                       self.maxItems, swqs, mwqs,
                       eqs, "s"[eqs==1:],
                       tac, "s"[tac==1:],
                       self.totals.getPerformance(wqs)))

  def run(self):
    while not stopped.is_set():
      self.showProgress()

      item = self.work_queue.get()

      if not self.loadImage(item) and not item.missingOK:
        self.error_queue.put(item)

      self.work_queue.task_done()

      if self.work_queue.empty():
        break

    self.showProgress(ignoreSelf=True)

    self.totals.stop()

  def loadImage(self, item):
    ATTEMPT = 1 if self.retry < 1 else self.retry
    PDRETRY = self.retry
    PERFORM_DOWNLOAD = False

    self.totals.start(item.mtype, item.itype)

    # Call Files.PrepareDownload. If failure, retry up to retry times, waiting a short
    # interval between each attempt.
    url = self.json.getDownloadURL(item.filename)

    while PDRETRY > 0 and not url:
      self.logger.log("Retrying getDownloadURL(), %d attempts remaining" % PDRETRY)
      time.sleep(0.5)
      PDRETRY -= 1
      url = self.json.getDownloadURL(item.filename)

    if url:
      if not self.config.DOWNLOAD_PREDELETE:
        if item.dbid != 0 and self.force:
          self.logger.log("Deleting old image from cache with id [%d], cachedurl [%s] for filename [%s]"
                          % (item.dbid, item.cachedurl, item.decoded_filename))
          with self.database:
            self.database.deleteItem(item.dbid, item.cachedurl)
          self.totals.bump("Deleted", item.itype)
          PERFORM_DOWNLOAD = True
      if self.config.DOWNLOAD_PAYLOAD or PERFORM_DOWNLOAD:
        self.logger.log("Proceeding with download of URL [%s]" % url)
    else:
      self.logger.log("Image not available for download - uncacheable (embedded?), or doesn't exist. Filename [%s]" % item.filename)
      ATTEMPT = 0

    while ATTEMPT > 0 and (self.config.DOWNLOAD_PAYLOAD or PERFORM_DOWNLOAD):
      try:
        # Don't need to download the whole image for it to be cached so just grab the first 1KB
        PAYLOAD = self.json.sendWeb("GET", url, readAmount=1024, rawData=True)
        if self.json.WEB_LAST_STATUS == httplib.OK:
          self.logger.log("Successfully downloaded image with size [%d] bytes, attempts required [%d], filename [%s]" \
                        % (len(PAYLOAD), (self.retry - ATTEMPT + 1), item.decoded_filename))
          break
      except:
        pass
      ATTEMPT -= 1
      self.logger.log("Failed to download image URL [%s], status [%d], " \
                   "attempts remaining [%d]" % (url, self.json.WEB_LAST_STATUS, ATTEMPT))
      if stopped.is_set(): ATTEMPT = 0

    if ATTEMPT == 0:
      if not item.missingOK:
        self.totals.bump("Error", item.itype)
    else:
      self.totals.bump("Cached", item.itype)

    self.totals.finish(item.mtype, item.itype)

    return ATTEMPT != 0

#
# Simple thread class to manage Raspberry Pi HDMI power state
#
class MyHDMIManager(threading.Thread):
  def __init__(self, config, logger, cmdqueue, binpath, hdmidelay=900, onstopdelay=5):
    threading.Thread.__init__(self)

    self.EV_PLAY_STOP = "play.stop"
    self.EV_HDMI_OFF  = "hdmi.off"

    self.events = {}

    self.config = config
    self.logger = logger
    self.cmdqueue = cmdqueue
    self.binpath = binpath

    hdmidelay = 0 if hdmidelay < 0 else hdmidelay
    onstopdelay = 5 if onstopdelay < 5 else onstopdelay

    # Order of event processing is important, as
    # we want to process the hdmi.off event after
    # all other events.
    #
    # Higher numbers for order are processed last.
    #
    self.EventAdd(name=self.EV_PLAY_STOP, delayTime=onstopdelay, order=1)
    self.EventAdd(name=self.EV_HDMI_OFF,  delayTime=hdmidelay,   order=99)

    self.logger.debug("HDMI Power off delay: %d seconds" % self.EventInterval(self.EV_HDMI_OFF))
    self.logger.debug("Player OnStop delay : %d seconds" % self.EventInterval(self.EV_PLAY_STOP))
    self.logger.debug("Path to tvservice   : %s" % self.binpath)

  def run(self):
    try:
      self.MonitorXBMC()
    except:
      pass

  def MonitorXBMC(self):
    clientState = {}
    hdmi_on = True

    screensaver_active = False
    player_active = False
    library_active = False
    qtimeout = None

    # This is the order events will be processed...
    ordered_event_keys = [x[0] for x in sorted(self.events.items(), key=lambda e: e[1]["event.order"])]

    while not stopped.is_set():
      try:
        notification = self.cmdqueue.get(block=True, timeout=qtimeout)
        self.cmdqueue.task_done()

        method = notification["method"]
        params = notification["params"]

        if method == "pong":
          self.logger.debug("Connected to XBMC")
          self.logger.debug("HDMI power management thread - initialising XBMC and HDMI state")

          clientState = self.getXBMCStatus()
          hdmi_on = self.getHDMIStatus()

          screensaver_active = clientState["screensaver.active"]
          player_active = clientState["players.active"]
          library_active = (clientState["scanning.music"] or clientState["scanning.video"])

          self.logger.debug("HDMI is [%s], Screensaver is [%s], Player is [%s], Library scan [%s]" %
                            (("on" if hdmi_on else "off"),
                             ("active" if screensaver_active else "inactive"),
                             ("active" if player_active else "inactive"),
                             ("active" if library_active else "inactive")))

          if screensaver_active and hdmi_on:
            self.EventSet(self.EV_HDMI_OFF)

        elif method == "GUI.OnScreensaverActivated":
          self.logger.debug("Screensaver has activated")
          screensaver_active = True
          self.EventSet(self.EV_HDMI_OFF)

        elif method == "GUI.OnScreensaverDeactivated":
          self.logger.debug("Screensaver has deactivated")
          screensaver_active = False
          if hdmi_on:
            if self.EventEnabled(self.EV_HDMI_OFF):
              self.logger.debug("Scheduled HDMI power-off cancelled")
          else:
            hdmi_on = self.enable_hdmi()
            self.sendXBMCExit()
          self.EventStop(self.EV_HDMI_OFF)

        elif method == "Player.OnStop":
          self.EventSet(self.EV_PLAY_STOP)

        elif method == "Player.OnPlay":
          if not player_active:
            self.logger.debug("Player has started")
          player_active = True
          self.EventStop(self.EV_PLAY_STOP)

        elif method.endswith(".OnScanStarted") or method.endswith(".OnCleanStarted"):
          self.logger.debug("Library scan has started")
          library_active = True

        elif method.endswith(".OnScanFinished") or method.endswith(".OnCleanFinished"):
          self.logger.debug("Library scan has finished")
          library_active = False

        elif method == "System.OnQuit":
          self.EventsStopAll()

      except Queue.Empty as e:
        pass

      qtimeout = None

      # Process events once queue is empty of all notifications
      if self.cmdqueue.empty():
        now = time.time()
        for event in ordered_event_keys:
          # Start any pending events
          if self.EventPending(event):
            self.EventStart(event, now)
            if event == self.EV_HDMI_OFF:
              self.logger.debug("HDMI power off in %d seconds unless cancelled" % int(self.EventInterval(event)))
              if player_active or library_active:
                self.logger.debug("HDMI power-off will not occur until both player and library become inactive")

          # Process any expired events
          if self.EventExpired(event, now):
            if event == self.EV_PLAY_STOP:
              self.logger.debug("Player has stopped")
              player_active = False
              self.EventStop(event)
            elif event == self.EV_HDMI_OFF:
              if player_active or library_active:
                if not self.EventOverdue(event, now):
                  self.logger.debug("HDMI power-off timeout reached - waiting for player and library to become inactive")
              else:
                hdmi_on = self.disable_hdmi()
                self.EventStop(self.EV_HDMI_OFF)

          # Block until the next scheduled event, or block
          # indefinitely if no events are currently scheduled
          if self.EventEnabled(event) and not self.EventOverdue(event, now):
            nextevent = self.EventInterval(event, now)
            qtimeout = nextevent if nextevent >= 0 and (not qtimeout or nextevent < qtimeout) else qtimeout

  def EventExpired(self, name, currentTime):
    if self.events[name]["start"] != 0:
      return (self.EventInterval(name, currentTime) <= 0)
    else:
      return False

  def EventInterval(self, name, currentTime=None):
    if not currentTime or self.events[name]["start"] == 0:
      return self.events[name]["timeout"]
    else:
      t = self.events[name]["start"] + self.events[name]["timeout"]
      if currentTime:
        return t - currentTime
      else:
        return t - time.time()

  def EventEnabled(self, name):
    return self.events[name]["start"] != 0

  def EventPending(self, name):
    return self.events[name]["pending"]

  def EventOverdue(self, name, currentTime=None):
    overdue = self.events[name]["overdue"]
    if not overdue:
      if self.EventExpired(name, currentTime):
        self.events[name]["overdue"] = True
    return overdue

  def EventAdd(self, name, delayTime, order=None):
    self.events[name] = {"event.order": order, "timeout": delayTime}
    self.EventStop(name)

  def EventSet(self, name):
    self.events[name]["pending"] = True

  def EventStart(self, name, currentTime):
    self.events[name]["start"] = currentTime
    self.events[name]["pending"] = False

  def EventStop(self, name):
    self.events[name]["start"] = 0
    self.events[name]["overdue"] = False
    self.events[name]["pending"] = False

  def EventsStopAll(self):
    for event in self.events:
      self.EventStop(event)

  def sendXBMCExit(self):
    self.logger.debug("Sending Application.Quit() to XBMC")
    REQUEST = {"method": "Application.Quit"}
    MyJSONComms(self.config, self.logger).sendJSON(REQUEST, "libExit", checkResult=False)

  def getXBMCStatus(self):
    jcomms = MyJSONComms(self.config, self.logger)

    statuses = {}

    REQUEST = {"method": "XBMC.GetInfoBooleans",
               "params": {"booleans": ["System.ScreenSaverActive", "Library.IsScanningMusic", "Library.IsScanningVideo"]}}

    data = jcomms.sendJSON(REQUEST, "libBooleans", checkResult=False)
    values = data.get("result", {})
    statuses["screensaver.active"] = values.get("System.ScreenSaverActive", False)
    statuses["scanning.music"] = values.get("Library.IsScanningMusic", False)
    statuses["scanning.video"] = values.get("Library.IsScanningVideo", False)

    REQUEST = {"method": "Player.GetActivePlayers"}
    data = jcomms.sendJSON(REQUEST, "libPlayers", checkResult=False)
    values = data.get("result", [])
    statuses["players.active"] = (values != [])

    return statuses

  # Determine if TV is on or off - if off, no need to disable HDMI
  # True = ON, False = OFF
  #
  # The hotplug shows in state:
  #   VC_HDMI_UNPLUGGED = (1 << 0), /**<HDMI cable is detached */
  #   VC_HDMI_ATTACHED = (1 << 1), /**<HDMI cable is attached but not powered on */
  #   VC_HDMI_DVI = (1 << 2), /**<HDMI is on but in DVI mode (no audio) */
  #   VC_HDMI_HDMI = (1 << 3), /**<HDMI is on and HDMI mode is active */
  #   VC_HDMI_HDCP_UNAUTH = (1 << 4), /**<HDCP authentication is broken (e.g. Ri mismatched) or not active */
  #   VC_HDMI_HDCP_AUTH = (1 << 5), /**<HDCP is active */
  #   VC_HDMI_HDCP_KEY_DOWNLOAD = (1 << 6), /**<HDCP key download successful/fail */
  #   VC_HDMI_HDCP_SRM_DOWNLOAD = (1 << 7), /**<HDCP revocation list download successful/fail */
  #   VC_HDMI_CHANGING_MODE = (1 << 8), /**<HDMI is starting to change mode, clock has not yet been set */
  #
  # Typical values: 2 = HDMI off; 9 = HDMI on, TV off/standby; 10 (a) = HDMI+TV on
  #
  def getDisplayStatus(self):
    if self.config.FORCE_HOTPLUG:
      self.logger.debug("No hotplug support - assuming display is powered on")
      return True

    response = subprocess.check_output([self.binpath, "--status"], stderr=subprocess.STDOUT).decode("utf-8")
    state = re.search("state (0x[0-9a-f]*) .*", response)
    if state:
      vc_hdmi = int(state.group(1)[-1:], 16)
      tv_on = (vc_hdmi & (1 << 1) != 0)
    else:
      tv_on = True
    return tv_on

  # HDMI Power: True = ON, False = OFF
  def getHDMIStatus(self):
    response = subprocess.check_output([self.binpath, "--status"], stderr=subprocess.STDOUT).decode("utf-8")
    return response.find("TV is off") == -1

  def setHDMIState(self, state):
    option = "--preferred" if state else "--off"
    response = subprocess.check_output([self.binpath, option], stderr=subprocess.STDOUT).decode("utf-8")

  def disable_hdmi(self):
    if not self.getDisplayStatus():
      self.logger.debug("Display device is not turned on, no need to disable HDMI")
      return True

    self.setHDMIState(False)
    ison = self.getHDMIStatus()
    if not ison:
      self.logger.debug("HDMI is now off")
    else:
      self.logger.debug("HDMI failed to power off")
    return ison

  def enable_hdmi(self):
    self.setHDMIState(True)
    ison = self.getHDMIStatus()
    if ison:
      self.logger.debug("HDMI is now on")
    else:
      self.logger.debug("HDMI failed to power on")
    return ison

#
# Simple database wrapper class.
#
class MyDB(object):
  def __init__(self, config, logger):
    self.config = config
    self.logger = logger

    self.usejson = config.USEJSONDB

    #mydb will be either a SQL db or MyJSONComms object
    self.mydb = None

    self.DBVERSION = None
    self.cursor = None

    self.RETRY_MAX = 10
    self.RETRY = 0

  def __enter__(self):
    self.getDB()
    return self

  def __exit__(self, atype, avalue, traceback):
    if self.cursor: self.cursor.close()
    if self.mydb: self.mydb.close()
    self.cursor = self.mydb = None

  def getDB(self):
    if not self.mydb:
      if self.usejson:
        self.mydb = MyJSONComms(self.config, self.logger)
      else:
        if not os.path.exists(self.config.getDBPath()):
          raise lite.OperationalError("Database [%s] does not exist" % self.config.getDBPath())
        self.mydb = lite.connect(self.config.getDBPath(), timeout=10)
        self.mydb.text_factory = lambda x: x.decode("iso-8859-1")
        self.DBVERSION = self.execute("SELECT idVersion FROM version").fetchone()[0]
    return self.mydb

  def execute(self, SQL):
    self.cursor = self.getDB().cursor()
    self.logger.log("EXECUTING SQL: %s" % SQL)

    try:
      self.cursor.execute(SQL)
    except lite.OperationalError as e:
      if str(e) == "database is locked":
        if self.RETRY < self.RETRY_MAX:
          time.sleep(0.5 + (random.randint(10, 50)/100))
          self.RETRY += 1
          self.logger.log("EXCEPTION SQL: %s - retrying attempt #%d" % (e, self.RETRY))
          self.execute(SQL)
        else:
          self.logger.out("ERROR: Database %s is locked - try again later." % self.config.getDBPath(), newLine=True, log=True)
          self.logger.out("", newLine=True)
          raise
      else:
        raise

    self.RETRY = 0

    return self.cursor

  def getRows(self, filter=None, order=None, allfields=False):
    if self.usejson:
      data = self.mydb.getTextures(filter, order, allfields)
      if "result" in data and "textures" in data["result"]:
        funcNormalise = MyUtility.normalise
        for r in data["result"]["textures"]:
          r["url"] = funcNormalise(r["url"], strip=True)
        return data["result"]["textures"]
      else:
        return []
    else:
      return self._transform(self._getAllColumns(filter, order))

  def getSingleRow(self, filter):
    rows = self.getRows(filter, allfields=True)
    if rows != []:
      return rows[0]
    else:
      return None

  def _getAllColumns(self, filter=None, order=None):
    if self.DBVERSION >= 13:
      SQL = "SELECT t.id, t.cachedurl, t.lasthashcheck, t.url, s.height, s.width, s.usecount, s.lastusetime, s.size, t.imagehash " \
            "FROM texture t JOIN sizes s ON (t.id = s.idtexture)"
    else:
      SQL = "SELECT t.id, t.cachedurl, t.lasthashcheck, t.url, 0 as height, 0 as width, t.usecount, t.lastusetime, 0 as size, t.imagehash " \
            "FROM texture t"

    if filter: SQL = "%s %s" % (SQL, filter)
    if order: SQL = "%s %s" % (SQL, order)

    return self.execute(SQL).fetchall()

  # Return SQLite database rows as a dictionary list
  # to match JSON equivalent
  def _transform(self, rows):
    data = []
    funcNormalise = MyUtility.normalise
    if rows:
      for r in rows:
        url = funcNormalise(r[3], strip=True)
        data.append({u"textureid": r[0], u"cachedurl": r[1],
                     u"lasthashcheck": r[2], u"url": url,
                     u"sizes":[{u"height": r[4], u"width": r[5], u"usecount": r[6],
                               u"lastused": r[7], u"size": r[8]}],
                     u"imagehash": r[9]})
    return data

  def delRowByID(self, id):
    if id > 0:
      if self.usejson:
        data = self.mydb.delTexture(id)
        if not ("result" in data and data["result"] == "OK"):
          self.logger.out("id %s is not valid\n" % (self.config.IDFORMAT % int(id)))
      else:
        self.execute("DELETE FROM texture WHERE id=%d" % id)
        self.getDB().commit()

  def deleteItem(self, id, cachedURL=None, warnmissing=True):
    # When deleting rows via JSON, the artwork file and also
    # any corresponding dds file should also be removed
    if self.usejson and id > 0:
        self.delRowByID(id)
        return

    if not cachedURL and id > 0:
      row = self.getSingleRow("WHERE id = %d" % id)
      if row == None:
        self.logger.out("id %s is not valid\n" % (self.config.IDFORMAT % int(id)))
        return
      else:
        localFile = row["cachedurl"]
    else:
      localFile = cachedURL

    if localFile and os.path.exists(self.config.getFilePath(localFile)):
      os.remove(self.config.getFilePath(localFile))
      self.logger.log("FILE DELETE: Removed cached thumbnail file %s for id %s" % (localFile, (self.config.IDFORMAT % id)))
    else:
      if warnmissing:
        self.logger.out("WARNING: id %s, cached thumbnail file %s not found" % ((self.config.IDFORMAT % id), localFile), newLine=True)

    # Check for any matching .dds file and remove that too
    if localFile:
      localFile_dds = "%s.dds" % os.path.splitext(localFile)[0]
      if localFile_dds and os.path.exists(self.config.getFilePath(localFile_dds)):
        os.remove(self.config.getFilePath(localFile_dds))
        self.logger.log("FILE DELETE: Removed cached thumbnail file %s for id %s" % (localFile_dds, (self.config.IDFORMAT % id)))

    self.delRowByID(id)

  def getRowByFilename(self, filename):
  # Strip image:// prefix, trailing / suffix, and unquote...
    row = self.getRowByFilename_Impl(filename[8:-1], unquote=True)

  # Didn't find anyhing so try again, this time leave filename quoted, and don't truncate
    if not row:
      self.logger.log("Failed to find row by filename with the expected formatting, trying again (with prefix, quoted)")
      row = self.getRowByFilename_Impl(filename, unquote=False)

    return row

  def getRowByFilename_Impl(self, filename, unquote=True):
    if unquote:
      ufilename = MyUtility.normalise(filename)
    else:
      ufilename = filename

    # If string contains unicode, replace unicode chars with % and
    # use LIKE instead of equality
    if ufilename.encode("ascii", "ignore") == ufilename.encode("utf-8"):
      SQL = "WHERE url = \"%s\"" % ufilename
    else:
      self.logger.log("Removing ASCII from filename: [%s]" % ufilename)
      SQL = "WHERE url LIKE \"%s\"" % removeNonAscii(ufilename, "%")

    rows = self.getRows(filter=SQL, allfields=True)

    return rows[0] if rows != [] else None

  def removeNonAscii(self, s, replaceWith = ""):
    if replaceWith == "":
      return  "".join([x if ord(x) < 128 else ("%%%02x" % ord(x)) for x in s])
    else:
      return  "".join([x if ord(x) < 128 else replaceWith for x in s])

  def dumpRow(self, row):
    line= ("%s%s%-14s%s%04d%s%04d%s%04d%s%19s%s%19s%s%s\n" % \
           ((self.config.IDFORMAT % row["textureid"]),
             self.config.FSEP, row["cachedurl"],
             self.config.FSEP, row["sizes"][0]["height"],
             self.config.FSEP, row["sizes"][0]["width"],
             self.config.FSEP, row["sizes"][0]["usecount"],
             self.config.FSEP, row["sizes"][0]["lastused"],
             self.config.FSEP, row["lasthashcheck"],
             self.config.FSEP, row["url"]))

    self.logger.out(line)

#
# Handle all JSON RPC communication.
#
# Uses sockets except for those methods (Files.*) that must
# use HTTP.
#
class MyJSONComms(object):
  def __init__(self, config, logger, connecttimeout=None):
    self.config = config
    self.logger = logger
    self.connecttimeout = connecttimeout

    self.mysocket = None
    self.myweb = None
    self.WEB_LAST_STATUS = -1
    self.config.WEB_SINGLESHOT = True
    self.aUpdateCount = self.vUpdateCount = 0
    self.jcomms2 = None

    self.EXTRA_ART_DIR_CACHE = {}
    self.QUIT_METHOD = self.QUIT_PARAMS = None

  def __enter__(self):
    return self

  def __exit__(self, atype, avalue, traceback):
    return

  def __del__(self):
    if self.mysocket: self.mysocket.close()
    if self.myweb: self.myweb.close()

  def close(self):
    pass

  def getSocket(self):
    if not self.mysocket:
      self.mysocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.mysocket.settimeout(self.connecttimeout)
      self.mysocket.connect((self.config.XBMC_HOST, int(self.config.RPC_PORT)))
      self.mysocket.settimeout(None)
    return self.mysocket

  # Use a secondary socket object for simple lookups to avoid having to handle
  # re-entrant code due to notifications being received out of sequence etc.
  # Could instantiate an object whenever required, but keeping a reference here
  # should improve effeciency slightly.
  def getLookupObject(self):
    if not self.jcomms2:
      self.jcomms2 = MyJSONComms(self.config, self.logger)
    return self.jcomms2

  def getWeb(self):
    if not self.myweb or self.config.WEB_SINGLESHOT:
      if self.myweb: self.myweb.close()
      self.myweb = httplib.HTTPConnection("%s:%s" % (self.config.XBMC_HOST, self.config.WEB_PORT), timeout=self.connecttimeout)
      self.WEB_LAST_STATUS = -1
      if self.config.DEBUG: self.myweb.set_debuglevel(1)
    return self.myweb

  def sendWeb(self, request_type, url, request=None, headers={}, readAmount = 0, timeout=15.0, rawData=False):
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
      if sys.version_info >= (3, 0) and not rawData:
        if readAmount == 0: return response.read().decode("utf-8")
        else: return response.read(readAmount).decode("utf-8")
      else:
        if readAmount == 0: return response.read()
        else: return response.read(readAmount)
    except socket.timeout:
      self.logger.log("** iotimeout occurred during web request **")
      self.WEB_LAST_STATUS = httplib.REQUEST_TIMEOUT
      self.myweb.close()
      self.myweb = None
      return ""
    except:
      if self.config.WEB_SINGLESHOT == False:
        self.logger.log("SWITCHING TO WEBSERVER.SINGLESHOT MODE")
        self.config.WEB_SINGLESHOT = True
        return self.sendWeb(request_type, url, request, headers, readAmount, timeout, rawData)
      raise

  def sendJSON(self, request, id, callback=None, timeout=5.0, checkResult=True, useWebServer=False):
    BUFFER_SIZE = 32768

    request["jsonrpc"] = "2.0"
    request["id"] =  id

    # Suppress complaints about Sets having no results (due to Sets not having been defined)
    if request["method"] == "VideoLibrary.GetMovieSets": checkResult=False

    # Following methods don't work over sockets - by design.
    if request["method"] in ["Files.PrepareDownload", "Files.Download"] or useWebServer:
      self.logger.log("%s.JSON WEB REQUEST:" % id, jsonrequest=request)
      data = self.sendWeb("POST", "/jsonrpc", json.dumps(request), {"Content-Type": "application/json"}, timeout=timeout)
      if self.logger.LOGGING:
        self.logger.log("%s.RECEIVED DATA: %s" % (id, data), maxLen=256)
      return json.loads(data) if data != "" else ""

    s = self.getSocket()
    self.logger.log("%s.JSON SOCKET REQUEST:" % id, jsonrequest=request)
    START_IO_TIME = time.time()

    if sys.version_info >= (3, 0):
      s.send(bytes(json.dumps(request), "utf-8"))
    else:
      s.send(json.dumps(request))

    ENDOFDATA = True
    LASTIO = 0
    jdata = {}

    while True:
      if ENDOFDATA:
        ENDOFDATA = False
        s.setblocking(1)
        data = b""

      try:
        newdata = s.recv(BUFFER_SIZE)
        if len(data) == 0: s.settimeout(1.0)
        data += newdata
        LASTIO = time.time()
        self.logger.log("%s.BUFFER RECEIVED (len %d)" % (id, len(newdata)))
        if len(newdata) == 0: raise IOError("nodata")
        READ_ERR = False

      except IOError as e:
        # Hack to exit monitor mode when socket dies
        if callback:
          jdata = {"jsonrpc":"2.0","method":"System.OnQuit","params":{"data":-1,"sender":"xbmc"}}
          self.handleResponse(id, jdata, callback)
          return jdata
        else:
          self.logger.err("ERROR: Socket closed prematurely - exiting", newLine=True, log=True)
          sys.exit(2)

      except socket.error as e:
        READ_ERR = True

      # Keep reading unless accumulated data is a likely candidate for successful parsing...
      if not READ_ERR and len(data) != 0 and (data[-1:] == b"}" or data[-2:] == b"}\n"):

        # If data is not a str (Python2) then decode Python3 bytes to unicode representation
        if isinstance(data, str):
          udata = MyUtility.toUnicode(data)
        else:
          try:
            udata = data.decode("utf-8")
          except UnicodeDecodeError as e:
            continue

        try:
          START_PARSE_TIME = time.time()

          # Parse messages, to ensure the entire buffer is valid
          # If buffer is not valid (VlueError exception), we may need to read more data.
          messages = []
          for m in self.parseResponse(udata):
            if self.logger.LOGGING and messages == []:
              self.logger.log2("%s.PARSING JSON DATA: " % id, udata, maxLen=256)
            messages.append(m)

          # Discard these buffers which could potentially be very large, as they're no longer required
          del data, udata

          self.logger.log("%s.PARSING COMPLETE, elapsed time: %f seconds" % (id, time.time() - START_PARSE_TIME))

          # Process any notifications first.
          # Any message with an id must be processed after notification - should only be one at most...
          result = False
          jdata = {}
          for m in messages:
            if "id" not in m:
              if callback:
                if self.handleResponse(id, m, callback):
                  result = True
              elif self.logger.LOGGING:
                self.logger.log("%s.IGNORING NOTIFICATION" % id, jsonrequest=m, maxLen=256)
            elif m["id"] == id:
              jdata = m

          # Discard - no longer required
          del messages

          if ("result" in jdata and "limits" in jdata["result"]):
            self.logger.log("%s.RECEIVED LIMITS: %s" % (id, jdata["result"]["limits"]))

          # Flag to reset buffers next time we read the socket.
          ENDOFDATA = True

          # callback result for a comingled Notification - stop blocking/reading and
          # return to caller with response (jdata)
          if result: break

          # Got a response...
          if jdata != {}:
            # If callback defined, pass it the message then break if result is True.
            # Otherwise break only if message has an id, that is to
            # say, continue reading data (blocking) until a message (response)
            # with an id is available.
            if callback:
              if self.handleResponse(id, jdata, callback): break
            elif "id" in jdata:
              break

          if callback:
            self.logger.log("%s.READING SOCKET UNTIL CALLBACK SUCCEEDS..." % id)
          else:
            self.logger.log("%s.READING SOCKET FOR A RESPONSE..." % id)

        except ValueError as e:
          # If we think we've reached EOF (no more data) and we have invalid data then
          # raise exception,  otherwise continue reading more data
          if READ_ERR:
            self.logger.log("%s.VALUE ERROR EXCEPTION: %s" % (id, str(e)))
            raise
          else:
            self.logger.log("%s.Incomplete JSON data - continue reading socket" % id)
            if self.logger.VERBOSE: self.logger.log2("Ignored Value Error: ", str(e))
            continue
        except Exception as e:
          self.logger.log("%s.GENERAL EXCEPTION: %s" % (id, str(e)))
          raise

      # Still more data to be read...
      if not ENDOFDATA:
        if (time.time() - LASTIO) > timeout:
          self.logger.log("SOCKET IO TIMEOUT EXCEEDED")
          raise socket.error("Socket IO timeout exceeded")

    if checkResult and not "result" in jdata:
      self.logger.out("%s.ERROR: JSON response has no result!\n%s\n" % (id, jdata))

    self.logger.log("%s.FINISHED, elapsed time: %f seconds" % (id, time.time() - START_IO_TIME))
    return jdata

  # Split data into individual json objects.
  def parseResponse(self, data):

    decoder = json._default_decoder
    _w=json.decoder.WHITESPACE.match

    idx = _w(data, 0).end()
    end = len(data)

    try:
      while idx != end:
        (val, idx) = decoder.raw_decode(data, idx=idx)
        yield val
        idx = _w(data, idx).end()
    except ValueError as exc:
#      raise ValueError("%s (%r at position %d)." % (exc, data[idx:], idx))
      raise ValueError("%s" % exc)

  # Process Notifications, optionally executing a callback function for
  # additional custom processing.
  def handleResponse(self, callingId, jdata, callback):
    id = jdata["id"] if "id" in jdata else None
    method = jdata["method"] if "method" in jdata else jdata["result"]
    params = jdata["params"] if "params" in jdata else None

    if callback:
      cname = callback.__name__
      self.logger.log("%s.PERFORMING CALLBACK: Name [%s], with Id [%s], Method [%s], Params [%s]" % (callingId, cname, id, method, params))
      result = callback(id, method, params)
      self.logger.log("%s.CALLBACK RESULT: [%s] Name [%s], Id [%s], Method [%s], Params [%s]" % (callingId, result, cname, id, method, params))
      if result:
        self.QUIT_METHOD = method
        self.QUIT_PARAMS = params
      return result

    return False

  def listen(self):
    REQUEST = {"method": "JSONRPC.Ping"}
    self.sendJSON(REQUEST, "libListen", callback=self.speak, checkResult=False)

  def speak(self,id, method, params):
    # Only interested in Notifications...
    if id: return False

    item = None
    title = None
    pmsg = None

    if params["data"]:
      pmsg = json.dumps(params["data"])
      if type(params["data"]) is dict:
        if "item" in params["data"]:
          item = params["data"]["item"]
        elif "type" in params["data"]:
          item = params["data"]

      if item:
        title = self.getTitleForLibraryItem(item.get("type", None), item.get("id", None))

    if not pmsg: pmsg = "{}"

    if title:
      self.logger.out("%s: %-21s: %s [%s]" % (datetime.datetime.now(), method, pmsg, title), newLine=True)
    else:
      self.logger.out("%s: %-21s: %s" % (datetime.datetime.now(), method, pmsg), newLine=True)

    return True if method == "System.OnQuit" else False

  def jsonWaitForScanFinished(self, id, method, params):
    if method.endswith("Library.OnUpdate") and "data" in params:
      if method == "AudioLibrary.OnUpdate": self.aUpdateCount += 1
      if method == "VideoLibrary.OnUpdate": self.vUpdateCount += 1

      if "item" in params["data"]:
        item = params["data"]["item"]
      elif "type" in params["data"]:
        item = params["data"]
      else:
        item = None

      if item:
        iType = item["type"]
        libraryId = item["id"]
        title = self.getTitleForLibraryItem(iType, libraryId)

        if title:
          self.logger.out("Updating Library: New %-9s %5d [%s]\n" % (iType + "id", libraryId, title))
        else:
          self.logger.out("Updating Library: New %-9s %5d\n" % (iType + "id", libraryId))

    return True if method.endswith("Library.OnScanFinished") else False

  def jsonWaitForCleanFinished(self, id, method, params):
    return True if method.endswith("Library.OnCleanFinished") else False

  def addProperties(self, request, fields):
    if not "properties" in request["params"]: return
    aList = request["params"]["properties"]
    if fields != None:
      for f in [f.strip() for f in fields.split(",")]:
        if f != "" and not f in aList:
          aList.append(f)
    request["params"]["properties"] = aList

  def addFilter(self, request, newFilter, condition="and"):
    filter = request["params"]
    if "filter" in filter:
       filter["filter"] = { condition: [ filter["filter"], newFilter ] }
    else:
       filter["filter"] = newFilter
    request["params"] = filter

  def rescanDirectories(self, workItems):
    if workItems == {}: return

    # Seems to be a bug in rescan method when scanning the root folder of a source
    # So if any items are in the root folder, just scan the entire library after
    # items have been removed.
    rootScan = False
    sources = self.getSources("video")

    for directory in sorted(workItems):
      (mediatype, dpath) = directory.split(";")
      if dpath in sources: rootScan = True

    for directory in sorted(workItems):
      (mediatype, dpath) = directory.split(";")

      for disc_folder in [ ".BDMV$", ".VIDEO_TS$" ]:
        re_match = re.search(disc_folder, dpath, flags=re.IGNORECASE)
        if re_match:
          dpath = dpath[:re_match.start()]
          break

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

      for libraryid in workItems[directory]:
        self.logger.log("Removing %s %d from media library." % (idName, libraryid))
        REQUEST = {"method": removeMethod, "params":{idName: libraryid}}
        self.sendJSON(REQUEST, "libRemove")

      if not rootScan: self.scanDirectory(scanMethod, path=dpath)

    if rootScan: self.scanDirectory(scanMethod)

  def scanDirectory(self, scanMethod, path=None):
    if path and path != "":
      self.logger.out("Rescanning directory: %s..." % path, newLine=True, log=True)
      REQUEST = {"method": scanMethod, "params":{"directory": path}}
    else:
      self.logger.out("Rescanning library...", newLine=True, log=True)
      REQUEST = {"method": scanMethod}

    self.sendJSON(REQUEST, "libRescan", callback=self.jsonWaitForScanFinished, checkResult=False)

  def cleanLibrary(self, cleanMethod):
    self.logger.out("Cleaning library...", newLine=True, log=True)
    REQUEST = {"method": cleanMethod}
    self.sendJSON(REQUEST, "libClean", callback=self.jsonWaitForCleanFinished, checkResult=False)

  def getDirectoryList(self, path, mediatype="files", properties=["file"]):
    REQUEST = {"method":"Files.GetDirectory",
               "params": {"directory": path, "media": mediatype}}

    if properties:
      REQUEST["properties"] = properties

    data = self.sendJSON(REQUEST, "libDirectory", checkResult=False)

    # Fix null being returned for "files" on some systems...
    if "result" in data and "files" in data["result"]:
      if data["result"]["files"] == None:
        data["result"]["files"] = []

    return data

  def getExtraArt(self, item):
    if not (item and self.config.CACHE_EXTRA): return []

    # Movies, Tags and TVShows have a file property which can be used as the media root.
    # Artists and Albums do not, so try and find a usable local path from the
    # fanart/thumbnail artwork.
    directory = None
    if "file" in item:
      directory = item["file"]
    else:
      for a in ["fanart", "thumbnail"]:
        if a in item:
          tmp = MyUtility.normalise(item[a], strip=True)
          hostname = re.search("^.*@", tmp)
          if hostname and hostname.end() < 10:
            directory = tmp[hostname.end():]
            break
          elif not tmp.startswith("http:"):
            directory = tmp
            break

    if not directory: return []

    # Remove filename, leaving just parent directory.
    # Could use os.path.dirname() here but we need
    # to know which slash is being used so that it
    # can be appended before the relevant subdir is added.
    for slash in ["/", "\\"]:
      pos = directory.rfind(slash)
      if pos != -1:
        directory = "%s" % directory[:pos+1]
        SLASH = directory[pos:pos+1]
        break
    else:
      return []

    # This cache of previous GetDirectory lookups avoids
    # repeated lookups on the same path
    if directory in self.EXTRA_ART_DIR_CACHE:
      return self.EXTRA_ART_DIR_CACHE[directory]

    self.EXTRA_ART_DIR_CACHE[directory] = []

    data = self.getDirectoryList(directory)

    if "result" not in data: return []
    if "files" not in data["result"]: return []

    artitems = []
    if self.config.CACHE_EXTRA_FANART:
      artitems.append("%sextrafanart%s" % (SLASH, SLASH))
    if self.config.CACHE_EXTRA_THUMBS:
      artitems.append("%sextrathumbs%s" % (SLASH, SLASH))
    if self.config.CACHE_VIDEO_EXTRAS:
      artitems.append("%sextras%s" % (SLASH, SLASH))
      artitems.append("%sExtras%s" % (SLASH, SLASH))

    dirs = []
    for file in data["result"]["files"]:
      if file["filetype"] == "directory" and file["file"]:
        for a in artitems:
          if file["file"].endswith(a):
            dirs.append({"file": file["file"], "type": a[1:-1]})
            break

    files = []
    for dir in dirs:
      data = self.getDirectoryList(dir["file"])
      if "result" in data and "files" in data["result"]:
        for file in data["result"]["files"]:
          if file["filetype"] == "file" and file["file"]:
            if os.path.splitext(file["file"])[1].lower() in [".jpg", ".png", ".tbn"]:
              files.append({"file": MyUtility.denormalise(file["file"], prefix=True), "type": dir["type"].lower()})

    self.EXTRA_ART_DIR_CACHE[directory] = files

    return files

  def getSeasonAll(self, filename):
    # If "Season All" items are not being cached, return no results
    if self.config.CACHE_HIDEALLITEMS: return (None, None, None)

    # Not able to get a directory for remote files...
    if filename.find("image://http") != -1: return (None, None, None)

    directory = MyUtility.normalise(filename, strip=True)

    # Remove filename, leaving just parent directory.
    # Could use os.path.dirname() here but we need to know
    # which slash is being used so that it can be
    # appended before the filename is added by the caller.
    for slash in ["/", "\\"]:
      pos = directory.rfind(slash)
      if pos != -1:
        directory = directory[:pos]
        break
    else:
      return (None, None, None)

    data = self.getDirectoryList(directory)

    if "result" in data and "files" in data["result"]:
      poster_url = fanart_url = banner_url = None
      for f in data["result"]["files"]:
        if f["filetype"] == "file":
          fname = os.path.split(f["label"])[1].lower()
          if fname.startswith("season-all-poster."): poster_url = MyUtility.joinQuotedPath(filename, f["file"])
          elif not poster_url and fname.startswith("season-all."): poster_url = MyUtility.joinQuotedPath(filename, f["file"])
          elif fname.startswith("season-all-banner."): banner_url = MyUtility.joinQuotedPath(filename, f["file"])
          elif fname.startswith("season-all-fanart."): fanart_url = MyUtility.joinQuotedPath(filename, f["file"])
      return (poster_url, fanart_url, banner_url)

    return (None, None, None)

  def getDownloadURL(self, filename):
    REQUEST = {"method":"Files.PrepareDownload",
               "params":{"path": filename }}

    data = self.sendJSON(REQUEST, "preparedl")

    if "result" in data:
      return "/%s" % data["result"]["details"]["path"]
    else:
#      if filename[8:12].lower() != "http":
#        self.logger.log("Files.PrepareDownload failed. It's a local file, what the heck... trying anyway.")
#        return "/image/%s" % urllib2.quote(filename, "")
      return None

  def getFileDetails(self, filename):
    REQUEST = {"method":"Files.GetFileDetails",
               "params":{"file": filename,
                         "properties": ["streamdetails", "lastmodified", "dateadded", "size", "mimetype", "tag", "file"]}}

    data = self.sendJSON(REQUEST, "filedetails", checkResult=False)

    if "result" in data:
      return data["result"].get("filedetails", None)
    else:
      return None

  # Get title of item - usually during a notification. As this can be
  # an OnRemove notification, don't check for result as the item may have
  # been removed before it can be looked up, in which case return None.
  def getTitleForLibraryItem(self, iType, libraryId):
    title = None

    if iType and libraryId:
      # Use the secondary socket object to avoid consuming
      # notifications that are meant for the caller.
      if iType == "song":
        title = self.getLookupObject().getSongName(libraryId)
      elif iType == "movie":
        title = self.getLookupObject().getMovieName(libraryId)
      elif iType == "tvshow":
        title = self.getLookupObject().getTVShowName(libraryId)
      elif iType == "episode":
        title = self.getLookupObject().getEpisodeName(libraryId)
      elif iType == "musicvideo":
        title = self.getLookupObject().getMusicVideoName(libraryId)

    return title

  def getSongName(self, songid):
    REQUEST = {"method":"AudioLibrary.GetSongDetails",
               "params":{"songid": songid, "properties":["title", "artist", "albumartist"]}}
    data = self.sendJSON(REQUEST, "libSong", checkResult=False)
    if "result" in data and "songdetails" in data["result"]:
      s = data["result"]["songdetails"]
      if s["artist"]:
        return "%s (%s)" % (s["title"], "/".join(s["artist"]))
      else:
        return "%s (%s)" % (s["title"], "/".join(s["albumartist"]))
    else:
      return None

  def getTVShowName(self, tvshowid):
    REQUEST = {"method":"VideoLibrary.GetTVShowDetails",
               "params":{"tvshowid": tvshowid, "properties":["title"]}}
    data = self.sendJSON(REQUEST, "libTVShow", checkResult=False)
    if "result" in data and "tvshowdetails" in data["result"]:
      t = data["result"]["tvshowdetails"]
      return "%s" % t["title"]
    else:
      return None

  def getEpisodeName(self, episodeid):
    REQUEST = {"method":"VideoLibrary.GetEpisodeDetails",
               "params":{"episodeid": episodeid, "properties":["title", "showtitle", "season", "episode"]}}
    data = self.sendJSON(REQUEST, "libEpisode", checkResult=False)
    if "result" in data and "episodedetails" in data["result"]:
      e = data["result"]["episodedetails"]
      return "%s S%02dE%02d (%s)" % (e["showtitle"], e["season"], e["episode"], e["title"])
    else:
      return None

  def getMovieName(self, movieid):
    REQUEST = {"method":"VideoLibrary.GetMovieDetails",
               "params":{"movieid": movieid, "properties":["title"]}}
    data = self.sendJSON(REQUEST, "libMovie", checkResult=False)
    if "result" in data and "moviedetails" in data["result"]:
      m = data["result"]["moviedetails"]
      return "%s" % m["title"]
    else:
      return None

  def getMusicVideoName(self, videoid):
    REQUEST = {"method":"VideoLibrary.GetMusicVideoDetails",
               "params":{"movieid": videoid, "properties":["title"]}}
    data = self.sendJSON(REQUEST, "libMusicVideo", checkResult=False)
    if "result" in data and "musicvideodetails" in data["result"]:
      m = data["result"]["musicvideodetails"]
      return "%s" % m["title"]
    else:
      return None

  def removeLibraryItem(self, iType, libraryId):
    if iType and libraryId:
      # Use the secondary socket object to avoid consuming
      # notifications that are meant for the caller.
      if iType == "movie":
        (method, arg) = ("VideoLibrary.RemoveMovie", "movieid")
      elif iType == "tvshow":
        (method, arg) = ("VideoLibrary.RemoveTVShow", "tvshowid")
      elif iType == "episode":
        (method, arg) = ("VideoLibrary.RemoveEpisode", "episodeid")
      elif iType == "musicvideo":
        (method, arg) = ("VideoLibrary.RemoveMusicVideo", "musicvideoid")

    REQUEST = {"method": method, "params":{arg: libraryId}}
    data = self.sendJSON(REQUEST, "libRemove", checkResult=True)

  def dumpJSON(self, data, decode=False, ensure_ascii=True):
    if decode:
      self.logger.progress("Decoding URLs...")
      self.unquoteArtwork(data)
    self.logger.progress("")
    self.logger.out(json.dumps(data, indent=2, ensure_ascii=ensure_ascii, sort_keys=True), newLine=True)

  def unquoteArtwork(self, items):
    for item in items:
      for field in item:
        if field in ["seasons", "episodes", "channels", "tc.members"]:
          self.unquoteArtwork(item[field])
        elif field in ["fanart", "thumbnail"]:
          item[field] = MyUtility.normalise(item[field])
        elif field == "art":
          art = item["art"]
          for image in art:
            art[image] = MyUtility.normalise(art[image])
        elif field == "cast":
          for cast in item["cast"]:
            if "thumbnail" in cast:
              cast["thumbnail"] = MyUtility.normalise(cast["thumbnail"])

  def getSources(self, media, labelPrefix=False, withLabel=None):
    REQUEST = {"method": "Files.GetSources", "params":{"media": media}}

    data = self.sendJSON(REQUEST, "libSources")

    source_list = []

    if "result" in data and "sources" in data["result"]:
      for source in data["result"]["sources"]:
        file = source["file"]
        label = source["label"]
        if not withLabel or withLabel.lower() == label.lower():
          if file.startswith("multipath://"):
            for apath in file[12:].split("/"):
              if apath != "":
                apath= MyUtility.normalise(apath)[:-1]
                if labelPrefix:
                  source_list.append("%s: %s" % (label, apath))
                else:
                  source_list.append(apath)
          else:
            apath = MyUtility.normalise(file)[:-1]
            if labelPrefix:
              source_list.append("%s: %s" % (label, apath))
            else:
              source_list.append(apath)

    return sorted(source_list)

  def getAllFilesForSource(self, mediatype, labels):
    if mediatype == "songs":
      mtype = "music"
    else:
      mtype = "video"

    # Mostly image, nfo and audio-related playlist file types,
    # but also some random junk...
    ignoreList = self.config.PICTURE_FILETYPES
    ignoreList.extend([".nfo", ".srt", ".sub", ".idx", ".strm", \
                       ".m3u", ".pls", ".cue", \
                       ".log", ".ini", ".txt", ".url", ".md5", \
                       ".bak", ".info", ".db", ".gz", ".tar", ".rar", ".zip"])

    # Allow custom non-media extensions
    for extension in self.config.NONMEDIA_FILETYPES:
      if extension not in ignoreList:
        ignoreList.append(extension)

    fileList = []

    for label in labels:
      sources = self.getSources(mtype, withLabel=label)

      for path in sources:
        self.logger.progress("Walking source: [%s]" % path)

        for file in self.getFilesForPath(path):
          ext = os.path.splitext(file)[1].lower()
          if ext in ignoreList: continue

          if os.path.splitext(file)[0].lower().endswith("trailer"): continue

          isVIDEOTS = (file.find("/VIDEO_TS/") != -1 or file.find("\\VIDEO_TS\\") != -1)
          isBDMV    = (file.find("/BDMV/") != -1 or file.find("\\BDMV\\") != -1)

          if isVIDEOTS and ext != ".vob": continue
          if isBDMV    and ext != ".m2ts": continue

          # Avoiding adding file to list more than once, which is possible
          # if a folder appears within multiple different sources, or the
          # same source is processed more than once...
          if not file in fileList:
            fileList.append(file)

    if fileList == []:
      self.logger.out("WARNING: No files obtained from filesystem - ensure valid source(s) specified!", newLine=True)

    fileList.sort()

    return fileList

  def getFilesForPath(self, path):
    fileList = []
    self.getFilesForPath_recurse(fileList, path)
    return fileList

  def getFilesForPath_recurse(self, fileList, path):
    data = self.getDirectoryList(path)
    if not "result" in data: return
    if not "files" in data["result"]: return

    for file in data["result"]["files"]:
      ftype = file["filetype"]
      fname = file["file"]
      fext = os.path.splitext(fname)[1].lower()
      #Real directories won't have extensions, but .m3u and .pls playlists will
      #leading to infinite recursion, so don't try to traverse playlists
      if ftype == "directory" and fext == "":
        self.getFilesForPath_recurse(fileList, os.path.dirname(fname))
      else:
        fileList.append(fname)

  def setPower(self, state):
    if state == "exit":
      REQUEST = {"method": "Application.Quit"}
    else:
      REQUEST = {"method": "System.%s" % state.capitalize()}
    data = self.sendJSON(REQUEST, "libPower")

  def getData(self, action, mediatype,
              filter = None, useExtraFields = False, secondaryFields = None,
              showid = None, seasonid = None, channelgroupid = None, lastRun = False, subType = None):

    EXTRA = mediatype
    SECTION = mediatype
    FILTER = "title"
    TITLE = "title"
    IDENTIFIER = "%sid" % re.sub("(.*)s$", "\\1", mediatype)

    if mediatype == "addons":
      REQUEST = {"method":"Addons.GetAddons",
                 "params":{"properties":["name", "version", "thumbnail", "fanart"]}}
      FILTER = "name"
      TITLE = "name"
    elif mediatype in ["pvr.tv", "pvr.radio"]:
      REQUEST = {"method":"PVR.GetChannelGroups",
                 "params":{"channeltype": mediatype.split(".")[1]}}
      SECTION = "channelgroups"
      FILTER = "channeltype"
      TITLE = "label"
      IDENTIFIER = "channelgroupid"
    elif mediatype in ["pvr.tv.channel", "pvr.radio.channel"]:
      REQUEST = {"method":"PVR.GetChannels",
                 "params":{"channelgroupid": channelgroupid,
                           "properties": ["channeltype", "channel", "thumbnail", "hidden", "locked", "lastplayed"]}}
      SECTION = "channels"
      FILTER = "channel"
      TITLE = "channel"
      IDENTIFIER = "channelid"
    elif mediatype == "albums":
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
                           "properties":["title", "artist", "album", "fanart", "thumbnail"]}}
    elif mediatype in ["movies", "tags"]:
      REQUEST = {"method":"VideoLibrary.GetMovies",
                 "params":{"sort": {"order": "ascending", "method": "title"},
                           "properties":["title", "art"]}}
      EXTRA = "movies"
      SECTION = "movies"
      IDENTIFIER = "movieid"
    elif mediatype == "sets":
      REQUEST = {"method":"VideoLibrary.GetMovieSets",
                 "params":{"sort": {"order": "ascending", "method": "title"},
                           "properties":["title", "art"]}}
      FILTER = ""
    elif mediatype == "sets-members":
      REQUEST = {"method":"VideoLibrary.GetMovies",
                 "params":{"sort": {"order": "ascending", "method": "sorttitle"},
                           "properties":["file", "set", "title", "sorttitle"]}}
      EXTRA = "movies"
      SECTION = "movies"
      IDENTIFIER = "movieid"
    elif mediatype == "tvshows":
      REQUEST = {"method":"VideoLibrary.GetTVShows",
                 "params":{"sort": {"order": "ascending", "method": "title"},
                           "properties":["title", "art"]}}
      EXTRA = "tvshows.tvshow"
    elif mediatype == "seasons":
      REQUEST = {"method":"VideoLibrary.GetSeasons",
                 "params":{"sort": {"order": "ascending", "method": "season"},
                           "tvshowid": showid, "properties":["season", "art"]}}
      FILTER = ""
      TITLE = "label"
      EXTRA = "tvshows.season"
      IDENTIFIER = "season"
    elif mediatype == "episodes":
      REQUEST = {"method":"VideoLibrary.GetEpisodes",
                 "params":{"sort": {"order": "ascending", "method": "label"},
                           "tvshowid": showid, "season": seasonid, "properties":["art"]}}
      FILTER = ""
      TITLE = "label"
      EXTRA = "tvshows.episode"
    elif mediatype == "agenres":
        REQUEST = {"method":"AudioLibrary.GetGenres",
                   "params":{"properties":["title", "thumbnail"]}}
        FILTER = "title"
        TITLE = "title"
        SECTION = "genres"
        IDENTIFIER = "genreid"
    elif mediatype == "vgenres":
        REQUEST = {"method":"VideoLibrary.GetGenres",
                   "params":{"type": subType,
                             "properties":["title", "thumbnail"]}}
        FILTER = "title"
        TITLE = "title"
        SECTION = "genres"
        IDENTIFIER = "genreid"
    else:
      raise ValueError("Invalid mediatype: [%s]" % mediatype)

    if mediatype == "tags":
        if not filter or filter.strip() == "":
          self.addFilter(REQUEST, {"field": "tag", "operator": "contains", "value": "%"})
        else:
          word = 0
          filterBoolean = "and"
          for tag in [x.strip() for x in re.split("( and | or )", filter)]:
            word += 1
            if (word%2 == 0) and tag in ["and","or"]: filterBoolean = tag
            else: self.addFilter(REQUEST, {"field": "tag", "operator": "contains", "value": tag}, filterBoolean)
    elif mediatype == "sets-members":
        if filter:
          self.addFilter(REQUEST, {"field": "set", "operator": "contains", "value": filter})
        else:
          # JSON filter is broken when handling empty (null) strings - they're ignored - though
          # hopefully this will be fixed in a later version of API, in which case use it
          if self.config.JSON_HAS_FILTERNULLVALUE:
            self.addFilter(REQUEST, {"field": "set", "operator": "isnot", "value": ""})
          else:
            self.addFilter(REQUEST, {"field": "set", "operator": "doesnotcontain", "value": "@@@@@@@@@@@@"})
    elif filter and filter.strip() != "" and not mediatype in ["addons", "agenres", "vgenres",
                                                               "sets", "seasons", "episodes",
                                                               "pvr.tv", "pvr.radio", "pvr.channels"]:
        self.addFilter(REQUEST, {"field": FILTER, "operator": "contains", "value": filter})

    if mediatype in ["movies", "tags", "episodes"]:
      if lastRun and self.config.LASTRUNFILE_DATETIME:
        self.addFilter(REQUEST, {"field": "dateadded", "operator": "after", "value": self.config.LASTRUNFILE_DATETIME })

    # Add extra required fields/propreties based on action to be performed

    if action == "duplicates":
      if "art" in REQUEST["params"]["properties"]:
        REQUEST["params"]["properties"].remove("art")
      self.addProperties(REQUEST, "file")
      self.addProperties(REQUEST, "imdbnumber")
      self.addProperties(REQUEST, "playcount")
      self.addProperties(REQUEST, "lastplayed")
      self.addProperties(REQUEST, "dateadded")

    elif action == "imdb":
      self.addProperties(REQUEST, "imdbnumber")
      self.addProperties(REQUEST, self.config.IMDB_FIELDS)

    elif action == "missing":
      for unwanted in ["artist", "art", "fanart", "thumbnail"]:
        if unwanted in REQUEST["params"]["properties"]:
          REQUEST["params"]["properties"].remove(unwanted)
      if mediatype in ["songs", "movies", "tvshows", "episodes" ]:
        self.addProperties(REQUEST, "file")

    elif action == "watched" and mediatype in ["movies", "episodes"]:
        if "art" in REQUEST["params"]["properties"]:
          REQUEST["params"]["properties"].remove("art")
        if mediatype == "movies":
          self.addProperties(REQUEST, "year")
        self.addProperties(REQUEST, "playcount, lastplayed, resume")

    elif action == "qa":
      qaSinceDate = self.config.QADATE
      if qaSinceDate and mediatype in ["movies", "tags", "episodes"]:
          self.addFilter(REQUEST, {"field": "dateadded", "operator": "after", "value": qaSinceDate})

      if mediatype in ["songs", "movies", "tags", "tvshows", "episodes" ]:
        self.addProperties(REQUEST, "file")

      self.addProperties(REQUEST, ", ".join(self.config.getQAFields("zero", EXTRA)))
      self.addProperties(REQUEST, ", ".join(self.config.getQAFields("blank", EXTRA)))

    elif action == "dump":
      if mediatype in ["songs", "movies", "tvshows", "episodes" ]:
        self.addProperties(REQUEST, "file")
      extraFields = self.config.XTRAJSON["extrajson.%s" % EXTRA] if EXTRA != "" else None
      if useExtraFields and extraFields:
        self.addProperties(REQUEST, extraFields)
      if secondaryFields:
        self.addProperties(REQUEST, secondaryFields)

    elif action == "query" and not mediatype in ["tvshows", "seasons", "pvr.tv", "pvr.radio"]:
      if secondaryFields:
        self.addProperties(REQUEST, secondaryFields)

    elif action == "cache":
      if mediatype in ["movies", "tags", "tvshows", "episodes"] and self.config.CACHE_CAST_THUMB:
        self.addProperties(REQUEST, "cast")
      if self.config.CACHE_EXTRA:
        if mediatype in ["movies", "tags", "tvshows"]:
          self.addProperties(REQUEST, "file")
        elif mediatype in ["artists", "albums"]:
          self.addProperties(REQUEST, "fanart")
          self.addProperties(REQUEST, "thumbnail")

    return (SECTION, TITLE, IDENTIFIER, self.sendJSON(REQUEST, "lib%s" % mediatype.capitalize()))

  # Return a list of all pictures (jpg/png/tbn) with a source of "pictures"
  def getPictures(self):
    list = []

    for path in self.getSources("pictures"):
      self.getPicturesForPath(path, list)

    return list

  def getPicturesForPath(self, path, list):
    data = self.getDirectoryList(path)
    if "result" not in data or "files" not in data["result"]: return

    DIR_ADDED = False
    for file in data["result"]["files"]:
      if file["file"]:
        if file["filetype"] == "directory":
          self.getPicturesForPath(file["file"], list)
        elif file["filetype"] == "file" and os.path.splitext(file["file"])[1].lower() in self.config.PICTURE_FILETYPES:
          if not DIR_ADDED:
            DIR_ADDED = True
            list.append({"type": "directory", "label": path, "thumbnail": "picturefolder@%s" % path})
          list.append({"type": "file", "label": file["file"], "thumbnail": "%s/transform?size=thumb" % file["file"]})

  def parseSQLFilter(self, filter):
    if type(filter) is dict: return filter

    filter = filter.strip()

    if not filter: return []

    if filter.lower().startswith("where "):
      filter = filter[6:]

    PATTERN = re.compile(r'''((?:[^ "']|"[^"]*"|'[^']*')+)''')

    data = []
    fields = []
    condition = None
    f = 0
    for token in PATTERN.split(filter)[1::2]:
      if token in ["and", "or"]:
        condition = token
        continue

      fields.append(token)
      f += 1

      if f == 3:
        if fields[0].startswith("t."): fields[0] = fields[0][2:]
        if fields[0] == "id": fields[0] = "textureid"

        if (fields[2].startswith("'") and fields[2].endswith("'")) or \
           (fields[2].startswith('"') and fields[2].endswith('"')):
          fields[2] = fields[2][1:-1]

        if   fields[1] in ["=", "=="]:
          fields[1] = "is"
        elif fields[1] == "!=":
          fields[1] = "isnot"
        elif fields[1] == ">":
          fields[1] = "greaterthan"
        elif fields[1] == "<":
          fields[1] = "lessthan"
        elif fields[1] == ">=":
          fields[1] = "=greaterthan"
        elif fields[1] == "<=":
          fields[1] = "=lessthan"
        elif fields[1].lower() == "like":
          if re.match("^%.*%", fields[2]):
            fields[1] = "contains"
          elif re.match("^%.*", fields[2]):
            fields[1] = "endswith"
          elif re.match("^.*%", fields[2]):
            fields[1] = "startswith"
          else:
            fields[1] = "is"
          fields[2] = fields[2].replace("%","")
        else:
          fields[1] = "is"

        if fields[1].startswith("="):
          data.append({"or": [{"field": fields[0], "operator": "is", "value": fields[2]},
                              {"field": fields[0], "operator": fields[1][1:], "value": fields[2]}]})
        else:
          data.append({"field": fields[0], "operator": fields[1], "value": fields[2]})

        fields = []
        f = 0

    if data:
      if condition:
        return { condition: data }
      else:
        return data[0]
    else:
      return data

  def parseSQLOrder(self, order):
    if type(order) is dict: return order

    order = order.strip()

    if not order: return []

    if order.lower().startswith("order by "):
      order = order[9:]

    PATTERN = re.compile(r'''((?:[^ "']|"[^"]*"|'[^']*')+)''')

    data = []
    fields = []
    f = 0
    for word in PATTERN.split(order)[1::2]:
      fields.append(word)
      f += 1

      if f == 2:
        if fields[0].startswith("t."): fields[0] = fields[0][2:]
        if fields[0] == "id": fields[0] = "textureid"
        if fields[1].lower().startswith("asc"):
          fields[1] = "ascending"
        else:
          fields[1] = "descending"

        data.append({"method": fields[0], "order": fields[1]})
        break

    return data[0] if data else data

  def getTextures(self, filter=None, order=None, allfields=False):
    REQUEST = {"method": "Textures.GetTextures",
               "params": {"properties": ["cachedurl", "url"]}}

    if allfields:
      REQUEST["params"]["properties"].extend(["lasthashcheck", "imagehash", "sizes"])

    if filter:
        param = self.parseSQLFilter(filter)
        if param:
          REQUEST["params"]["filter"] = param

#    if order:
#        param = self.parseSQLOrder(order)
#        if param:
#          REQUEST["params"]["sort"] = param

    return self.sendJSON(REQUEST, "libTextures", checkResult=False)

  def delTexture(self, id):
    REQUEST = {"method": "Textures.RemoveTexture",
               "params": {"textureid": id}}

    return self.sendJSON(REQUEST, "libTextures", checkResult=False)

#
# Hold and print some pretty totals.
#
class MyTotals(object):
  def __init__(self, lastRunDateTime):
    self.LASTRUNDATETIME = lastRunDateTime

    self.TIMES = {}

    self.ETIMES = {}

    self.THREADS = {}
    self.THREADS_HIST = {}
    self.HISTORY = []
    self.PCOUNT = self.PMIN = self.PAVG = self.PMAX = 0

    self.TOTALS = {}
    self.TOTALS["Skipped"] = {}
    self.TOTALS["Deleted"] = {}
    self.TOTALS["Duplicate"] = {}
    self.TOTALS["Error"] = {}
    self.TOTALS["Cached"] = {}
    self.TOTALS["Ignored"] = {}
    self.TOTALS["Undefined"] = {}

  def addSeasonAll(self):
    if not "Season-all" in self.TOTALS:
      self.TOTALS["Season-all"] = {}

  def addNotCached(self):
    if not "Not in Cache" in self.TOTALS:
      self.TOTALS["Not in Cache"] = {}

  def TimeStart(self, mediatype, item):
    if not mediatype in self.TIMES: self.TIMES[mediatype] = {}
    self.TIMES[mediatype][item] = (time.time(), 0)

  def TimeEnd(self, mediatype, item):
    self.TIMES[mediatype][item] = (self.TIMES[mediatype][item][0], time.time())

  def TimeDuration(self, item):
    tElapsed = 0
    for m in self.TIMES:
      for i in self.TIMES[m]:
        if i == item:
          tuple = self.TIMES[m][i]
          tElapsed += (tuple[1] - tuple[0])
    return tElapsed

  def gotTimeDuration(self, item):
    for m in self.TIMES:
      for i in self.TIMES[m]:
        if i == item:
          return True
    return False

  def init(self, name = ""):
    with threading.Lock():
      tname = threading.current_thread().name if name == "" else name
      self.THREADS[tname] = 0
      self.THREADS_HIST[tname] = (0, 0)

  # Record start time for an image type.
  def start(self, mediatype, imgtype):
    with threading.Lock():
      tname = threading.current_thread().name
      ctime = time.time()
      self.THREADS[tname] = ctime
      if not mediatype in self.ETIMES: self.ETIMES[mediatype] = {}
      if not imgtype in self.ETIMES[mediatype]: self.ETIMES[mediatype][imgtype] = {}
      if not tname in self.ETIMES[mediatype][imgtype]: self.ETIMES[mediatype][imgtype][tname] = (ctime, 0)

  # Record current time for imgtype - this will allow stats to
  # determine cumulative time taken to download an image type.
  def finish(self, mediatype, imgtype):
    with threading.Lock():
      tname = threading.current_thread().name
      ctime = time.time()
      self.THREADS_HIST[tname] = (self.THREADS[tname], ctime)
      self.THREADS[tname] = 0
      self.ETIMES[mediatype][imgtype][tname] = (self.ETIMES[mediatype][imgtype][tname][0], ctime)

  def stop(self):
    self.init()

  # Increment counter for action/imgtype pairing
  def bump(self, action, imgtype):
    with threading.Lock():
      if not action in self.TOTALS: self.TOTALS[action] = {}
      if not imgtype in self.TOTALS[action]: self.TOTALS[action][imgtype] = 0
      self.TOTALS[action][imgtype] += 1

  # Calculate average performance per second.
  # Record history of averages to use as a basic smoothing function
  # Calculate and store min/max/avg peak performance.
  def getPerformance(self, remaining):

    active = tmin = tmax = 0

    with threading.Lock():
      for t in self.THREADS_HIST:
        times = self.THREADS_HIST[t]
        if times[0] != 0:
          active += 1
          if tmin == 0 or times[0] < tmin: tmin = times[0]
          if times[1] > tmax: tmax = times[1]

      if tmax == 0: return ""

      tpersec = active / (tmax - tmin)

      self.PCOUNT += 1
      self.PAVG += tpersec
      if self.PMIN == 0 or tpersec < self.PMIN: self.PMIN = tpersec
      if tpersec > self.PMAX: self.PMAX = tpersec

      # Maintain history of times to smooth out performance result...
      self.HISTORY.insert(0,tpersec)
      if len(self.HISTORY) > 25: self.HISTORY.pop()
      tpersec = 0
      for t in self.HISTORY: tpersec += t
      tpersec = tpersec/len(self.HISTORY)

    eta = self.secondsToTime(remaining / tpersec, withMillis=False)
    return " (%05.2f downloads per second, ETA: %s)" % (tpersec, eta)

  def libraryStats(self, item="", multi=[], filter="", lastRun=False, query=""):
    if multi: item = "/".join(multi)

    # Determine the artwork types that have been accumulated
    items = {}
    for a in self.TOTALS:
      for c in self.TOTALS[a]:
        if c not in items: items[c] = None

    # Ensure some basic items are included in the summary
    if item.find("pvr.") != -1:
      if "thumbnail" not in items: items["thumbnail"] = None
    else:
      if "fanart" not in items: items["fanart"] = None
    if item.find("movies") != -1:
      if "poster" not in items: items["poster"] = None
    if item.find("tvshows") != -1:
      if "thumb" not in items: items["thumb"] = None
    if item.find("artists") != -1 or \
       item.find("albums") != -1 or \
       item.find("songs") != -1:
      if "thumbnail" not in items:
        items["thumbnail"] = None

    DOWNLOAD_LABEL = "Download Time"

    sortedItems = sorted(items.items())
    sortedItems.append(("TOTAL", None))
    items["TOTAL"] = 0

    sortedTOTALS = sorted(self.TOTALS.items())
    sortedTOTALS.append(("TOTAL", {}))
    self.TOTALS["TOTAL"] = {}

    if len(self.THREADS_HIST) != 0:
      sortedTOTALS.append((DOWNLOAD_LABEL, {}))
      self.TOTALS[DOWNLOAD_LABEL] = {"TOTAL": 0}

    # Transfer elapsed times for each image type to our matrix of values
    # Times are held by mediatype, so accumulate for each mediatype
    # Total Download Time is sum of elapsed time for each mediatype
      self.TOTALS[DOWNLOAD_LABEL]["TOTAL"] = 0
      for mtype in self.ETIMES:
        tmin = tmax = mmin = mmax = 0.0
        for itype in self.ETIMES[mtype]:
          itmin = itmax = mtmin = mtmax = 0.0
          for tname in self.ETIMES[mtype][itype]:
            tuple = self.ETIMES[mtype][itype][tname]
            if tname.startswith("Main"):
              mtmin = tuple[0]
              mtmax = tuple[1]
            else:
              if tuple[0] < itmin or itmin == 0.0: itmin = tuple[0]
              if tuple[1] > itmax: itmax = tuple[1]
              if itype not in self.TOTALS[DOWNLOAD_LABEL]: self.TOTALS[DOWNLOAD_LABEL][itype] = 0
          self.TOTALS[DOWNLOAD_LABEL][itype] = (itmax - itmin) + (mtmax - mtmin)
          if itmin < tmin or tmin == 0.0: tmin = itmin
          if itmax > tmax: tmax = itmax
          if mtmin < mmin or mmin == 0.0: mmin = mtmin
          if mtmax > mmax: mmax = mtmax
        self.TOTALS[DOWNLOAD_LABEL]["TOTAL"] += (tmax - tmin) + (mmax - mmin)

    line0 = "Cache pre-load activity summary for \"%s\"" % item
    if filter != "": line0 = "%s, filtered by \"%s\"" % (line0, filter)
    if lastRun and self.LASTRUNDATETIME: line0 = "%s, added since %s" % (line0, self.LASTRUNDATETIME)
    line0 = "%s:" % line0

    line1 = "%-14s" % " "
    line2 = "-" * 14
    for i in sortedItems:
      i = i[1] if i[1] else i[0]
      width = 12 if len(i) < 12 else len(i)+1
      line1 = "%s| %s" % (line1, i.center(width))
      line2 = "%s+-%s" % (line2, "-" * width)

    print("")
    print(line0)
    print("")
    print(line1)
    print(line2)

    for a in sortedTOTALS:
      a = a[0]
      if a != DOWNLOAD_LABEL: self.TOTALS[a]["TOTAL"] = 0
      if a == "TOTAL": print(line2.replace("-","=").replace("+","="))
      line = "%-13s " % a
      for i in sortedItems:
        i = i[0]
        if a == "TOTAL":
          value = "%d" % items[i] if items[i] != None else "-"
        elif a == DOWNLOAD_LABEL:
          if i in self.TOTALS[a] and self.TOTALS[a][i] != 0:
            value = self.secondsToTime(self.TOTALS[a][i])
          else:
            value = "-"
        elif i in self.TOTALS[a]:
          ivalue = self.TOTALS[a][i]
          value = "%d" % ivalue
          if items[i] == None: items[i] = 0
          items[i] += ivalue
          self.TOTALS[a]["TOTAL"] += ivalue
        else:
          value = "-"
        width = 12 if len(i) < 12 else len(i)+1
        line = "%s| %s" % (line, value.center(width))
      print(line)

    print("")
    self.libraryStatsSummary()

  def libraryStatsSummary(self):
    # Failed to load anything so don't display time stats that we don't have
    if not self.gotTimeDuration("Load"): return

    if len(self.THREADS_HIST) != 0:
      tcount = 0
      for tname in self.THREADS_HIST:
        if not tname.startswith("Main"):
          tcount += 1
      print("  Threads Used: %d" % tcount)
      print("   Min/Avg/Max: %3.2f / %3.2f / %3.2f" % (self.PMIN, self.PAVG/self.PCOUNT, self.PMAX))
      print("")

    print("       Loading: %s" % self.secondsToTime(self.TimeDuration("Load")))
    print("       Parsing: %s" % self.secondsToTime(self.TimeDuration("Parse")))
    if self.gotTimeDuration("Compare"):
      print("     Comparing: %s" % self.secondsToTime(self.TimeDuration("Compare")))
    if self.gotTimeDuration("Rescan"):
      print("    Rescanning: %s" % self.secondsToTime(self.TimeDuration("Rescan")))

    if self.gotTimeDuration("PreDelete"):
      print("  Pre-Deleting: %s" % self.secondsToTime(self.TimeDuration("PreDelete")))

    if len(self.THREADS_HIST) != 0:
      print("   Downloading: %s" % self.secondsToTime(self.TimeDuration("Download")))

    print(" TOTAL RUNTIME: %s" % self.secondsToTime(self.TimeDuration("Total")))

  def secondsToTime(self, seconds, withMillis=True):
    ms = int(100 * (seconds - int(seconds)))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)

    if d == 0:
      t = "%02d:%02d:%02d" % (h, m, s)
    else:
      t = "%dd %02d:%02d:%02d" % (d, h, m, s)

    if withMillis: t = "%s.%02d" % (t, ms)

    return t

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
    self.status = 1 # 0=Ignore/Skipped, 1=To be cached, 2=Queued for downloading
    self.mtype = mediaType
    self.itype = imageType
    self.name = name
    self.season = season
    self.episode = episode
    self.filename = filename
    self.decoded_filename = MyUtility.normalise(self.filename, strip=True) if self.filename else self.filename
    self.dbid = dbid
    self.cachedurl = cachedurl
    self.libraryid = libraryid
    self.missingOK = missingOK

  def __str__(self):
    season = "\"%s\"" % self.season if self.season else self.season
    episode = "\"%s\"" % self.episode if self.episode else self.episode
    cachedurl = "\"%s\"" % self.cachedurl if self.cachedurl else self.cachedurl

    return "{%d, \"%s\", \"%s\", \"%s\", %s, %s, \"%s\", %d, %s, %s, %s}" % \
            (self.status, self.mtype, self.itype, self.name, season, episode, \
             self.decoded_filename, self.dbid, cachedurl, \
             self.libraryid, self.missingOK)

  def getFullName(self):
    if self.episode:
      if self.mtype == "tvshows":
        return "%s, %s Episode %s" % (self.name, self.season, self.episode)
      elif self.mtype == "songs":
        return "%s from: %s by: %s" % (self.name, self.episode, " & ".join(self.season))
      else:
        return "%s, %s: %s" % (self.name, self.season, self.episode)
    elif self.season:
      if self.itype == "cast.thumb":
        return "%s in %s" % (self.name, self.season)
      elif self.mtype == "tvshows":
        return "%s, %s" % (self.name, self.season)
      elif self.mtype.startswith("pvr."):
        return "%s (%s)" % (self.season, self.name)
      elif self.mtype in ["albums", "songs"]:
        return "%s by: %s" % (self.name, " & ".join(self.season))
      else:
        return "%s, %s" % (self.name, self.season)
    else:
      return "%s" % self.name

#
# Simple container for watched items.
#
class MyWatchedItem(object):
  def __init__(self, mediaType, name, episode_year, playcount, lastplayed, resume):
    self.mtype = mediaType
    self.name = name
    self.episode_year = episode_year
    self.playcount = int(playcount)
    self.lastplayed = lastplayed
    self.resume = resume
    self.libraryid = 0

    # 0 = Valid (write to Media Library)
    # 1 = Unchanged - same as Media Library (don't update Media Library)
    # 2 = Out of Date - Media Library has been updated since backup list created
    self.state = 0

    if self.episode_year == None: self.episode_year = ""

  def __str__(self):
    return "['%s', %d, '%s', '%s', %d, '%s, %s']" % \
            (self.mtype, self.libraryid, self.name, self.episode_year, self.playcount, self.lastplayed, self.resume)

  def getList(self):
    return [ self.mtype, self.libraryid, self.name, self.episode_year, self.playcount, self.lastplayed, self.resume ]

  def match(self, mediatype, name, episode_year):
    if mediatype != self.mtype: return False

    xepisode_year = episode_year
    if xepisode_year == None: xepisode_year = ""

    return (self.name == name and self.episode_year == xepisode_year)

  def refresh(self, HAS_RESUME, playcount, lastplayed, resume):
    # Update this object to reflect most recent (latest) values

    if playcount > self.playcount:   self.playcount = playcount
    if lastplayed > self.lastplayed: self.lastplayed = lastplayed

    if HAS_RESUME:
      if resume["position"] > self.resume["position"]:
        self.resume["position"] = resume["position"]

      if resume["total"] > self.resume["total"]:
        self.resume["total"] = resume["total"]

  def setState(self, HAS_RESUME, playcount, lastplayed, resume):
    # Assume no change is required
    self.state = 1

    if self.playcount == playcount and self.lastplayed == lastplayed:
      if not HAS_RESUME: return
      if self.resume == resume: return

    # Something has changed, apply object values to library
    self.state = 0
    return

# Helper class...
class MyUtility(object):
  isPython3 = (sys.version_info >= (3, 0))

  # Convert quoted filename into consistent utf-8
  # representation for both Python2 and Python3
  @staticmethod
  def normalise(value, strip=False):
    if not value: return value

    v = urllib2.unquote(value)

    if strip:
      s = 8 if v.startswith("image://") else None
      if s:
        e = -1 if v[-1:] == "/" else None
        v = v[s:e]

    if not MyUtility.isPython3:
      try:
        v = bytes(v.encode("iso-8859-1")).decode("utf-8")
      except UnicodeDecodeError:
        pass

    return v

  # Quote unquoted filename
  @staticmethod
  def denormalise(value, prefix=True):
    v = value

    if not MyUtility.isPython3:
      try:
        v = bytes(v.encode("utf-8"))
      except UnicodeDecodeError:
        pass

    v = urllib2.quote(v, "")
    if prefix: v = "image://%s/" % v

    return MyUtility.toUnicode(v)

  @staticmethod
  def toUnicode(data):
    if MyUtility.isPython3: return data

    if isinstance(data, basestring):
      if not isinstance(data, unicode):
        try:
          data = unicode(data, encoding="utf-8", errors="ignore")
        except UnicodeDecodeError:
          pass

    return data

  # Join an unquoted filename to a quoted path,
  # returning a quoted result.
  #
  # Running urllib2.quote() on a path that contains
  # foreign characters would often fail with a unicode error
  # so avoid the quote() call entirely (except on the filename
  # which should be safe (as this is only called from getSeasonAll()
  # so the only filenames are season-all-poster etc.).
  #
  @staticmethod
  def joinQuotedPath(qpath, filename):

    # Remove filename, leaving just directory.
    # Could use dirname() here but the path is quoted
    # and we need to know which slash is being used so
    # that it can be re-appended
    for qslash in ["%2f", "%5c"]:
      pos = qpath.rfind(qslash)
      if pos != -1:
        directory = "%s%s" % (qpath[:pos], qslash)
        break
    else:
      return None

    fname = urllib2.quote(os.path.basename(filename), "")

    return "%s%s/" % (directory, fname)

  #
  # Some JSON paths may have incorrect path seperators.
  # Use this function to attempt to correct those path seperators.
  #
  # Shares ("smb://", "nfs://" etc.) will always use forward slashes.
  #
  # Non-shares will use a slash appropriate to the OS to which the path
  # corresponds so attempt to find the FIRST slash (forward or back) and
  # then use that as the path seperator, replacing any of the opposite
  # kind. The reason being that path mangling addons are likely to mangle
  # only the last slashes but not the first.
  #
  # If only one type of slash found (or neither slash found), do nothing.
  #
  # See: http://forum.xbmc.org/showthread.php?tid=153502&pid=1477147#pid1477147
  #
  @staticmethod
  def fixSlashes(filename):
    # Share (eg. "smb://", "nfs://" etc.)
    if re.search("^.*://.*", filename):
      return filename.replace("\\", "/")

    bslash = filename.find("\\")
    fslash = filename.find("/")

    if bslash == -1 or fslash == -1:
      return filename
    elif bslash < fslash:
      return filename.replace("/", "\\")
    else: #fslash < bslash:
      return filename.replace("\\", "/")

  # Same as above, but url is quoted
  @staticmethod
  def fixSlashesQuoted(url):
    # Share (eg. "smb://", "nfs://" etc.)
    if re.search("^.*%3a%2f%2f.*", url):
      return url.replace("%5c", "%2f")

    bslash = url.find("%5c")
    fslash = url.find("%2f")

    if bslash == -1 or fslash == -1:
      return url
    elif bslash < fslash:
      return url.replace("%2f", "%5c")
    else: #fslash < bslash:
      return url.replace("%5c", "%2f")

  @staticmethod
  def getIMDBInfo(imdbnumber, plotFull=False, plotOutline=False):
    try:
      base_url = "http://www.omdbapi.com"

      if plotOutline or not plotFull:
        f = urllib2.urlopen("%s?i=%s&plot=short" % (base_url, imdbnumber))
        data = json.loads(f.read().decode("utf-8"))
        outline = data.get("Plot", None)
      else:
        outline=None

      if plotFull:
        f = urllib2.urlopen("%s?i=%s&plot=full" % (base_url, imdbnumber))
        data = json.loads(f.read().decode("utf-8"))

      # Convert omdbapi.com fields to xbmc fields - mostly just a case
      # of converting to lowercase, and removing "imdb" prefix
      newdata = {}
      for key in data:
        newkey = key.replace("imdb", "").lower()
        try:
          # Convert rating from str to float
          if newkey == "rating":
            newdata[newkey] = float(data[key])
          # Munge plot/plotoutline together as required
          elif newkey == "plot":
            if plotOutline and outline:
              newdata["plotoutline"] = outline
            if plotFull:
              newdata["plot"] = data[key]
          # Convert genre to a list
          elif newkey == "genre":
            newdata[newkey] = [g.strip() for g in data[key].split(",")]
          # Year to an int
          elif newkey == "year":
            newdata[newkey] = int(data[key])
          # Runtime from "2 h", "36 min", "2 h 22 min" or "N/A" to seconds
          elif newkey == "runtime":
            t = data[key]
            h = re.search("([0-9]+) h", t)
            m = re.search("([0-9]+) min", t)
            r = 0
            r += (int(h.group(1))*3600) if h else 0
            r += (int(m.group(1))*60) if m else 0
            if r > 0:
              newdata[newkey] = r
          else:
            newdata[newkey] = data[key]
        except:
          pass
      return newdata
    except urllib2.URLError:
      return None

#
# Load data using JSON-RPC. In the case of TV Shows, also load Seasons
# and Episodes into a single data structure.
#
# Sets doesn't support filters, so filter this list after retrieval.
#
def jsonQuery(action, mediatype, filter="", force=False, extraFields=False, rescan=False, \
                      decode=False, ensure_ascii=True, nodownload=False, lastRun=False, \
                      labels=None, query="", filename=None, wlBackup=True):

  if mediatype not in ["addons", "agenres", "vgenres", "albums", "artists", "songs",
                       "movies", "sets", "tags", "tvshows", "pvr.tv", "pvr.radio"]:
    gLogger.err("Error: %s is not a valid media class" % mediatype, newLine=True)
    sys.exit(2)

  # Only QA movies and tvshows (and sub-types) for now...
  if action == "qa" and rescan and mediatype not in ["movies", "tags", "sets", "tvshows", "seasons", "episodes"]:
    gLogger.err("Error: media class [%s] is not currently supported by qax" % mediatype, newLine=True)
    sys.exit(2)

  # Only songs, movies and tvshows (and sub-types) valid for missing...
  if action == "missing" and mediatype not in ["songs", "movies", "tvshows", "seasons", "episodes"]:
    gLogger.err("Error: media class [%s] is not currently supported by missing" % mediatype, newLine=True)
    sys.exit(2)

  # Only movies and tvshows for "watched"...
  if action == "watched" and mediatype not in ["movies", "tvshows"]:
    gLogger.err("Error: media class [%s] is not currently supported by watched" % mediatype, newLine=True)
    sys.exit(2)

  # Only movies for "imdb"...
  if action == "imdb" and mediatype not in ["movies"]:
    gLogger.err("Error: media class [%s] is not currently supported by imdb" % mediatype, newLine=True)
    return

  TOTALS.TimeStart(mediatype, "Total")

  jcomms = MyJSONComms(gConfig, gLogger)
  database = MyDB(gConfig, gLogger)

  if mediatype == "tvshows": TOTALS.addSeasonAll()

  gLogger.progress("Loading %s..." % mediatype)

  TOTALS.TimeStart(mediatype, "Load")

  if action == "query":
    secondaryFields = parseQuery(query)[0]
  else:
    secondaryFields = None

  if mediatype in ["pvr.tv", "pvr.radio"] and not gConfig.HAS_PVR:
    (section_name, title_name, id_name, data) = ("", "", "", [])
  elif mediatype == "vgenres":
    _data = []
    for subtype in ["movie", "tvshow", "musicvideo"]:
      (section_name, title_name, id_name, data) = jcomms.getData(action, mediatype, filter, extraFields, lastRun=lastRun, secondaryFields=secondaryFields, subType=subtype)
      if data and "result" in data and section_name in data["result"]:
        if filter != "":
          filteredData = []
          for d in data["result"][section_name]:
            if re.search(filter, d[title_name], re.IGNORECASE):
              filteredData.append(d)
          data["result"][section_name] = filteredData
        if len(data["result"][section_name]) > 0:
          _data.append({"type": subtype, section_name: data["result"][section_name]})
    title_name = "type"
    section_name = mediatype
    data["result"] = { section_name: _data}
  else:
    (section_name, title_name, id_name, data) = jcomms.getData(action, mediatype, filter, extraFields, lastRun=lastRun, secondaryFields=secondaryFields)

  if data and "result" in data and section_name in data["result"]:
    data = data["result"][section_name]
  else:
    data = []

  # Manually filter these mediatypes as JSON doesn't support filtering
  if data and filter and mediatype in ["addons", "agenres", "sets", "pvr.tv", "pvr.radio"]:
    gLogger.log("Filtering %s on %s = %s" % (mediatype, title_name, filter))
    filteredData = []
    for d in data:
      if re.search(filter, d[title_name], re.IGNORECASE):
        filteredData.append(d)
    data = filteredData

  # Add movie file members to sets when dumping
  if action == "dump" and mediatype == "sets" and gConfig.ADD_SET_MEMBERS and data:
    gLogger.progress("Loading movie set members...")
    (s, t, i, fdata) = jcomms.getData(action, "sets-members", filter, extraFields, lastRun=lastRun, secondaryFields=None)
    if fdata and "result" in fdata and s in fdata["result"]:
      set_files = {}
      for movie in fdata["result"][s]:
        set_name = movie["set"]
        if set_name:
          del movie["set"]
          if "label" in movie: del movie["label"]
          if set_name not in set_files: set_files[set_name] = []
          set_files[set_name].append(movie)
      for set in data:
        set["tc.members"] = set_files.get(set["title"], [])

  # Combine PVR channelgroups with PVR channels to create a hierarchical structure that can be parsed
  if mediatype in ["pvr.tv", "pvr.radio"]:
    pvrdata = []
    for cg in data:
      (s1, t1, i1, data1) = jcomms.getData(action, "%s.channel" % mediatype, filter, extraFields, channelgroupid=cg["channelgroupid"], lastRun=lastRun, secondaryFields=secondaryFields)
      if "result" in data1:
        channels = []
        for channel in data1["result"].get(s1, []):
          if "label" in channel: del channel["label"]
          channels.append(channel)
        pvrdata.append({"label":          cg["label"],
                        "channeltype":    cg["channeltype"],
                        "channelgroupid": cg["channelgroupid"],
                        "channels": channels})
    data = pvrdata

  if mediatype == "tvshows":
    for tvshow in data:
      title = tvshow["title"]
      gLogger.progress("Loading TV Show: [%s]..." % title)
      (s2, t2, i2, data2) = jcomms.getData(action, "seasons", filter, extraFields, showid=tvshow[id_name], lastRun=lastRun)
      if not "result" in data2: return
      limits = data2["result"]["limits"]
      if limits["total"] == 0: continue
      tvshow[s2] = data2["result"][s2]
      for season in tvshow[s2]:
        seasonid = season["season"]
        gLogger.progress("Loading TV Show: [%s, Season %d]..." % (title, seasonid))
        (s3, t3, i3, data3) = jcomms.getData(action, "episodes", filter, extraFields, showid=tvshow[id_name], seasonid=season[i2], lastRun=lastRun, secondaryFields=secondaryFields)
        if not "result" in data3: return
        limits = data3["result"]["limits"]
        if limits["total"] == 0: continue
        season[s3] = data3["result"][s3]

  if lastRun and mediatype in ["movies", "tvshows"]:
    # Create a new list containing only tvshows with episodes...
    if mediatype == "tvshows":
      newData = []
      for tvshow in data:
        newtvshow = {}
        epCount = 0
        for season in tvshow.get("seasons", {}):
          if season.get("episodes", None):
            if newtvshow == {}:
              newtvshow = tvshow
              del newtvshow["seasons"]
              newtvshow["seasons"] = []
            newtvshow["seasons"].append(season)
            epCount += len(season.get("episodes", {}))
        if newtvshow != {}:
          newData.append(newtvshow)
          gLogger.out("Recently added TV Show: %s (%d episode%s)" % (tvshow.get("title"), epCount, "s"[epCount==1:]), newLine=True)
      data = newData
    else:
      for item in data:
        gLogger.out("Recently added Movie: %s" % item.get("title", item.get("artist", item.get("name", None))), newLine=True)

    if len(data) != 0: gLogger.out("", newLine=True)

  TOTALS.TimeEnd(mediatype, "Load")

  if data != []:
    if action == "cache":
      cacheImages(mediatype, jcomms, database, data, title_name, id_name, force, nodownload)
    elif action == "qa":
      qaData(mediatype, jcomms, database, data, title_name, id_name, rescan)
    elif action == "dump":
      jcomms.dumpJSON(data, decode, ensure_ascii)
    elif action == "missing":
      fileList = jcomms.getAllFilesForSource(mediatype, labels)
      missingFiles(mediatype, data, fileList, title_name, id_name)
    elif action == "query":
      queryLibrary(mediatype, query, data, title_name, id_name)
    elif action == "watched" and wlBackup:
      watchedBackup(mediatype, filename, data, title_name, id_name)
    elif action == "watched" and not wlBackup:
      watchedRestore(mediatype, jcomms, filename, data, title_name, id_name)
    elif action == "duplicates":
      duplicatesList(mediatype, jcomms, data)
    elif action == "imdb":
      updateIMDb(mediatype, jcomms, data)
    else:
      raise ValueError("Unknown action [%s]" % action)

  gLogger.progress("")

  TOTALS.TimeEnd(mediatype, "Total")

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
def cacheImages(mediatype, jcomms, database, data, title_name, id_name, force, nodownload):

  mediaitems = []
  imagecache = {}
  imagecache[""] = 0 # Ensure an empty image is already in the imagecache, with a zero reference count

  TOTALS.TimeStart(mediatype, "Parse")

  parseURLData(jcomms, mediatype, mediaitems, imagecache, data, title_name, id_name)

  TOTALS.TimeEnd(mediatype, "Parse")

  # Don't need this data anymore, make it available for garbage collection
  del data, imagecache

  TOTALS.TimeStart(mediatype, "Compare")

  gLogger.progress("Loading database items...")
  dbfiles = {}
  with database:
    for r in database.getRows(allfields=False):
      dbfiles[r["url"]] = r

  gLogger.log("Loaded %d items from texture cache database" % len(dbfiles))

  gLogger.progress("Matching database items...")

  ITEMLIMIT = -1 if nodownload else 100

  itemCount = 0
  for item in mediaitems:
    if item.mtype == "tvshows" and item.season == "Season All": TOTALS.bump("Season-all", item.itype)

    dbrow = dbfiles.get(item.decoded_filename, None)

    # Don't need to cache file if it's already in the cache, unless forced...
    # Assign the texture cache database id and cachedurl so that removal will avoid having
    # to retrieve these items from the database.
    if dbrow:
      if force:
        itemCount += 1
        item.status = 1
        item.dbid = dbrow["textureid"]
        item.cachedurl = dbrow["cachedurl"]
      else:
        item.status = 0
        TOTALS.bump("Skipped", item.itype)
        if gLogger.VERBOSE and gLogger.LOGGING: gLogger.log("ITEM SKIPPED: %s" % item)
    # These items we are missing from the cache...
    else:
      itemCount += 1
      item.status = 1
      if not force:
        if ITEMLIMIT == -1 or itemCount < ITEMLIMIT:
          MSG = "Need to cache: [%-10s] for %s: %s\n" % (item.itype.center(10), re.sub("(.*)s$", "\\1", item.mtype), item.getFullName())
          gLogger.out(MSG)
        elif itemCount == ITEMLIMIT:
          gLogger.out("...and many more! (First %d items shown)\n" % ITEMLIMIT)

  TOTALS.TimeEnd(mediatype, "Compare")

  # Don't need this data anymore, make it available for garbage collection
  del dbfiles

  if nodownload:
    TOTALS.addNotCached()
    for item in mediaitems:
      if item.status == 1: TOTALS.bump("Not in Cache", item.itype)

  gLogger.progress("")

  if itemCount > 0 and not nodownload:
    single_work_queue = Queue.Queue()
    multiple_work_queue = Queue.Queue()
    error_queue = Queue.Queue()

    gLogger.out("\n")

    # Identify unique itypes, so we can group items in the queue
    # This is crucial to working out when the first/last item is loaded
    # in order to calculate accurate elapsed times by itype
    unique_items = {}
    for item in mediaitems:
      if not item.itype in unique_items:
        unique_items[item.itype] = True

    if force and gConfig.DOWNLOAD_PREDELETE:
      TOTALS.TimeStart(mediatype, "PreDelete")
      TOTALS.init()
      dbitems = 0
      for item in mediaitems:
        if item.dbid != 0:
          dbitems += 1
      dbitem = 0
      with database:
        for ui in sorted(unique_items):
          for item in mediaitems:
            if item.dbid != 0 and item.itype == ui:
              dbitem += 1
              gLogger.progress("Pre-deleting cached items %d of %d... rowid %d, cachedurl %s" % (dbitem, dbitems, item.dbid, item.cachedurl))
              TOTALS.start(item.mtype, item.itype)
              database.deleteItem(item.dbid, item.cachedurl)
              TOTALS.bump("Deleted", item.itype)
              TOTALS.finish(item.mtype, item.itype)
              item.dbid = 0
              item.cachedurl = ""
      TOTALS.stop()
      TOTALS.TimeEnd(mediatype, "PreDelete")
      gLogger.progress("")

    c = sc = mc = 0
    for ui in sorted(unique_items):
      for item in mediaitems:
        if item.status == 1 and item.itype == ui:
          c += 1

          isSingle = False
          if gConfig.SINGLETHREAD_URLS:
            for site in gConfig.SINGLETHREAD_URLS:
              if site.search(item.decoded_filename):
                sc += 1
                if gLogger.VERBOSE and gLogger.LOGGING: gLogger.log("QUEUE ITEM: single [%s], %s" % (site.pattern, item))
                single_work_queue.put(item)
                item.status = 2
                isSingle = True
                break

          if not isSingle:
            mc += 1
            if gLogger.VERBOSE and gLogger.LOGGING: gLogger.log("QUEUE ITEM: %s" % item)
            multiple_work_queue.put(item)
            item.status = 2

          gLogger.progress("Queueing work item: Single thread %d, Multi thread %d" % (sc, mc), every=50, finalItem=(c==itemCount))

    # Don't need this data anymore, make it available for garbage collection
    del mediaitems

    TOTALS.TimeStart(mediatype, "Download")

    THREADS = []

    if not single_work_queue.empty():
      gLogger.log("Creating 1 download thread for single access sites")
      t = MyImageLoader(True, single_work_queue, multiple_work_queue, error_queue, itemCount,
                        gConfig, gLogger, TOTALS, force, gConfig.DOWNLOAD_RETRY)
      THREADS.append(t)
      t.setDaemon(True)

    if not multiple_work_queue.empty():
      tCount = gConfig.DOWNLOAD_THREADS["download.threads.%s" % mediatype]
      THREADCOUNT = tCount if tCount <= mc else mc
      gLogger.log("Creating %d download thread(s) for multi-access sites" % THREADCOUNT)
      for i in range(THREADCOUNT):
        t = MyImageLoader(False, multiple_work_queue, single_work_queue, error_queue, itemCount,
                          gConfig, gLogger, TOTALS, force, gConfig.DOWNLOAD_RETRY)
        THREADS.append(t)
        t.setDaemon(True)

    # Start the threads...
    for t in THREADS: t.start()

    try:
      ALIVE = True
      while ALIVE:
        ALIVE = False
        for t in THREADS: ALIVE = True if t.isAlive() else ALIVE
        if ALIVE: time.sleep(1.0)
    except (KeyboardInterrupt, SystemExit):
      stopped.set()
      gLogger.progress("Please wait while threads terminate...")
      ALIVE = True
      while ALIVE:
        ALIVE = False
        for t in THREADS: ALIVE = True if t.isAlive() else ALIVE
        if ALIVE: time.sleep(0.1)

    TOTALS.TimeEnd(mediatype, "Download")

    gLogger.progress("", newLine=True, noBlank=True)

    if not error_queue.empty():
      gLogger.out("\nThe following items could not be downloaded:\n\n")
      while not error_queue.empty():
        item = error_queue.get()
        name = item.getFullName()[:40]
        gLogger.out("[%-10s] [%-40s] %s\n" % (item.itype, name, item.decoded_filename))
        gLogger.log("ERROR ITEM: %s" % item)
        error_queue.task_done()

#
# Iterate over all the elements, seeking out artwork to be stored in a list.
# Use recursion to process season and episode sub-elements.
#
def parseURLData(jcomms, mediatype, mediaitems, imagecache, data, title_name, id_name, showName = None, season = None, pvrGroup = None):
  gLogger.reset()

  SEASON_ALL = (showName != None and season == None)

  for item in data:
    if title_name in item: title = item[title_name]

    if showName:
      mediatype = "tvshows"
      name = showName
      if season:
        episode = re.sub("([0-9]*x[0-9]*)\..*", "\\1", title)
        longName = "%s, %s Episode %s" % (showName, season, episode)
      else:
        season = title
        episode = None
        longName = "%s, %s" % (showName, title)
    elif pvrGroup:
        name = pvrGroup
        season = title
        longName = "%s, %s" % (pvrGroup, title)
        episode = None
    else:
      name = title
      longName = name
      season = item.get("artist", None) if title_name != "artist" else None
      episode= item.get("album", None) if title_name != "album" else None

    gLogger.progress("Parsing [%s]..." % longName, every = 25)

    for a in ["fanart", "poster", "thumb", "thumbnail"]:
      if a in item and evaluateURL(a, item[a], imagecache):
        mediaitems.append(MyMediaItem(mediatype, a, name, season, episode, item[a], 0, None, item[id_name], False))

    if "art" in item:
      if SEASON_ALL and "poster" in item["art"]:
        SEASON_ALL = False
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
        if "thumbnail" in a and evaluateURL("cast.thumb", a["thumbnail"], imagecache):
          mediaitems.append(MyMediaItem(mediatype, "cast.thumb", a["name"], name, None, a["thumbnail"], 0, None, item[id_name], False))

    if mediatype in ["artists", "albums", "movies", "tags", "tvshows"]:
      for file in jcomms.getExtraArt(item):
        if evaluateURL(file["type"], file["file"], imagecache):
          mediaitems.append(MyMediaItem(mediatype, file["type"], name, season, episode, file["file"], 0, None, item[id_name], False))

    if "seasons" in item:
      parseURLData(jcomms, "seasons", mediaitems, imagecache, item["seasons"], "label", "season", showName=title)
    elif "episodes" in item:
      parseURLData(jcomms, "episodes", mediaitems, imagecache, item["episodes"], "label", "episodeid", showName=showName, season=title)
      season = None
    elif "channels" in item:
      parseURLData(jcomms, "%s.channel" % mediatype, mediaitems, imagecache, item["channels"], "channel", "channelid", pvrGroup=title)
    elif "genres" in item:
      parseURLData(jcomms, "genres", mediaitems, imagecache, item["genres"], "label", "genreid", showName=title)

# Include or exclude url depending on basic properties - has it
# been "seen" before (in which case, discard as no point caching
# it twice. Or discard if matches an "ignore" rule.
#
# Otherwise include it, and add it to the imagecache so it can
# be excluded in future if "seen" again.
#
def evaluateURL(imgtype, url, imagecache):
  if not url or url == "":
    TOTALS.bump("Undefined", imgtype)
    imagecache[""] += 1
    return False

  if gConfig.CACHE_ARTWORK and imgtype not in gConfig.CACHE_ARTWORK:
    if gLogger.LOGGING:
      decoded_url = MyUtility.normalise(url, strip=True)
      gLogger.log("Ignored [%-12s] for [%s] as image type not in cache.artwork list" % (imgtype, decoded_url))
    TOTALS.bump("Ignored", imgtype)
    imagecache[url] = 1
    return False

  if url in imagecache:
    TOTALS.bump("Duplicate", imgtype)
    imagecache[url] += 1
    return False

  if gConfig.CACHE_IGNORE_TYPES:
    decoded_url = MyUtility.normalise(url, strip=True)
    for ignore in gConfig.CACHE_IGNORE_TYPES:
      if ignore.search(decoded_url):
        gLogger.log("Ignored [%-12s] image due to [%s] rule: %s" % (imgtype, ignore.pattern, decoded_url))
        TOTALS.bump("Ignored", imgtype)
        imagecache[url] = 1
        return False

  imagecache[url] = 0
  return True

def qaData(mediatype, jcomms, database, data, title_name, id_name, rescan, work=None, mitems=None, showName=None, season=None, pvrGroup=None):
  gLogger.reset()

  if mitems == None:
      TOTALS.TimeStart(mediatype, "Parse")
      workItems= {}
      mediaitems = []
  else:
      workItems = work
      mediaitems = mitems

  zero_items = []
  blank_items = []
  art_items = []
  check_file = False

  check_file = (gConfig.QA_FILE and mediatype in ["movies", "tags", "episodes"])

  zero_items.extend(gConfig.getQAFields("zero", mediatype, stripModifier=False))
  blank_items.extend(gConfig.getQAFields("blank", mediatype, stripModifier=False))
  art_items.extend(gConfig.getQAFields("art", mediatype, stripModifier=False))

  #Hack to prevent top level genre group items (movie, tvshow, musicvideo) being
  #reported as having missing artwork (since they don't have any artwork).
  if mediatype == "vgenres" and not showName:
    zero_items = blank_items = art_items = []

  for item in data:
    title = item.get(title_name, "")
    libraryid = item.get(id_name, 0)

    if showName:
      if season:
        episode = re.sub("([0-9]*x[0-9]*)\..*", "\\1", title)
        name = "%s, %s Episode %s" % (showName, season, episode)
      else:
        episode = None
        name = "%s, %s" % (showName, title)
    elif pvrGroup:
        name = "%s, %s" % (pvrGroup, title)
    else:
      name = title
      season = None
      episode = None

    gLogger.progress("Parsing [%s]..." % name, every = 25)

    missing = {}

    for i in zero_items:
      j = i[1:] if i.startswith("?") else i
      ismissing = True
      if j in item:
        ismissing = (item[j] == 0)
      if missing: missing["Zero %s" % j] = not i.startswith("?")

    for i in blank_items:
      j = i[1:] if i.startswith("?") else i
      ismissing = True
      if j in item:
        if type(item[j]) is dict:
          # Example dict: streamdetails
          for field in item[j]:
            if item[j][field]:
              ismissing = False
              break
        else:
          ismissing = (item[j] == "" or item[j] == [] or item[j] == [""])
      if ismissing: missing["Missing %s" % j] = not i.startswith("?")

    for i in art_items:
      j = i[1:] if i.startswith("?") else i
      if "art" in item:
        artwork = item.get("art", {}).get(j, "")
      else:
        artwork = item.get(j, "")
      if artwork == "":
        missing["Missing %s" % j] = not i.startswith("?")
      else:
        decoded_url = MyUtility.normalise(artwork, strip=True)
        FAILED = False
        if gConfig.QA_FAIL_TYPES:
          for qafailtype in gConfig.QA_FAIL_TYPES:
            if qafailtype.search(decoded_url):
              missing["Fail URL (%s, \"%s\")" % (j, qafailtype.pattern)] = True
              FAILED = True
              break
        if not FAILED and gConfig.QA_WARN_TYPES:
          for qawarntype in gConfig.QA_WARN_TYPES:
            if qawarntype.search(decoded_url):
              missing["Warn URL (%s, \"%s\")" % (j, qawarntype.pattern)] = False
              break

    if check_file and "file" in item:
      for file in unstackFiles(item["file"]):
        if not jcomms.getFileDetails(file):
          missing["file"] = False
          break

    if "seasons" in item:
      qaData("seasons", jcomms, database, item["seasons"], "label", "season", False, \
              work=workItems, mitems=mediaitems, showName=title)
    if "episodes" in item:
      qaData("episodes", jcomms, database, item["episodes"], "label", "episodeid", False, \
              work=workItems, mitems=mediaitems, showName=showName, season=title)
      season = None
    if "channels" in item:
      qaData("%s.channel" % mediatype, jcomms, database, item["channels"], "channel", "channelid", False, \
              work=workItems, mitems=mediaitems, pvrGroup=title)
    if "genres" in item:
      qaData(mediatype, jcomms, database, item["genres"], "label", "genreid", False, \
              work=workItems, mitems=mediaitems, showName=title)

    if missing != {}:
      if mediatype.startswith("pvr.") or mediatype in ["agenres", "vgenres"]:
        mtype = mediatype
      else:
        mtype = mediatype[:-1].capitalize()
        if mtype == "Tvshow": mtype = "TVShow"
      mediaitems.append("%s [%-50s]: %s" % (mtype, addEllipsis(50, name), ", ".join(missing)))
      if "file" in item and "".join(["Y" if missing[m] else "" for m in missing]) != "":
        dir = "%s;%s" % (mediatype, os.path.dirname(unstackFiles(item["file"])[0]))
        libraryids = workItems[dir] if dir in workItems else []
        libraryids.append(libraryid)
        workItems[dir] = libraryids
#      else:
#        gLogger.out("ERROR: No file for QA item - won't rescan [%s]" % name, newLine=True)

  if mitems == None:
    TOTALS.TimeEnd(mediatype, "Parse")
    gLogger.progress("")
    for m in mediaitems: gLogger.out("%s\n" % m)

  if rescan:
    TOTALS.TimeStart(mediatype, "Rescan")
    jcomms.rescanDirectories(workItems)
    TOTALS.TimeEnd(mediatype, "Rescan")

def missingFiles(mediatype, data, fileList, title_name, id_name, showName=None, season=None):
  gLogger.reset()

  if showName == None:
      TOTALS.TimeStart(mediatype, "Parse")

  for item in data:
    libraryid = item[id_name]

    if title_name in item: title = item[title_name]

    if showName:
      name = showName
      if season:
        episode = re.sub("([0-9]*x[0-9]*)\..*", "\\1", title)
        name = "%s, %s Episode %s" % (showName, season, episode)
      else:
        season = title
        episode = None
        name = "%s, %s" % (showName, season)
    else:
      name = title
      season = None
      episode = None

    gLogger.progress("Parsing [%s]..." % name, every = 25)

    # Remove matched file from fileList - what files remain at the end
    # will be reported to the user
    if mediatype != "tvshows" and "file" in item:
      for file in unstackFiles(item["file"]):
        try:
          fileList.remove(file)
        except ValueError:
          pass

    if "seasons" in item:
      missingFiles("seasons", item["seasons"], fileList, "label", "season", showName=title)
    if "episodes" in item:
      missingFiles("episodes", item["episodes"], fileList, "label", "episodeid", showName=showName, season=title)
      season = None

  if showName == None:
    TOTALS.TimeEnd(mediatype, "Parse")
    gLogger.progress("")
    if fileList != []:
      gLogger.out("The following media files are not present in the \"%s\" media library:\n\n" % mediatype)
      for file in fileList: gLogger.out("%s\n" % file)

def queryLibrary(mediatype, query, data, title_name, id_name, work=None, mitems=None, showName=None, season=None, pvrGroup=None):
  gLogger.reset()

  if mitems == None:
      TOTALS.TimeStart(mediatype, "Parse")
      workItems= {}
      mediaitems = []
  else:
      workItems = work
      mediaitems = mitems

  fields, tuples = parseQuery(query)

  for item in data:
    libraryid = item.get(id_name, 0)

    if id_name == "songid":
      if title_name in item and "artist" in item:
        title = "%s (%s)" % (item[title_name], "/".join(item["artist"]))
    else:
      if title_name in item: title = item[title_name]

    if showName:
      if season:
        episode = re.sub("([0-9]*x[0-9]*)\..*", "\\1", title)
        name = "%s, %s Episode %s" % (showName, season, episode)
      else:
        episode = None
        name = "%s, %s" % (showName, title)
    elif pvrGroup:
        name = "%s, %s" % (pvrGroup, title)
    else:
      name = title
      season = None
      episode = None

    gLogger.progress("Parsing [%s]..." % name, every = 25)

    RESULTS = []

    try:
      for field, field_split, condition, inverted, value, logic in tuples:
        temp = item
        for f in field_split:
          temp = searchItem(temp, f)
          if temp == None: break

        if temp != None:
          if type(temp) is list:
            for t in temp:
              MATCHED = evaluateCondition(t, condition, value)
              if inverted: MATCHED = not MATCHED
              if MATCHED: break
            matched_value = ", ".join(str(x) for x in temp)
          else:
            if isinstance(temp, basestring): temp = MyUtility.normalise(temp, strip=True)
            MATCHED = evaluateCondition(temp, condition, value)
            if inverted: MATCHED = not MATCHED
            matched_value = temp
        else:
          MATCHED = False
          matched_value = None

        RESULTS.append([MATCHED, logic, field, matched_value])
    except:
      pass

    MATCHED = False
    FIELDS = []
    DISPLAY = ""
    for matched, logic, field, value in RESULTS:
      if logic == "and":
        if matched == False: MATCHED = False
      elif logic == "or":
        if matched == True: MATCHED = True
      elif logic == None:
        MATCHED = matched
      else:
        MATCHED = False

      # Only output each field value once...
      if not field in FIELDS:
        FIELDS.append(field)
        try:
          throw_exception = value + 1
          DISPLAY = "%s, %s = %s" % (DISPLAY, field, value)
        except:
          DISPLAY = "%s, %s = \"%s\"" % (DISPLAY, field, value)

    if MATCHED: mediaitems.append([name, DISPLAY[2:]])

    if "seasons" in item:
      queryLibrary("seasons", query, item["seasons"], "label", "season", \
              work=workItems, mitems=mediaitems, showName=title)
    if "episodes" in item:
      queryLibrary("episodes", query, item["episodes"], "label", "episodeid", \
              work=workItems, mitems=mediaitems, showName=showName, season=title)
      season = None
    if "channels" in item:
      queryLibrary("%s.channel" % mediatype, query, item["channels"], "channel", "channelid", \
              work=workItems, mitems=mediaitems, pvrGroup=title)
    if "genres" in item:
      queryLibrary("genres", query, item["genres"], "label", "genreid", \
              work=workItems, mitems=mediaitems, showName=title)

  if mitems == None:
    TOTALS.TimeEnd(mediatype, "Parse")
    gLogger.progress("")
    for m in mediaitems:
      gLogger.out("Matched: [%-50s] %s" % (addEllipsis(50, m[0]), m[1]), newLine=True)

def addEllipsis(maxlen, aStr):
  if len(aStr) <= maxlen: return aStr

  ileft = int(maxlen/2) - 2
  iright = int(maxlen/2) - 1

  return "%s...%s" % (aStr[0:ileft], aStr[-iright:])

def unstackFiles(files):
  if files.startswith("stack://"):
    return files[8:].split(" , ")
  else:
    return [files]

def searchItem(data, field):
  if field in data: return data[field]

  if type(data) is list:
    tList = []
    for item in data:
      value = searchItem(item, field)
      if value: tList.append(value)
    return tList

  return None

def evaluateCondition(input, condition, value):
  if type(input) is int: value = int(value)
  if type(input) is float: value = float(value)

  if condition in ["=", "=="]:    return (input == value)
  elif condition == "!=":         return (input != value)
  elif condition == ">":          return (input > value)
  elif condition == "<":          return (input < value)
  elif condition == ">=":         return (input >= value)
  elif condition == "<=":         return (input <= value)
  elif condition == "contains":   return (input.find(value) != -1)
  elif condition == "startswith": return (input.startswith(value))
  elif condition == "endswith":   return (input.endswith(value))

  return False

def parseQuery(query):
  condition = ["==", "=", "!=", ">", ">=", "<", "<=", "contains", "startswith", "endswith"]
  logic = ["and", "or"]

  fields = []
  tuples = []

  FIELDNAME_NEXT = True
  tField = tValue = tCondition = tLogic = None

  query = MyUtility.toUnicode(query)

  newValue = ""
  IN_STR=False
  for value in query:
    if value == "'" or value == '"': IN_STR = not IN_STR
    if value == " " and IN_STR:
      newValue = "%s\t" % newValue
    else:
      newValue = "%s%s" % (newValue, value)

  INVERT=False
  for value in newValue.split(" "):
    if value == "": continue
    value_lower = value.lower()

    if value_lower == "not":
      INVERT=True
      continue

    #and, or etc.
    if value_lower  in logic:
      FIELDNAME_NEXT=True
      tLogic = value
    # ==, >=, contains etc.
    elif value_lower in condition:
      if value == "=": value = "=="
      FIELDNAME_NEXT=False
      tCondition = value
    #Value
    elif not FIELDNAME_NEXT:
      if value.startswith("'") or value.startswith('"'): value = value[1:]
      if value.endswith("'") or value.endswith('"'): value = value[:-1]
      FIELDNAME_NEXT=True
      tValue = value.replace("\t", " ")
      tuples.append([tField, tField.split("."), tCondition, INVERT, tValue, tLogic])
      INVERT=False
    #Field name
    else:
      tField = value_lower
      fields.append(tField.split(".")[0])
      FIELDNAME_NEXT=False

  return ",".join(fields), tuples

def watchedWrite(filename, mediaitems):
  MYLIST = []
  for m in mediaitems:
    MYLIST.append({ "type": m.mtype, "name": m.name, "episode_year": m.episode_year,
                    "playcount": m.playcount, "lastplayed": m.lastplayed, "resume": m.resume })

  try:
    OUTPUTFILE = codecs.open(filename, "wb", encoding="utf-8")
    OUTPUTFILE.write(json.dumps(MYLIST, indent=2, ensure_ascii=True))
    OUTPUTFILE.close()
  except:
    gLogger.out("ERROR: Failed to write the watched list to file [%s]" % filename, newLine=True)

def watchedRead(filename, mediaitems):
  BUFFER = ""
  try:
    INPUTFILE = codecs.open(filename, "rb", encoding="utf-8")
    BUFFER = INPUTFILE.read()
    INPUTFILE.close()

    MYLIST = json.loads(BUFFER)
    for m in MYLIST:
      mediakey = "%s;%s;%s" % (m["type"], m["name"], m["episode_year"])
      mediaitems[mediakey] = MyWatchedItem(m["type"], m["name"], m["episode_year"], m["playcount"], m["lastplayed"], m["resume"])
  except:
    gLogger.out("ERROR: Failed to read the watched list from file [%s]" % filename, newLine=True)
    return False

  return True

def watchedBackup(mediatype, filename, data, title_name, id_name, work=None, mitems=None, showName=None, season=None):
  gLogger.reset()

  if mitems == None:
      TOTALS.TimeStart(mediatype, "Parse")
      workItems= {}
      mediaitems = []
  else:
      workItems = work
      mediaitems = mitems

  for item in data:
    libraryid = item.get(id_name, 0)
    title = item.get(title_name, "")

    if showName:
      shortName = showName
      if season:
        episode_year = re.sub("([0-9]*x[0-9]*)\..*", "\\1", title)
        longName = "%s, %s Episode %s" % (showName, season, episode_year)
      else:
        episode_year = None
        longName = "%s, %s" % (showName, title)
    else:
      season = None
      episode_year = item.get("year", 0)
      longName = shortName = title

    gLogger.progress("Parsing [%s]..." % longName, every = 25)

    playcount = item.get("playcount", 0)
    lastplayed = item.get("lastplayed", "")
    resume = item.get("resume", {"position": 0.0, "total": 0.0})

    if playcount != 0 or lastplayed != "" or resume["position"] != 0.0 or resume["total"] != 0.0:
      mediaitems.append(MyWatchedItem(mediatype, shortName, episode_year, playcount, lastplayed, resume))

    if "seasons" in item:
      watchedBackup("seasons", filename, item["seasons"], "label", "season", \
              work=workItems, mitems=mediaitems, showName=title)
    if "episodes" in item:
      watchedBackup("episodes", filename, item["episodes"], "label", "episodeid", \
              work=workItems, mitems=mediaitems, showName=showName, season=title)
      season = None

  if mitems == None:
    TOTALS.TimeEnd(mediatype, "Parse")
    gLogger.progress("")
    watchedWrite(filename, mediaitems)

def watchedRestore(mediatype, jcomms, filename, data, title_name, id_name, work=None, mitems=None, showName=None, season=None):
  gLogger.reset()

  if mitems == None:
      TOTALS.TimeStart(mediatype, "Parse")
      workItems= {}
      mediaitems = {}
      if not watchedRead(filename, mediaitems): return
  else:
      workItems = work
      mediaitems = mitems

  for item in data:
    libraryid = item.get(id_name, 0)
    title = item.get(title_name, "")

    if showName:
      shortName = showName
      if season:
        episode_year = re.sub("([0-9]*x[0-9]*)\..*", "\\1", title)
        longName = "%s, %s Episode %s" % (showName, season, episode_year)
      else:
        episode_year = None
        longName = "%s, %s" % (showName, title)
    else:
      season = None
      episode_year = item.get("year", 0)
      longName = shortName = title

    gLogger.progress("Parsing [%s]..." % longName, every = 25)

    playcount = item.get("playcount", 0)
    lastplayed = item.get("lastplayed", "")
    resume = item.get("resume", {"position": 0.0, "total": 0.0})

    if mediatype in ["movies", "episodes"]:
      mediakey = "%s;%s;%s" % (mediatype, shortName, episode_year)
      if mediakey in mediaitems:
        m = mediaitems[mediakey]
        if m.libraryid == 0:
          m.libraryid = libraryid
          # Update watched object with latest library values unless overwriting,
          # in which case keep the values that are being restored.
          if not gConfig.WATCHEDOVERWRITE:
            m.refresh(gConfig.JSON_HAS_SETRESUME, playcount, lastplayed, resume)
          # Set update state based on old/new values
          m.setState(gConfig.JSON_HAS_SETRESUME, playcount, lastplayed, resume)

    if "seasons" in item:
      watchedRestore("seasons", jcomms, filename, item["seasons"], "label", "season", \
              work=workItems, mitems=mediaitems, showName=title)
    if "episodes" in item:
      watchedRestore("episodes", jcomms, filename, item["episodes"], "label", "episodeid", \
              work=workItems, mitems=mediaitems, showName=showName, season=title)
      season = None

  if mitems == None:
    TOTALS.TimeEnd(mediatype, "Parse")
    gLogger.progress("")
    RESTORED = UNCHANGED = UNMATCHED = ERROR = 0
    for mediakey in sorted(mediaitems):
      m = mediaitems[mediakey]
      shortName = "%s, Episode %s" % (m.name, m.episode_year) if m.mtype == "episodes" else "%s (%s)" % (m.name, m.episode_year)
      if m.libraryid == 0:
        gLogger.out("NO MATCH %s: %s" % (m.mtype[:-1], shortName), newLine = True, log = True)
        UNMATCHED += 1
      else:
        if m.state != 0:
          UNCHANGED += 1
        elif watchedItemUpdate(jcomms, m, shortName):
          gLogger.out("Restored %s: %s" % (m.mtype[:-1], shortName), newLine = True, log = True)
          RESTORED += 1
        else:
          gLogger.out("FAILED   %s: %s" % (m.mtype[:-1], shortName), newLine = True, log = True)
          ERROR += 1
    gLogger.out("", newLine=True)
    gLogger.out("Watched List item summary: Restored %d, Unchanged %d, Unmatched %d, Failed %d\n" %
        (RESTORED, UNCHANGED, UNMATCHED, ERROR), newLine=True)

def watchedItemUpdate(jcomms, mediaitem, shortName):
  if mediaitem.mtype == "movies":
    method = "VideoLibrary.SetMovieDetails"
    mediaid = "movieid"
  else:
    method = "VideoLibrary.SetEpisodeDetails"
    mediaid = "episodeid"

  REQUEST = { "method": method,
              "params": {mediaid: mediaitem.libraryid,
                         "playcount": mediaitem.playcount,
                         "lastplayed": mediaitem.lastplayed
                         }}

  if gConfig.JSON_HAS_SETRESUME:
    REQUEST["params"]["resume"] = mediaitem.resume

  gLogger.progress("Restoring %s: %s..." % (mediaitem.mtype[:-1], shortName))

  data = jcomms.sendJSON(REQUEST, "libWatchedList", checkResult=False)

  return ("result" in data and data["result"] == "OK")

def duplicatesList(mediatype, jcomms, data):
  imdblist = []
  dupelist = []

  # Iterate over movies, building up list of imdb numbers
  # for movies that appear more than once...
  for movie in data:
    imdb = movie["imdbnumber"]
    if imdb:
      if imdb in imdblist:
        if not imdb in dupelist:
          dupelist.append(imdb)
      else:
        imdblist.append(imdb)

  # Iterate over the list of duplicate imdb numbers,
  # and build up a list of matching movie details.
  #
  # dupelist will be in ascending alphabetical order based
  # on the title name of the first movie to be matched
  # above (the JSON data is in title order).
  #
  # Sort the list of movie details into dateadded (asc)
  # order before outputting the details.
  #
  # Since it's possible for movies to be added with the
  # same time, add an extra component to ensure the key
  # is unique.
  unique = 0
  for imdb in dupelist:
    dupes = {}
    for movie in data:
      if imdb == movie["imdbnumber"]:
        unique += 1
        dupes["%s.%d" % (movie["dateadded"], unique)] = movie

    gLogger.out("IMDb Number: %s" % imdb, newLine=True)
    for dupekey in sorted(dupes):
      movie = dupes[dupekey]
      gLogger.out("        Title: %s" % movie["title"], newLine=True)
      gLogger.out("     Movie ID: %d" % movie["movieid"], newLine=True)
      gLogger.out("    Playcount: %d" % movie["playcount"], newLine=True)
      gLogger.out("  Last Played: %s" % movie["lastplayed"], newLine=True)
      gLogger.out("   Date Added: %s" % movie["dateadded"], newLine=True)
      gLogger.out("         File: %s" % movie["file"], newLine=True)
      gLogger.out("", newLine=True)

def updateIMDb(mediatype, jcomms, data):
  worklist = []

  imdbfields = [f.strip() for f in gConfig.IMDB_FIELDS.split(",")]

  plotFull    = ("plot" in imdbfields)
  plotOutline = ("plotoutline" in imdbfields)

  for item in data:
    title = item["title"]
    libid = item["movieid"]
    imdbnumber = item.get("imdbnumber", "")

    gLogger.progress("Querying IMDb: %s..." % title)

    newimdb = MyUtility.getIMDBInfo(imdbnumber, plotFull, plotOutline) if imdbnumber else None

    if not newimdb or newimdb.get("response", "False") != "True":
      gLogger.err("Could not obtain imdb details for [%s] (%s)" % (imdbnumber, title), newLine=True)
      continue

    # Truncate rating to 1 decimal place
    if "rating" in imdbfields:
      item["rating"] = float("%.1f" % item.get("rating", 0.0))

    # Sort genre lists for comparison purposes
    if "genre" in imdbfields:
      item["genre"] = sorted(item.get("genre", []))
      newimdb["genre"] = sorted(newimdb.get("genre", []))

    olditems = {"items": {}}
    workitem = {"type": "movie",
                "libraryid": libid,
                "title": title,
                "items": {}}

    for field in imdbfields:
      if field in newimdb:
        if field not in item or item[field] != newimdb[field]:
          workitem["items"][field] = newimdb[field]
          olditems["items"][field] = item.get(field, None)

    if workitem["items"]:
      worklist.append(workitem)
      gLogger.log("Workitem for id: %d, type: %s, title: %s" %
                  (workitem["libraryid"], workitem["type"], workitem["title"]))
      gLogger.log("  Old items: %s" % olditems["items"])
      gLogger.log("  New items: %s" % workitem["items"])

  gLogger.progress("")

  jcomms.dumpJSON(worklist, decode=True, ensure_ascii=True)

def getIntFloatStr(aValue):
  if type(aValue) is str:
    if (aValue.startswith('"') and aValue.endswith('"')) or \
       (aValue.startswith("'") and aValue.endswith("'")):
      return aValue[1:-1]

  if aValue == "null":
    return None

  try:
    if int(aValue) == float(aValue):
      return int(aValue)
    else:
      return float(aValue)
  except:
    try:
      return float(aValue)
    except:
      return aValue

def setDetails_batch(dryRun=True):
  jcomms = MyJSONComms(gConfig, gLogger)

  data=[]
  for line in sys.stdin: data.append(line)
  gLogger.log("Read %d lines of data from stdin" % len(data))

  jdata = json.loads("".join(data))
  gLogger.log("Parsed %d items" % len(jdata))

  i = 0
  for item in jdata:
    i += 1
    kvpairs = []
    for key in item["items"]:
      kvpairs.append(key)
      kvpairs.append(item["items"][key])
    setDetails_worker(jcomms, item["type"], item["libraryid"], kvpairs, item.get("title", None), dryRun, i, len(jdata))

  gLogger.progress("")

def setDetails_single(mtype, libraryid, kvpairs, dryRun=True):
  # Fix unicode bacsklash mangling from the command line...
  ukvpairs = []
  for kv in kvpairs:
    ukvpairs.append(MyUtility.toUnicode(kv))

  jcomms = MyJSONComms(gConfig, gLogger) if not dryRun else None
  setDetails_worker(jcomms, mtype, libraryid, ukvpairs, None, dryRun, None, None)
  gLogger.progress("")

def setDetails_worker(jcomms, mtype, libraryid, kvpairs, title, dryRun, itemnum, maxitems):
  if mtype == "movie":
    method = "VideoLibrary.SetMovieDetails"
    idname = "movieid"
  elif mtype == "set":
    if gConfig.JSON_HAS_SETMOVIESET:
      method = "VideoLibrary.SetMovieSetDetails"
      idname = "setid"
    else:
      gLogger.out("WARNING: %s is not supported by this version of JSON API (%s) - ignored"
                  % (mtype, gConfig.JSON_VER_STR), newLine=True)
      return
  elif mtype == "tvshow":
    method = "VideoLibrary.SetTVShowDetails"
    idname = "tvshowid"
  elif mtype == "season":
    if gConfig.JSON_HAS_SETSEASON:
      method = "VideoLibrary.SetSeasonDetails"
      idname = "seasonid"
    else:
      gLogger.out("WARNING: %s is not supported by this version of JSON API (%s) - ignored"
                  % (mtype, gConfig.JSON_VER_STR), newLine=True)
      return
  elif mtype == "episode":
    method = "VideoLibrary.SetEpisodeDetails"
    idname = "episodeid"
  elif mtype == "musicvideo":
    method = "VideoLibrary.SetMusicVideoDetails"
    idname = "musicvideoid"
  elif mtype == "artist":
    method = "AudioLibrary.SetArtistDetails"
    idname = "artistid"
  elif mtype == "album":
    method = "AudioLibrary.SetAlbumDetails"
    idname = "albumid"
  elif mtype == "song":
    method = "AudioLibrary.SetSongDetails"
    idname = "songid"
  else:
    gLogger.out("ERROR: %s is not a valid media type for this operation (id: %d)"
                % (mtype, libraryid), newLine=True)
    return

  if libraryid < 1:
    gLogger.out("ERROR: %d is not a valid libraryid" % libraryid, newLine=True)
    return

  mytitle = title if title else "%s %d" % (idname, libraryid)
  if itemnum:
    gLogger.progress("Updating %d of %d: %s..." % (itemnum, maxitems, mytitle))
  else:
    gLogger.progress("Updating: %s..." % mytitle)

  REQUEST = {"method": method, "params": {idname: libraryid}}

  # Iterate over list of name/value pairs
  # Build up dictionary of pairs, and with correct data types
  pairs = {}
  KEY = ""
  bKEY = True
  for pair in kvpairs:
    if bKEY:
      KEY = pair
    else:
      if pair == None:
        pairs[KEY] = None
      elif type(pair) is list:
        pairs[KEY] = []
        for item in pair:
          if item: pairs[KEY].append(getIntFloatStr(item))
      elif type(pair) is str and pair.startswith("[") and pair.endswith("]"):
        pairs[KEY] = []
        for item in [x.strip() for x in pair[1:-1].split(",")]:
          if item: pairs[KEY].append(getIntFloatStr(item))
      else:
        pairs[KEY] = getIntFloatStr(pair)

      if (pairs[KEY] == None or pairs[KEY] == "") and \
         (KEY.startswith("art.") or KEY in ["fanart", "thumbnail", "thumb"]) and \
         not gConfig.JSON_HAS_SETNULL:
        value = "null" if pairs[KEY] == None else "\"%s\"" % pairs[KEY]
        gLogger.out("WARNING: Cannot set null/empty string value on field with " \
                    "JSON API %s - ignoring %s %6d (%s = %s)" % \
                    (gConfig.JSON_VER_STR, idname, libraryid, KEY, value), newLine=True, log=True)
        return

    bKEY = not bKEY

  # Iterate over name/value pairs, adding to params property of the request.
  # Correctly nest parameters using to dot notation.
  for pair in pairs:
    R = REQUEST["params"]
    fc = len(pair.split("."))
    i = 0
    for field in pair.split("."):
      i += 1
      if not field in R: R[field] = {}
      if i == fc:
        if pairs[pair]:
          R[field] = pairs[pair]
        else:
          R[field] = None
      R = R[field]

  if dryRun:
    gLogger.out("### DRY RUN ###", newLine=True)
    gLogger.out(json.dumps(REQUEST, indent=2, ensure_ascii=True, sort_keys=False), newLine=True)
    gLogger.out("### DRY RUN ###", newLine=True)
  else:
    # Don't bother calling SetFoo if nothing actually being set
    if len(REQUEST["params"]) > 1:
      data = jcomms.sendJSON(REQUEST, "libSetDetails")

# Extract data, using optional simple search, or complex SQL filter.
def sqlExtract(ACTION="NONE", search="", filter="", delete=False, silent=False):
  database = MyDB(gConfig, gLogger)

  with database:
    SQL = ""
    if (search != "" or filter != ""):
      if search != "": SQL = "WHERE t.url LIKE '%" + search + "%'"
      if filter != "": SQL = filter + " "

    FSIZE = 0
    FCOUNT = 0
    ROWS = []

    gLogger.progress("Loading database items...")
    dbrows = database.getRows(filter=SQL, order="ORDER BY t.cachedurl ASC", allfields=True)
    rpcnt = 100.0
    if len(dbrows) != 0:
      rpcnt = rpcnt / len(dbrows)

    i = 0
    for row in dbrows:
      if ACTION == "NONE":
        ROWS.append(row)
      else:
        i += 1
        gLogger.progress("Parsing [%s] %2.0f%%..." % (row["cachedurl"], rpcnt * i), every = 50)
        if ACTION == "EXISTS":
          if not os.path.exists(gConfig.getFilePath(row["cachedurl"])):
            ROWS.append(row)
        elif ACTION == "STATS":
          if os.path.exists(gConfig.getFilePath(row["cachedurl"])):
            FSIZE += os.path.getsize(gConfig.getFilePath(row["cachedurl"]))
            ROWS.append(row)

    gLogger.progress("")

    FCOUNT=len(ROWS)

    if delete:
      i = 0
      for row in ROWS:
        i += 1
        gLogger.progress("Deleting row %d (%d of %d)..." % (row["textureid"], i, FCOUNT))
        database.deleteItem(row["textureid"], row["cachedurl"], warnmissing=False)
        gLogger.progress("")
    elif not silent:
      for row in ROWS: database.dumpRow(row)

    if ACTION == "STATS":
      gLogger.out("\nFile Summary: %s files; Total size: %s KB\n\n" % (format(FCOUNT, ",d"), format(int(FSIZE/1024), ",d")))

    if (search != "" or filter != "") and not delete and not silent:
      gLogger.progress("Matching row ids: %s\n" % " ".join("%d" % r["textureid"] for r in ROWS))

# Delete row by id, and corresponding file item
def sqlDelete( ids=[] ):
  database = MyDB(gConfig, gLogger)
  with database:
    for id in ids:
      try:
        database.deleteItem(int(id))
      except ValueError:
        gLogger.out("id %s is not valid\n" % id)
        continue

def orphanCheck(removeOrphans=False):
  database = MyDB(gConfig, gLogger)

  dbfiles = {}
  ddsmap = {}
  orphanedfiles = []

  gLogger.progress("Loading texture cache...")

  with database:
    for r in database.getRows(allfields=False):
      hash = r["cachedurl"]
      dbfiles[hash] = r
      ddsmap[os.path.splitext(hash)[0]] = hash

  gLogger.log("Loaded %d rows from texture cache" % len(dbfiles))

  gLogger.progress("Scanning Thumbnails directory...")

  path = gConfig.getFilePath()

  for (root, dirs, files) in os.walk(path):
    newroot = root.replace(path,"")
    basedir = os.path.basename(newroot)
    for file in files:
      if basedir == "":
        hash = file
      else:
        hash = "%s/%s" % (basedir, file)

      gLogger.progress("Scanning Thumbnails directory [%s]..." % hash, every=25)

      hash_parts = os.path.splitext(hash)

      # If it's a dds file, it should be associated with another
      # file with the same hash, but different extension. Find
      # this other file in the ddsmap - if it's there, ignore
      # the dds file, otherwise leave the dds file to be reported
      # as an orphaned file.
      if hash_parts[1] == ".dds" and ddsmap.get(hash_parts[0], None):
          continue

      row = dbfiles.get(hash, None)

      if not row:
        filename = os.path.join(newroot, file)
        gLogger.log("Orphan file detected: [%s] with likely hash [%s]" % (filename, hash))
        orphanedfiles.append(filename)

  gLogger.progress("")

  gLogger.log("Identified %d orphaned files" % len(orphanedfiles))

  if removeOrphans and gConfig.ORPHAN_LIMIT_CHECK and len(orphanedfiles) > (len(dbfiles)/20):
    gLogger.log("Something is wrong here, that's far too many orphaned files - 5% limit exceeded!")
    gLogger.out("Found %s orphaned files for %s database files.\n\n" % (format(len(orphanedfiles), ",d"), format(len(dbfiles), ",d")))
    gLogger.out("This is far too many orphaned files for this number of\n")
    gLogger.out("database files - more than 5% - and something may be wrong.\n\n")
    gLogger.out("Check your configuration, database, and Thumbnails folder.\n\n")
    gLogger.out("Add \"orphan.limit.check = no\" to the properties file\n")
    gLogger.out("if you wish to disable this check.\n")
    return

  FSIZE=0

  for ofile in orphanedfiles:
    fsize = os.path.getsize(gConfig.getFilePath(ofile))
    FSIZE += fsize
    gLogger.out("Orphaned file found: Name [%s], Created [%s], Size [%s]%s\n" % \
      (ofile,
       time.ctime(os.path.getctime(gConfig.getFilePath(ofile))),
       format(fsize, ",d"),
       ", REMOVING..." if removeOrphans else ""))
    if removeOrphans:
      gLogger.log("Removing orphan file: %s" % gConfig.getFilePath(ofile))
      os.remove(gConfig.getFilePath(ofile))

  gLogger.out("\nSummary: %s files; Total size: %s KB\n\n" \
                  % (format(len(orphanedfiles),",d"), format(int(FSIZE/1024), ",d")))

def pruneCache(remove_nonlibrary_artwork=False):
  dbfiles = {}
  localfiles = []
  libraryFiles = getAllFiles(keyFunction=getKeyFromFilename)

  gLogger.progress("Loading texture cache...")
  database = MyDB(gConfig, gLogger)

  with database:
    for r in database.getRows(allfields=True):
      dbfiles[r["cachedurl"]] = r

  totalrows = len(dbfiles)

  gLogger.log("Loaded %d rows from texture cache" % totalrows)

  gLogger.progress("Processing texture cache...")

  re_search_addon = re.compile(r"^.*[/\\]\.xbmc[/\\]addons[/\\].*")
  re_search_mirror = re.compile(r"^http://mirrors.xbmc.org/addons/.*")

  for rownum, hash in enumerate(dbfiles):
    gLogger.progress("Processing texture cache...%d%%" % (100 * rownum / totalrows), every=25)

    row = dbfiles[hash]
    URL = row["url"]

    isRetained = False
    if gConfig.PRUNE_RETAIN_TYPES:
      for retain in gConfig.PRUNE_RETAIN_TYPES:
        if retain.search(URL):
          gLogger.log("Retained image due to rule [%s]" % retain.pattern)
          isRetained = True
          break

    # Ignore add-on/mirror related images
    if not isRetained and \
       not re_search_addon.search(URL) and \
       not re_search_mirror.search(URL):
      if URL in libraryFiles:
        del libraryFiles[URL]
      else:
        localfiles.append(row)

  gLogger.progress("")

  # Prune, with optional remove...
  if localfiles != []:
    if remove_nonlibrary_artwork:
      gLogger.out("Pruning cached images from texture cache...", newLine=True)
    else:
      gLogger.out("The following items are present in the texture cache but not the media library:", newLine=True)
    gLogger.out("", newLine=True)

  FSIZE = 0
  GOTSIZE = False
  localfiles.sort(key=lambda row: row["url"])

  with database:
    for row in localfiles:
      database.dumpRow(row)
      if os.path.exists(gConfig.getFilePath(row["cachedurl"])):
          GOTSIZE = True
          FSIZE += os.path.getsize(gConfig.getFilePath(row["cachedurl"]))
      if remove_nonlibrary_artwork:
        database.deleteItem(row["textureid"], row["cachedurl"], warnmissing=False)

  if GOTSIZE:
    gLogger.out("\nSummary: %s files; Total size: %s KB\n\n" \
                  % (format(len(localfiles), ",d"),
                     format(int(FSIZE/1024), ",d")))
  else:
    gLogger.out("\nSummary: %s files\n\n" \
                  % (format(len(localfiles), ",d")))

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
  return "%08x" % crc

# The following method is extremely slow on a Raspberry Pi, and
# doesn't work well with unicode strings (returns wrong hash).
# Fortunately, using the encoded url/filename as the key (next
# function) is sufficient for our needs and also about twice
# as fast on a Pi.
def getKeyFromHash(filename):
  url = MyUtility.normalise(filename, strip=True)
  hash = getHash(url)
  return "%s/%s" % (hash[0:1], hash)

def getKeyFromFilename(filename):
  if not filename: return filename
  return MyUtility.normalise(filename, strip=True)

def getAllFiles(keyFunction):
  jcomms = MyJSONComms(gConfig, gLogger)

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

              {"method":"AudioLibrary.GetGenres",
               "params":{"sort": {"order": "ascending", "method": "title"},
                         "properties":["title", "thumbnail"]}},

              {"method":"VideoLibrary.GetMusicVideos",
               "params":{"sort": {"order": "ascending", "method": "title"},
                         "properties":["title", "thumbnail", "fanart", "art"]}},

              {"method":"VideoLibrary.GetMovies",
               "params":{"sort": {"order": "ascending", "method": "title"},
                         "properties":["title", "cast", "art"]}},

              {"method":"VideoLibrary.GetMovieSets",
               "params":{"sort": {"order": "ascending", "method": "title"},
                         "properties":["title", "art"]}},

              {"method":"VideoLibrary.GetGenres",
               "params":{"sort": {"order": "ascending", "method": "title"},
                         "type": "movie",
                         "properties":["title", "thumbnail"]}},

              {"method":"VideoLibrary.GetGenres",
               "params":{"sort": {"order": "ascending", "method": "title"},
                         "type": "tvshow",
                         "properties":["title", "thumbnail"]}},

              {"method":"VideoLibrary.GetGenres",
               "params":{"sort": {"order": "ascending", "method": "title"},
                         "type": "musicvideo",
                         "properties":["title", "thumbnail"]}},

              {"method":"Addons.GetAddons",
               "params":{"properties":["name", "thumbnail", "fanart"]}}
             ]

  for r in REQUEST:
    mediatype = re.sub(".*\.Get(.*)","\\1",r["method"])

    if gConfig.CACHE_EXTRA and mediatype == "Movies":
      jcomms.addProperties(r, "file")

    gLogger.progress("Loading: %s..." % mediatype)
    data = jcomms.sendJSON(r, "libFiles")

    for items in data.get("result", []):
      if items != "limits":
        if mediatype in ["MovieSets","Addons","Genres"]:
          interval = 0
        else:
          interval = int(int(data["result"]["limits"]["total"])/10)
          interval = 50 if interval > 50 else interval
        title = ""
        for i in data["result"][items]:
          title = i.get("title", i.get("artist", i.get("name", None)))
          gLogger.progress("Loading: %s [%s]..." % (mediatype, title), every=interval)
          if "fanart" in i: files[keyFunction(i["fanart"])] = "fanart"
          if "thumbnail" in i: files[keyFunction(i["thumbnail"])] = "thumbnail"

          for a in i.get("art", []):
            files[keyFunction(i["art"][a])] = a

          for c in i.get("cast", []):
            if "thumbnail" in c:
              files[keyFunction(c["thumbnail"])] = "cast.thumb"

          if mediatype in ["Artists", "Albums", "Movies"]:
            for file in jcomms.getExtraArt(i):
              files[keyFunction(file["file"])] = file["type"]

        if title != "": gLogger.progress("Parsing: %s [%s]..." % (mediatype, title))

  gLogger.progress("Loading: TVShows...")

  REQUEST = {"method":"VideoLibrary.GetTVShows",
             "params": {"sort": {"order": "ascending", "method": "title"},
                        "properties":["title", "cast", "art"]}}

  if gConfig.CACHE_EXTRA:
    jcomms.addProperties(REQUEST, "file")

  tvdata = jcomms.sendJSON(REQUEST, "libTV")

  if "result" in tvdata and "tvshows" in tvdata["result"]:
    for tvshow in tvdata["result"]["tvshows"]:
      gLogger.progress("Loading: TVShows [%s]..." % tvshow["title"])
      tvshowid = tvshow["tvshowid"]

      for a in tvshow.get("art", []):
        files[keyFunction(tvshow["art"][a])] = a

      for c in tvshow.get("cast", []):
        if "thumbnail" in c:
          files[keyFunction(c["thumbnail"])] = "cast.thumb"

      for file in jcomms.getExtraArt(tvshow):
        files[keyFunction(file["file"])] = file["type"]

      REQUEST = {"method":"VideoLibrary.GetSeasons",
                 "params":{"tvshowid": tvshowid,
                           "sort": {"order": "ascending", "method": "season"},
                           "properties":["season", "art"]}}

      seasondata = jcomms.sendJSON(REQUEST, "libTV")

      if "seasons" in seasondata["result"]:
        SEASON_ALL = True
        for season in seasondata["result"]["seasons"]:
          seasonid = season["season"]
          gLogger.progress("Loading: TVShows [%s, Season %d]..." % (tvshow["title"], seasonid))

          for a in season.get("art", []):
            if SEASON_ALL and a in ["poster", "tvshow.poster", "tvshow.fanart", "tvshow.banner"]:
              SEASON_ALL = False
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

            for a in episode.get("art", []):
              files[keyFunction(episode["art"][a])] = a

            for c in episode.get("cast", []):
              if "thumbnail" in c:
                files[keyFunction(c["thumbnail"])] = "cast.thumb"

  # Pictures
  if gConfig.PRUNE_RETAIN_PREVIEWS:
    gLogger.progress("Loading: Pictures...")
    pictures = jcomms.getPictures()
    for picture in pictures:
      files[keyFunction(picture["thumbnail"])] = "thumbnail"
    del pictures

  # PVR Channels
  if gConfig.HAS_PVR:
    gLogger.progress("Loading: PVR Channels...")
    for channelType in ["tv", "radio"]:
      REQUEST = {"method":"PVR.GetChannelGroups",
                 "params":{"channeltype": channelType}}
      pvrdata = jcomms.sendJSON(REQUEST, "libPVR", checkResult=False)
      if "result" in pvrdata:
        for channelgroup in pvrdata["result"].get("channelgroups", []):
          REQUEST = {"method":"PVR.GetChannels",
                     "params":{"channelgroupid": channelgroup["channelgroupid"],
                               "properties": ["channeltype", "channel", "thumbnail"]}}
          channeldata = jcomms.sendJSON(REQUEST, "libPVR", checkResult=False)
          if "result" in channeldata:
            for channel in channeldata["result"].get("channels", []):
              files[keyFunction(channel["thumbnail"])] = "pvr.thumb"

  return files

def removeMedia(mtype, libraryid):
  MTYPE = {}
  MTYPE["movie"] = "Movie"
  MTYPE["musicvideo"] = "MusicVideo"
  MTYPE["tvshow"] = "TVShow"
  MTYPE["episode"] = "Episode"

  if mtype not in MTYPE:
    gLogger.out("ERROR: %s is not a valid media type for removal - valid types: %s" % (mtype, ", ".join(MTYPE)), newLine=True)
    return

  if libraryid < 1:
    gLogger.out("ERROR: %d is not a valid libraryid for removal" % libraryid, newLine=True)
    return

  jcomms = MyJSONComms(gConfig, gLogger)
  title = jcomms.getTitleForLibraryItem(mtype, libraryid)

  if title:
    gLogger.out("Removing %s %d [%s]... " % (mtype, libraryid, title))
    jcomms.removeLibraryItem(mtype, libraryid)
    gLogger.out("Done", newLine=True)
  else:
    gLogger.out("ERROR: Does not exist - media type [%s] libraryid [%d]" % (mtype, libraryid), newLine=True)

# Remove artwork urls containing specified patterns, with or without lasthaschcheck
def purgeArtwork(patterns, hashType="all", dryRun=True):
  database = MyDB(gConfig, gLogger)

  SQL = "WHERE"
  if not gConfig.USEJSONDB or gConfig.JSON_HAS_FILTERNULLVALUE:
    if hashType == "hashed":
      SQL = "%s lasthashcheck != '' and" % SQL
    elif hashType == "unhashed":
      SQL = "%s lasthashcheck == '' and" % SQL
  SQL = "%s url like '%%s'" % SQL

  with database:
    for pattern in [x for x in patterns if x != ""]:
      if len(pattern.replace("%", "")) < gConfig.PURGE_MIN_LEN:
        gLogger.err("Ignoring [%s] as pattern length (excluding wildcards) is less than " \
                    "%d characters configured by purge.minlen property" % \
                    (pattern, gConfig.PURGE_MIN_LEN), newLine=True)
        continue

      gLogger.progress("Querying database for pattern: %s" % pattern)

      sqlpattern = pattern
      if sqlpattern.find("%") == -1:
        sqlpattern = "%%%s%%" % sqlpattern

      rows = database.getRows(filter=(SQL % sqlpattern), order="ORDER BY t.id ASC", allfields=True)

      # Filter out hashed/unhashed rows if JSON API ignores null values on the filter...
      if gConfig.USEJSONDB and not gConfig.JSON_HAS_FILTERNULLVALUE:
        newrows = []
        for r in rows:
          if (hashType == "all") or \
             (hashType == "hashed" and r["lasthashcheck"]) or \
             (hashType == "unhashed" and not r["lasthashcheck"]):
            newrows.append(r)
        rows = newrows
        newrows = None

      gLogger.out("Purging %d (%s) items for pattern: %s" % (len(rows), hashType, pattern), newLine=True)

      for r in rows:
        if dryRun:
          gLogger.out("Dry-run, would remove: %s" % r["url"], newLine=True)
        else:
          gLogger.progress("Removing: %s" % r["url"])
          database.deleteItem(r["textureid"], r["cachedurl"], warnmissing=False)

      gLogger.progress("")

def fix_mangled_artwork_urls():
  jcomms = MyJSONComms(gConfig, gLogger)

  files = get_mangled_artwork(jcomms)

  workitems = {}
  for f in files:
    key = "%s[%d]" % (f["idname"], f["id"])
    item = workitems.get(key, {})
    if item == {}:
      item["libraryid"] = f["id"]
      item["type"] = f["type"]
      item["title"] = f["title"]
      item["items"] = {}
    item["items"][f["art"]] = f["fixedurl"]
    workitems[key] = item

  worklist = []
  for item in workitems:
    worklist.append(workitems[item])

  jcomms.dumpJSON(worklist, decode=True, ensure_ascii=True)

def get_mangled_artwork(jcomms):
  def addItems(item, mediatype, idname):
    title = item["label"]
    id = item[idname]
    if "fanart" in item:
      allfiles.append({"type": mediatype, "idname": idname, "id": id, "art": "fanart", "url": item["fanart"], "title": title})
    if "thumbnail" in i:
      allfiles.append({"type": mediatype, "idname": idname, "id": id, "art": "thumbnail", "url": item["thumbnail"], "title": title})
    if "art" in item:
      for a in item["art"]:
        # ignore artwork such as "tvshow.banner" which is a tvshow banner at the episode or season level
        if a.find(".") == -1:
          allfiles.append({"type": mediatype, "idname": idname, "id": item[idname], "art": "art.%s" % a, "url": item["art"][a], "title": title})

  allfiles = []
  idnames = {"Movies": "movieid", "MovieSets": "setid"}
  types   = {"Movies": "movie",   "MovieSets": "set"}

  REQUEST = [
              {"method":"VideoLibrary.GetMovies",
               "params":{"sort": {"order": "ascending", "method": "title"},
                         "properties":["title", "art"]}},

              {"method":"VideoLibrary.GetMovieSets",
               "params":{"sort": {"order": "ascending", "method": "title"},
                         "properties":["title", "art"]}}
             ]

  for r in REQUEST:
    mediatype = re.sub(".*\.Get(.*)","\\1",r["method"])
    idname = idnames[mediatype]
    mtype = types[mediatype]

    gLogger.progress("Loading: %s..." % mediatype)
    data = jcomms.sendJSON(r, "libFiles")

    for items in data.get("result", []):
      if items != "limits":
        if mediatype == "set":
          interval = 0
        else:
          interval = int(int(data["result"]["limits"]["total"])/10)
          interval = 50 if interval > 50 else interval
        title = ""
        for i in data["result"][items]:
          title = i.get("title", i.get("artist", i.get("name", None)))
          gLogger.progress("Parsing: %s [%s]..." % (mediatype, title), every=interval)
          addItems(i, mtype, idname)
        if title != "": gLogger.progress("Parsing: %s [%s]..." % (mediatype, title))

  gLogger.progress("Loading: TVShows...")

  REQUEST = {"method":"VideoLibrary.GetTVShows",
             "params": {"sort": {"order": "ascending", "method": "title"},
                        "properties":["title", "art"]}}

  tvdata = jcomms.sendJSON(REQUEST, "libTV")

  if "result" in tvdata and "tvshows" in tvdata["result"]:
    for tvshow in tvdata["result"]["tvshows"]:
      gLogger.progress("Loading: TVShows [%s]..." % tvshow["title"])

      tvshowid = tvshow["tvshowid"]
      addItems(tvshow, "tvshow", "tvshowid")

      REQUEST = {"method":"VideoLibrary.GetSeasons",
                 "params":{"tvshowid": tvshowid,
                           "sort": {"order": "ascending", "method": "season"},
                           "properties":["season", "art"]}}

      seasondata = jcomms.sendJSON(REQUEST, "libTV")

      if "seasons" in seasondata["result"]:
        for season in seasondata["result"]["seasons"]:
          seasonid = season["season"]
          gLogger.progress("Loading: TVShows [%s, Season %d]..." % (tvshow["title"], seasonid))

          # Can't set items on season unless seasonid is present...
          if "seasonid" in season:
            addItems(season, "season", "seasonid")

          REQUEST = {"method":"VideoLibrary.GetEpisodes",
                     "params":{"tvshowid": tvshowid, "season": seasonid,
                               "properties":["art"]}}

          episodedata = jcomms.sendJSON(REQUEST, "libTV")

          for episode in episodedata["result"]["episodes"]:
            addItems(episode, "episode", "episodeid")

  files = []
  for f in allfiles:
    original = MyUtility.normalise(f["url"], strip=True)
    fixed = MyUtility.fixSlashes(original)
    if original != fixed:
      f["fixedurl"] = fixed
      files.append(f)

  return files

def doLibraryScan(media, path):
  jcomms = MyJSONComms(gConfig, gLogger)

  scanMethod = "VideoLibrary.Scan" if media == "video" else "AudioLibrary.Scan"

  jcomms.scanDirectory(scanMethod, path)

  if media == "video":
    return jcomms.vUpdateCount
  else:
    return jcomms.aUpdateCount

def doLibraryClean(media):
  jcomms = MyJSONComms(gConfig, gLogger)

  cleanMethod = "VideoLibrary.Clean" if media == "video" else "AudioLibrary.Clean"

  jcomms.cleanLibrary(cleanMethod)

def getDirectoryList(path, recurse=False):
  jcomms = MyJSONComms(gConfig, gLogger)

  data = jcomms.getDirectoryList(path)

  if "result" not in data or "files" not in data["result"]:
    gLogger.out("No directory listing available.", newLine=True)
    return

  for file in sorted(data["result"]["files"]):
    ftype = file["filetype"]
    fname = file["file"]

    if ftype == "directory":
      FTYPE = "DIR"
      FNAME = os.path.dirname(fname)
    else:
      FTYPE = "FILE"
      FNAME = fname

    gLogger.out("%-4s: %s" % (FTYPE, FNAME), newLine=True)
    if recurse and ftype == "directory":
      getDirectoryList(FNAME, recurse)

def showSources(media=None, withLabel=None):
  jcomms = MyJSONComms(gConfig, gLogger)

  mlist = [media] if media else ["video", "music", "pictures", "files", "programs"]

  for m in mlist:
    for s in jcomms.getSources(m, labelPrefix=True, withLabel=withLabel):
      gLogger.out("%s: %s" % (m, s), newLine=True)

def setPower(state):
  if state in ["hibernate", "reboot", "shutdown", "suspend", "exit"]:
    MyJSONComms(gConfig, gLogger).setPower(state)
  else:
    gLogger.out("Invalid power state: %s" % state, newLine=True)

def execAddon(addon, params, wait=False):
  REQUEST = {"method":"Addons.ExecuteAddon",
             "params": {"addonid": addon, "wait": wait}}

  if params: REQUEST["params"]["params"] = params

  MyJSONComms(gConfig, gLogger).sendJSON(REQUEST, "libAddon")

def wake_on_lan():
  macaddress = gConfig.MAC_ADDRESS.upper()

  # Check MAC address format and try to normalise to only 12 hex-digits
  if len(macaddress) == 12 + 5:
    macaddress = macaddress.replace(macaddress[2], "")

  # Determine if MAC address consists of only hex digits
  hex_digits = set("0123456789ABCDEF")
  validhex = True
  for char in macaddress:
    validhex = (char in hex_digits)
    if not validhex: break

  # If not 12 digits or not all hex, throw an exception
  if len(macaddress) != 12 or not validhex:
    raise ValueError("Incorrect MAC address format [%s]" % gConfig.MAC_ADDRESS)

  # Format the hex data as 6 bytes of FF, and 16 repetitions of the target MAC address (102 bytes total)
  data = "".join(["FF" * 6, macaddress * 16])

  # Create the broadcast frame by converting each 2-char hex value to a byte
  frame = bytearray([])
  for i in range(0, len(data), 2):
    frame.append(int(data[i: i + 2], 16))

  # Broadcast data to the LAN as a UDP datagram
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
  sock.sendto(frame, ("<broadcast>", 7))
  sock.close()

def showStatus(idleTime=600):
  jcomms = MyJSONComms(gConfig, gLogger)

  STATUS = []

  REQUEST = {"method": "XBMC.GetInfoBooleans",
             "params": { "booleans": ["System.ScreenSaverActive", "Library.IsScanningMusic", "Library.IsScanningVideo"] }}
  data = jcomms.sendJSON(REQUEST, "libSSaver")
  if "result" in data:
    STATUS.append("Scanning Music: %s" % ("Yes" if data["result"].get("Library.IsScanningMusic",False) else "No"))
    STATUS.append("Scanning Video: %s" % ("Yes" if data["result"].get("Library.IsScanningVideo",False) else "No"))
    STATUS.append("ScreenSaver Active: %s" % ("Yes" if data["result"].get("System.ScreenSaverActive",False) else "No"))

  property = "System.IdleTime(%s) " % idleTime
  REQUEST = {"method": "XBMC.GetInfoBooleans", "params": { "booleans": [property] }}
  data = jcomms.sendJSON(REQUEST, "libIdleTime")
  if "result" in data:
    STATUS.append("System Idle > %ss: %s" % (idleTime, ("Yes" if data["result"].get(property,False) else "No")))

  STATUS.append("PVR Enabled: %s" % ("Yes" if gConfig.HAS_PVR else "No"))

  REQUEST = {"method":"Player.GetActivePlayers"}
  data = jcomms.sendJSON(REQUEST, "libGetPlayers")
  if "result" in data:
    for player in data["result"]:
      if "playerid" in player:
        pType = player["type"]
        pId = player["playerid"]
        STATUS.append("Player: %s" % pType.capitalize())

        REQUEST = {"method": "Player.GetItem", "params": {"playerid": pId}}
        data = jcomms.sendJSON(REQUEST, "libGetItem")

        if "result" in data and "item" in data["result"]:
          item = data["result"]["item"]
          iType = item.get("type", None)
          libraryId = item.get("id", None)

          if libraryId == None and "label" in item:
            title = item["label"]
          elif iType == "song":
            title = jcomms.getSongName(libraryId)
          elif iType == "movie":
            title = jcomms.getMovieName(libraryId)
          elif iType == "episode":
            title = jcomms.getEpisodeName(libraryId)
          elif iType == "musicvideo":
            title = jcomms.getMusicVideoName(libraryId)
          else:
            title = None

          STATUS.append("Activity: %s" % iType.capitalize())
          STATUS.append("Title: %s" % title)

          REQUEST = {"method": "Player.GetProperties", "params": {"playerid": pId, "properties": ["percentage", "time", "totaltime"]}}
          data = jcomms.sendJSON(REQUEST, "libGetProps")
          if "result" in data:
            eTime = getSeconds(data["result"].get("time",0))
            tTime = getSeconds(data["result"].get("totaltime",0))
            elapsed = getHMS(eTime)
            pcnt = data["result"].get("percentage", 0)
            remaining = getHMS(tTime - eTime)
            STATUS.append("Progress: %s (%4.2f%%, %s remaining)" % (elapsed, pcnt, remaining))

    if data["result"] == []:
      STATUS.append("Player: None")

  if STATUS != []:
    for x in STATUS:
      pos = x.find(":")
      gLogger.out("%-20s: %s" % (x[:pos], x[pos+2:]), newLine=True)

def getSeconds(aTime):
  return (aTime["hours"] * 3600) + (aTime["minutes"] * 60) + aTime["seconds"] + (aTime["milliseconds"] / 1000)

def getHMS(seconds):
  return "%02d:%02d:%02d" % (int(seconds/3600) % 24, int(seconds/60) % 60, seconds % 60)

def showNotifications():
  MyJSONComms(gConfig, gLogger).listen()

def rbphdmi(delay):

  def rbphdmi_listen(self, method, params):
    cmdqueue.put({"method": method, "params": params})
    return (method == "System.OnQuit")

  RETRIES = 12
  ATTEMPTS = 0

  cmdqueue = Queue.Queue()
  hdmimgr = MyHDMIManager(gConfig, gLogger, cmdqueue, binpath=gConfig.BIN_TVSERVICE, hdmidelay=delay)
  hdmimgr.setDaemon(True)
  hdmimgr.start()

  gLogger.debug("Connecting to XBMC on %s..." % gConfig.XBMC_HOST)
  while True:
    try:
      MyJSONComms(gConfig, gLogger).sendJSON({"method": "JSONRPC.Ping"}, "libListen", callback=rbphdmi_listen, checkResult=False)
      gLogger.debug("XBMC exited - waiting for restart...")
      time.sleep(15.0)
      ATTEMPTS = 0
    except socket.error as e:
      gLogger.debug("XBMC not responding, retries remaining %d" % (RETRIES - ATTEMPTS))
      if ATTEMPTS >= RETRIES: raise
      time.sleep(5.0)
      ATTEMPTS += 1

def MediaLibraryStats(media_list):
  jcomms = MyJSONComms(gConfig, gLogger)

  METHODS = ["AudioLibrary.GetAlbums", "AudioLibrary.GetArtists", "AudioLibrary.GetSongs",
              "VideoLibrary.GetMovies", "VideoLibrary.GetMovieSets",
              "VideoLibrary.GetTVShows", "VideoLibrary.GetEpisodes",
              "VideoLibrary.GetMusicVideos",
              "Addons.GetAddons"]

  lmedia_list = [m.lower() for m in media_list]

  # Add filters for meta-classes
  if "audio" in lmedia_list:
    lmedia_list.extend(["albums", "artists", "songs"])
  if "video" in lmedia_list:
    lmedia_list.extend(["movies", "moviesets", "tvshows", "episodes", "musicvideos"])

  # Clean up
  lmedia_list = [m for m in lmedia_list if m not in ["audio", "video"]]

  for m in METHODS:
    media = re.search(".*Get(.*)", m).group(1)
    if not lmedia_list or media.lower() in lmedia_list:
      REQUEST = {"method": m, "params": {"limits": {"start": 0, "end": 1}}}
      data = jcomms.sendJSON(REQUEST, "libStats")
      if "result" in data and "limits" in data["result"]:
        gLogger.out("%-11s: %d" % (media, data["result"]["limits"]["total"]), newLine=True)

def ProcessInput(args):
  ACTIONS = ["Back", "ContextMenu", "Down",
             "ExecuteAction", "Home", "Info",
             "Left", "Right", "Select",
             "SendText", "ShowCodec", "ShowOSD",
             "Up", "Pause"]

  actionparam = []

  i = 0
  while i < len(args):
    _action = args[i].lower()
    for action in ACTIONS:
      if action.lower() == _action:
        break
    else:
      gLogger.err("Invalid action [%s]" % args[i], newLine=True)
      return
    if action in ["ExecuteAction", "SendText", "Pause"]:
      i += 1
      if i >= len(args) or not args[i]:
        gLogger.err("Insufficient arguments for [%s]" % action, newLine=True)
        return
      else:
        param = args[i]
    else:
      param = None
    i += 1
    actionparam.append({"action": action, "param": param})

  # If first action is not a Pause or noop, insert a noop in case screensaver
  # is active otherwise client will ignore the first input
  if len(actionparam) > 0:
    if not (actionparam[0]["action"] == "Pause" or \
            (actionparam[0]["action"] == "ExecuteAction" and actionparam[0]["param"] == "noop")):
      actionparam.insert(0, {"action": "ExecuteAction", "param": "noop"})

  jcomms = MyJSONComms(gConfig, gLogger)

  for ap in actionparam:
    if ap["action"] == "Pause":
      time.sleep(float(ap["param"]))
      continue

    REQUEST = {"method": "Input.%s" % ap["action"]}

    if ap["action"] == "ExecuteAction":
      REQUEST["params"] = {"action": ap["param"].lower()}

    if ap["action"] == "SendText":
      REQUEST["params"] = {"text": ap["param"], "done": True}

    data = jcomms.sendJSON(REQUEST, "libInput", checkResult=False)
    if "result" not in data or data["result"] != "OK":
      gLogger.err("Unexpected error during [%s] with params [%s]" % (REQUEST["method"], REQUEST["params"]), newLine=True)
      return

def pprint(msg):
  MAXWIDTH=0

  line = "Usage: %s" % os.path.basename(__file__)
  indent = (" " * len(line))

  lines = []
  for index, token in enumerate(msg.split("|")):
    token = token.strip().replace(";", "|")
    if index > 0 and (len(token) + len(line)) > MAXWIDTH:
      lines.append(line)
      line = indent
    line = "%s %s |" % (line, token)

  lines.append(line[:-2])
  lines.append("%s [@property=value ...]" % indent)

  print("\n".join(lines))

def usage(EXIT_CODE):
  print("Version: %s" % gConfig.VERSION)
  print("")
  pprint("[s, S] <string> | [x, X, f, F] [sql-filter] | Xd | d <id[id id]>] | \
          c [class [filter]] | nc [class [filter]] | lc [class] | lnc [class] | C class filter | \
          [j, J, jd, Jd, jr, Jr] class [filter] | qa class [filter] | qax class [filter] | [p, P] | [r, R] | \
          imdb movies [filter] | \
          purge hashed;unhashed;all pattern [pattern [pattern ]] | \
          purgetest hashed;unhashed;all pattern [pattern [pattern]] | \
          fixurls | \
          remove mediatype libraryid | watched class backup <filename> | \
          watched class restore <filename> | duplicates | set | testset | set class libraryid key1 value 1 [key2 value2...] | \
          missing class src-label [src-label]* | ascan [path] |vscan [path] | aclean | vclean | \
          sources [media] | sources media [label] | directory path | rdirectory path | \
          status [idleTime] | monitor | power <state> | exec [params] | execw [params] | wake | \
          rbphdmi [seconds] | stats [class]* |\
          input action* [parameter] | screenshot |\
          config | version | update | fupdate")
  print("")
  print("  s          Search url column for partial movie or tvshow title. Case-insensitive.")
  print("  S          Same as \"s\" (search) but will validate cachedurl file exists, displaying only those that fail validation")
  print("  x          Extract details, using optional SQL filter")
  print("  X          Same as \"x\" (extract) but will validate cachedurl file exists, displaying only those that fail validation")
  print("  Xd         Same as \"x\" (extract) but will DELETE those rows for which no cachedurl file exists")
  print("  f          Same as x, but includes file summary (file count, accumulated file size)")
  print("  F          Same as f, but doesn't include database rows")
  print("  d          Delete rows with matching ids, along with associated cached images")
  print("  c          Re-cache missing artwork. Class can be movies, tags, sets, tvshows, artists, albums or songs.")
  print("  C          Re-cache artwork even when it exists. Class can be movies, tags, sets, tvshows, artists, albums or songs. Filter mandatory.")
  print("  nc         Same as c, but don't actually cache anything (ie. see what is missing). Class can be movies, tags, sets, tvshows, artists, albums or songs.")
  print("  lc         Like c, but only for content added since the modification date of the file specficied in property lastrunfile")
  print("  lnc        Like nc, but only for content added since the modification date of the file specficied in property lastrunfile")
  print("  j          Query library by class (movies, tags, sets, tvshows, artists, albums or songs) with optional filter, return JSON results.")
  print("  J          Same as \"j\", but includes extra JSON audio/video fields as defined in properties file.")
  print("  jd, Jd     Functionality equivalent to j/J, but all urls are decoded")
  print("  jr, Jr     Functionality equivalent to j/J, but all urls are decoded and non-ASCII characters output (ie. \"raw\")")
  print("  qa         Run QA check on movies, tags and tvshows, identifying media with missing artwork or plots")
  print("  qax        Same as qa, but remove and rescan those media items with missing details.")
  print("             Configure with qa.zero.*, qa.blank.* and qa.art.* properties. Prefix field with ? to render warning only.")
  print("  p          Display files present in texture cache that don't exist in the media library")
  print("  P          Prune (automatically remove) cached items that don't exist in the media library")
  print("  r          Reverse search to identify \"orphaned\" Thumbnail files that are not present in the texture cache database")
  print("  R          Same as \"r\" (reverse search) but automatically deletes \"orphaned\" Thumbnail files")
  print("  imdb       Update imdb fields (default: ratings and votes) on movies - pipe output into set to apply changes to media library. Specify alternate fields with @imdb.fields")
  print("  purge      Remove cached artwork with urls containing specified patterns, with or without hash")
  print("  purgetest  Dry-run version of purge")
  print("  fixurls    Output new urls for Movies, Sets and TVShows that have urls containing both forward and backward slashes. Output suitable as stdin for set option")
  print("  remove     Remove a library item - specify type (movie, tvshow, episode or musicvideo) and libraryid")
  print("  watched    Backup or restore movies and tvshows watched statuses, to/from the specified text file")
  print("  duplicates List movies with multiple versions as determined by imdb number")
  print("  set        Set values on objects (movie, tvshow, episode, musicvideo, album, artist, song) eg. \"set movie 312 art.fanart 'http://assets.fanart.tv/fanart/movies/19908/hdmovielogo/zombieland-5145e97ed73a4.png'\"")
  print("  testset    Dry run version of set")
  print("  missing    Locate media files missing from the specified media library, matched against one or more source labels, eg. missing movies \"My Movies\"")
  print("  ascan      Scan entire audio library, or specific path")
  print("  vscan      Scan entire video library, or specific path")
  print("  aclean     Clean audio library")
  print("  vclean     Clean video library")
  print("  sources    List all sources, or sources for specfic media type (video, music, pictures, files, programs) or label (eg. \"My Movies\")")
  print("  directory  Retrieve list of files in a specific directory (see sources)")
  print("  rdirectory Recursive version of directory")
  print("  status     Display state of client - ScreenSaverActive, SystemIdle (default 600 seconds), active Player state etc.")
  print("  monitor    Display client event notifications as they occur")
  print("  power      Control power state of client, where state is one of suspend, hibernate, shutdown, reboot and exit")
  print("  wake       Wake (over LAN) the client corresponding to the MAC address specified by property network.mac")
  print("  exec       Execute specified addon, with optional parameters")
  print("  execw      Execute specified addon, with optional parameters and wait (although often wait has no effect)")
  print("  rbphdmi    Manage HDMI power saving on a Raspberry Pi by monitoring Screensaver notifications. Default power-off delay is 900 seconds after screensaver has started.")
  print("  stats      Ouptut media library stats")
  print("  input      Send keyboard/remote control input to client, where action is back, left, right, up, down, executeaction, sendtext etc.")
  print("  screenshot Take a screen grab of the current display")
  print("")
  print("  config     Show current configuration")
  print("  version    Show current version and check for new version")
  print("  update     Update to new version (if available)")
  print("")
  print("Valid media classes: addons, pvr.tv, pvr.radio, artists, albums, songs, movies, sets, tags, tvshows")
  print("Valid meta classes:  audio (artists + albums + songs) and video (movies + sets + tvshows) and all (music + video + addons + pvr.tv + pvr.radio)")
  print("Meta classes can be used in place of media classes for: c/C/nc/lc/lnc/j/J/jd/Jd/qa/qax options.")
  print("")
  print("SQL Filter fields:")
  print("  id, cachedurl, height, width, usecount, lastusetime, lasthashcheck, url")

  sys.exit(EXIT_CODE)

def loadConfig(argv):
  global DBVERSION, MYWEB, MYSOCKET, MYDB
  global TOTALS
  global gConfig, gLogger

  DBVERSION = MYWEB = MYSOCKET = MYDB = None

  gConfig = MyConfiguration(argv)
  gLogger = MyLogger()
  TOTALS  = MyTotals(gConfig.LASTRUNFILE_DATETIME)

  gLogger.DEBUG = gConfig.DEBUG
  gLogger.VERBOSE = gConfig.LOGVERBOSE
  gLogger.OPTION = argv[0] if len(argv) != 0 else ""

  gLogger.setLogFile(gConfig.LOGFILE)

  gLogger.log("Command line args: %s" % sys.argv)
  gLogger.log("Current version #: v%s" % gConfig.VERSION)
  gLogger.log("Current platform : %s" % sys.platform)
  gLogger.log("Python  version #: v%d.%d.%d.%d (%s)" % (sys.version_info[0], sys.version_info[1], \
                                               sys.version_info[2], sys.version_info[4], sys.version_info[3]))

def checkConfig(option):

  jsonNeedVersion = 6

  # Web server access
  optWeb = ["c","C"]

  # Socket (JSON RPC) access
  optSocket = ["c","C","nc","lc","lnc","j","J","jd","Jd","jr","Jr",
                "qa","qax","query", "p","P",
                "remove", "vscan", "ascan", "vclean", "aclean",
                "directory", "rdirectory", "sources",
                "status", "monitor", "power", "rbphdmi", "stats", "input", "screenshot",
                "exec", "execw", "missing", "watched", "duplicates", "set", "testset",
                "fixurls", "imdb"]

  # Database access (could be SQLite, could be JSON - needs to be determined later)
  optDb = ["s", "S", "x", "X", "Xd", "f", "F",
           "c", "C", "nc", "lc", "lnc", "d",
           "r", "R", "p", "P", "purge", "purgetest"]

  # These options require direct filesystem access
  # Dependency: os.remove(), os.path.exists(), os.path.getsize()
  optFS1 = ["f", "F", "r", "R", "S", "X", "Xd"]

  # These options require direct filesystem access unless JSON Texture API is available.
  # Dependency: os.remove()
  optFS2 = ["d", "P", "C", "purge"]

  # Network MAC
  optMAC = ["wake"]

  needWeb    = (option in optWeb)
  needSocket = (option in optSocket)
  needDb     = (option in optDb)
  needFS1    = (option in optFS1)
  needFS2    = (option in optFS2)
  needMAC    = (option in optMAC)

  # If we need to work out a value for USEJSONDB, we need to check JSON
  # to determine the current version of JSON API
  trySocket = False

  if needDb or needFS2:
    if gConfig.DBJSON == "auto":
      trySocket = True
    elif gConfig.USEJSONDB:
      needSocket = True

  gotWeb = gotSocket = gotDb = gotFS = gotMAC = False
  jsonGotVersion = 0

  if needWeb:
    try:
      jcomms = MyJSONComms(gConfig, gLogger, connecttimeout=gConfig.WEB_CONNECTTIMEOUT)
      REQUEST = {"method": "JSONRPC.Ping"}
      data = jcomms.sendJSON(REQUEST, "libPing", checkResult=False, useWebServer=True)
      gotWeb = ("result" in data and data["result"] == "pong")
    except socket.error:
      pass

  if needWeb and not gotWeb:
    MSG = "FATAL: The task you wish to perform requires that the web server is\n" \
          "       enabled and running on the XBMC system you wish to connect.\n\n" \
          "       A connection cannot be established to the following webserver:\n" \
          "       %s:%s\n\n" \
          "       Check settings in properties file %s\n" % (gConfig.XBMC_HOST, gConfig.WEB_PORT, gConfig.CONFIG_NAME)
    gLogger.err(MSG)
    return False

  if needSocket or trySocket:
    try:
      jcomms = MyJSONComms(gConfig, gLogger, connecttimeout=gConfig.RPC_CONNECTTIMEOUT)

      REQUEST = {"method": "JSONRPC.Version"}
      data = jcomms.sendJSON(REQUEST, "libVersion", checkResult=False)

      gotSocket = True

      if "result" in data and "version" in data["result"]:
        jsonGotVersion = data["result"]["version"]
        if type(jsonGotVersion) is dict and "major" in jsonGotVersion:
          gConfig.SetJSONVersion(jsonGotVersion.get("major",0),
                                 jsonGotVersion.get("minor",0),
                                 jsonGotVersion.get("patch",0))
          jsonGotVersion = jsonGotVersion["major"]

      REQUEST = {"method": "XBMC.GetInfoBooleans",
                 "params": { "booleans": ["System.GetBool(pvrmanager.enabled)"] }}
      data = jcomms.sendJSON(REQUEST, "libPVR", checkResult=False)
      gConfig.HAS_PVR = ("result" in data and data["result"].get("System.GetBool(pvrmanager.enabled)", False))
    except socket.error:
      pass

  if needSocket and not gotSocket:
    MSG = "FATAL: The task you wish to perform requires that the JSON-RPC server is\n" \
          "       enabled and running on the XBMC system you wish to connect.\n\n" \
          "       In addtion, ensure that the following options are ENABLED on the\n" \
          "       XBMC client in Settings -> Services -> Remote control:\n\n" \
          "            Allow programs on this system to control XBMC\n" \
          "            Allow programs on other systems to control XBMC\n\n" \
          "       A connection cannot be established to the following JSON-RPC server:\n" \
          "       %s:%s\n\n" \
          "       Check settings in properties file %s\n" % (gConfig.XBMC_HOST, gConfig.RPC_PORT, gConfig.CONFIG_NAME)
    gLogger.err(MSG)
    return False

  if needSocket and jsonGotVersion  < jsonNeedVersion :
    MSG = "FATAL: The task you wish to perform requires that a JSON-RPC server with\n" \
          "       version %d or above of the XBMC JSON-RPC API is provided.\n\n" \
          "       The JSON-RPC API version of the connected server is: %d (0 means unknown)\n\n" \
          "       Check settings in properties file %s\n" % (jsonNeedVersion, jsonGotVersion, gConfig.CONFIG_NAME)
    gLogger.err(MSG)
    return False

  # If auto detection enabled, when API level insufficient to read Textures DB
  # using JSON, fall back to SQLite3 calls
  if needDb and gConfig.DBJSON == "auto":
    if gConfig.JSON_HAS_TEXTUREDB:
      # If able to use JSON for Texture db access, no need to check DB availability
      gConfig.USEJSONDB = True
    else:
      gConfig.USEJSONDB = False
      gLogger.log("JSON Texture DB API not supported - will use SQLite to access Texture DB")

  # If JSON Textures API is to be used...
  if gConfig.USEJSONDB:
    # Don't access Textures database using SQLite
    # Don't access file system either
    needDb = needFS2 = False

  # If db access required, import SQLite3 module
  if needDb:
    global lite
    try:
      import sqlite3 as lite
      try:
        database = MyDB(gConfig, gLogger)
        con = database.getDB()
        if database.DBVERSION < 13:
          MSG = "WARNING: The sqlite3 database pre-dates Frodo (v12), some problems may be encountered!"
          gLogger.err(MSG, newLine=True)
          gLogger.log(MSG)
        gotDb = True
      except lite.OperationalError:
        pass
    except ImportError:
      gLogger.log("ERROR: SQLite3 module not imported")
      lite = None

  if needDb and not gotDb:
    MSG = "FATAL: The task you wish to perform requires read/write file\n" \
          "       access to the XBMC sqlite3 Texture Cache database.\n\n" \
          "       The following sqlite3 database could not be opened:\n" \
          "       %s\n\n" \
          "       Check settings in properties file %s,\n" \
          "       or upgrade your XBMC client to use a more recent\n" \
          "       version that supports Textures JSON API.\n" \
                  % (gConfig.getDBPath(), gConfig.CONFIG_NAME)
    gLogger.err(MSG)
    return False

  if needFS1 or needFS2:
    gotFS = os.path.exists(gConfig.getFilePath())

  if (needFS1 or needFS2) and not gotFS:
    MSG = "FATAL: The task you wish to perform requires read/write file\n" \
          "       access to the Thumbnails folder, which is inaccessible.\n\n" \
          "       Specify the location of this folder using the thumbnails property\n" \
          "       as an absolute path or relative to the userdata property.\n\n" \
          "       The currently configured Thumbnails path is:\n" \
          "       %s\n\n" \
          "       Check userdata and thumbnails settings in properties file %s\n" % (gConfig.getFilePath(), gConfig.CONFIG_NAME)
    gLogger.err(MSG)
    return False

  if needMAC:
    gotMAC = (gConfig.MAC_ADDRESS != "")

  if needMAC and not gotMAC:
    MSG = "FATAL: The task you wish to perform requires a valid MAC address\n" \
          "       specified in the property \"network.mac\".\n\n" \
          "       Check settings in properties file %s\n" % gConfig.CONFIG_NAME
    gLogger.err(MSG)
    return False

  if option == "rbphdmi":
    if not (gConfig.BIN_TVSERVICE and os.path.exists(gConfig.BIN_TVSERVICE)):
      MSG = "FATAL: The task you wish to perform requires a valid path specified\n" \
            "       in the property \"bin.tvservice\".\n\n" \
            "       The current value [%s]\n" \
            "       is either not set or cannot be accessed.\n\n" \
            "       Check settings in properties file %s\n" % (gConfig.BIN_TVSERVICE, gConfig.CONFIG_NAME)
      gLogger.err(MSG)
      return False

  gConfig.postConfig()

  if gLogger.VERBOSE and gLogger.LOGGING:
    gLogger.log("JSON CAPABILITIES: %s" % gConfig.dumpJSONCapabilities())
    gLogger.log("CONFIG VALUES: \n%s" % gConfig.dumpMemberVariables())

  return True

def checkUpdate(argv, forcedCheck = False):
  (remoteVersion, remoteHash) = getLatestVersion(argv)

  if forcedCheck:
    gLogger.out("Current Version: v%s" % gConfig.VERSION, newLine=True)
    gLogger.out("Latest  Version: %s" % ("v" + remoteVersion if remoteVersion else "Unknown"), newLine=True)
    gLogger.out("", newLine=True)

  if remoteVersion and remoteVersion > gConfig.VERSION:
    out_method = gLogger.out if forcedCheck else gLogger.err
    out_method("A new version of this script is available - use the \"update\" option to apply update.", newLine=True)
    out_method("", newLine=True)

  if forcedCheck:
    url = gConfig.GITHUB.replace("//raw.","//").replace("/master","/blob/master")
    gLogger.out("Full changelog: %s/CHANGELOG.md" % url, newLine=True)

def getLatestVersion(argv):
  # Need user agent etc. for analytics
  BITS = "64" if platform.architecture()[0] == "64bit" else "32"
  ARCH = "ARM" if platform.machine().lower().startswith("arm") else "x86"
  PLATFORM = platform.system()
  if PLATFORM.lower() == "darwin": PLATFORM = "Mac OSX"
  if PLATFORM.lower() == "linux": PLATFORM = "%s %s" % (PLATFORM, ARCH)

  user_agent = "Mozilla/5.0 (%s; %s_%s; rv:%s) Gecko/20100101 Py-v%d.%d.%d.%d/1.0" % \
      (PLATFORM, ARCH, BITS, gConfig.VERSION,
       sys.version_info[0], sys.version_info[1], sys.version_info[2], sys.version_info[4])

  # Construct "referer" to indicate usage:
  USAGE = "unknown"
  if argv[0] in ["c", "C", "nc", "lc", "lnc"]:
    USAGE = "cache"
  elif argv[0] in ["j", "J", "jd", "Jd", "jr", "Jr"]:
    USAGE  = "dump"
  elif argv[0] in ["p", "P"]:
    USAGE  = "prune"
  elif argv[0] in ["r", "R"]:
    USAGE  = "orphan"
  elif argv[0] in ["s", "S", "d", "f", "F", "x", "X", "Xd"]:
    USAGE  = "db"
  elif argv[0] in ["exec", "execw"]:
    USAGE  = "exec"
  elif argv[0] in ["set", "testset"]:
    USAGE  = "set"
  elif argv[0] in ["purge", "purgetest"]:
    USAGE  = "purge"
  elif argv[0] in ["qa", "qax"]:
    USAGE  = "qa"
  elif argv[0] in ["query", "missing", "watched",
                   "power", "wake", "status", "monitor", "rbphdmi",
                   "directory", "rdirectory", "sources", "remove",
                   "vscan", "ascan", "vclean", "aclean",
                   "duplicates", "fixurls", "imdb", "stats",
                   "input", "screenshot",
                   "version", "update", "fupdate", "config"]:
    USAGE  = argv[0]

  HEADERS = []
  HEADERS.append(("User-agent", user_agent))
  HEADERS.append(("Referer", "http://www.%s" % USAGE))

  # Try checking version via Analytics URL
  (remoteVersion, remoteHash) = getLatestVersion_ex(gConfig.ANALYTICS, headers = HEADERS)

  # If the Analytics call fails, go direct to github
  if remoteVersion == None or remoteHash == None:
    (remoteVersion, remoteHash) = getLatestVersion_ex("%s/%s" % (gConfig.GITHUB, "VERSION"))

  return (remoteVersion, remoteHash)

def getLatestVersion_ex(url, headers=None):
  GLOBAL_TIMEOUT = socket.getdefaulttimeout()
  ITEMS = (None, None)

  try:
    socket.setdefaulttimeout(5.0)

    if headers:
      opener = urllib2.build_opener()
      opener.addheaders = headers
      response = opener.open(url)
    else:
      response = urllib2.urlopen(url)

    if sys.version_info >= (3, 0):
      data = response.read().decode("utf-8")
    else:
      data = response.read()

    items = data.replace("\n","").split(" ")

    if len(items) == 2:
      ITEMS = items
    else:
      gLogger.log("Bogus data in getLatestVersion_ex(): url [%s], data [%s]" % (url, data), maxLen=512)
  except Exception as e:
    gLogger.log("Exception in getLatestVersion_ex(): url [%s], text [%s]" % (url, e))

  socket.setdefaulttimeout(GLOBAL_TIMEOUT)
  return ITEMS

def downloadLatestVersion(argv, force=False, autoupdate=False):
  (remoteVersion, remoteHash) = getLatestVersion(argv)

  if autoupdate and (not remoteVersion or remoteVersion <= gConfig.VERSION):
    return False

  if not remoteVersion:
    gLogger.err("FATAL: Unable to determine version of the latest file, check internet and github.com are available.", newLine=True)
    sys.exit(2)

  if not force and remoteVersion <= gConfig.VERSION:
    gLogger.err("Current version is already up to date - no update required.", newLine=True)
    sys.exit(2)

  try:
    response = urllib2.urlopen("%s/%s" % (gConfig.GITHUB, "texturecache.py"))
    data = response.read()
  except Exception as e:
    gLogger.log("Exception in downloadLatestVersion(): %s" % e)
    if autoupdate: return False
    gLogger.err("FATAL: Unable to download latest file, check internet and github.com are available.", newLine=True)
    sys.exit(2)

  digest = hashlib.md5()
  digest.update(data)

  if (digest.hexdigest() != remoteHash):
    if autoupdate: return False
    gLogger.err("FATAL: Checksum of new version is incorrect, possibly corrupt download - abandoning update.", newLine=True)
    sys.exit(2)

  path = os.path.realpath(__file__)
  dir = os.path.dirname(path)

  if os.path.exists("%s%s.git" % (dir, os.sep)):
    gLogger.err("FATAL: Might be updating version in git repository... Abandoning update!", newLine=True)
    sys.exit(2)

  try:
    THISFILE = open(path, "wb")
    THISFILE.write(data)
    THISFILE.close()
  except:
    if autoupdate:
      gLogger.err("NOTICE: A new version (v%s) of this script is available." % remoteVersion, newLine=True)
      gLogger.err("NOTICE: Use the \"--update\" option to apply update.", newLine=True)
      return False
    else:
      gLogger.err("FATAL: Unable to update current file, check you have write access", newLine=True)
      sys.exit(2)

  gLogger.err("Successfully updated from v%s to v%s" % (gConfig.VERSION, remoteVersion), newLine=True)

  return True

#
# Download new version if available, then replace current
# process - os.execl() doesn't return.
#
# Do nothing if newer version not available.
#
def autoUpdate(argv):
  if downloadLatestVersion(argv, force=False, autoupdate=True):
    args = sys.argv
    args.append("@checkupdate=no")
    os.execl(sys.executable, sys.executable, *args)

def main(argv):

  loadConfig(argv)

  if len(argv) == 0: usage(1)

  if not checkConfig(argv[0]): sys.exit(2)

  if gConfig.CHECKUPDATE and argv[0] not in ["version", "update", "fupdate"]:
    if gConfig.AUTOUPDATE:
      autoUpdate(argv)
    else:
      checkUpdate(argv)

  EXIT_CODE = 0

  multi_call_a = ["albums", "artists", "songs"]
  multi_call_v = ["movies", "sets", "tvshows"]
  multi_call   = ["addons", "agenres", "vgenres", "pvr.tv", "pvr.radio"] + multi_call_a + multi_call_v

  if argv[0] == "s" and len(argv) == 2:
    sqlExtract("NONE", search=argv[1])
  elif argv[0] == "S" and len(argv) == 2:
    sqlExtract("EXISTS", search=argv[1])

  elif argv[0] == "x" and len(argv) == 1:
    sqlExtract("NONE")
  elif argv[0] == "x" and len(argv) == 2:
    sqlExtract("NONE", filter=argv[1])
  elif argv[0] == "X" and len(argv) == 1:
    sqlExtract("EXISTS")
  elif argv[0] == "X" and len(argv) == 2:
    sqlExtract("EXISTS", filter=argv[1])
  elif argv[0] == "Xd" and len(argv) == 1:
    sqlExtract("EXISTS", delete=True)
  elif argv[0] == "Xd" and len(argv) == 2:
    sqlExtract("EXISTS", filter=argv[1], delete=True)

  elif argv[0] == "f" and len(argv) == 1:
    sqlExtract("STATS")
  elif argv[0] == "f" and len(argv) == 2:
    sqlExtract("STATS", filter=argv[1])
  elif argv[0] == "F" and len(argv) == 1:
    sqlExtract("STATS", silent=True)
  elif argv[0] == "F" and len(argv) == 2:
    sqlExtract("STATS", filter=argv[1], silent=True)

  elif argv[0] in ["c", "C", "nc", "lc", "lnc",
                   "j", "J", "jd", "Jd", "jr", "Jr",
                   "qa", "qax", "query", "imdb"]:
    _stats  = False

    if argv[0] in ["j", "J", "jd", "Jd", "jr", "Jr"]:
      _action = "dump"
    elif argv[0] in ["qa", "qax"]:
      _action = "qa"
    elif argv[0] in ["query", "imdb"]:
      _action = argv[0]
    else:
      _action = "cache"
      _stats  = True

    _force      = True if argv[0] == "C" else False
    _rescan     = True if argv[0] == "qax" else False
    _lastRun    = True if argv[0] in ["lc", "lnc"] else False
    _nodownload = True if argv[0] in ["nc", "lnc"] else False
    _decode     = True if argv[0] in ["jd", "Jd", "jr", "Jr"] else False
    _ensure_ascii=False if argv[0] in ["jr", "Jr"] else True
    _extraFields= True if argv[0] in ["J", "Jd", "Jr"] else False

    _filter     = ""
    _query      = ""

    if argv[0] != "query":
      _filter     = argv[2] if len(argv) > 2 else ""
    else:
      if len(argv) == 3:
        _query      = argv[2]
      elif len(argv) > 3:
        _filter     = argv[2]
        _query      = argv[3]

    if _force and not gConfig.RECACHEALL and _filter == "":
      print("Forcing re-cache of all items is disabled. Enable by setting \"allow.recacheall=yes\" in property file.")
      sys.exit(2)

    _multi_call = []
    if len(argv) == 1:
      _multi_call = multi_call
      if "songs" in _multi_call: _multi_call.remove("songs")
    else:
      if argv[1] == "audio": _multi_call = multi_call_a
      if argv[1] == "video": _multi_call = multi_call_v
      if argv[1] == "all":   _multi_call = multi_call

    if _multi_call != [] and not gConfig.HAS_PVR:
      for item in ["pvr.tv", "pvr.radio"]:
        if item in _multi_call: _multi_call.remove(item)

    if _multi_call == [] and len(argv) >= 2:
      _multi_call.append(argv[1])

    if _multi_call != []:
      for _media in _multi_call:
        jsonQuery(_action, mediatype=_media, filter=_filter,
                  force=_force, lastRun=_lastRun, nodownload=_nodownload,
                  rescan=_rescan, decode=_decode, ensure_ascii=_ensure_ascii,
                  extraFields=_extraFields, query=_query)
      if _stats: TOTALS.libraryStats(multi=_multi_call, filter=_filter, lastRun=_lastRun, query=_query)
    else:
      usage(1)

  elif argv[0] == "duplicates":
    jsonQuery("duplicates", "movies")

  elif argv[0] == "d" and len(argv) >= 2:
    sqlDelete(argv[1:])

  elif argv[0] == "r":
    orphanCheck(removeOrphans=False)

  elif argv[0] == "R":
    orphanCheck(removeOrphans=True)

  elif argv[0] == "p" and len(argv) == 1:
    pruneCache(remove_nonlibrary_artwork=False)

  elif argv[0] == "P" and len(argv) == 1:
    pruneCache(remove_nonlibrary_artwork=True)

  elif argv[0] == "remove" and len(argv) == 3:
    removeMedia(mtype=argv[1], libraryid=int(argv[2]))

  elif argv[0] in ["purge", "purgetest"] and len(argv) >= 3:
    if argv[1] not in ["hashed", "unhashed", "all"]: usage(1)
    purgeArtwork(argv[2:], hashType=argv[1], dryRun=(argv[0] == "purgetest"))

  elif argv[0] == "fixurls":
    fix_mangled_artwork_urls()

  elif argv[0] == "vscan":
    EXIT_CODE = doLibraryScan("video", path=argv[1] if len(argv) == 2 else None)

  elif argv[0] == "ascan":
    EXIT_CODE = doLibraryScan("audio", path=argv[1] if len(argv) == 2 else None)

  elif argv[0] == "vclean":
    doLibraryClean("video")

  elif argv[0] == "aclean":
    doLibraryClean("audio")

  elif argv[0] == "directory" and len(argv) == 2:
    getDirectoryList(argv[1], recurse=False)
  elif argv[0] == "rdirectory" and len(argv) == 2:
    getDirectoryList(argv[1], recurse=True)

  elif argv[0] == "sources" and len(argv) < 3:
    showSources(media=argv[1] if len(argv) == 2 else None)
  elif argv[0] == "sources" and len(argv) == 3:
    showSources(media=argv[1], withLabel=argv[2])

  elif argv[0] == "status":
    if len(argv) == 2:
      showStatus(idleTime=argv[1])
    else:
      showStatus()

  elif argv[0] == "monitor":
    showNotifications()

  elif argv[0] == "version":
    checkUpdate(argv, forcedCheck=True)

  elif argv[0] == "config":
    gConfig.showConfig()

  elif argv[0] == "update":
    downloadLatestVersion(argv, force=False)
  elif argv[0] == "fupdate":
    downloadLatestVersion(argv, force=True)

  elif argv[0] == "power" and len(argv) == 2:
    setPower(argv[1])

  elif argv[0] == "exec" and len(argv) > 1:
    execAddon(argv[1], argv[2:], wait=False)
  elif argv[0] == "execw" and len(argv) > 1:
    execAddon(argv[1], argv[2:], wait=True)

  elif argv[0] == "missing" and len(argv) >= 3:
    jsonQuery(action="missing", mediatype=argv[1], labels=argv[2:])

  elif argv[0] == "watched" and len(argv) == 4:
    if argv[2] == "backup":
      jsonQuery(action="watched", mediatype=argv[1], filename=argv[3], wlBackup=True)
    elif argv[2] == "restore":
      jsonQuery(action="watched", mediatype=argv[1], filename=argv[3], wlBackup=False)
    else:
      usage(1)

  elif argv[0] == "wake":
    wake_on_lan()

  elif argv[0] in ["set", "testset"] and len(argv) == 1:
    dryRun = (argv[0] != "set")
    setDetails_batch(dryRun=dryRun)

  elif argv[0] in ["set", "testset"] and len(argv) >= 4:
    dryRun = (argv[0] != "set")
    mtype = argv[1]
    libraryid = int(argv[2]) + 0 if len(argv) >= 3 else 0
    kvpairs = argv[3:] if len(argv) >= 4 else []
    setDetails_single(mtype, libraryid, kvpairs, dryRun=dryRun)

  elif argv[0] == "rbphdmi":
    _delay = 900 if len(argv) == 1 else int(argv[1])
    rbphdmi(delay=_delay)

  elif argv[0] == "stats":
    MediaLibraryStats(argv[1:])

  elif argv[0] == "input" and len(argv) > 1:
    ProcessInput(argv[1:])

  elif argv[0] == "screenshot":
    ProcessInput(["executeaction", "screenshot"])

  else:
    usage(1)

  gLogger.log("Successful completion")

  sys.exit(EXIT_CODE)

if __name__ == "__main__":
  try:
    stopped = threading.Event()
    main(sys.argv[1:])
  except (KeyboardInterrupt, SystemExit) as e:
    if type(e) == SystemExit: sys.exit(int(str(e)))
