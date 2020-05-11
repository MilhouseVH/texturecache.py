#!/usr/bin/env python
# -*- coding: utf-8 -*-

################################################################################
#
#  Copyright (C) 2013-present Neil MacLeod (texturecache@nmacleod.com)
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
# Simple utility to query, validate, clean and refresh the Kodi texture cache.
#
# https://github.com/MilhouseVH/texturecache.py
#
# Usage:
#
#  See built-in help (run script without parameters), or the README file
#  on Github for more details.
#
################################################################################

import os, sys, platform, re, datetime, time
import socket, base64, hashlib
import threading, random
import errno, codecs
import subprocess
import tempfile

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

lock = threading.RLock()

#
# Config class. Will be a global object.
#
class MyConfiguration(object):
  def __init__(self, argv):

    self.VERSION = "2.5.4"

    self.GITHUB = "https://raw.github.com/MilhouseVH/texturecache.py/master"
    self.ANALYTICS_GOOD = "http://goo.gl/BjH6Lj"

    self.DEBUG = True if os.environ.get("PYTHONDEBUG", "n").lower()=="y" else False

    self.GLOBAL_SECTION = "global"
    self.THIS_SECTION = self.GLOBAL_SECTION
    self.CONFIG_NAME = "texturecache.cfg"

    self.HAS_PVR = False

    # https://github.com/xbmc/xbmc/blob/master/xbmc/settings/AdvancedSettings.cpp
    m_pictureExtensions = ".png|.jpg|.jpeg|.bmp|.gif|.ico|.tif|.tiff|.tga|.pcx|.cbz|.zip|.cbr|.rar|.dng|.nef|.cr2|.crw|.orf|.arw|.erf|.3fr|.dcr|.x3f|.mef|.raf|.mrw|.pef|.sr2|.rss"
    m_musicExtensions = ".nsv|.m4a|.flac|.aac|.strm|.pls|.rm|.rma|.mpa|.wav|.wma|.ogg|.mp3|.mp2|.m3u|.mod|.amf|.669|.dmf|.dsm|.far|.gdm|.imf|.it|.m15|.med|.okt|.s3m|.stm|.sfx|.ult|.uni|.xm|.sid|.ac3|.dts|.cue|.aif|.aiff|.wpl|.ape|.mac|.mpc|.mp+|.mpp|.shn|.zip|.rar|.wv|.nsf|.spc|.gym|.adx|.dsp|.adp|.ymf|.ast|.afc|.hps|.xsp|.xwav|.waa|.wvs|.wam|.gcm|.idsp|.mpdsp|.mss|.spt|.rsd|.mid|.kar|.sap|.cmc|.cmr|.dmc|.mpt|.mpd|.rmt|.tmc|.tm8|.tm2|.oga|.url|.pxml|.tta|.rss|.cm3|.cms|.dlt|.brstm|.wtv|.mka|.tak|.opus|.dff|.dsf"
    m_videoExtensions = ".m4v|.3g2|.3gp|.nsv|.tp|.ts|.ty|.strm|.pls|.rm|.rmvb|.m3u|.m3u8|.ifo|.mov|.qt|.divx|.xvid|.bivx|.vob|.nrg|.img|.iso|.pva|.wmv|.asf|.asx|.ogm|.m2v|.avi|.bin|.dat|.mpg|.mpeg|.mp4|.mkv|.mk3d|.avc|.vp3|.svq3|.nuv|.viv|.dv|.fli|.flv|.rar|.001|.wpl|.zip|.vdr|.dvr-ms|.xsp|.mts|.m2t|.m2ts|.evo|.ogv|.sdp|.avs|.rec|.url|.pxml|.vc1|.h264|.rcv|.rss|.mpls|.webm|.bdmv|.wtv"
    m_subtitlesExtensions = ".utf|.utf8|.utf-8|.sub|.srt|.smi|.rt|.txt|.ssa|.text|.ssa|.aqt|.jss|.ass|.idx|.ifo|.rar|.zip"

    # These features become available with the respective API version
    self.JSON_VER_CAPABILITIES = {"setresume":        (6,  2, 0),
                                  "profilesupport":   (6,  6, 0),
                                  "texturedb":        (6,  9, 0),
                                  "removeart":        (6,  9, 1),
                                  "setseason":        (6, 10, 0),
                                  "setmovieset":      (6, 12, 0),
                                  "setsettings":      (6, 13, 0),
                                  "filternullval":    (6, 13, 1),
                                  "isodates":         (6, 13, 2),
                                  "debugextralog":    (6, 15, 3),
                                  "dpmsnotify":       (6, 16, 0),
                                  "openplayercoredef":(6, 18, 3),
                                  "libshowdialogs":   (6, 19, 0),
                                  "exitcode":         (6, 21, 0),
                                  "refreshrefactor":  (6, 27, 0),
                                  "votesnogrouping":  (7,  1, 0),
                                  "playerprocessinfo":(7, 20, 0),
                                  "codecinforemoved": (7, 21, 0),
                                  "musichasart":      (9, 4,  2),
                                  "profiledirectory": (999, 99, 9)
                                 }

    self.SetJSONVersion(0, 0, 0)

    namedSection = False
    serial_urls = "assets\.fanart\.tv"
    embedded_urls = "^video, ^music, ^DefaultVideo.png"

    if MyUtility.isPython3:
      config = ConfigParser.ConfigParser(strict=False)
    else:
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
        if not os.path.exists(self.FILENAME):
          self.FILENAME = os.path.expanduser("~/.config/%s" % self.CONFIG_NAME)

    cfg = StringIO.StringIO()
    cfg.write("[%s]\n" % self.GLOBAL_SECTION)

    if os.path.exists(self.FILENAME):
      cfg.write(open(self.FILENAME, "r").read())
      cfg.write("\n")

    cfg.seek(0, os.SEEK_SET)
    if MyUtility.isPython3:
      config.read_file(cfg)
    else:
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

    #Add any command line settings - eg. @kodi.host=192.168.0.8 - to the named section.
    for arg in list(argv):
      arg_match = re.match("^[ ]*@([^ ]+)[ ]*=(.*)", arg)
      if arg_match and len(arg_match.groups()) == 2:
        argKey, argVal = arg.split("=", 1)
        config.set(self.THIS_SECTION, argKey.strip()[1:], argVal.strip())
        argv.remove(arg)

    if not self.DEBUG and self.getBoolean(config, "debug", ""):
      self.DEBUG = self.getBoolean(config, "debug", "no")

    self.IDFORMAT = self.getValue(config, "format", "%06d")
    self.FSEP = self.getValue(config, "sep", "|")

    UD_SYS_DEFAULT = self.getdefaultuserdata("Kodi")
    if UD_SYS_DEFAULT is None: UD_SYS_DEFAULT = self.getdefaultuserdata("XBMC")
    if UD_SYS_DEFAULT is None: UD_SYS_DEFAULT = "~/userdata"

    self.KODI_BASE = os.path.expanduser(self.getValue(config, "userdata", UD_SYS_DEFAULT))
    self.TEXTUREDB = self.getValue(config, "dbfile", "Database/Textures13.db")
    self.THUMBNAILS = self.getValue(config, "thumbnails", "Thumbnails")

    self.CURRENT_PROFILE = {"label": "", "lockmode": 0, "thumbnail": "", "directory": "", "tc.profilepath": self.KODI_BASE} # Not yet known
    self.PROFILE_ENABLED = self.getBoolean(config, "profile.enabled", "yes")
    self.PROFILE_MASTER = self.getValue(config, "profile.master", "Master user")
    self.PROFILE_AUTOLOAD = self.getBoolean(config, "profile.autoload", "yes")
    self.PROFILE_RETRY = int(self.getValue(config, "profile.retry", "60"))
    self.PROFILE_WAIT = int(self.getValue(config, "profile.wait", "0"))
    self.PROFILE_NAME = self.getValue(config, "profile.name", self.PROFILE_MASTER)
    self.PROFILE_PASSWORD = self.getValue(config, "profile.password", "")
    self.PROFILE_ENCRYPTED = self.getBoolean(config, "profile.password.encrypted", "no")
    self.PROFILE_DIRECTORY = self.getValue(config, "profile.directory", "")

    if self.PROFILE_DIRECTORY == "" and self.PROFILE_NAME != self.PROFILE_MASTER:
      self.PROFILE_DIRECTORY = self.PROFILE_NAME

    if self.PROFILE_DIRECTORY != "":
      self.PROFILE_DIRECTORY = os.path.join("profiles", self.PROFILE_DIRECTORY)

    # Read library and textures data in chunks to minimise server/client memory usage
    self.CHUNKED = self.getBoolean(config, "chunked", "yes")

    self.DBJSON = self.getValue(config, "dbjson", "auto")
    self.USEJSONDB = self.getBoolean(config, "dbjson", "yes")

    if self.KODI_BASE[-1:] not in ["/", "\\"]: self.KODI_BASE += "/"
    if self.THUMBNAILS[-1:] not in ["/", "\\"]: self.THUMBNAILS += "/"

    self.KODI_BASE = self.KODI_BASE.replace("/", os.sep)
    self.TEXTUREDB = self.TEXTUREDB.replace("/", os.sep)
    self.THUMBNAILS = self.THUMBNAILS.replace("/", os.sep)
    self.HAS_THUMBNAILS_FS = os.path.exists(self.getFilePath())

    self.KODI_HOST = self.getValue(config, "xbmc.host", None, True)
    if self.KODI_HOST is None:
      self.KODI_HOST = self.getValue(config, "kodi.host", "localhost")
    self.WEB_PORT = self.getValue(config, "webserver.port", "8080")
    self.WEB_SINGLESHOT = self.getBoolean(config, "webserver.singleshot", "no")
    self.RPC_PORT = self.getValue(config, "rpc.port", "9090")
    self.RPC_IPVERSION = self.getValue(config, "rpc.ipversion", "")
    self.RPC_RETRY = int(self.getValue(config, "rpc.retry", "12"))
    self.RPC_RETRY = 0 if self.RPC_RETRY < 0 else self.RPC_RETRY

    web_user = self.getValue(config, "webserver.username", "")
    web_pass = self.getValue(config, "webserver.password", "")

    self.WEB_CONNECTTIMEOUT = self.getValue(config, "webserver.ctimeout", 0.5, allowundefined=True)
    if self.WEB_CONNECTTIMEOUT: self.WEB_CONNECTTIMEOUT = float(self.WEB_CONNECTTIMEOUT)

    self.RPC_CONNECTTIMEOUT = self.getValue(config, "rpc.ctimeout", 0.5, allowundefined=True)
    if self.RPC_CONNECTTIMEOUT: self.RPC_CONNECTTIMEOUT = float(self.RPC_CONNECTTIMEOUT)

    if (web_user and web_pass):
      token = "%s:%s" % (web_user, web_pass)
      if MyUtility.isPython3:
        self.WEB_AUTH_TOKEN = base64.encodebytes(bytes(token, "utf-8")).decode()
      else:
        self.WEB_AUTH_TOKEN = base64.encodestring(token)
      self.WEB_AUTH_TOKEN = self.WEB_AUTH_TOKEN.replace("\n", "")
    else:
      self.WEB_AUTH_TOKEN = None

    self.QUERY_SEASONS = self.getBoolean(config, "query.seasons", "yes")
    self.QUERY_EPISODES = self.getBoolean(config, "query.episodes", "yes") if self.QUERY_SEASONS else False

    self.DOWNLOAD_THREADS_DEFAULT = int(self.getValue(config, "download.threads", "2"))
    self.DOWNLOAD_RETRY = int(self.getValue(config, "download.retry", "3"))
    self.DOWNLOAD_PRIME = self.getBoolean(config, "download.prime", "yes")

    # It seems that Files.Preparedownload is sufficient to populate the texture cache
    # so there is no need to actually download the artwork.
    # v0.8.8: Leave enabled for now, may only be sufficient in recent builds.
    self.DOWNLOAD_PAYLOAD = self.getBoolean(config, "download.payload","yes")

    self.DOWNLOAD_THREADS = {}
    for x in ["addons", "albums", "artists", "songs", "movies", "sets", "tags", "tvshows", "musicvideos", "pvr.tv", "pvr.radio"]:
      temp = int(self.getValue(config, "download.threads.%s" % x, self.DOWNLOAD_THREADS_DEFAULT))
      self.DOWNLOAD_THREADS["download.threads.%s" % x] = temp

    self.SINGLETHREAD_URLS = self.getPatternFromList(config, "singlethread.urls", serial_urls, allowundefined=True)

    self.XTRAJSON = {}
    self.QA_FIELDS = {}

    # Modifiers - all are optional:
    #    ? - warn instead of fail when item is missing (or present in fail/warn pattern)
    #    # - don't warn when missing, warn otherwise (unless art present in fail list, then fail)
    #    ! - don't warn when missing, fail otherwise (unless art present in warn list, then warn)
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
              "albums", "artists", "songs", "musicvideos",
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
          self.QA_FIELDS[key] = temp if temp is not None else self.QA_FIELDS.get(key, None)

    self.QAPERIOD = int(self.getValue(config, "qaperiod", "30"))
    adate = datetime.date.today() - datetime.timedelta(days=self.QAPERIOD)
    self.QADATE = adate.strftime("%Y-%m-%d") if self.QAPERIOD >= 0 else None

    self.QA_FILE = self.getBoolean(config, "qa.file", "no")
    self.QA_FAIL_CHECKEXISTS = self.getBoolean(config, "qa.fail.checkexists", "yes")
    self.QA_FAIL_MISSING_LOCAL_ART = self.getBoolean(config, "qa.fail.missinglocalart", "no")
    self.QA_FAIL_TYPES = self.getPatternFromList(config, "qa.fail.urls", embedded_urls, allowundefined=True)
    self.QA_WARN_TYPES = self.getPatternFromList(config, "qa.warn.urls", "")

    (self.QA_NFO_REFRESH, self.qa_nfo_refresh_date, self.qa_nfo_refresh_date_fmt) = self.getRelativeDateAndFormat(config, "qa.nfo.refresh", "")
    self.QA_USEOLDREFRESHMETHOD = self.getBoolean(config, "qa.useoldrefreshmethod", "yes")

    self.CACHE_CAST_THUMB = self.getBoolean(config, "cache.castthumb", "no")

    (self.CACHE_REFRESH, self.cache_refresh_date, self.cache_refresh_date_fmt) = self.getRelativeDateAndFormat(config, "cache.refresh", "")

    yn = "yes" if self.getBoolean(config, "cache.extra", "no") else "no"
    self.CACHE_EXTRA_FANART = self.getBoolean(config, "cache.extrafanart", yn)
    self.CACHE_EXTRA_THUMBS = self.getBoolean(config, "cache.extrathumbs", yn)
    # http://kodi.wiki/view/Add-on:VideoExtras
    self.CACHE_VIDEO_EXTRAS = self.getBoolean(config, "cache.videoextras", yn)
    self.CACHE_EXTRA = (self.CACHE_EXTRA_FANART or self.CACHE_EXTRA_THUMBS or self.CACHE_VIDEO_EXTRAS)

    self.LOGFILE = self.getValue(config, "logfile", "")
    self.LOGVERBOSE = self.getBoolean(config, "logfile.verbose", "yes")
    self.LOGUNIQUE = self.getBoolean(config, "logfile.unique", "no")
    self.LOGDCACHE = self.getBoolean(config, "logfile.dcache", "no")

    self.CACHE_ARTWORK = self.getSimpleList(config, "cache.artwork", "")
    self.CACHE_IGNORE_TYPES = self.getPatternFromList(config, "cache.ignore.types", embedded_urls, allowundefined=True)
    self.PRUNE_RETAIN_TYPES = self.getPatternFromList(config, "prune.retain.types", "")

    self.CACHE_DROP_INVALID_FILE = self.getValue(config, "cache.dropfile", "")

    # Fix patterns as we now strip image:// from the URLs, so we need to remove
    # this prefix from any legacy patterns that may be specified by the user
    for index, r in enumerate(self.CACHE_IGNORE_TYPES):
      self.CACHE_IGNORE_TYPES[index] = re.compile(re.sub("^\^image://", "^", r.pattern))
    for index, r in enumerate(self.PRUNE_RETAIN_TYPES):
      self.PRUNE_RETAIN_TYPES[index] = re.compile(re.sub("^\^image://", "^", r.pattern))

    self.PRUNE_RETAIN_PREVIEWS = self.getBoolean(config, "prune.retain.previews", "yes")
    self.PRUNE_RETAIN_PICTURES = self.getBoolean(config, "prune.retain.pictures", "no")
    self.PRUNE_RETAIN_CHAPTERS = self.getBoolean(config, "prune.retain.chapters", "yes")

    self.MISSING_IGNORE_PATTERNS = self.getPatternFromList(config, "missing.ignore.patterns", "", allowundefined=True)

    self.picture_filetypes    = m_pictureExtensions.split("|")
    self.PICTURE_FILETYPES_EX = self.getFileExtList(config, "picture.filetypes", "")
    self.picture_filetypes.extend(self.PICTURE_FILETYPES_EX)

    self.video_filetypes    = m_videoExtensions.split("|")
    self.VIDEO_FILETYPES_EX = self.getFileExtList(config, "video.filetypes", "")
    self.video_filetypes.extend(self.VIDEO_FILETYPES_EX)

    self.audio_filetypes    = m_musicExtensions.split("|")
    self.AUDIO_FILETYPES_EX = self.getFileExtList(config, "audio.filetypes", "")
    self.audio_filetypes.extend(self.AUDIO_FILETYPES_EX)

    self.subtitle_filetypes    = m_subtitlesExtensions.split("|")
    self.SUBTITLE_FILETYPES_EX = self.getFileExtList(config, "subtitle.filetypes", "")
    self.subtitle_filetypes.extend(self.SUBTITLE_FILETYPES_EX)

    self.IGNORE_PLAYLISTS = self.getBoolean(config, "ignore.playlists","yes")

    self.RECACHEALL = self.getBoolean(config, "allow.recacheall","no")
    self.CHECKUPDATE = self.getBoolean(config, "checkupdate", "yes")
    self.AUTOUPDATE = self.getBoolean(config, "autoupdate", "yes")

    self.LASTRUNFILE = self.getValue(config, "lastrunfile", "")
    self.LASTRUNFILE_DATETIME = None
    if self.LASTRUNFILE and os.path.exists(self.LASTRUNFILE):
        temp = datetime.datetime.fromtimestamp(os.path.getmtime(self.LASTRUNFILE))
        self.LASTRUNFILE_DATETIME = temp.strftime("%Y-%m-%d %H:%M:%S")

    self.ORPHAN_LIMIT_CHECK = self.getBoolean(config, "orphan.limit.check", "yes")

    self.CACHE_HIDEALLITEMS = self.getBoolean(config, "cache.hideallitems", "no")

    self.WATCHEDOVERWRITE = self.getBoolean(config, "watched.overwrite", "no")

    self.MAC_ADDRESS = self.getValue(config, "network.mac", "")

    self.ADD_SET_MEMBERS = self.getBoolean(config, "setmembers", "yes")
    self.ADD_SONG_MEMBERS = self.getBoolean(config, "songmembers", "no")

    self.PURGE_MIN_LEN = int(self.getValue(config, "purge.minlen", "5"))

    self.OMDB_API_KEY = self.getValue(config, "omdb.apikey", None, True)

    self.IMDB_FIELDS_MOVIES = self.getExRepList(config, "imdb.fields.movies", ["rating", "votes", "top250"], True)
    self.IMDB_FIELDS_TVSHOWS = self.getExRepList(config, "imdb.fields.tvshows", ["rating", "votes"], True)
    self.IMDB_IGNORE_TVTITLES = self.getSimpleList(config, "imdb.ignore.tvtitles", "", True, "|")
    self.IMDB_MAP_TVTITLES = self.getSimpleList(config, "imdb.map.tvtitles", "", True, "|")
    self.IMDB_TRANSLATE_TVTITLES = self.getSimpleList(config, "imdb.translate.tvtitles", "", True, "|", False)
    self.IMDB_TRANSLATE_TVYEARS = self.getSimpleList(config, "imdb.translate.tvyears", "", True, "|")
    self.IMDB_IGNORE_MISSING_EPISODES = self.getBoolean(config, "imdb.ignore.missing.episodes", "no")
    self.IMDB_THREADS = int(self.getValue(config, "imdb.threads", 10))
    self.IMDB_THREADS = 1 if self.IMDB_THREADS < 1 else self.IMDB_THREADS
    self.IMDB_THREADS = 20 if self.IMDB_THREADS > 20 else self.IMDB_THREADS
    self.IMDB_TIMEOUT = self.getValue(config, "imdb.timeout", 15.0, allowundefined=True)
    if self.IMDB_TIMEOUT: self.IMDB_TIMEOUT = float(self.IMDB_TIMEOUT)
    self.IMDB_RETRY = int(self.getValue(config, "imdb.retry", 3))
    self.IMDB_RETRY = 0 if self.IMDB_RETRY < 0 else self.IMDB_RETRY
    self.IMDB_GROUPING = self.getValue(config, "imdb.grouping", ",", allowundefined=True)
    self.IMDB_GROUPING = self.IMDB_GROUPING if self.IMDB_GROUPING is not None else ""
    self.IMDB_DEL_PARENTHESIS = self.getBoolean(config, "imdb.delete_parenthesis", "yes")

    self.IMDB_PERIOD = self.getValue(config, "imdb.period", None, allowundefined=True)
    if self.IMDB_PERIOD:
      adate = datetime.date.today() - datetime.timedelta(days=int(self.IMDB_PERIOD))
      self.IMDB_PERIOD_FROM = adate.strftime("%Y-%m-%d")
    else:
      self.IMDB_PERIOD_FROM = None

    self.BIN_TVSERVICE = self.getValue(config, "bin.tvservice", "/usr/bin/tvservice")
    self.BIN_VCGENCMD = self.getValue(config, "bin.vcgencmd", "/usr/bin/vcgencmd", allowundefined=True)
    self.BIN_CECCONTROL = self.getValue(config, "bin.ceccontrol", "")
    self.HDMI_FORCE_HOTPLUG = self.getBoolean(config, "hdmi.force.hotplug", "no")
    self.HDMI_IGNORE_SUSPEND = self.getBoolean(config, "hdmi.ignoresuspend", "no")
    self.HDMI_IGNORE_DISABLE = self.getBoolean(config, "hdmi.ignoredisable", "no")
    self.HDMI_IGNORE_PLAYER = self.getBoolean(config, "hdmi.ignoreplayer", "no")
    self.HDMI_IGNORE_LIBRARY = self.getBoolean(config, "hdmi.ignorelibrary", "no")

    # Use a smaller cache on ARM systems, based on the assumption that ARM systems
    # will have less memory than other platforms
    defSize = "512" if platform.machine().lower().startswith("arm") else "2048"
    self.DCACHE_SIZE = int(self.getValue(config, "dcache.size", defSize))
    self.DCACHE_AGELIMIT = int(self.getValue(config, "dcache.agelimit", "180"))

    self.FILTER_FIELD = self.getValue(config, "filter", "")
    self.FILTER_OPERATOR = self.getValue(config, "filter.operator", "contains")

    self.SEARCH_ENCODE = self.getBoolean(config, "encode", "yes")

    self.POSTER_WIDTH = int(self.getValue(config, "posterwidth", "5"))

    self.CLEAN_SHOW_DIALOGS = self.getBoolean(config, "clean.showdialogs", "no")
    self.SCAN_SHOW_DIALOGS = self.getBoolean(config, "scan.showdialogs", "no")

    self.LOG_REPLAY_FILENAME = self.getValue(config, "replayfile", "")
    self.log_replay_fmap = {}
    self.log_replay_tmap = {}

  def getdefaultuserdata(self, appid):
    atv2_path     = "/User/Library/Preferences/%s/userdata" % appid
    macosx_path   = "~/Library/Application Support/%s/userdata" % appid

    linux1_path    = "/var/lib/%s/.%s/userdata" % (appid.lower(), appid.lower())
    linux2_path    = "~/.%s/userdata" % appid.lower()

    android1_path = "Android/data/org.%s.%s/files/.%s/userdata" % (appid.lower(), appid.lower(), appid.lower())
    android2_path = "/sdcard/%s" % android1_path
    firetv_path = "/storage/emulated/0/%s" % android1_path

    if sys.platform == "win32":
      win32_path = "%s\\%s\\userdata" % (os.environ["appdata"], appid)
      if os.path.exists(win32_path):
        return win32_path
    elif sys.platform == "darwin" and os.path.exists(atv2_path):
      return atv2_path
    elif sys.platform == "darwin" and os.path.exists(os.path.expanduser(macosx_path)):
      return macosx_path
    else: #Linux/Android
      if os.path.exists(os.path.expanduser(linux1_path)):
        return linux1_path
      elif os.path.exists(os.path.expanduser(linux2_path)):
        return linux2_path
      elif os.path.exists(firetv_path):
        return firetv_path
      elif os.path.exists(android2_path):
        return android2_path
      elif os.path.exists(android1_path):
        return android1_path

    return None

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

    # https://github.com/xbmc/xbmc/commit/20717c1b0cc2e5b35996be52cabd7267e0799995
    self.JSON_HAS_ISO_DATES = self.HasJSONCapability("isodates")

    # https://github.com/xbmc/xbmc/pull/4766
    self.JSON_HAS_DPMS_NOTIFY = self.HasJSONCapability("dpmsnotify")

    # https://github.com/xbmc/xbmc/commit/77812fbc7e35aaea67e5df31a96a932f85595184
    self.JSON_HAS_DEBUG_EXTRA_LOG = self.HasJSONCapability("debugextralog")

    # https://github.com/xbmc/xbmc/pull/5454
    self.JSON_HAS_OPEN_PLAYERCORE_DEFAULT = self.HasJSONCapability("openplayercoredef")

    # https://github.com/xbmc/xbmc/pull/5324
    self.JSON_HAS_LIB_SHOWDIALOGS_PARAM = self.HasJSONCapability("libshowdialogs")

    #https://github.com/xbmc/xbmc/pull/5786
    self.JSON_HAS_EXIT_CODE = self.HasJSONCapability("exitcode")

    #https://github.com/xbmc/xbmc/pull/7306
    self.JSON_HAS_REFRESH_REFACTOR = self.HasJSONCapability("refreshrefactor")

    # Support profile switching?
    self.JSON_HAS_PROFILE_SUPPORT = self.HasJSONCapability("profilesupport")

    #https://github.com/xbmc/xbmc/pull/8080
    self.JSON_VOTES_HAVE_NO_GROUPING = self.HasJSONCapability("votesnogrouping")

    self.JSON_PLAYER_PROCESS_INFO = self.HasJSONCapability("playerprocessinfo")
    self.JSON_CODEC_INFO_REMOVED = self.HasJSONCapability("codecinforemoved")

    # https://github.com/xbmc/xbmc/pull/8196
    self.JSON_HAS_PROFILE_DIRECTORY = self.HasJSONCapability("profiledirectory")

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

    # Depending on JSON version, and user region, lastmodified date will be formatted in several ways.
    # When JSON_HAS_ISO_DATES, the date will always be YYYY-MM-DD HH:MM:SS, easy.
    # Otherwise it may be any format... assume either US (mm/dd/yyyy) or non-US (dd/mm/yyyy).
    self.MDATE_MDY = self.getBoolean(self.config, "modifieddate.mdy", "no") # US (mm/dd/yyyy) or euro (dd/mm/yyyy)
    if self.JSON_HAS_ISO_DATES:
      self.qa_lastmodified_fmt = "%Y-%m-%d %H:%M:%S"
    else:
      if self.MDATE_MDY:
        self.qa_lastmodified_fmt = "%m/%d/%Y %H:%M:%S"
      else:
        self.qa_lastmodified_fmt = "%d/%m/%Y %H:%M:%S"

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
          if default is None and not allowundefined:
            raise ConfigParser.NoOptionError(aKey, "%s (or global section)" % self.THIS_SECTION)
      else:
        if default is None and not allowundefined:
          raise ConfigParser.NoOptionError(aKey, self.GLOBAL_SECTION)

    return value if value else default

  # default value will be used if key is present, but without a value
  def getBoolean(self, config, aKey, default="no"):
    temp = self.getValue(config, aKey, default).lower()
    return temp in ["yes", "true"]

  def getSimpleList(self, config, aKey, default="", allowundefined=False, delimiter=",", strip=True):
    aStr = self.getValue(config, aKey, default, allowundefined)

    newlist = []

    if aStr:
      for item in [x for x in aStr.split(delimiter) if x]:
        if item and strip:
          item = item.strip()
        if item:
          newlist.append(item)
    elif aStr is None and allowundefined:
      return default

    return newlist

  def getFileExtList(self, config, aKey, default="", allowundefined=False):
    newList = []
    for x in [x.lower() for x in self.getSimpleList(config, aKey, default, allowundefined)]:
      if not x.startswith("."):
        x = ".%s" % x
      if x not in newList:
        newList.append(x)
    return newList

  # Return an extended or replacement list
  def getExRepList(self, config, aKey, initialList=[], allowundefined=False):
    if self.getValue(config, aKey, "", allowundefined=True) is None:
      return []

    aList = self.getSimpleList(config, aKey, "", allowundefined)
    iList = initialList

    if aList:
      if len(aList) != 0 and aList[0][:1] == "+":
        aList[0] = aList[0][1:]
      else:
        iList = []

    for a in aList:
      if a not in iList:
        iList.append(a)

    return iList

  def getPatternFromList(self, config, aKey, default="", allowundefined=False):
    aList = self.getValue(config, aKey, default, allowundefined)

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

  def getRelativeDateAndFormat(self, config, key, default, allowundefined=False):
    adate = self.getValue(config, key, default, allowundefined)
    if adate:
      if adate.lower() == "today":
        t = datetime.date.today()
        temp_date = datetime.datetime(t.year, t.month, t.day, 0, 0, 0)
      elif re.search("^[0-9]*$", adate):
        t = datetime.date.today() - datetime.timedelta(days=int(adate))
        temp_date = datetime.datetime(t.year, t.month, t.day, 0, 0, 0)
      else:
        temp_date = datetime.datetime.strptime(adate, "%Y-%m-%d %H:%M:%S")
      date_seconds = MyUtility.SinceEpoch(temp_date)
      date_formatted = temp_date.strftime("%Y-%m-%d %H:%M:%S")
    else:
      date_seconds = None
      date_formatted = None

    return (adate, date_seconds, date_formatted)

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
          if stripModifier and item[:1] in ["?", "#", "!"]:
            newitem = item[1:]
          else:
            newitem = item
          if newitem and newitem not in newlist:
            newlist.append(newitem)

    return newlist

  def getFilePath(self, filename=""):
    if os.path.isabs(self.THUMBNAILS):
      return os.path.join(self.THUMBNAILS, filename)
    else:
      return os.path.join(self.CURRENT_PROFILE["tc.profilepath"], self.THUMBNAILS, filename)

  def getDBPath(self):
    if os.path.isabs(self.TEXTUREDB):
      return self.TEXTUREDB
    else:
      return os.path.join(self.CURRENT_PROFILE["tc.profilepath"], self.TEXTUREDB)

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

  # Dump configuration variables, ignoring any keys that are not entirely upper case
  def dumpMemberVariables(self):
    mv = {}
    for key in self.__dict__.keys():
      if key == key.upper():
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
    print("  userdata = %s " % self.KODI_BASE)
    print("  dbfile = %s" % self.TEXTUREDB)
    print("  thumbnails = %s " % self.THUMBNAILS)
    print("  kodi.host = %s" % self.KODI_HOST)
    print("  webserver.port = %s" % self.WEB_PORT)
    print("  webserver.ctimeout = %s" % self.NoneIsBlank(self.WEB_CONNECTTIMEOUT))
    print("  rpc.port = %s" % self.RPC_PORT)
    print("  rpc.ipversion = %s" % self.RPC_IPVERSION)
    print("  rpc.retry = %s" % self.RPC_RETRY)
    print("  rpc.ctimeout = %s" % self.NoneIsBlank(self.RPC_CONNECTTIMEOUT))
    print("  chunked = %s" % self.BooleanIsYesNo(self.CHUNKED))
    print("  modifieddate.mdy = %s" % self.BooleanIsYesNo(self.MDATE_MDY))
    print("  query.seasons = %s" % self.BooleanIsYesNo(self.QUERY_SEASONS))
    print("  query.episodes = %s" % self.BooleanIsYesNo(self.QUERY_EPISODES))
    print("  download.predelete = %s" % self.BooleanIsYesNo(self.DOWNLOAD_PREDELETE))
    print("  download.payload = %s" % self.BooleanIsYesNo(self.DOWNLOAD_PAYLOAD))
    print("  download.retry = %d" % self.DOWNLOAD_RETRY)
    print("  download.prime = %s" % self.BooleanIsYesNo(self.DOWNLOAD_PRIME))
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
    print("  songmembers = %s" % self.BooleanIsYesNo(self.ADD_SONG_MEMBERS))
    print("  qaperiod = %d (added after %s)" % (self.QAPERIOD, self.QADATE))
    print("  qa.file = %s" % self.BooleanIsYesNo(self.QA_FILE))
    print("  qa.nfo.refresh = %s%s" % (self.NoneIsBlank(self.QA_NFO_REFRESH), " (%s)" % self.qa_nfo_refresh_date_fmt if self.qa_nfo_refresh_date_fmt else ""))
    print("  qa.useoldrefreshmethod = %s" % (self.BooleanIsYesNo(self.QA_USEOLDREFRESHMETHOD)))
    print("  qa.fail.checkexists = %s" % self.BooleanIsYesNo(self.QA_FAIL_CHECKEXISTS))
    print("  qa.fail.missinglocalart = %s" % self.BooleanIsYesNo(self.QA_FAIL_MISSING_LOCAL_ART))
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
    print("  cache.refresh = %s%s" % (self.NoneIsBlank(self.CACHE_REFRESH), " (%s)" % self.cache_refresh_date_fmt if self.cache_refresh_date_fmt else ""))
    print("  cache.dropfile = %s" % self.NoneIsBlank(self.CACHE_DROP_INVALID_FILE))
    print("  prune.retain.types = %s" % self.NoneIsBlank(self.getListFromPattern(self.PRUNE_RETAIN_TYPES)))
    print("  prune.retain.previews = %s" % self.BooleanIsYesNo(self.PRUNE_RETAIN_PREVIEWS))
    print("  prune.retain.pictures = %s" % self.BooleanIsYesNo(self.PRUNE_RETAIN_PICTURES))
    print("  prune.retain.chapters = %s" % self.BooleanIsYesNo(self.PRUNE_RETAIN_CHAPTERS))
    print("  missing.ignore.patterns = %s" % self.NoneIsBlank(self.getListFromPattern(self.MISSING_IGNORE_PATTERNS)))
    print("  logfile = %s" % self.NoneIsBlank(self.LOGFILE))
    print("  logfile.verbose = %s" % self.BooleanIsYesNo(self.LOGVERBOSE))
    print("  logfile.unique = %s" % self.BooleanIsYesNo(self.LOGUNIQUE))
    print("  logfile.dcache = %s" % self.BooleanIsYesNo(self.LOGDCACHE))
    print("  checkupdate = %s" % self.BooleanIsYesNo(self.CHECKUPDATE))
    print("  autoupdate = %s" % self.BooleanIsYesNo(self.AUTOUPDATE))
    if self.RECACHEALL:
      print("  allow.recacheall = yes")
    temp = " (%s)" % self.LASTRUNFILE_DATETIME if self.LASTRUNFILE and self.LASTRUNFILE_DATETIME else ""
    print("  lastrunfile = %s%s" % (self.NoneIsBlank(self.LASTRUNFILE), temp))
    print("  orphan.limit.check = %s" % self.BooleanIsYesNo(self.ORPHAN_LIMIT_CHECK))
    print("  purge.minlen = %s" % self.PURGE_MIN_LEN)
    print("  picture.filetypes = %s" % self.NoneIsBlank(", ".join(self.PICTURE_FILETYPES_EX)))
    print("  video.filetypes = %s" % self.NoneIsBlank(", ".join(self.VIDEO_FILETYPES_EX)))
    print("  audio.filetypes = %s" % self.NoneIsBlank(", ".join(self.AUDIO_FILETYPES_EX)))
    print("  subtitle.filetypes = %s" % self.NoneIsBlank(", ".join(self.SUBTITLE_FILETYPES_EX)))
    print("  watched.overwrite = %s" % self.BooleanIsYesNo(self.WATCHEDOVERWRITE))
    print("  network.mac = %s" % self.NoneIsBlank(self.MAC_ADDRESS))
    print("  imdb.fields.movies = %s" % self.NoneIsBlank(", ".join(self.IMDB_FIELDS_MOVIES)))
    print("  imdb.fields.tvshows = %s" % self.NoneIsBlank(", ".join(self.IMDB_FIELDS_TVSHOWS)))
    print("  imdb.ignore.tvtitles = %s" % self.NoneIsBlank("|".join(self.IMDB_IGNORE_TVTITLES)))
    print("  imdb.map.tvtitles = %s" % self.NoneIsBlank("|".join(self.IMDB_MAP_TVTITLES)))
    print("  imdb.translate.tvtitles = %s" % self.NoneIsBlank("|".join(self.IMDB_TRANSLATE_TVTITLES)))
    print("  imdb.translate.tvyears = %s" % self.NoneIsBlank("|".join(self.IMDB_TRANSLATE_TVYEARS)))
    print("  imdb.ignore.missing.episodes = %s" % self.BooleanIsYesNo(self.IMDB_IGNORE_MISSING_EPISODES))
    print("  imdb.threads = %s" % self.IMDB_THREADS)
    print("  imdb.timeout = %s" % self.NoneIsBlank(self.IMDB_TIMEOUT))
    print("  imdb.retry = %s" % self.IMDB_RETRY)
    print("  imdb.grouping = %s" % self.IMDB_GROUPING)
    if self.IMDB_PERIOD_FROM:
      print("  imdb.period = %s (added after %s)" % (self.NoneIsBlank(self.IMDB_PERIOD), self.NoneIsBlank(self.IMDB_PERIOD_FROM)))
    else:
      print("  imdb.period = %s" % (self.NoneIsBlank(self.IMDB_PERIOD)))
    print("  imdb.delete_parenthesis = %s" % self.BooleanIsYesNo(self.IMDB_DEL_PARENTHESIS))
    print("  bin.tvservice = %s" % self.NoneIsBlank(self.BIN_TVSERVICE))
    print("  bin.vcgencmd = %s" % self.NoneIsBlank(self.BIN_VCGENCMD))
    print("  bin.ceccontrol = %s" % self.NoneIsBlank(self.BIN_CECCONTROL))
    print("  hdmi.force.hotplug = %s" % self.BooleanIsYesNo(self.HDMI_FORCE_HOTPLUG))
    print("  hdmi.ignoresuspend = %s" % self.BooleanIsYesNo(self.HDMI_IGNORE_SUSPEND))
    print("  hdmi.ignoredisable = %s" % self.BooleanIsYesNo(self.HDMI_IGNORE_DISABLE))
    print("  hdmi.ignoreplayer = %s" % self.BooleanIsYesNo(self.HDMI_IGNORE_PLAYER))
    print("  hdmi.ignorelibrary = %s" % self.BooleanIsYesNo(self.HDMI_IGNORE_LIBRARY))
    print("  dcache.size = %d" % self.DCACHE_SIZE)
    print("  dcache.agelimit = %d" % self.DCACHE_AGELIMIT)
    print("  posterwidth = %d" % self.POSTER_WIDTH)
    print("  clean.showdialogs = %s" % self.BooleanIsYesNo(self.CLEAN_SHOW_DIALOGS))
    print("  scan.showdialogs = %s" % self.BooleanIsYesNo(self.SCAN_SHOW_DIALOGS))

#    print("  profile.master = %s" % self.NoneIsBlank(self.PROFILE_MASTER))
    print("  profile.enabled = %s" % self.BooleanIsYesNo(self.PROFILE_ENABLED))
    print("  profile.autoload = %s" % self.BooleanIsYesNo(self.PROFILE_AUTOLOAD))
    print("  profile.retry = %s" % self.PROFILE_RETRY)
    print("  profile.wait = %s" % self.PROFILE_WAIT)
    print("  profile.name = %s" % self.NoneIsBlank(self.PROFILE_NAME))
    print("  profile.password = %s" % self.NoneIsBlank(self.PROFILE_PASSWORD))
    print("  profile.password.encrypted = %s" % self.BooleanIsYesNo(self.PROFILE_ENCRYPTED))
    print("  profile.directory = %s" % self.NoneIsBlank(self.PROFILE_DIRECTORY))

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
  def __init__(self):
    self.lastlen = 0
    self.now = 0
    self.LOGGING = False
    self.LOGFILE = None
    self.LOGFLUSH = False
    self.DEBUG = False
    self.VERBOSE = False

    try:
      self.ISATTY = sys.stdout.isatty()
    except:
      self.ISATTY = False

    #Ensure stdout/stderr use utf-8 encoding...
    if MyUtility.isPython3_1:
      sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
      sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    else:
      sys.stdout = codecs.getwriter("utf-8")(sys.stdout)
      sys.stderr = codecs.getwriter("utf-8")(sys.stderr)

  def __del__(self):
    if self.LOGFILE: self.LOGFILE.close()

  def setLogFile(self, config=None):
    with lock:
      if config and config.LOGFILE:
        if not self.LOGGING:
          filename = config.LOGFILE
          self.LOGFLUSH = filename.startswith("+")
          if self.LOGFLUSH: filename = filename[1:]
          try:
            if config.LOGUNIQUE:
              t = tempfile.mkstemp(prefix="%s." % os.path.basename(filename), suffix="", dir=os.path.dirname(filename))
              filename = t[1]
              os.close(t[0])
            self.LOGFILE = codecs.open(filename, "w", encoding="utf-8")
            self.LOGGING = True
          except:
            raise IOError("Unable to open logfile for writing!")
      else:
        self.LOGGING = False
        if self.LOGFILE:
          self.LOGFILE.close()
          self.LOGFILE = None

  def progress(self, data, every=0, finalItem=False, newLine=False, noBlank=False):
    with lock:
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
        sys.stderr.write("%-s%*s\r%s" % (udata, spaces, " ", ("\n" if newLine else "")))
      else:
        sys.stderr.write("%-s\r%s" % (udata, ("\n" if newLine else "")))
      if newLine:
        self.lastlen = 0
      sys.stderr.flush()

  def reset(self, initialValue=0):
    self.now = initialValue

  def out(self, data, newLine=False, log=False, padspaces=True):
    with lock:
      udata = MyUtility.toUnicode(data)
      ulen = len(data)
      spaces = self.lastlen - ulen
      self.lastlen = ulen if udata.rfind("\n") == -1 else 0

      NL = "\n" if newLine else ""

      if spaces > 0:
        sys.stdout.write("%-s%*s%s" % (udata, spaces, " ", NL))
      else:
        sys.stdout.write("%-s%s" % (udata, NL))

      if newLine or not padspaces:
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
    with lock:
      if self.DEBUG:
        if self.ISATTY:
          self.out("%s: [%s] %s" % (datetime.datetime.now(), self.OPTION, data), newLine=True)
        else:
          self.out("[%s] %s" % (self.OPTION, data), newLine=True)
        if self.LOGGING:
          self.log("[DEBUG] %s" % data, jsonrequest=jsonrequest)

  def log(self, data, jsonrequest=None, maxLen=0):
    if self.LOGGING:
      with lock:
        udata = MyUtility.toUnicode(data)

        t = threading.current_thread().name
        if jsonrequest is None:
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

  # Use this method for large Unicode data - tries to minimize
  # creation of additional temporary buffers through concatenation.
  def log2(self, prefix, udata, jsonrequest=None, maxLen=0):
    if self.LOGGING:
      with lock:
        t = threading.current_thread().name
        self.LOGFILE.write("%s:%-10s: %s" % (datetime.datetime.now(), t, prefix))

        if jsonrequest is None:
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
    with lock:
      self.progress("")
      udata = MyUtility.toUnicode(data)
      if newLine:
        sys.stderr.write("%-s\n" % udata)
      else:
        sys.stderr.write("%-s" % udata)
      sys.stderr.flush()
    if log: self.log(data)

  def flush(self):
    sys.stdout.flush()
    sys.stderr.flush()
    if self.LOGFILE: self.LOGFILE.flush()

#
# Image loader thread class.
#
class MyImageLoader(threading.Thread):
  def __init__(self, work_queue, other_queue, error_queue, complete_queue,
                config, logger, totals, force=False, retry=0):
    threading.Thread.__init__(self)

    self.work_queue = work_queue
    self.other_queue = other_queue
    self.error_queue = error_queue
    self.complete_queue = complete_queue

    self.config = config
    self.logger = logger
    self.database = MyDB(config, logger)
    self.json = MyJSONComms(config, logger)
    self.totals = totals

    self.force = force
    self.retry = retry

    self.totals.init(self.name)

  def run(self):
    with self.database:
      while not stopped.is_set():
        try:
          item = self.work_queue.get(block=False)
          self.work_queue.task_done()

          if not self.loadImage(item) and not item.missingOK:
            self.error_queue.put(item)

          self.complete_queue.put(item)

        except Queue.Empty:
          break

        except IOEndOfReplayLog:
          break

    self.totals.stop()
    self.complete_queue.put(None)

  def geturl(self, item):
    PDRETRY = self.retry

    # Call Files.PrepareDownload. If failure, retry up to retry times, waiting a short
    # interval between each attempt.
    url = self.json.getDownloadURL(item.filename)
    rowexists = True

    # If no URL, could be because thumbnail is missing but DB row exists - if thumbnail
    # no longer available, then delete the row and try again to obtain URL
    if url is None and not self.config.DOWNLOAD_PREDELETE and item.dbid != 0 and self.force:
      if self.config.HAS_THUMBNAILS_FS and not os.path.exists(self.config.getFilePath(item.cachedurl)):
        self.logger.log("Deleting row with missing image from cache - id [%d], cachedurl [%s] for filename [%s]"
                      % (item.dbid, item.cachedurl, item.decoded_filename))
        self.database.deleteItem(item.dbid, None)
        rowexists = False

    # If DOWNLOAD_PRIME is enabled, request the remote URL directly. If not available, don't bother
    # retrying call to Files.PrepareDownload as it will surely fail.
    if PDRETRY > 0 and url is None and self.config.DOWNLOAD_PRIME:
      isAvailable = self.prime_the_request(item.decoded_filename)
    else:
      isAvailable  = True

    # Retry call to Files.PrepareDownload - hopefully it will succeed eventually...
    while PDRETRY > 0 and url is None and isAvailable:
      self.logger.log("Retrying getDownloadURL(), %d attempts remaining" % PDRETRY)
      # Introduce a short delay, unless we're playing back a log file...
      if self.json.LOG_REPLAYFILE is None: time.sleep(0.5)
      PDRETRY -= 1
      url = self.json.getDownloadURL(item.filename)

    return (url, rowexists)

  # Directly request the remote URL returning True if still available
  def prime_the_request(self, url):
    if url is None: return False

    if url.startswith("http://"):
      domain = url.replace("http://", "").split("/")[0]
      page = "/" + "/".join(url.replace("http://", "").split("/")[1:])
      issecure = False
    elif url.startswith("https://"):
      domain = url.replace("https://", "").split("/")[0]
      page = "/" + "/".join(url.replace("https://", "").split("/")[1:])
      issecure = True
    else:
      return True

    isAvailable = True
    try:
      PAYLOAD = self.json.sendWeb("GET", page, "primeImage", headers={"User-agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:38.0) Gecko/20100101 Firefox/38.0"}, \
                                  readAmount=1024, rawData=True, domain=domain, useSSL=issecure)
      self.logger.log("Primed request of: HTTPS=%s, Domain [%s] with URL [%s], result [%d, %s]" % (issecure, domain, page, self.json.WEB_LAST_STATUS, self.json.WEB_LAST_REASON))
      isAvailable = (self.json.WEB_LAST_STATUS == 200 or 300 <= self.json.WEB_LAST_STATUS < 400)
    except:
      isAvailable = False

    return isAvailable

  def loadImage(self, item):
    ATTEMPT = 1 if self.retry < 1 else self.retry
    PERFORM_DOWNLOAD = False

    self.totals.start(item.mtype, item.itype)

    (url, rowexists) = self.geturl(item)

    if url:
      if not self.config.DOWNLOAD_PREDELETE:
        if item.dbid != 0 and self.force:
          if rowexists:
            self.logger.log("Deleting old image from cache with id [%d], cachedurl [%s] for filename [%s]"
                            % (item.dbid, item.cachedurl, item.decoded_filename))
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
        PAYLOAD = self.json.sendWeb("GET", url, "loadImage", readAmount=1024, rawData=True)
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
# IMDB Thread
#
class MyIMDBLoader(threading.Thread):
  def __init__(self, config, logger, input_queue, output_queue, plotFull, plotOutline, movies250, imdbfields):
    threading.Thread.__init__(self)

    self.config = config
    self.logger = logger

    self.input_queue = input_queue
    self.output_queue = output_queue

    self.plotFull = plotFull
    self.plotOutline = plotOutline
    self.movies250 = movies250

    # We don't need to query OMDb if only updating top250
    self.omdbquery = (imdbfields != ["top250"])

    # Avoid querying OMDb if we're only updating fields available from Top250 movie list
    self.onlyt250fields = (set(imdbfields).issubset(["top250", "rating", "votes"]))

    self.ignore_missing_episodes = config.IMDB_IGNORE_MISSING_EPISODES

    self.timeout = self.config.IMDB_TIMEOUT
    self.retry = self.config.IMDB_RETRY
    self.apikey = self.config.OMDB_API_KEY

  def run(self):
    while not stopped.is_set():
      try:
        qItem = self.input_queue.get(block=False)
        self.input_queue.task_done()

        item = qItem["item"]

        imdbnumber = item.get("imdbnumber", None)

        title = item.get("title", item["label"])
        original_title = qItem.get("OriginalShowTitle", title)
        year = item.get("year", None)

        multipart_ep = qItem.get("multipart_ep", None) # (season#, episode#) of first episode in a multipart episode

        showTitle = title
        showYear = year
        season = None
        episode = None

        isMovie = isTVShow = isEpisode = False

        if "movieid" in item:
          libid = item["movieid"]
          isMovie = True
        elif "tvshowid" in item:
          libid = item["tvshowid"]
          if year and title.endswith("(%d)" % year):
            title = re.sub("\(%d\)$" % year, "", title).strip()
          isTVShow = True
        elif "episodeid" in item:
          libid = item["episodeid"]
          show_title = qItem["ShowTitle"]
          show_year = qItem["ShowYear"]
          season = qItem["Season"]
          episode = qItem["Episode"]
          isEpisode = True

        if isMovie and self.movies250 is not None and imdbnumber is not None:
          movie250 = self.movies250.get(imdbnumber, {})
          # No need to query OMDb if all Top250 fields are available and they're all we need
          needomdb = not (movie250 is not {} and self.onlyt250fields and ("rank" in movie250 and "rating" in movie250 and "votes" in movie250))
        else:
          movie250 = {}
          needomdb = True

        if self.omdbquery and needomdb:
          attempt = 0
          newimdb = None
          ismultipartquery = False
          while True:
            if isMovie:
              self.logger.log("Querying OMDb [a=%d, r=%d]: [movie] %s, imdb=%s" % (attempt, self.retry, imdbnumber, title))
              newimdb = MyUtility.getIMDBInfo("movie", self.apikey, imdbnumber=imdbnumber, plotFull=self.plotFull, plotOutline=self.plotOutline, qtimeout=self.timeout) if imdbnumber else None
            elif isTVShow:
              self.logger.log("Querying OMDb [a=%d, r=%d]: [tvshow] %s, %d, imdb=%s" % (attempt, self.retry, title, year, MyUtility.nonestr(imdbnumber)))
              newimdb = MyUtility.getIMDBInfo("tvshow", self.apikey, imdbnumber=imdbnumber, title=title, year=year, plotFull=self.plotFull, plotOutline=self.plotOutline, qtimeout=self.timeout)
            elif isEpisode:
              self.logger.log("Querying OMDb [a=%d, r=%d]: [episode] %s, %d, S%02d, E%02d, imdb=%s" % (attempt, self.retry, show_title, show_year, season, episode, MyUtility.nonestr(imdbnumber)))
              newimdb = MyUtility.getIMDBInfo("episode", self.apikey, imdbnumber=imdbnumber, title=show_title, year=show_year, season=season, episode=episode,
                                              plotFull=(self.plotFull and not ismultipartquery), plotOutline=(self.plotOutline and not ismultipartquery), qtimeout=self.timeout)

            if newimdb is not None:
              newimdb = newimdb if newimdb.get("response", "False") == "True" else None

              # If nothing found and it's a multipart episode that hasn't already been re-queried, then
              # try querying omdbapi again using the first episode of the multipart sequence (ignoring plot details)
              if newimdb is None and multipart_ep is not None and not ismultipartquery:
                ismultipartquery = True
                self.logger.log("Re-querying OMDb [a=%d, r=%d]: [multipart] %s, %d, S%02d, E%02d => S%02d, E%02d" %
                                (attempt, self.retry, show_title, show_year, season, episode, multipart_ep[0], multipart_ep[1]))
                (season, episode) = multipart_ep
                continue
              break
            elif attempt >= self.retry:
              break

            attempt += 1

          if newimdb is None:
            if isMovie:
              logmsg = "Could not obtain OMDb details for [movie] %s (%s)" % (imdbnumber, original_title)
            elif isTVShow:
              logmsg = "Could not obtain OMDb details for [tvshow] %s (%d)" % (original_title, year)
            elif isEpisode:
              logmsg = "Could not obtain OMDb details for [episode] %s S%02dE%02d" % (original_title, season, episode)

            if isEpisode and self.ignore_missing_episodes:
              self.logger.log(logmsg)
            else:
              self.logger.err(logmsg, newLine=True, log=True)

            continue
        else:
          self.logger.log("Avoided OMDb query, movies250 has all we need: %s (%s)" % (imdbnumber, original_title))
          newimdb = {}

        # Add top250 only if we've got a 250 list
        if self.movies250 is not None:
          newimdb["top250"] = movie250.get("rank", 0)
          newimdb["rating"] = movie250.get("rating", newimdb.get("rating",None))
          newimdb["votes"] = movie250.get("votes", newimdb.get("votes", None))

        qItem["newimdb"] = newimdb

        self.output_queue.put(qItem)

      except Queue.Empty:
        self.output_queue.put(None)
        break

#
# Simple thread class to manage Raspberry Pi HDMI power state
#
class MyHDMIManager(threading.Thread):
  def __init__(self, config, logger, cmdqueue, hdmidelay=900, onstopdelay=5):
    threading.Thread.__init__(self)

    self.EV_PLAY_STOP = "play.stop"
    self.EV_HDMI_OFF  = "hdmi.off"

    self.events = {}

    self.config = config
    self.logger = logger
    self.cmdqueue = cmdqueue
    self.ignoreplayer = self.config.HDMI_IGNORE_PLAYER
    self.ignorelibrary = self.config.HDMI_IGNORE_LIBRARY

    self.bin_tvservice = config.BIN_TVSERVICE
    self.bin_vcgencmd = config.BIN_VCGENCMD if config.BIN_VCGENCMD and os.path.exists(config.BIN_VCGENCMD) else None
    self.bin_ceccontrol = config.BIN_CECCONTROL if config.BIN_CECCONTROL and os.path.exists(config.BIN_CECCONTROL) else None

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

    self.logger.debug("HDMI Power off delay: %d seconds (ignored when CanSuspend is yes)" % self.EventInterval(self.EV_HDMI_OFF))
    self.logger.debug("Player OnStop delay : %d seconds (ignored when CanSuspend is yes)" % self.EventInterval(self.EV_PLAY_STOP))
    self.logger.debug("Path to tvservice   : %s" % self.bin_tvservice)
    self.logger.debug("Path to vcgencmd    : %s" % self.bin_vcgencmd)
    self.logger.debug("Path to ceccontrol  : %s" % self.bin_ceccontrol)
    self.logger.debug("Ignore Active Player: %s" % ("Yes" if self.ignoreplayer else "No"))
    self.logger.debug("Ignore Library Scan : %s" % ("Yes" if self.ignorelibrary else "No"))

  def run(self):
    try:
      self.MonitorKodi()
    except:
      pass

  def MonitorKodi(self):
    clientState = {}
    hdmi_on = True

    screensaver_active = False
    player_active = False
    library_active = False

    self.cansuspend = False
    self.candisable = False

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
          self.logger.debug("Connected to Kodi")
          self.logger.debug("HDMI power management thread - initialising Kodi and HDMI state")

          clientState = self.getKodiStatus()
          hdmi_on = self.getHDMIState()

          screensaver_active = clientState["screensaver.active"]
          player_active = clientState["players.active"]
          library_active = (clientState["scanning.music"] or clientState["scanning.video"])

          # If the Pi can self-suspend, don't schedule the EV_HDMI_OFF event or restart Kodi
          # to re-init the HDMI. Instead, just log various events and call ceccontrol
          # whenever sleeping or waking.
          self.cansuspend = clientState["cansuspend"]

          # If firmware supports ability to disable HDMI power, then use "vcgencmd display_power 0|1"
          # to control HDMI rather than tvservice.
          self.candisable = clientState["vcgencmd.display_power"]

          if hdmi_on == False:
            hdmi_status = "off"
          elif self.candisable and not self.getPowerState():
            hdmi_status = "disabled"
            hdmi_on = False
          else:
            hdmi_status = "on"

          self.logger.debug("HDMI is [%s], Screensaver is [%s], Player is [%s], Library scan [%s], CanSuspend [%s], CanDisable [%s]" %
                            (hdmi_status,
                             ("active" if screensaver_active else "inactive"),
                             ("active" if player_active else "inactive"),
                             ("active" if library_active else "inactive"),
                             ("yes" if self.cansuspend else "no"),
                             ("yes" if self.candisable else "no")
                             ))

          if not self.cansuspend:
            if screensaver_active and hdmi_on:
              self.EventSet(self.EV_HDMI_OFF)

        elif method == "GUI.OnScreensaverActivated":
          self.logger.debug("Screensaver has activated")
          screensaver_active = True
          if not self.cansuspend:
            self.EventSet(self.EV_HDMI_OFF)

        elif method == "GUI.OnScreensaverDeactivated":
          self.logger.debug("Screensaver has deactivated")
          screensaver_active = False
          if not self.cansuspend:
            if self.EventEnabled(self.EV_HDMI_OFF):
              self.EventStop(self.EV_HDMI_OFF)
              self.logger.debug("Scheduled HDMI power-off cancelled")
            else:
              hdmi_on = self.enable_hdmi()
              if not self.candisable:
                self.sendKodiExit()

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

        elif method == "System.OnSleep" and self.cansuspend:
          self.logger.debug("Client is now suspended")
          # HDMI already disabled, but may need to process CEC functionality
          self.callCECControl("off")

        elif method == "System.OnWake" and self.cansuspend:
          self.logger.debug("Client has resumed")
          # HDMI already enabled, but may need to process CEC functionality
          self.callCECControl("on")

        elif method == "System.OnQuit":
          self.EventsStopAll()
          if not hdmi_on:
            hdmi_on = self.enable_hdmi()

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
              if (player_active and not self.ignoreplayer) or (library_active and not self.ignorelibrary):
                self.logger.debug("HDMI power-off will not occur until both player and library become inactive")

          # Process any expired events
          if self.EventExpired(event, now):
            if event == self.EV_PLAY_STOP:
              self.logger.debug("Player has stopped")
              player_active = False
              self.EventStop(event)
            elif event == self.EV_HDMI_OFF:
              if (player_active and not self.ignoreplayer) or (library_active and not self.ignorelibrary):
                if not self.EventOverdue(event, now):
                  self.logger.debug("HDMI power-off timeout reached - waiting for player and/or library to become inactive")
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

  def sendKodiExit(self):
    self.logger.debug("Sending Application.Quit() to Kodi")
    REQUEST = {"method": "Application.Quit"}
    MyJSONComms(self.config, self.logger).sendJSON(REQUEST, "libExit", checkResult=False)

  def getKodiStatus(self):
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

    REQUEST = {"method": "System.GetProperties",
               "params": {"properties": ["canshutdown", "cansuspend", "canreboot", "canhibernate"]}}
    data = jcomms.sendJSON(REQUEST, "libProperties", checkResult=False)
    values = data.get("result", {})
    for s in REQUEST["params"]["properties"]:
      statuses[s] = values.get(s, False)

    statuses["cansuspend"] = (statuses["cansuspend"] and not self.config.HDMI_IGNORE_SUSPEND)

    svalue = False
    if self.bin_vcgencmd:
      try:
        response = subprocess.check_output([self.bin_vcgencmd, "commands"], stderr=subprocess.STDOUT).decode("utf-8")
        response = response[:-1] if response.endswith("\n") else response
        if response.find("display_power") != -1:
          svalue = True
      except:
        pass
    statuses["vcgencmd.display_power"] = (svalue and not self.config.HDMI_IGNORE_DISABLE)

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
    if self.config.HDMI_FORCE_HOTPLUG:
      self.logger.debug("No hotplug support - assuming display is powered on")
      return True

    option = "--status"
    self.logger.log("bin.tvservice (checking if TV is powered on) calling subprocess [%s %s]" % (self.bin_tvservice, option))
    response = subprocess.check_output([self.bin_tvservice, option], stderr=subprocess.STDOUT).decode("utf-8")
    response = response[:-1] if response.endswith("\n") else response
    self.logger.log("bin.tvservice response: [%s]" % response)

    state = re.search("state (0x[0-9a-f]*) .*", response)
    if state:
      vc_hdmi = int(state.group(1)[-1:], 16)
      tv_on = (vc_hdmi & (1 << 1) != 0)
    else:
      tv_on = True
    return tv_on

  # HDMI Power: True = ON, False = OFF
  def getHDMIState(self):
    option = "--status"
    self.logger.log("bin.tvservice (checking HDMI status) calling subprocess [%s %s]" % (self.bin_tvservice, option))
    response = subprocess.check_output([self.bin_tvservice, option], stderr=subprocess.STDOUT).decode("utf-8")
    response = response[:-1] if response.endswith("\n") else response
    self.logger.log("bin.tvservice response: [%s]" % response)
    return response.find("TV is off") == -1

  def setHDMIState(self, state):
    option = "--preferred" if state else "--off"
    self.logger.log("bin.tvservice (enabling/disabling HDMI) calling subprocess [%s %s]" % (self.bin_tvservice, option))
    response = subprocess.check_output([self.bin_tvservice, option], stderr=subprocess.STDOUT).decode("utf-8")
    response = response[:-1] if response.endswith("\n") else response
    self.logger.log("bin.tvservice response: [%s]" % response)
    return self.getHDMIState()

  def getPowerState(self):
    self.logger.log("bin.vcgencmd (checking HDMI power status) calling subprocess [%s %s]" % (self.bin_vcgencmd, "display_power"))
    response = subprocess.check_output([self.bin_vcgencmd, "display_power"], stderr=subprocess.STDOUT).decode("utf-8")
    response = response[:-1] if response.endswith("\n") else response
    self.logger.log("bin.vcgencmd response: [%s]" % response)
    return response.endswith("=1")

  def setPowerState(self, enabled):
    option = "1" if enabled else "0"
    self.logger.log("bin.vcgencmd (enabling/disabling HDMI power) calling subprocess [%s %s %s]" % (self.bin_vcgencmd, "display_power", option))
    response = subprocess.check_output([self.bin_vcgencmd, "display_power", option], stderr=subprocess.STDOUT).decode("utf-8")
    response = response[:-1] if response.endswith("\n") else response
    self.logger.log("bin.vcgencmd response: [%s]" % response)
    return response.endswith("=1")

  def callCECControl(self, option):
    if self.bin_ceccontrol:
      self.logger.debug("Executing CEC Control script [%s]" % option)
      self.logger.log("bin.ceccontrol calling subprocess [%s %s]" % (self.bin_ceccontrol, option))
      response = subprocess.check_output([self.bin_ceccontrol, option], stderr=subprocess.STDOUT).decode("utf-8")
      response = response[:-1] if response.endswith("\n") else response
      self.logger.log("bin.ceccontrol response: [%s]" % response)

  def disable_hdmi(self):
    if not self.getDisplayStatus():
      self.logger.debug("Display device is not turned on, no need to disable HDMI")
      return True

    if self.candisable:
      ison = self.setPowerState(False)
    else:
      ison = self.setHDMIState(False)

    if not ison:
      self.logger.debug("HDMI is now off")
      self.callCECControl("off")
    else:
      self.logger.debug("HDMI failed to power off")

    return ison

  def enable_hdmi(self):
    if self.candisable:
      ison = self.setPowerState(True)
    else:
      ison = self.setHDMIState(True)

    if ison:
      self.logger.debug("HDMI is now on")
      self.callCECControl("on")
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

    #mydb will be either a SQL DB or MyJSONComms object
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

  def _getAllColumns(self, filter, order):
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
    # any corresponding DDS file should also be removed
    if self.usejson and id > 0:
        self.delRowByID(id)
        return

    if cachedURL is not None and id > 0:
      row = self.getSingleRow("WHERE id = %d" % id)
      if row is None:
        self.logger.out("id %s is not valid\n" % (self.config.IDFORMAT % int(id)))
        return
      else:
        localFile = row["cachedurl"]
    else:
      localFile = cachedURL

    if localFile is not None and os.path.exists(self.config.getFilePath(localFile)):
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

  # Didn't find anything so try again, this time leave filename quoted, and don't truncate
    if not row:
      self.logger.log("Failed to find row by filename with the expected formatting, trying again (with prefix, quoted)")
      row = self.getRowByFilename_Impl(filename, unquote=False)

    return row

  def getRowByFilename_Impl(self, filename, unquote=True):
    if unquote:
      ufilename = MyUtility.normalise(filename)
    else:
      ufilename = filename

    # If string contains Unicode, replace Unicode chars with % and
    # use LIKE instead of equality
    if ufilename.encode("ascii", "ignore") == ufilename.encode("utf-8"):
      SQL = "WHERE url = \"%s\"" % ufilename
    else:
      self.logger.log("Removing ASCII from filename: [%s]" % ufilename)
      SQL = "WHERE url LIKE \"%s\"" % removeNonAscii(ufilename, "%")

    rows = self.getRows(filter=SQL, allfields=True)

    return rows[0] if rows != [] else None

  def removeNonAscii(self, s, replaceWith=""):
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

  def getTextureFolders(self):
    # One extra folder (!) which is used to try and identify non-standard folders
    return ["0","1","2","3","4","5","6","7","8","9","a","b","c","d","e","f","!"]

  def getTextureFolderFilter(self, folder):
    if folder == "!":
      # Everything other than the regular folders
      return "WHERE (cachedurl < '0' or cachedurl > ':') and (cachedurl < 'a' or cachedurl > 'g')"
    else:
      return "WHERE cachedurl LIKE '%s/%%'" % folder

# Raise this exception when we run out of replay log input
class IOEndOfReplayLog(Exception):
  def __init__(self, value):
    self.value = value
  def __str__(self):
    return repr(self.value)

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
    self.WEB_LAST_REASON = ""
    self.config.WEB_SINGLESHOT = True
    self.aUpdateCount = self.vUpdateCount = 0
    self.jcomms2 = None

    self.BUFFER_SIZE = 32768

    self.QUIT_METHOD = self.QUIT_PARAMS = None

    self.LOG_REPLAYFILE = None

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
    lastexception = None
    if not self.mysocket:
      useipv = int(self.config.RPC_IPVERSION) if self.config.RPC_IPVERSION else None
      for ipversion in [socket.AF_INET6, socket.AF_INET]:
        if useipv and useipv == 4 and ipversion != socket.AF_INET: continue
        if useipv and useipv == 6 and ipversion != socket.AF_INET6: continue
        try:
          self.mysocket = socket.socket(ipversion, socket.SOCK_STREAM)
          self.mysocket.settimeout(self.connecttimeout)
          self.mysocket.connect((self.config.KODI_HOST, int(self.config.RPC_PORT)))
          self.mysocket.settimeout(None)
          self.logger.log("RPC connection established with IPv%s" % ("4" if ipversion == socket.AF_INET else "6"))
          self.config.RPC_IPVERSION = "4" if ipversion == socket.AF_INET else "6"
          return self.mysocket
        except Exception as e:
          lastexception = e
          pass
      else:
        raise lastexception if lastexception is not None else socket.error("Unknown socket error")
    return self.mysocket

  # Use a secondary socket object for simple lookups to avoid having to handle
  # re-entrant code due to notifications being received out of sequence etc.
  # Could instantiate an object whenever required, but keeping a reference here
  # should improve efficiency slightly.
  def getLookupObject(self):
    if not self.jcomms2:
      self.jcomms2 = MyJSONComms(self.config, self.logger)
    return self.jcomms2

  def getWeb(self):
    if not self.myweb or self.config.WEB_SINGLESHOT:
      if self.myweb: self.myweb.close()
      self.myweb = httplib.HTTPConnection("%s:%s" % (self.config.KODI_HOST, self.config.WEB_PORT), timeout=self.connecttimeout)
      self.WEB_LAST_STATUS = -1
      self.WEB_LAST_REASON = ""
      if self.config.DEBUG: self.myweb.set_debuglevel(1)
    return self.myweb

  def logreplay_open(self):
    try:
      thread = threading.current_thread().name
      if thread not in self.config.log_replay_fmap:
        self.LOG_REPLAYFILE = codecs.open(self.config.LOG_REPLAY_FILENAME, "r", encoding="utf-8")
        self.config.log_replay_fmap[thread] = self.LOG_REPLAYFILE
      else:
        self.LOG_REPLAYFILE = self.config.log_replay_fmap[thread]
      self.logreplay_mapthread(None)
    except:
      self.logger.err("ERROR: Unable to open replay file [%s] - exiting" % self.config.LOG_REPLAY_FILENAME, newLine=True, log=True)
      sys.exit(2)

  # When replaying muti-threaded input, map each new thread of input data to the
  # currently available threads. Once a thread is allocated a thread from the data,
  # it will only process data for that thread.
  def logreplay_mapthread(self, map_to_thread=None):
    thread = threading.current_thread().name

    if map_to_thread is None: # process data for all threads
      tpattern = thread if thread == "MainThread" else "Thread-[0-9]*"
    else: # process data for a specific thread
      tpattern = map_to_thread
      self.config.log_replay_tmap[map_to_thread] = thread

    self.web_re_result = re.compile("^.*:(%s)[ ]*: .*\.RECEIVED WEB DATA: ([0-9]*), (.*), (.*)$" % tpattern)
    self.json_re_result = re.compile("^.*:(%s)[ ]*: .*\.PARSING JSON DATA: (.*)$" % tpattern)

  # If the thread data being processed is mapped to a thread other than the current
  # thread then ignore this thread data
  def logreplay_ignore_thread(self, map_to_thread):
    with lock:
      thread = threading.current_thread().name

      if map_to_thread in self.config.log_replay_tmap:
         return self.config.log_replay_tmap[map_to_thread] != thread

      self.logreplay_mapthread(map_to_thread)
      return False

  # Read responses from log, use in place of actual socket/web responses (requests are never made)
  def logreplay(self, request, useWebServer):
    if not self.LOG_REPLAYFILE:
      self.logreplay_open()

    while True:
      line = self.LOG_REPLAYFILE.readline()
      if not line: break

      # Remove trailing newline and - if present, ie. Windows/DOS file format - carriage return
      if len(line) != 0 and line[-1] in ["\n", "\r"]: line = line[0:-1]
      if len(line) != 0 and line[-1] in ["\n", "\r"]: line = line[0:-1]

      if useWebServer:
        match = self.web_re_result.match(line)
        if match and not self.logreplay_ignore_thread(match.group(1)):
          self.WEB_LAST_STATUS = int(match.group(2))
          self.WEB_LAST_REASON = match.group(3)
          return match.group(4).encode("utf-8")
      else:
        match = self.json_re_result.match(line)
        if match and not self.logreplay_ignore_thread(match.group(1)):
          return match.group(2).encode("utf-8")

    self.LOG_REPLAYFILE.close()
    raise IOEndOfReplayLog("End of replay log data")

  def sendWeb(self, request_type, url, id, request=None, headers={}, readAmount=0, timeout=15.0, rawData=False, domain=None, useSSL=False):
    if request is not None:
      sdata = json.dumps(request)
      self.logger.log("%s.JSON WEB REQUEST: [%s] [%s]" % (id, request_type, sdata))
    else:
      sdata = None
      if domain is not None:
        self.logger.log("%s.DIRECT WEB REQUEST: [%s], HTTPS=%s, [%s] [%s]" % (id, request_type, useSSL, domain, url))
      else:
        self.logger.log("%s.DIRECT WEB REQUEST: [%s], [%s]" % (id, request_type, url))

    if self.config.LOG_REPLAY_FILENAME:
      data = self.logreplay(url, True)
      data = "" if sdata and data == "<raw data>" else data
      if MyUtility.isPython3 and not rawData:
        data = data.decode("utf-8")
    else:
      if domain:
        if useSSL:
          web = httplib.HTTPSConnection(domain)
        else:
          web = httplib.HTTPConnection(domain)
      else:
        if self.config.WEB_AUTH_TOKEN:
          headers.update({"Authorization": "Basic %s" % self.config.WEB_AUTH_TOKEN})
        web = self.getWeb()

      web.request(request_type, url, sdata, headers)

      if timeout is None: web.sock.setblocking(1)
      else: web.sock.settimeout(timeout)

      data = ""

      try:
        response = web.getresponse()
        self.WEB_LAST_STATUS = response.status
        self.WEB_LAST_REASON = response.reason

        if self.WEB_LAST_STATUS == httplib.UNAUTHORIZED:
          raise httplib.HTTPException("Remote web host requires webserver.username/webserver.password properties")

        if MyUtility.isPython3 and not rawData:
          if readAmount == 0:
            data = response.read().decode("utf-8")
          else:
            data = response.read(readAmount).decode("utf-8")
        else:
          if readAmount == 0:
            data = response.read()
          else:
            data = response.read(readAmount)
      except socket.timeout:
        self.logger.log("** iotimeout occurred during web request **")
        self.WEB_LAST_STATUS = httplib.REQUEST_TIMEOUT
        self.WEB_LAST_REASON = "Request Timeout"
        self.myweb.close()
        self.myweb = None
        data = ""
      except:
        if domain:
          self.logger.log("%s.RECEIVED WEB DATA: %d, %s, <exception>" % (id, response.status, response.reason), maxLen=256)
          raise
        if self.config.WEB_SINGLESHOT == False:
          self.logger.log("SWITCHING TO WEBSERVER.SINGLESHOT MODE")
          self.config.WEB_SINGLESHOT = True
          data = self.sendWeb(request_type, url, id, request, headers, readAmount, timeout, rawData)
        else:
          raise
      finally:
        if domain and web:
          web.close()

    if self.logger.LOGGING:
      if rawData:
        self.logger.log("%s.RECEIVED WEB DATA: %d, %s, <raw data>" % (id, self.WEB_LAST_STATUS, self.WEB_LAST_REASON), maxLen=256)
      else:
        self.logger.log("%s.RECEIVED WEB DATA: %d, %s, %s" % (id, self.WEB_LAST_STATUS, self.WEB_LAST_REASON, data), maxLen=256)

    if sdata:
      return json.loads(data) if data != "" else ""
    else:
      return data

  def sendJSON(self, request, id, callback=None, timeout=5.0, checkResult=True, useWebServer=False, ignoreSocketError=False):
    request["jsonrpc"] = "2.0"
    request["id"] =  id

    # Suppress complaints about Sets having no results (due to Sets not having been defined)
    if request["method"] == "VideoLibrary.GetMovieSets": checkResult=False

    # Following methods don't work over sockets - by design.
    if request["method"] in ["Files.PrepareDownload", "Files.Download"] or useWebServer:
      return self.sendWeb("POST", "/jsonrpc", id, request, {"Content-Type": "application/json"}, timeout=timeout)

    self.logger.log("%s.JSON SOCKET REQUEST:" % id, jsonrequest=request)
    START_IO_TIME = time.time()

    if self.config.LOG_REPLAY_FILENAME:
      jsocket = None
    else:
      jsocket = self.getSocket()
      if MyUtility.isPython3:
        jsocket.send(bytes(json.dumps(request), "utf-8"))
      else:
        jsocket.send(json.dumps(request))

    ENDOFDATA = True
    LASTIO = 0
    jdata = {}
    cbjdata = None

    while True:
      if ENDOFDATA:
        ENDOFDATA = False
        data = b""
        if jsocket: jsocket.setblocking(1)

      try:
        if jsocket:
          newdata = jsocket.recv(self.BUFFER_SIZE)
          if len(data) == 0: jsocket.settimeout(1.0)
        else:
          newdata = self.logreplay(request, useWebServer)

        data += newdata
        LASTIO = time.time()
        self.logger.log("%s.BUFFER RECEIVED (len %d)" % (id, len(newdata)))
        if len(newdata) == 0: raise IOError("nodata")
        READ_ERR = False

      except (IOError, IOEndOfReplayLog) as e:
        # Hack to exit monitor mode when socket dies
        if callback:
          jdata = {"jsonrpc":"2.0","method":"System.OnQuit","params":{"data":-1,"sender":"xbmc"}}
          self.handleResponse(id, jdata, callback)
          return jdata
        elif ignoreSocketError == False:
          self.logger.err("ERROR: Socket closed prematurely - exiting", newLine=True, log=True)
          sys.exit(2)
        else:
          return {}

      except socket.error as e:
        READ_ERR = True

      # Keep reading unless accumulated data is a likely candidate for successful parsing...
      if not READ_ERR and len(data) != 0 and (data[-1:] == b"}" or data[-2:] == b"}\n"):

        # If data is not a str (Python2) then decode Python3 bytes to Unicode representation
        if isinstance(data, str):
          udata = MyUtility.toUnicode(data)
        else:
          try:
            udata = data.decode("utf-8")
          except UnicodeDecodeError as e:
            udata = data

        try:
          START_PARSE_TIME = time.time()

          # Parse messages, to ensure the entire buffer is valid
          # If buffer is not valid (VlueError exception), we may need to read more data.
          messages = []
          for m in self.parseResponse(udata):
            if self.logger.LOGGING and messages == []:
              if udata.find("\n") != -1:
                self.logger.log2("%s.PARSING JSON DATA: " % id, udata.replace("\t", "").replace("\n", ""), maxLen=256)
              else:
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

          # "result" on response for an Application.SetMute()/SetVolume() is
          # not iterable so just ignore it if we cause an exception...
          try:
            if ("result" in jdata and "limits" in jdata["result"]):
              self.logger.log("%s.RECEIVED LIMITS: %s" % (id, jdata["result"]["limits"]))
          except TypeError:
            pass

          # Flag to reset buffers next time we read the socket.
          ENDOFDATA = True

          # callback result for a commingled Notification - stop blocking/reading and
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
              #Save this jdata as it's our original response
              if cbjdata is None: cbjdata = jdata
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

    if cbjdata is not None: jdata = cbjdata
    if checkResult and not "result" in jdata:
      self.logger.out("%s.ERROR: JSON response has no result!\n%s\n" % (id, jdata))

    self.logger.log("%s.FINISHED, elapsed time: %f seconds" % (id, time.time() - START_IO_TIME))
    return jdata

  # Split data into individual JSON objects.
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
    if "error" in jdata:
      return True

    id = jdata["id"] if "id" in jdata else None
    method = jdata["method"] if "method" in jdata else jdata.get("result", None)
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
          self.logger.out("Updating library: New %-9s %5d [%s]\n" % (iType + "id", libraryId, title))
        else:
          self.logger.out("Updating library: New %-9s %5d\n" % (iType + "id", libraryId))

    return True if method.endswith("Library.OnScanFinished") else False

  def jsonWaitForCleanFinished(self, id, method, params):
    if method.endswith("Library.OnRemove") and "data" in params:
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
          self.logger.out("Cleaning library: %-9s %5d [%s]\n" % (iType + "id", libraryId, title))
        else:
          self.logger.out("Cleaning library: %-9s %5d\n" % (iType + "id", libraryId))

    return True if method.endswith("Library.OnCleanFinished") else False

  def addProperties(self, request, fields):
    if not "properties" in request["params"]: return
    aList = request["params"]["properties"]
    if fields is not None:
      for f in [f.strip() for f in fields.split(",")]:
        if f != "" and f not in aList:
          aList.append(f)
    request["params"]["properties"] = aList

  def delProperties(self, request, fields):
    if not "properties" in request["params"]: return
    aList = request["params"]["properties"]
    if fields is not None:
      for f in [f.strip() for f in fields.split(",")]:
        if f != "" and f in aList:
          aList.remove(f)
    request["params"]["properties"] = aList

  def addFilter(self, request, newFilter, condition="and"):
    filter = request["params"]
    if "filter" in filter:
       filter["filter"] = {condition: [filter["filter"], newFilter]}
    else:
       filter["filter"] = newFilter
    request["params"] = filter

  def rescanDirectories(self, workItems):
    if workItems == {}: return

    doRefresh = (gConfig.JSON_HAS_REFRESH_REFACTOR and not gConfig.QA_USEOLDREFRESHMETHOD)
    method = "Refresh" if doRefresh else "Remove"

    # Seems to be a bug in rescan method when scanning the root folder of a source
    # So if any items are in the root folder, just scan the entire library after
    # items have been removed.
    rootScan = False
    sources = self.getSources("video")

    for directory in sorted(workItems):
      (mediatype, dpath) = directory.split(";", 1)
      if dpath in sources: rootScan = True

    for directory in sorted(workItems):
      (mediatype, dpath) = directory.split(";", 1)

      for disc_folder in [".BDMV$", ".VIDEO_TS$"]:
        re_match = re.search(disc_folder, dpath, flags=re.IGNORECASE)
        if re_match:
          dpath = dpath[:re_match.start()]
          break

      if mediatype == "movies":
        scanMethod = "VideoLibrary.Scan"
        removeMethod = "VideoLibrary.%sMovie" % method
        idName = "movieid"
      elif mediatype == "tvshows":
        scanMethod = "VideoLibrary.Scan"
        removeMethod = "VideoLibrary.%sTVShow" % method
        idName = "tvshowid"
      elif mediatype == "episodes":
        scanMethod = "VideoLibrary.Scan"
        removeMethod = "VideoLibrary.%sEpisode" % method
        idName = "episodeid"
      else:
        raise ValueError("mediatype [%s] not yet implemented" % mediatype)

      for libraryitem in workItems[directory]:
        libraryid = libraryitem["id"]
        if doRefresh:
          self.logger.log("Refreshing %s %d in media library." % (idName, libraryid))
        else:
          self.logger.log("Removing %s %d from media library." % (idName, libraryid))
        REQUEST = {"method": removeMethod, "params":{idName: libraryid}}
        if doRefresh:
          REQUEST["params"]["ignorenfo"] = False
          if mediatype == "tvshows":
            REQUEST["params"]["refreshepisodes"] = False
        self.sendJSON(REQUEST, "lib%s" % method)
        if doRefresh:
          gLogger.out("Updating library: Refreshed %s %d [%s]" % (idName, libraryid, libraryitem["name"]), newLine=True)

      if not doRefresh and not rootScan: self.scanDirectory(scanMethod, path=dpath)

    if not doRefresh and rootScan: self.scanDirectory(scanMethod)

  def scanDirectory(self, scanMethod, path=None):
    if path and path != "":
      self.logger.out("Rescanning directory: %s..." % path, newLine=True, log=True)
      REQUEST = {"method": scanMethod, "params":{"directory": path}}
    else:
      self.logger.out("Rescanning library...", newLine=True, log=True)
      REQUEST = {"method": scanMethod}

    if self.config.JSON_HAS_LIB_SHOWDIALOGS_PARAM:
      if "params" not in REQUEST: REQUEST["params"] = {}
      REQUEST["params"].update({"showdialogs": self.config.SCAN_SHOW_DIALOGS})

    self.sendJSON(REQUEST, "libRescan", callback=self.jsonWaitForScanFinished, checkResult=False)

  def cleanLibrary(self, cleanMethod):
    self.logger.out("Cleaning library...", newLine=True, log=True)
    REQUEST = {"method": cleanMethod}

    if self.config.JSON_HAS_LIB_SHOWDIALOGS_PARAM:
      REQUEST["params"] = {"showdialogs": self.config.CLEAN_SHOW_DIALOGS}

    self.sendJSON(REQUEST, "libClean", callback=self.jsonWaitForCleanFinished, checkResult=False)

  def getDirectoryList(self, path, mediatype="files", properties=["file","lastmodified"], use_cache=True, timestamp=False, honour_nomedia=False):
    data = MyUtility.getDirectoryCacheItem(properties, path)

    if not data:
      REQUEST = {"method":"Files.GetDirectory",
                 "params": {"directory": path,
                            "media": mediatype,
                            "properties": properties}}

      data = self.sendJSON(REQUEST, "libDirectory", checkResult=False)

      # Fix null being returned for "files" on some systems...
      if "result" in data and "files" in data["result"]:
        if data["result"]["files"] is None:
          data["result"]["files"] = []

        for f in data["result"]["files"]:
          if "file" in f:
            # Real directories won't have extensions, but .m3u and .pls playlists will
            # leading to infinite recursion, so fix the filetype so as not to try and
            # traverse playlists.
            if f["filetype"] == "directory":
              extension = os.path.splitext(f["file"])[1]
              if extension and extension.find("/") != -1 and extension.find("\\") != -1:
                f["filetype"] = "file"

            # Convert last modified date/time to epoch
            if timestamp: self.setTimeStamp(f)

      if use_cache:
        MyUtility.setDirectoryCacheItem(data, properties, path)

    if honour_nomedia and data and "result" in data and "files" in data["result"]:
      for f in data["result"]["files"]:
        if f["label"] == ".nomedia" or f["label"] == ".nomedia.":
          data["result"]["files"] = []
          break

    return data

  def setTimeStamp(self, item):
    if "lastmodified" in item:
      try:
        item["lastmodified_timestamp"] = MyUtility.SinceEpoch(datetime.datetime.strptime(item["lastmodified"], self.config.qa_lastmodified_fmt))
      except ValueError:
        self.logger.err("ERROR: Invalid \"lastmodified\" date detected - try specifying @modifieddate.mdy=%s" %
                        ("no" if self.config.MDATE_MDY else "yes"), newLine=True)
        sys.exit(2)

  def getExtraArt(self, item):
    if not (item and self.config.CACHE_EXTRA): return []

    # Movies, Tags and TV shows have a file property which can be used as the media root.
    # Artists and Albums do not, so try and find a usable local path from the
    # fanart/thumbnail artwork.
    directory = None
    if "file" in item:
      directory = MyUtility.unstackFiles(item["file"])[0]
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
               "params":{"path": filename}}

    data = self.sendJSON(REQUEST, "preparedl")

    if "result" in data:
      return "/%s" % data["result"]["details"]["path"]
    else:
      return None

  # Get file details from a directory lookup, this prevents errors on Kodi when
  # the file doesn't exist (unless the directory doesn't exist), and also allows the
  # query results to be cached for use by subsequent file requests in the same directory.
  def getFileDetails(self, filename, properties=["file", "lastmodified", "size"]):
    data = self.getDirectoryList(os.path.dirname(filename), mediatype="files", properties=properties)

    if "result" in data:
      files = data["result"].get("files", [])
      for file in [x for x in files if x["filetype"] == "file" and x.get("file", None) == filename]:
        if "lastmodified" in properties: self.setTimeStamp(file)
        return file

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
               "params":{"musicvideoid": videoid, "properties":["title"]}}
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
        elif field in ["file", "fanart", "thumbnail"]:
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

  def getAllFilesForSource(self, mediatype, labels, ignore_list=None, honour_nomedia=False):
    if mediatype == "songs":
      mtype = "music"
      includeList = self.config.audio_filetypes
    elif mediatype == "pictures":
      mtype = "pictures"
      includeList = self.config.picture_filetypes
    else:
      mtype = "video"
      includeList = self.config.video_filetypes

    if self.config.IGNORE_PLAYLISTS:
      for ignoreExt in [".m3u", ".pls", ".cue"]:
        if ignoreExt in includeList:
          includeList.remove(ignoreExt)

    fileList = []

    for label in labels:
      sources = self.getSources(mtype, withLabel=label)

      for path in sources:
        self.logger.progress("Walking source: %s" % path)

        for file in self.getFiles(path, honour_nomedia):
          ext = os.path.splitext(file)[1].lower()
          if ext not in includeList: continue

          if os.path.splitext(file)[0].lower().endswith("trailer"): continue

          isVIDEOTS = (file.find("/VIDEO_TS/") != -1 or file.find("\\VIDEO_TS\\") != -1)
          isBDMV    = (file.find("/BDMV/") != -1 or file.find("\\BDMV\\") != -1)

          if isVIDEOTS and ext != ".vob": continue
          if isBDMV    and ext != ".m2ts": continue

          if ignore_list is not None:
            ignore_matched = False
            for ignore in ignore_list:
              if ignore.search(os.path.basename(file)):
                ignore_matched = True
                break
            if ignore_matched: continue

          # Avoid adding file to list more than once, which is possible
          # if a folder appears within multiple different sources, or the
          # same source is processed more than once...
          if not file in fileList:
            fileList.append(file)

    if fileList == []:
      self.logger.out("WARNING: no files obtained from filesystem - ensure valid source(s) specified!", newLine=True)

    fileList.sort()

    return fileList

  def getFiles(self, path, honour_nomedia=False):
    fileList = []
    self.getFilesForPath(fileList, path, honour_nomedia)
    return fileList

  def getFilesForPath(self, fileList, path, honour_nomedia=False):
    data = self.getDirectoryList(path, use_cache=False, honour_nomedia=honour_nomedia)
    if not "result" in data: return
    if not "files" in data["result"]: return

    for file in data["result"]["files"]:
      if "file" in file:
        if file["filetype"] == "directory":
          self.getFilesForPath(fileList, os.path.dirname(file["file"]), honour_nomedia)
        else:
          fileList.append(file["file"])

  def setPower(self, state):
    if state == "exit":
      REQUEST = {"method": "Application.Quit"}
    else:
      REQUEST = {"method": "System.%s" % state.capitalize()}
    data = self.sendJSON(REQUEST, "libPower")

  def getData(self, action, mediatype,
              filter = None, useExtraFields = False, secondaryFields = None,
              tvshow = None, tvseason = None, channelgroupid = None, lastRun = False, subType = None, uniquecast = None):

    EXTRA = mediatype
    SECTION = mediatype
    FILTER = "title"
    TITLE = "title"
    IDENTIFIER = "%sid" % re.sub("(.*)s$", "\\1", mediatype)

    if mediatype == "addons":
      REQUEST = {"method":"Addons.GetAddons",
                 "params":{"properties":["name", "version", "thumbnail", "fanart", "path"]}}
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
                           "properties":["title", "track", "artist", "album", "fanart", "thumbnail"]}}
    elif mediatype == "song-members":
      REQUEST = {"method":"AudioLibrary.GetSongs",
                 "params":{"sort": {"order": "ascending", "method": "track"},
                           "properties":["title", "track", "album", "fanart", "thumbnail", "file"]}}
      EXTRA = "songs"
      SECTION = "songs"
      IDENTIFIER = "songid"
    elif mediatype == "musicvideos":
      REQUEST = {"method":"VideoLibrary.GetMusicVideos",
                 "params":{"sort": {"order": "ascending", "method": "title"},
                           "properties":["title", "art", "tag"]}}
      EXTRA = "musicvideos"
      SECTION = "musicvideos"
      IDENTIFIER = "musicvideoid"
    elif mediatype in ["movies", "tags"]:
      REQUEST = {"method":"VideoLibrary.GetMovies",
                 "params":{"sort": {"order": "ascending", "method": "title"},
                           "properties":["title", "art"]}}
      if mediatype == "tags":
        REQUEST["params"]["properties"].append("tag")
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
                           "tvshowid": tvshow["tvshowid"], "properties":["season", "art"]}}
      FILTER = ""
      TITLE = "label"
      EXTRA = "tvshows.season"
      IDENTIFIER = "season"
    elif mediatype == "episodes":
      REQUEST = {"method":"VideoLibrary.GetEpisodes",
                 "params":{"sort": {"order": "ascending", "method": "label"},
                           "tvshowid": tvshow["tvshowid"], "season": tvseason["season"], "properties":["art"]}}
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
    elif mediatype in ["sets-members", "song-members"]:
        _f = "set" if mediatype == "sets-members" else "album"
        if filter and not self.config.FILTER_FIELD:
          self.addFilter(REQUEST, {"field": _f, "operator": self.config.FILTER_OPERATOR, "value": filter})
        else:
          # JSON filter is broken when handling empty (null) strings - they're ignored - though
          # hopefully this will be fixed in a later version of API, in which case use it
          if self.config.JSON_HAS_FILTERNULLVALUE:
            self.addFilter(REQUEST, {"field": _f, "operator": "isnot", "value": ""})
          else:
            self.addFilter(REQUEST, {"field": _f, "operator": "doesnotcontain", "value": "@@@@@@@@@@@@"})

    elif filter and filter.strip() != "" and not mediatype in ["addons", "agenres", "vgenres",
                                                               "sets", "seasons", "episodes",
                                                               "pvr.tv", "pvr.radio", "pvr.channels"]:
        FILTER = self.config.FILTER_FIELD if self.config.FILTER_FIELD else FILTER
        self.addFilter(REQUEST, {"field": FILTER, "operator": self.config.FILTER_OPERATOR, "value": filter})

    if mediatype in ["movies", "tags", "episodes"]:
      if lastRun and self.config.LASTRUNFILE_DATETIME:
        self.addFilter(REQUEST, {"field": "dateadded", "operator": "after", "value": self.config.LASTRUNFILE_DATETIME})

    # Add extra required fields/properties based on action to be performed

    if action == "duplicates":
      if "art" in REQUEST["params"]["properties"]:
        REQUEST["params"]["properties"].remove("art")
      self.addProperties(REQUEST, "file")
      self.addProperties(REQUEST, "imdbnumber")
      self.addProperties(REQUEST, "playcount")
      self.addProperties(REQUEST, "lastplayed")
      self.addProperties(REQUEST, "dateadded")

    elif action == "imdb":
      if self.config.IMDB_PERIOD_FROM and mediatype in ["movies", "episodes"]:
          self.addFilter(REQUEST, {"field": "dateadded", "operator": "after", "value": self.config.IMDB_PERIOD_FROM})

      if mediatype == "movies":
        self.addProperties(REQUEST, "imdbnumber")
        self.addProperties(REQUEST, ",".join(self.config.IMDB_FIELDS_MOVIES))
      elif mediatype in ["tvshows", "episodes"]:
        if mediatype == "tvshows":
          self.addProperties(REQUEST, "year")
        elif mediatype == "episodes":
          self.delProperties(REQUEST, "genre")
        self.addProperties(REQUEST, "file")
        self.addProperties(REQUEST, ",".join(self.config.IMDB_FIELDS_TVSHOWS))

    elif action == "missing":
      for unwanted in ["artist", "art", "fanart", "thumbnail"]:
        if unwanted in REQUEST["params"]["properties"]:
          REQUEST["params"]["properties"].remove(unwanted)
      if mediatype in ["songs", "movies", "tvshows", "episodes"]:
        self.addProperties(REQUEST, "file")

    elif action == "watched" and mediatype in ["movies", "episodes"]:
        if "art" in REQUEST["params"]["properties"]:
          REQUEST["params"]["properties"].remove("art")
        if mediatype == "movies":
          self.addProperties(REQUEST, "year")
        self.addProperties(REQUEST, "playcount, lastplayed, resume")

    elif action == "qa":
      if self.config.QADATE and mediatype in ["movies", "tags", "episodes"]:
          self.addFilter(REQUEST, {"field": "dateadded", "operator": "after", "value": self.config.QADATE})

      if mediatype in ["songs", "movies", "tags", "tvshows", "episodes"]:
        self.addProperties(REQUEST, "file")

      self.addProperties(REQUEST, ", ".join(self.config.getQAFields("zero", EXTRA)))
      self.addProperties(REQUEST, ", ".join(self.config.getQAFields("blank", EXTRA)))

    elif action == "dump":
      if mediatype in ["songs", "movies", "tvshows", "episodes", "musicvideos"]:
        self.addProperties(REQUEST, "file")
      if "extrajson.%s" % EXTRA in self.config.XTRAJSON:
        extraFields = self.config.XTRAJSON["extrajson.%s" % EXTRA] if EXTRA != "" else None
      else:
        extraFields = None
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

    return (SECTION, TITLE, IDENTIFIER,
            self.getDataProxy(mediatype, REQUEST, trim_cast_thumbs=(action != "dump"), uniquecast=uniquecast))

  # Load data chunked, or in one single query.
  # TV Shows, seasons and episodes are already "chunked" by definition.
  # If specified, remove cast members without thumbnails to reduce memory footprint.
  def getDataProxy(self, mediatype, request, trim_cast_thumbs=True, idname=None, uniquecast=None):
    if not idname:
      idname = "lib%s" % mediatype.capitalize()

    mediatype = mediatype.lower()

    if self.config.CHUNKED:
      silent = (mediatype in ["tvshows", "seasons", "episodes"])
      data = self.chunkedLoad(mediatype, request, trim_cast_thumbs, idname=idname, silent=silent, uniquecast=uniquecast)
    else:
      data = self.sendJSON(request, idname)
      if "result" in data and trim_cast_thumbs and "cast" in request.get("params",{}).get("properties",[]):
        for section in data["result"]:
          if section != "limits":
            for item in data["result"][section]:
              self.removecastwithoutthumbs(item, uniquecast)

    return data

  # Load library data in chunks, using limits.
  # Return resulting list of all requested items.
  def chunkedLoad(self, mediatype, request, trim_cast_thumbs=True, idname=None, silent=False, uniquecast=None):
    if not idname:
      idname = "libChunked%s" % mediatype.capitalize()

    CHUNK_SIZE = 400
    if mediatype in ["movies", "tags", "sets-members", "tvshows"]:
      if "cast" in request.get("params",{}).get("properties",[]):
        CHUNK_SIZE = 35

    chunk = 0
    chunk_start = 0
    total_items = 1
    chunks = 0
    section = None
    results = []

    while chunk_start < total_items:
      chunk += 1
      if not silent:
        # Don't yet know how many chunks there will be
        if chunk_start != 0:
          self.logger.progress("Loading %s: Chunk %d of %d..." % (mediatype.capitalize(), chunk, chunks))
        else:
          self.logger.progress("Loading %s: Chunk %d..." % (mediatype.capitalize(), chunk))

      request["params"]["limits"] = {"start": chunk_start, "end": chunk_start + CHUNK_SIZE}
      data = self.sendJSON(request, idname)
      if "result" not in data: break

      #Get total_items and section name once first chunk is retrieved
      if chunk_start == 0:
        if "limits" not in data["result"]:
          break

        total_items = data["result"]["limits"]["total"]
        chunks = -(-total_items // CHUNK_SIZE)
        self.logger.log("Chunk processing: found %d %s, retrieving in chunks of %d" % (total_items, mediatype, CHUNK_SIZE))

        for s in data.get("result", {}):
          if s != "limits":
            section = s
            break
        else:
          break

      # Add section to accumulated results
      if section and section in data["result"]:
        # Remove those cast members without thumbnails
        if trim_cast_thumbs and "cast" in request.get("params",{}).get("properties",[]):
          for item in data["result"][section]:
            self.removecastwithoutthumbs(item, uniquecast)
        results.extend(data["result"][section])

      chunk_start = (chunk * CHUNK_SIZE)

    response = {"result": {"limits": {"start": 0, "end": len(results), "total": len(results)}}}
    if section: response["result"][section] = results
    return response

  # Create a new cast list ignoring any cast member without a thumbnail.
  # Replace original cast list with the new cast list.
  def removecastwithoutthumbs(self, mediaitem, uniquecast=None):
    if "cast" in mediaitem:
      cast = []
      for i in mediaitem["cast"]:
        if "thumbnail" in i:
          if uniquecast is not None:
            if i["thumbnail"] not in uniquecast:
              uniquecast[i["thumbnail"]] = True
              cast.append(i)
          else:
            cast.append(i)
      mediaitem["cast"] = cast

  # Return a list of all pictures (jpg/png/tbn etc.) from any "pictures" source
  def getPictures(self, addPreviews=False, addPictures=True):
    list = []

    if addPreviews or addPictures:
      for path in self.getSources("pictures"):
        self.getPicturesForPath(path, list, addPreviews, addPictures)

    return list

  def getPicturesForPath(self, path, list, addPreviews, addPictures):
    data = self.getDirectoryList(path, use_cache=False)
    if "result" not in data or "files" not in data["result"]: return

    DIR_ADDED = False
    for file in data["result"]["files"]:
      if file["file"]:
        ftype = file["filetype"]
        fname = file["file"]

        if ftype == "directory":
          self.getPicturesForPath(fname, list, addPreviews, addPictures)
        elif ftype == "file" and os.path.splitext(fname)[1].lower() in self.config.picture_filetypes:
          if addPreviews:
            if not DIR_ADDED:
              DIR_ADDED = True
              list.append({"type": "directory", "label": path, "thumbnail": "picturefolder@%s" % path})
            list.append({"type": "file", "label": fname, "thumbnail": "%s/transform?size=thumb" % fname})
          if addPictures:
            list.append({"type": "file", "label": fname, "thumbnail": fname})

  def parseSQLFilter(self, filter):
    if type(filter) is dict: return filter

    filter = filter.strip()

    if not filter: return []

    if filter.lower().startswith("where "):
      filter = filter[6:]

    PATTERN = re.compile(r'''((?:[^ "']|"[^"]*"|'[^']*')+)''')

    stack = []
    data = []
    fields = []
    condition = None
    group = False
    f = 0
    for token in PATTERN.split(filter)[1::2]:
      #Unescape any escaped apostrophe
      token = token.replace("''","'")

      if token.startswith("("):
        group = False
        token = token[1:]
      elif token.endswith(")"):
        group = True
        token = token[:-1]

      if token in ["and", "or"]:
        if condition and condition != token:
          if group:
            if token in ["and", "or"]:
              if stack == []:
                stack.append({token: [{condition: data}]})
              else:
                s = stack.pop()
                stack.append({token: [s]})
          data = []
        condition = token if not group else None
        continue

      fields.append(token)
      f += 1

      if f == 3:
        if fields[0].startswith("t."): fields[0] = fields[0][2:]
        if fields[0] == "id": fields[0] = "textureid"
        if fields[0] == "lastusetime": fields[0] = "lastused"

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
          fields[1] = "greaterthanequal"
        elif fields[1] == "<=":
          fields[1] = "lessthanequal"
        elif fields[1].lower() == "like":
          if re.match("^%.*%$", fields[2]):
            fields[1] = "contains"
            fields[2] = fields[2][1:-1]
          elif re.match("^%.*", fields[2]):
            fields[1] = "endswith"
            fields[2] = fields[2][1:]
          elif re.match("^.*%", fields[2]):
            fields[1] = "startswith"
            fields[2] = fields[2][:-1]
          else:
            fields[1] = "is"
        else:
          fields[1] = "is"
          pass

        if fields[1].endswith("thanequal"):
          data.append({"or": [{"field": fields[0], "operator": "is", "value": fields[2]},
                              {"field": fields[0], "operator": fields[1][:-5], "value": fields[2]}]})
        else:
          data.append({"field": fields[0], "operator": fields[1], "value": fields[2]})
          if group:
            if stack == []:
              stack.append({condition: data})
            else:
              s = stack.pop()
              c1 = "or" if "or" in s else "and"
              c2 = "or" if "or" in s[c1][0] else "and"
              if condition:
                s[c1].append({condition: data})
              else:
                s[c1].extend(data)
              stack.append(s)
            data = []

        fields = []
        f = 0

    if stack:
      return stack[0]
    elif data:
      if condition:
        return {condition: data}
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
        if fields[0] == "lastusetime": fields[0] = "lastused"

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
    self.HISTORY = (time.time(), time.time(), 0)
    self.PCOUNT = self.PMIN = self.PAVG = self.PMAX = 0
    self.MCOUNT = self.MMIN = self.MAVG = self.MMAX = 0

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

  def init(self, name=""):
    with lock:
      tname = threading.current_thread().name if name == "" else name
      self.THREADS[tname] = 0
      self.THREADS_HIST[tname] = (0, 0)

  # Record start time for an image type.
  def start(self, mediatype, imgtype):
    with lock:
      tname = threading.current_thread().name
      ctime = time.time()
      self.THREADS[tname] = ctime
      if not mediatype in self.ETIMES: self.ETIMES[mediatype] = {}
      if not imgtype in self.ETIMES[mediatype]: self.ETIMES[mediatype][imgtype] = {}
      if not tname in self.ETIMES[mediatype][imgtype]: self.ETIMES[mediatype][imgtype][tname] = (ctime, 0)

  # Record current time for imgtype - this will allow stats to
  # determine cumulative time taken to download an image type.
  def finish(self, mediatype, imgtype):
    with lock:
      tname = threading.current_thread().name
      ctime = time.time()
      self.setPerformance(ctime - self.THREADS[tname])
      self.THREADS_HIST[tname] = (self.THREADS[tname], ctime)
      self.THREADS[tname] = 0
      self.ETIMES[mediatype][imgtype][tname] = (self.ETIMES[mediatype][imgtype][tname][0], ctime)

  def stop(self):
    self.init()

  # Increment counter for action/imgtype pairing
  def bump(self, action, imgtype):
    with lock:
      if not action in self.TOTALS: self.TOTALS[action] = {}
      if not imgtype in self.TOTALS[action]: self.TOTALS[action][imgtype] = 0
      self.TOTALS[action][imgtype] += 1

  # Calculate and store min/max/avg.
  def setPerformance(self, elapsed):
    with lock:
      (s, e, c) = self.HISTORY
      self.HISTORY = (s, time.time(), c+1)

      self.PCOUNT += 1
      self.PAVG += elapsed
      if self.PMIN == 0 or elapsed < self.PMIN: self.PMIN = elapsed
      if elapsed > self.PMAX: self.PMAX = elapsed

  # Calculate average performance per second.
  def getPerformance(self, remaining):
    with lock:
      (s, e, c) = self.HISTORY
      tpersec = (c / (e - s)) if c != 0 else 1.0
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
          value = "%d" % items[i] if items[i] is not None else "-"
        elif a == DOWNLOAD_LABEL:
          if i in self.TOTALS[a] and self.TOTALS[a][i] != 0:
            value = self.secondsToTime(self.TOTALS[a][i])
          else:
            value = "-"
        elif i in self.TOTALS[a]:
          ivalue = self.TOTALS[a][i]
          value = "%d" % ivalue
          if items[i] is None: items[i] = 0
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
      pcount = 1 if self.PCOUNT == 0 else self.PCOUNT
      mavg = 1 if self.MAVG == 0.0 else self.MAVG
      for tname in self.THREADS_HIST:
        if not tname.startswith("Main"):
          tcount += 1
      print("  Threads Used: %d" % tcount)
      print("   Min/Avg/Max: %05.2f / %05.2f / %05.2f downloads per second" % (self.MMIN, self.MCOUNT/mavg, self.MMAX))
      print("   Min/Avg/Max: %05.2f / %05.2f / %05.2f seconds per download" % (self.PMIN, self.PAVG/pcount, self.PMAX))
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
  # 0=Ignore/Skipped; 1=Missing, to be cached; 2=Stale, to be cached; 3=Queued for downloading
  STATUS_UNKNOWN = 0
  STATUS_IGNORE = 1
  STATUS_MISSING = 2
  STATUS_STALE = 3
  STATUS_QUEUED = 4

  def __init__(self, mediaType, imageType, name, season, episode, filename, dbid, cachedurl, libraryid, missingOK):
    self.status = MyMediaItem.STATUS_UNKNOWN
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

  def getTypeSingular(self):
    return self.mtype[:-1]

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

    if self.episode_year is None: self.episode_year = ""

  def __str__(self):
    return "['%s', %d, '%s', '%s', %d, '%s, %s']" % \
            (self.mtype, self.libraryid, self.name, self.episode_year, self.playcount, self.lastplayed, self.resume)

  def getList(self):
    return [self.mtype, self.libraryid, self.name, self.episode_year, self.playcount, self.lastplayed, self.resume]

  def match(self, mediatype, name, episode_year):
    if mediatype != self.mtype: return False

    xepisode_year = episode_year
    if xepisode_year is None: xepisode_year = ""

    return (self.name == name and self.episode_year == xepisode_year)

  def refresh(self, HAS_RESUME, playcount, lastplayed, resume):
    # Update this object to reflect most recent (latest) values

    if playcount > self.playcount:   self.playcount = playcount
    if lastplayed > self.lastplayed: self.lastplayed = lastplayed

    if HAS_RESUME:
      if resume["position"] > self.resume["position"]:
        self.resume["position"] = resume["position"]

  def setState(self, HAS_RESUME, playcount, lastplayed, resume):
    # Assume no change is required
    self.state = 1

    if self.playcount == playcount and self.lastplayed == lastplayed:
      if not HAS_RESUME: return
      if self.resume["position"] == resume["position"]: return

    # Something has changed, apply object values to library
    self.state = 0
    return

# Helper class...
class MyUtility(object):
  isPython3 = (sys.version_info >= (3, 0))
  isPython3_1 = (sys.version_info >= (3, 1))
  EPOCH = datetime.datetime.utcfromtimestamp(0)

  DCData = {}
  DCStats = {}
  DCStatsAccumulated = {}

  #http://kodi.wiki/view/Advancedsettings.xml#moviestacking
  #<!-- <cd/dvd/part/pt/disk/disc> <0-N> -->
  #<regexp>(.*?)([ _.-]*(?:cd|dvd|p(?:ar)?t|dis[ck])[ _.-]*[0-9]+)(.*?)(\.[^.]+)$</regexp>
  #<!-- <cd/dvd/part/pt/disk/disc> <a-d> -->
  #<regexp>(.*?)([ _.-]*(?:cd|dvd|p(?:ar)?t|dis[ck])[ _.-]*[a-d])(.*?)(\.[^.]+)$</regexp>
  RE_STACKING_1_9 = re.compile("(.*?)([ _.-]*(?:cd|dvd|p(?:ar)?t|dis[ck])[ _.-]*[0-9]+)(.*?)(\.[^.]+)$", flags=re.IGNORECASE)
  RE_STACKING_A_D = re.compile("(.*?)([ _.-]*(?:cd|dvd|p(?:ar)?t|dis[ck])[ _.-]*[a-d])(.*?)(\.[^.]+)$", flags=re.IGNORECASE)

  RE_NOT_DIGITS = re.compile("[^0123456789]")

  # Convert quoted filename into consistent UTF-8
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
      except UnicodeEncodeError:
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

  # Cross-platform basename
  # os.path.basename() doesn't work when
  # processing a Windows filename on Linux
  @staticmethod
  def basename(filename):
    # If X:\ then assume a Windows filename
    if filename[1:].startswith(':\\'):
      return filename.split('\\')[-1]

    # Otherwise assume Linux or network (smb:// etc.) based filename
    return filename.split('/')[-1]

  # Join an unquoted filename to a quoted path,
  # returning a quoted result.
  #
  # Running urllib2.quote() on a path that contains
  # foreign characters would often fail with a Unicode error
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
    for qslash in ["%2f", "%2F", "%5c", "%5C"]:
      pos = qpath.rfind(qslash)
      if pos != -1:
        directory = "%s%s" % (qpath[:pos], qslash)
        break
    else:
      return None

    fname = urllib2.quote(MyUtility.basename(filename), "")

    return "%s%s/" % (directory, fname)

  #
  # Some JSON paths may have incorrect path separators.
  # Use this function to attempt to correct those path separators.
  #
  # Shares ("smb://", "nfs://" etc.) will always use forward slashes.
  #
  # Non-shares will use a slash appropriate to the OS to which the path
  # corresponds so attempt to find the FIRST slash (forward or back) and
  # then use that as the path separator, replacing any of the opposite
  # kind. The reason being that path mangling addons are likely to mangle
  # only the last slashes but not the first.
  #
  # If only one type of slash found (or neither slash found), do nothing.
  #
  # See: http://forum.kodi.tv/showthread.php?tid=153502&pid=1477147#pid1477147
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

  # Convert a path or filename from Windows or Linux format, to the "host" OS format
  @staticmethod
  def PathToHostOS(filename):
    # Share (eg. "smb://", "nfs://" etc.)
    if re.search("^.*://.*", filename):
      return filename.replace("\\", "/")

    if os.sep == "/":
      return filename.replace("\\", "/")
    else:
      return filename.replace("/", "\\")

  @staticmethod
  def Top250MovieList():
    gLogger.progress("Retrieving Top250 movie rankings...")

    try:
      import xml.etree.ElementTree as ET

      URL = "http://top250.info/charts"

      gLogger.log("Top250: Retrieving Top250 Movies from: [%s]" % URL)
      html = urllib2.urlopen(URL)
      if MyUtility.isPython3:
        data = html.read().decode('utf-8')
      else:
        data = html.read()
      html.close()

      gLogger.log("Top250: Read %d bytes of data" % len(data))

      tstamp = data.find("<title>")
      if tstamp  != -1:
        tstamp += 30
        gLogger.log("Top250: Data last updated [%s]" % data[tstamp:tstamp+18])

      # Find end of first table, as movie list is in the second table
      spos = data.find("</table>")
      epos = data[spos+8:].find("</table>") if spos != -1 else -1

      if spos != -1 and epos != -1:
        data = data[spos+8:spos+8+epos+8]
        gLogger.log("Top250: Table data found, %d bytes" % len(data))

        # Clean up garbage encodings
        newdata = ""
        for c in data:
          if c != "&":
            if ord(c) <= 127:
              newdata += c

        table = ET.fromstring(newdata)

        RE_IMDB = re.compile("/movie/\?([0-9]*)")

        movies = {}
        for row in table:
          if row.attrib["class"] == "row_header": continue
          movie = {}
          title = row[2][0][0].text
          anchor = row[2][0].attrib["href"]
          s = RE_IMDB.search(anchor)
          if s:
            movie["link"] = "tt%s" % s.group(1)
            movie["title"] = title
            movie["rank"] = len(movies)+1
            try:
              movie["rating"] = float(row[3].text)
            except:
              pass
            try:
              if gConfig.JSON_VOTES_HAVE_NO_GROUPING:
                movie["votes"] = u"%s" % int(MyUtility.getDigits(row[4].text))
              else:
                movie["votes"] = u"%s" % format(int(MyUtility.getDigits(row[4].text)), ",d").replace(",", gConfig.IMDB_GROUPING)
            except:
              pass
            movies[movie["link"]] = movie

        gLogger.log("Top250: loaded %d movies" % len(movies))
        return movies
      else:
        gLogger.log("Top250: ERROR: didn't find movie data, skipping Top250 movies")
        return None
    except Exception as e:
      gLogger.log("Top250: ERROR: failed to retrieve Top250 movie data: [%s]" % str(e))
      raise
      return None

  @staticmethod
  def getIMDBInfo(mediatype, apikey, imdbnumber=None, title=None, year=None, season=None, episode=None, plotFull=False, plotOutline=False, qtimeout=15.0):
    try:
      omdb_url = "http://www.omdbapi.com/"
      base_url = "%s?apikey=%s" % (omdb_url, apikey)
      redacted_url = "%s?apikey=%s" % (omdb_url, "<yourkey>")

      isMovie = isTVShow = isSeason = isEpisode = False

      if mediatype == "movie":
        query_url = "i=%s&type=movie" % imdbnumber
        reference = imdbnumber
        isMovie = True
      elif mediatype in ["tvshow", "episode"]:
        reference = "tvshow: %s (%d)" % (title, year)
        if imdbnumber is not None:
          query_url = "i=%s" % imdbnumber
        else:
          query_url = "t=%s&y=%d" % (MyUtility.denormalise(title, False), year)
        isTVShow = True
        if season:
          query_url = "%s&season=%d" % (query_url, season)
          reference = "season: %s (%d) S%02d" % (title, year, season)
          isSeason = True
        if episode:
          query_url = "%s&episode=%d" % (query_url, episode)
          reference = "episode: %s (%d) S%02dE%02d" % (title, year, season, episode)
          isEpisode = True
        query_url = "%s&type=%s" % (query_url, "episode" if isEpisode else "series")
      else:
        return {}

      data_short = data_full = data = {}

      # For movie, get both short plot, and optionally the full plot. Use fields from short query.
      if isMovie:
        f = urllib2.urlopen("%s&%s&plot=short" % (base_url, query_url), timeout=qtimeout)
        data_short = json.loads(f.read().decode("utf-8"))
        f.close()

      # For TV shows and Episodes, we only need the full plot and fields.
      if not isMovie or plotFull:
        f = urllib2.urlopen("%s&%s&plot=full" % (base_url, query_url), timeout=qtimeout)
        data_full = json.loads(f.read().decode("utf-8"))
        f.close()

      if data_short != {}:
        data = data_short
        data["Plotoutline"] = data_short.get("Plot", None)
        data["Plot"] = None

      if data_full != {}:
        if data == {}:
          data = data_full
        data["Plot"] = data_full.get("Plot", None)

      if "Response" not in data or data["Response"] == "False":
        gLogger.log("Failed OMDb API Query [%s&%s] => [%s]" % (redacted_url, query_url, data))
        if isTVShow and not isEpisode:
          gLogger.log("Try OMDb API Query [%s&s=%s&type=series] to see possible available titles (hint: year of tvshow is %d)" %(redacted_url, title, year))
        return {}

      # Convert omdbapi.com fields to Kodi fields - mostly just a case
      # of converting to lowercase, and removing "imdb" prefix
      newdata = {}
      for key in data:
        if data[key] is None or data[key] == "N/A":
          continue

        newkey = key.replace("imdb", "").lower()

        try:
          # Convert rating from str to float
          if newkey == "rating":
            newdata[newkey] = float(data[key])
          # Munge plot/plotoutline together as required
          elif newkey == "plot":
            if plotFull:
              newdata["plot"] = data.get(key, None)
          elif newkey == "plotoutline":
            if plotOutline:
              newdata["plotoutline"] = data.get(key, None)
          # Convert genre to a list
          elif newkey in ["genre", "country", "director", "writer"]:
            newdata[newkey] = [g.strip() for g in data[key].split(",")]
          # Year to an int
          elif newkey == "year":
            if not isMovie: continue
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
          elif newkey == "votes":
            if gConfig.JSON_VOTES_HAVE_NO_GROUPING:
              newdata[newkey] = "%s" % int(MyUtility.getDigits(data[key]))
            else:
              newdata[newkey] = format(int(MyUtility.getDigits(data[key])), ",d").replace(",", gConfig.IMDB_GROUPING)
          elif newkey == "rated":
            newkey = "mpaa"
            if data[key] == None or data[key] in ["Not Rated", "Unrated"]:
              newdata[newkey] = "Not Rated"
            else:
              newdata[newkey] = "Rated %s" % data[key]
          elif newkey == "released":
            newkey = "premiered"
            newdata[newkey] = datetime.datetime.strptime(data[key].replace(" ","-"), '%d-%b-%Y').strftime("%Y-%m-%d")
          else:
            newdata[newkey] = data[key]

          if newkey in newdata:
            newdata[newkey] = MyUtility.toUnicode(newdata[newkey])

        except Exception as e:
          gLogger.log("Exception during IMDb processing: reference [%s], key [%s]. msg [%s]" % (reference, key, str(e)))
          gLogger.log("OMDb API Query [%s&%s]" % (redacted_url, query_url))
      return newdata
    except Exception as e:
      gLogger.log("Exception during IMDb processing: reference [%s], timeout [%s], msg [%s]" % (reference, qtimeout, str(e)))
      gLogger.log("OMDb API Query [%s&%s]" % (redacted_url, query_url))
      return {}

  @staticmethod
  def nonestr(s):
    if s is None:
      return ""
    return str(s)

  @staticmethod
  def is_cache_item_stale(config, jcomms, mediaitem):
    if config.cache_refresh_date is None: return False
    if mediaitem.decoded_filename.startswith("http://"): return False

    # Only check file details for the following media types
    if mediaitem.mtype in ["movies", "tags", "sets", "tvshows", "seasons", "episodes", "albums", "artists", "songs"]:
      file = jcomms.getFileDetails(mediaitem.decoded_filename, properties=["file", "lastmodified"])
      if file and "lastmodified_timestamp" in file:
        return (file["lastmodified_timestamp"] >= config.cache_refresh_date)

    return False

  @staticmethod
  def invalidateDirectoryCache(mediatype):
    with lock:
      # Transfer current stats to accumulated
      for p in MyUtility.DCData:
        for c in MyUtility.DCStats[p]:
          if c not in MyUtility.DCStatsAccumulated: MyUtility.DCStatsAccumulated[c] = 0
          MyUtility.DCStatsAccumulated[c] += MyUtility.DCStats[p][c]

      MyUtility.logDirectoryCacheStats(mediatype, totals=False)

      del MyUtility.DCData
      del MyUtility.DCStats
      MyUtility.DCData = {}
      MyUtility.DCStats = {}

  @staticmethod
  def setDirectoryCacheItem(data, properties, path):
    props = ",".join(sorted(properties))

    fs_bs = "\\" if path.find("\\") != -1 else "/"
    if path[-1:] != fs_bs: path += fs_bs

    with lock:
      if props not in MyUtility.DCData:
        MyUtility.DCData[props] = {}
      if props not in MyUtility.DCStats:
        MyUtility.DCStats[props] = {"miss": 0, "store": 0, "hit": 0, "evicted": 0}

      count = MyUtility.DCData[props].get(path, {"count": 0})["count"]
      MyUtility.DCData[props][path] = {"time": time.time(), "count": count+1, "data": data}

      if gConfig.LOGDCACHE:
        hits = MyUtility.DCData[props][path]["count"]
        size = len(MyUtility.DCData[props])
        gLogger.log("Directory Cache %4s: %s (%s) [hit #1. %d items in cache]" %
                    ("STOR", props, path, size))

      # If we've just added a new item, we may need to now trim the cache
      if count == 0:
        MyUtility.DCStats[props]["store"] += 1
        MyUtility.trimDirectoryCache(props)

  @staticmethod
  def getDirectoryCacheItem(properties, path):
    props = ",".join(sorted(properties))

    fs_bs = "\\" if path.find("\\") != -1 else "/"
    if path[-1:] != fs_bs: path += fs_bs

    with lock:
      if props not in MyUtility.DCData:
        MyUtility.DCData[props] = {}
        if props not in MyUtility.DCStats:
          MyUtility.DCStats[props] = {"miss": 1, "store": 0, "hit": 0, "evicted": 0}
        result = None
      elif path not in MyUtility.DCData[props]:
        MyUtility.DCStats[props]["miss"] += 1
        result = None
      else:
        MyUtility.DCStats[props]["hit"] += 1
        c = MyUtility.DCData[props][path]
        c["time"] = time.time()
        c["count"] += 1
        result = c["data"]

      if gConfig.LOGDCACHE:
        hits = MyUtility.DCData[props][path]["count"] if result else 1
        size = len(MyUtility.DCData[props])
        gLogger.log("Directory Cache %4s: %s (%s) [hit #%d, %d items in cache]" %
                    (("HIT " if result else "MISS"), props, path, hits, size))

      return result

  @staticmethod
  def trimDirectoryCache(properties):
    if properties not in MyUtility.DCData: return
    if len(MyUtility.DCData[properties]) <= gConfig.DCACHE_SIZE: return

    cp = MyUtility.DCData[properties]

    now = time.time()
    cexpiry = now - gConfig.DCACHE_AGELIMIT

    delKeys = []

    # Identify any cache items that can be expired due to old age
    for citem in cp:
      if cp[citem]["time"] < cexpiry:
        delKeys.append(citem)

    for ditem in delKeys:
      if gConfig.LOGDCACHE:
        gLogger.log("Directory Cache TRIM: %s (%s) [%d hits, %d items] (Age: %5.2f seconds)" %
          (properties, ditem, MyUtility.DCData[properties][ditem]["count"],
            len(MyUtility.DCData[properties]), (now - cp[ditem]["time"])))
      del cp[ditem]

    if properties in MyUtility.DCStats:
      MyUtility.DCStats[properties]["evicted"] += len(delKeys)

    # If we still need to trim the cache
    # to its maximum size, get rid of the oldest item(s)
    while len(cp) > gConfig.DCACHE_SIZE:
      oldestTime = now
      oldestItem = None
      for citem in cp:
        if cp[citem]["time"] < oldestTime:
          oldestTime = cp[citem]["time"]
          oldestItem = citem
      if oldestItem:
        if properties in MyUtility.DCStats:
          MyUtility.DCStats[properties]["evicted"] += 1
        if gConfig.LOGDCACHE:
          gLogger.log("Directory Cache TRIM: %s (%s) [%d hits, %d items] (Size)" %
            (properties, oldestItem, cp[oldestItem]["count"], len(cp)))
        del cp[oldestItem]

  @staticmethod
  def logDirectoryCacheStats(mediatype=None, totals=False):
    if gLogger.LOGGING:
      if totals and MyUtility.DCStatsAccumulated:
        gLogger.log("Directory Cache Config: Maximum Size %d, Age Limit %d seconds" %
                     (gConfig.DCACHE_SIZE, gConfig.DCACHE_AGELIMIT))
        stats = MyUtility.DCStatsAccumulated
        gLogger.log("Directory Cache Totals: Misses %d, Stores %d, Hits %d, Evicted %d" %
                     (stats["miss"], stats["store"], stats["hit"], stats["evicted"]))
      else:
        for props in MyUtility.DCStats:
          stats = MyUtility.DCStats[props]
          gLogger.log("Directory Cache PERF: Misses %d, Stores %d, Hits %d, Evicted %d, mediatype [%s] for properties: %s" %
                       (stats["miss"], stats["store"], stats["hit"], stats["evicted"], mediatype, props.split(",")))

  @staticmethod
  def SinceEpoch(dt):
    return int((dt - MyUtility.EPOCH).total_seconds())

  @staticmethod
  def getVersion(strVersion):
    fields = strVersion.split(".")
    return int("%03d%03d%03d" % (int(fields[0]), int(fields[1]), int(fields[2])))

  @staticmethod
  def removeDiscPart(filename):

    match = MyUtility.RE_STACKING_1_9.match(filename)
    if not match:
      match = MyUtility.RE_STACKING_A_D.match(filename)

    if match and len(match.groups()) >= 3:
      p1 = match.string[:match.end(1)]
      p2 = match.string[match.start(3):]
      p1 = p1[:-1] if p1[-1] in [" ", "(", "[", ".", "-", "_"] else p1
      p2 = p2[1:] if p2[0] in [")", "]"] else p2
      return "%s%s" % (p1, p2)

    return filename

  @staticmethod
  def unstackFiles(files, addcombinedfile=False):
    if files.startswith("stack://"):
      unstack = files[8:].split(" , ")
      if addcombinedfile:
        unstack.insert(0, MyUtility.removeDiscPart(unstack[0]))
      return unstack
    else:
      return [files]

  @staticmethod
  def getDigits(text):
    return MyUtility.RE_NOT_DIGITS.sub("", text)

#
# Load data using JSON-RPC. In the case of TV shows, also load seasons
# and Episodes into a single data structure.
#
# Sets doesn't support filters, so filter this list after retrieval.
#
def jsonQuery(action, mediatype, filter="", force=False, extraFields=False, rescan=False, \
                      decode=False, ensure_ascii=True, nodownload=False, lastRun=False, \
                      labels=None, query="", filename=None, wlBackup=True, drop_items=None):
  if mediatype not in ["addons", "agenres", "vgenres", "albums", "artists", "songs", "musicvideos",
                       "movies", "sets", "tags", "tvshows", "pvr.tv", "pvr.radio"]:
    gLogger.err("ERROR: %s is not a valid media class" % mediatype, newLine=True)
    sys.exit(2)

  # Only songs, movies and tvshows (and sub-types) valid for missing...
  if action == "missing" and mediatype not in ["songs", "movies", "tvshows", "seasons", "episodes"]:
    gLogger.err("ERROR: media class [%s] is not currently supported by missing" % mediatype, newLine=True)
    sys.exit(2)

  # Only movies and tvshows for "watched"...
  if action == "watched" and mediatype not in ["movies", "tvshows"]:
    gLogger.err("ERROR: media class [%s] is not currently supported by watched" % mediatype, newLine=True)
    sys.exit(2)

  # Only movies and tvshows for "imdb"...
  if action == "imdb" and mediatype not in ["movies", "tvshows"]:
    gLogger.err("ERROR: media class [%s] is not currently supported by IMDb" % mediatype, newLine=True)
    return

  TOTALS.TimeStart(mediatype, "Total")

  jcomms = MyJSONComms(gConfig, gLogger)
  database = MyDB(gConfig, gLogger)

  if mediatype == "tvshows":
    TOTALS.addSeasonAll()
    gLogger.progress("Loading TV shows...")
  else:
    gLogger.progress("Loading %s..." % mediatype.capitalize())

  TOTALS.TimeStart(mediatype, "Load")

  if action == "query":
    secondaryFields = parseQuery(query)[0]
  else:
    secondaryFields = None

  # Keep a hash of unique cast thumbnails to minimise number of cast member
  # details that are loaded from the client - the vast majority will be
  # duplicates that can be discarded.
  UCAST = {}

  if mediatype in ["pvr.tv", "pvr.radio"] and not gConfig.HAS_PVR:
    (section_name, title_name, id_name, data) = ("", "", "", [])
  elif mediatype == "vgenres":
    _data = []
    for subtype in ["movie", "tvshow", "musicvideo"]:
      (section_name, title_name, id_name, data) = jcomms.getData(action, mediatype, filter, extraFields,
                                                                 lastRun=lastRun, secondaryFields=secondaryFields,
                                                                 subType=subtype)
      filter_name = gConfig.FILTER_FIELD if gConfig.FILTER_FIELD else title_name
      if data and "result" in data and section_name in data["result"]:
        if filter != "":
          filteredData = []
          for d in data["result"][section_name]:
            if re.search(filter, d[filter_name], re.IGNORECASE):
              filteredData.append(d)
          data["result"][section_name] = filteredData
        if len(data["result"][section_name]) > 0:
          _data.append({"type": subtype, section_name: data["result"][section_name]})
    title_name = "type"
    section_name = mediatype
    data["result"] = {section_name: _data}
  else:
    (section_name, title_name, id_name, data) = jcomms.getData(action, mediatype, filter, extraFields,
                                                               lastRun=lastRun, secondaryFields=secondaryFields, uniquecast=UCAST)

  if data and "result" in data and section_name in data["result"]:
    data = data["result"][section_name]
  else:
    data = []

  # Manually filter these mediatypes as JSON doesn't support filtering
  if data and filter and mediatype in ["addons", "agenres", "sets", "pvr.tv", "pvr.radio"]:
    filter_name = gConfig.FILTER_FIELD if gConfig.FILTER_FIELD else title_name
    gLogger.log("Filtering %s on %s = %s" % (mediatype, filter_name, filter))
    filteredData = []
    for d in data:
      if re.search(filter, d[filter_name], re.IGNORECASE):
        filteredData.append(d)
    data = filteredData

  # Add movie file members to sets when dumping
  if action == "dump" and data:
    if mediatype == "sets" and gConfig.ADD_SET_MEMBERS:
      gLogger.progress("Loading Sets members...")
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

    if mediatype == "albums" and gConfig.ADD_SONG_MEMBERS:
      gLogger.progress("Loading Song members...")
      (s, t, i, fdata) = jcomms.getData(action, "song-members", filter, extraFields, lastRun=lastRun, secondaryFields=None)
      if fdata and "result" in fdata and s in fdata["result"]:
        album_files = {}
        for album in fdata["result"][s]:
          album_name = album["album"]
          if album_name:
            del album["album"]
            if "label" in album: del album["label"]
            if album_name not in album_files: album_files[album_name] = []
            album_files[album_name].append(album)
        for album in data:
          album["tc.members"] = album_files.get(album["title"], [])

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

  if mediatype == "tvshows" and gConfig.QUERY_SEASONS:
    for tvshow in data:
      title = tvshow["title"]
      gLogger.progress("Loading TV show: %s..." % title)

      (s2, t2, i2, data2) = jcomms.getData(action, "seasons", filter, extraFields, tvshow=tvshow, lastRun=lastRun, uniquecast=UCAST)
      if not "result" in data2: return
      limits = data2["result"]["limits"]
      if limits["total"] == 0: continue
      tvshow[s2] = data2["result"][s2]
      for season in tvshow[s2]:
        seasonid = season["season"]
        if seasonid < 0:
          gLogger.err("WARNING: TV show [%s] has invalid season (%d) - ignored" % (title, seasonid), newLine=True)
          continue

        gLogger.progress("Loading TV show: %s, season %d..." % (title, seasonid))

        if gConfig.QUERY_EPISODES:
          (s3, t3, i3, data3) = jcomms.getData(action, "episodes", filter, extraFields, tvshow=tvshow, tvseason=season,
                                               lastRun=lastRun, secondaryFields=secondaryFields, uniquecast=UCAST)
          if not "result" in data3: return
          limits = data3["result"]["limits"]
          if limits["total"] == 0: continue
          season[s3] = data3["result"][s3]

  del UCAST

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
          gLogger.out("Recently added TV show: %s (%d episode%s)" % (tvshow.get("title"), epCount, "s"[epCount==1:]), newLine=True)
      data = newData
    else:
      for item in data:
        gLogger.out("Recently added movie: %s" % item.get("title", item.get("artist", item.get("name", None))), newLine=True)

    if len(data) != 0: gLogger.out("", newLine=True)

  TOTALS.TimeEnd(mediatype, "Load")

  if data != []:
    if action == "cache":
      cacheImages(mediatype, jcomms, database, data, title_name, id_name, force, nodownload, drop_items)
    elif action == "qa":
      qaData(mediatype, jcomms, database, data, title_name, id_name, rescan)
    elif action == "dump":
      jcomms.dumpJSON(data, decode, ensure_ascii)
    elif action == "missing":
      fileList = jcomms.getAllFilesForSource(mediatype, labels, gConfig.MISSING_IGNORE_PATTERNS, True)
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

  # Free memory used to cache any GetDirectory() information
  MyUtility.invalidateDirectoryCache(mediatype)

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
def cacheImages(mediatype, jcomms, database, data, title_name, id_name, force, nodownload, drop_items):

  mediaitems = []
  imagecache = {}
  imagecache[""] = 0 # Ensure an empty image is already in the imagecache, with a zero reference count

  TOTALS.TimeStart(mediatype, "Parse")

  parseURLData(jcomms, mediatype, mediaitems, imagecache, data, title_name, id_name)

  TOTALS.TimeEnd(mediatype, "Parse")

  # Don't need this data anymore, make it available for garbage collection
  del data, imagecache

  # Match media library items with any cached artwork
  matchTextures(mediatype, mediaitems, jcomms, database, force, nodownload)

  if force:
    ITEMLIMIT = 0
  elif nodownload:
    ITEMLIMIT = -1
  else:
    ITEMLIMIT = 100

  # Count number of items that need to be downloaded, and
  # output details of items that are stale or missing from the cache (unless force,
  # in which case everything is being downloaded so don't output anything!)
  itemCount = 0
  for item in mediaitems:
    if item.status in [MyMediaItem.STATUS_MISSING, MyMediaItem.STATUS_STALE]:
      itemCount += 1
      if ITEMLIMIT == -1 or itemCount < ITEMLIMIT:
        reason = "Need to cache" if item.status == MyMediaItem.STATUS_MISSING else "Cache stale  "
        MSG = "%s: [%-10s] for %s: %s\n" % (reason, item.itype.center(10), re.sub("(.*)s$", "\\1", item.mtype), item.getFullName())
        gLogger.out(MSG)
      elif itemCount == ITEMLIMIT:
        gLogger.out("...and many more! (First %d items shown)\n" % ITEMLIMIT)

  if nodownload:
    TOTALS.addNotCached()
    for item in mediaitems:
      if item.status == MyMediaItem.STATUS_MISSING:
        TOTALS.bump("Not in Cache", item.itype)

  # Don't proceed beyond this point unless there is something to download...
  if itemCount == 0 or nodownload: return

  # Queue up the items to be downloaded...
  single_work_queue = Queue.Queue()
  multiple_work_queue = Queue.Queue()
  error_queue = Queue.Queue()
  complete_queue = Queue.Queue()

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
      if item.status in [MyMediaItem.STATUS_MISSING, MyMediaItem.STATUS_STALE] and item.itype == ui:
        c += 1

        isSingle = False
        if gConfig.SINGLETHREAD_URLS:
          for site in gConfig.SINGLETHREAD_URLS:
            if site.search(item.decoded_filename):
              sc += 1
              if gLogger.VERBOSE and gLogger.LOGGING: gLogger.log("QUEUE ITEM: single [%s], %s" % (site.pattern, item))
              single_work_queue.put(item)
              item.status = MyMediaItem.STATUS_QUEUED
              isSingle = True
              break

        if not isSingle:
          mc += 1
          if gLogger.VERBOSE and gLogger.LOGGING: gLogger.log("QUEUE ITEM: %s" % item)
          multiple_work_queue.put(item)
          item.status = MyMediaItem.STATUS_QUEUED

        gLogger.progress("Queueing work item: single thread %d, multi thread %d" % (sc, mc), every=50, finalItem=(c==itemCount))

  # Don't need this data anymore, make it available for garbage collection
  del mediaitems

  TOTALS.TimeStart(mediatype, "Download")

  THREADS = []

  if not single_work_queue.empty():
    gLogger.log("Creating 1 download thread for single access sites")
    t = MyImageLoader(single_work_queue, multiple_work_queue, error_queue, complete_queue,
                      gConfig, gLogger, TOTALS, force, gConfig.DOWNLOAD_RETRY)
    THREADS.append(t)
    t.setDaemon(True)

  if not multiple_work_queue.empty():
    tCount = gConfig.DOWNLOAD_THREADS["download.threads.%s" % mediatype]
    THREADCOUNT = tCount if tCount <= mc else mc
    gLogger.log("Creating %d download thread(s) for multi-access sites" % THREADCOUNT)
    for i in range(THREADCOUNT):
      t = MyImageLoader(multiple_work_queue, single_work_queue, error_queue, complete_queue,
                        gConfig, gLogger, TOTALS, force, gConfig.DOWNLOAD_RETRY)
      THREADS.append(t)
      t.setDaemon(True)

  # Start the threads...
  for t in THREADS: t.start()

  threadcount = len(THREADS)

  updateInterval = 1.0
  itemsRemaining = itemCount
  perfhistory = []
  showProgress(threadcount, itemCount, single_work_queue.qsize(), multiple_work_queue.qsize(), error_queue.qsize(), itemsRemaining)
  while threadcount > 0:
    pace = time.time()
    completed = 0
    while True:
      try:
        qItem = complete_queue.get(block=True, timeout=updateInterval)
        complete_queue.task_done()
        if qItem is None:
          threadcount -= 1
        else:
          completed += 1
          itemsRemaining -= 1
        if (time.time() - pace) >= updateInterval or threadcount <= 0:
          break
      except Queue.Empty:
        break
    showProgress(threadcount, itemCount, single_work_queue.qsize(), multiple_work_queue.qsize(), error_queue.qsize(),
                  itemsRemaining, completed, time.time() - pace, perfhistory)

  TOTALS.TimeEnd(mediatype, "Download")

  gLogger.progress("", newLine=True, noBlank=True)

  if not error_queue.empty():
    gLogger.out("\nThe following items could not be downloaded:\n\n")
    while not error_queue.empty():
      item = error_queue.get()
      error_queue.task_done()

      # Ignore itypes with a period, eg. "cast.thumb" or "season.banner"
      if item.mtype in ["sets", "movies", "tvshows", "seasons", "episodes"] and item.itype.find(".") == -1:
        drop_id = "%s#%d" % (item.mtype, item.libraryid)
        if drop_id not in drop_items:
          drop_items[drop_id] = {"libraryid": item.libraryid, "title": item.name, "type": item.getTypeSingular(), "items": {}}
        drop_item = drop_items[drop_id]
        artwork_items = drop_item["items"]
        artwork_items["art.%s" % item.itype] = ""
        drop_item["items"] = artwork_items
        drop_items[drop_id] = drop_item

      name = addEllipsis(50, item.getFullName())
      gLogger.out("[%-10s] [%-40s] %s\n" % (item.itype, name, item.decoded_filename))
      gLogger.log("ERROR ITEM: %s" % item)

def dump_drop_items(drop_items):
  if gConfig.CACHE_DROP_INVALID_FILE:
    outfile = codecs.open(gConfig.CACHE_DROP_INVALID_FILE, "wb", encoding="utf-8")
    outfile.write(json.dumps(drop_items.values(), indent=2, ensure_ascii=True, sort_keys=True))
    outfile.close()

def showProgress(tRunning, maxItems, swqs, mwqs, ewqs, remaining=0, completed=0, interval=0.0, history=None):
  c = 0
  i = 0.0

  # Apply a smoothing function based on fixed number of previous samples
  if history is not None and interval != 0.0:
    history.insert(0, (completed, interval))
    if len(history) > 15: history.pop()
    for p in history:
      c += p[0]
      i += p[1]

  if i != 0.0:
    # Smoothed tpersec
    tpersec = c / i if i != 0.0 else 0.0
    # Instantaneous tpersec - if sub-second don't normalise to a second as it results in erroneous value
    if interval < 1.0:
      itpersec = completed
    else:
      itpersec = completed / interval if interval != 0.0 else 0.0
  else:
    tpersec = itpersec = 0.0

  # Accumulate per-second download stats
  TOTALS.MCOUNT += completed
  TOTALS.MAVG += interval
  if TOTALS.MMIN == 0 or TOTALS.MMIN > itpersec:
    TOTALS.MMIN = itpersec
  if TOTALS.MMAX < itpersec:
    TOTALS.MMAX = itpersec

  eta = TOTALS.secondsToTime(remaining / tpersec, withMillis=False) if tpersec != 0.0 else "**:**:**"

  msg = " (%05.2f downloads per second, ETA: %s)" % (itpersec, eta)

  gLogger.progress("Caching artwork: %d item%s remaining of %d (qs: %d, qm: %d), %d error%s, %d thread%s active%s" % \
                    (remaining, "s"[remaining==1:],
                     maxItems, swqs, mwqs,
                     ewqs, "s"[ewqs==1:],
                     tRunning, "s"[tRunning==1:],
                     msg))

def matchTextures(mediatype, mediaitems, jcomms, database, force, nodownload):

  TOTALS.TimeStart(mediatype, "Compare")

  if gConfig.CHUNKED:
    matchTextures_chunked(mediatype, mediaitems, jcomms, database, force, nodownload)
  else:
    matchTextures_fast(mediatype, mediaitems, jcomms, database, force, nodownload)

  TOTALS.TimeEnd(mediatype, "Compare")

  return

def matchTextures_fast(mediatype, mediaitems, jcomms, database, force, nodownload):
  gLogger.progress("Loading Textures DB...")

  dbfiles = {}
  with database:
    for r in database.getRows(allfields=False):
      dbfiles[r["url"]] = r

  gLogger.log("Loaded %d items from texture cache database" % len(dbfiles))

  gLogger.progress("Matching library and texture items...")

  itemCount = 0

  for item in mediaitems:
    dbrow = dbfiles.get(item.decoded_filename, None)
    matchTextures_item_row(mediatype, jcomms, item, dbrow, force, nodownload)

  # Don't need this data anymore, make it available for garbage collection
  del dbfiles

  gLogger.progress("")

  return

def matchTextures_chunked(mediatype, mediaitems, jcomms, database, force, nodownload):
  ITEMLIMIT = -1 if nodownload else 100

  unmatched = len(mediaitems)
  matched = 0
  skipped = 0

  # Build a URL based hash of indexes so that we can quickly access mediaitems
  # by index for a given URL
  url_to_index = {}
  for inum, item in enumerate(mediaitems):
    url_to_index[item.decoded_filename] = inum

  dbindex = 0
  dbmax = 0

  with database:
    folders = database.getTextureFolders()

    for fnum, folder in enumerate(folders):
      # Once all library items have been matched, no need to continue querying textures DB
      if unmatched == 0: break

      gLogger.progress("Loading Textures DB: chunk %2d of %d [unmatched %d: matched %d, skipped %d] (%d of %d)" %
        (fnum+1, len(folders), unmatched, matched, skipped, dbindex, dbmax))

      dbfiles = []
      for r in database.getRows(database.getTextureFolderFilter(folder), allfields=False):
        dbfiles.append(r)

      dbindex = 0
      dbmax = len(dbfiles)

      for dbrow in dbfiles:
        dbindex += 1

        gLogger.progress("Loading Textures DB: chunk %2d of %d [unmatched %d: matched %d, skipped %d] (%d of %d)" %
          (fnum+1, len(folders), unmatched, matched, skipped, dbindex, dbmax), every=50, finalItem=(dbindex==dbmax))

        inum = url_to_index.get(dbrow["url"], None)
        if inum is not None:
          item = mediaitems[inum]
          if item.status == MyMediaItem.STATUS_UNKNOWN:
            unmatched -= 1
            matchTextures_item_row(mediatype, jcomms, item, dbrow, force, nodownload)
            if item.status == MyMediaItem.STATUS_IGNORE:
              skipped += 1
            else:
              matched += 1

  # Any media library items that haven't been matched must also be processed
  for item in mediaitems:
    if item.status == MyMediaItem.STATUS_UNKNOWN:
      matchTextures_item_row(mediatype, jcomms, item, None, force, nodownload)

  gLogger.progress("")

  return

def matchTextures_item_row(mediatype, jcomms, item, dbrow, force, nodownload):
  if item.mtype == "tvshows" and item.season == "Season All": TOTALS.bump("Season-all", item.itype)

  # Don't need to cache file if it's already in the cache, unless forced...
  # Assign the texture cache database id and cachedurl so that removal will avoid having
  # to retrieve these items from the database.
  if dbrow:
    if force:
      if gConfig.cache_refresh_date:
        if MyUtility.is_cache_item_stale(gConfig, jcomms, item):
          item.status = MyMediaItem.STATUS_STALE
        else:
          item.status = MyMediaItem.STATUS_IGNORE
      else:
        item.status = MyMediaItem.STATUS_MISSING

      if item.status != MyMediaItem.STATUS_IGNORE:
        item.dbid = dbrow["textureid"]
        item.cachedurl = dbrow["cachedurl"]
      else:
        TOTALS.bump("Skipped", item.itype)
    else:
      if nodownload and MyUtility.is_cache_item_stale(gConfig, jcomms, item):
        item.status = MyMediaItem.STATUS_STALE
        TOTALS.bump("Stale Item", item.itype)
      else:
        item.status = MyMediaItem.STATUS_IGNORE
        TOTALS.bump("Skipped", item.itype)
        if gLogger.VERBOSE and gLogger.LOGGING: gLogger.log("ITEM SKIPPED: %s" % item)
  else:
    item.status = MyMediaItem.STATUS_MISSING

  return

#
# Iterate over all the elements, seeking out artwork to be stored in a list.
# Use recursion to process season and episode sub-elements.
#
def parseURLData(jcomms, mediatype, mediaitems, imagecache, data, title_name, id_name, showName=None, season=None, pvrGroup=None):
  gLogger.reset()

  SEASON_ALL = (showName is not None and season is None)

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
        # channelid may be missing for some reason
        item["channelid"] = item.get("channelid",0)
    else:
      name = title
      longName = name
      season = item.get("artist", None) if title_name != "artist" else None
      episode= item.get("album", None) if title_name != "album" else None

    gLogger.progress("Parsing %s: %s..." % (mediatype.capitalize(), longName), every = 25)

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

# Include or exclude URL depending on basic properties - has it
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

  if mitems is None:
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
  nfo_file = False

  if mediatype in ["movies", "tags", "episodes"]:
    check_file = gConfig.QA_FILE
    nfo_file = (gConfig.qa_nfo_refresh_date is not None)

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

    gLogger.progress("Parsing %s: %s..." % (mediatype.capitalize(), name), every = 25)

    missing = {}

    for i in zero_items:
      (j, MOD, MOD_MISSING_SILENT, MOD_MISSING_WARN_FAIL) = splitModifierToken(i)
      ismissing = True
      if j in item:
        ismissing = (item[j] == 0)
      if ismissing and not MOD_MISSING_SILENT:
          missing["zero %s" % j] = MOD_MISSING_WARN_FAIL

    for i in blank_items:
      (j, MOD, MOD_MISSING_SILENT, MOD_MISSING_WARN_FAIL) = splitModifierToken(i)
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
      if ismissing and not MOD_MISSING_SILENT:
        missing["missing %s" % j] = MOD_MISSING_WARN_FAIL

    for i in art_items:
      (j, MOD, MOD_MISSING_SILENT, MOD_MISSING_WARN_FAIL) = splitModifierToken(i)
      if "art" in item:
        artwork = item.get("art", {}).get(j, "")
      else:
        artwork = item.get(j, "")
      if artwork == "":
        if not MOD_MISSING_SILENT:
          if MOD_MISSING_WARN_FAIL:
            if gConfig.QA_FAIL_CHECKEXISTS and "file" in item:
              if qa_check_artfile_exists(jcomms, mediatype, item, i):
                missing["missing %s, local is available" % j] = True
              else:
                missing["missing %s, local not found" % j] = gConfig.QA_FAIL_MISSING_LOCAL_ART
            else:
              missing["missing %s" % j] = True
          else:
            missing["missing %s" % j] = False
      else:
        decoded_url = MyUtility.normalise(artwork, strip=True)
        FAILED = False
        if gConfig.QA_FAIL_TYPES and MOD_MISSING_WARN_FAIL:
          for qafailtype in gConfig.QA_FAIL_TYPES:
            if qafailtype.search(decoded_url):
              if gConfig.QA_FAIL_CHECKEXISTS and "file" in item:
                if qa_check_artfile_exists(jcomms, mediatype, item, i):
                  missing["URL %s %s, local is available" % (j, qafailtype.pattern)] = True
                else:
                  missing["URL %s %s, local not found" % (j, qafailtype.pattern)] = gConfig.QA_FAIL_MISSING_LOCAL_ART
              else:
                missing["URL %s %s" % (j, qafailtype.pattern)] = True
              FAILED = True
              break
        if not FAILED and gConfig.QA_WARN_TYPES:
          for qawarntype in gConfig.QA_WARN_TYPES:
            if qawarntype.search(decoded_url):
              missing["URL %s %s" % (j, qawarntype.pattern)] = False
              break

    if (check_file or nfo_file) and "file" in item:
      files = None
      file_not_found = check_file
      nfo_not_found = nfo_file
      for file in MyUtility.unstackFiles(item["file"], addcombinedfile=True):
        dir = os.path.dirname(file)
        data = jcomms.getDirectoryList(dir, mediatype="files", properties=["file", "lastmodified"])
        if files == None:
          files = data.get("result", {}).get("files", [])

        if check_file and file_not_found and [f for f in files if f["filetype"] == "file" and f.get("file", None) == file]:
          file_not_found = False

        if nfo_file and nfo_not_found:
          nfofile = "%s.nfo" % os.path.splitext(file)[0]
          for f in [x for x in files if x["filetype"] == "file" and x.get("file", None) == nfofile]:
            nfo_not_found = False
            jcomms.setTimeStamp(f)
            if "lastmodified_timestamp" in f and \
               f["lastmodified_timestamp"] >= gConfig.qa_nfo_refresh_date:
              missing["modified nfo"] = True

      if file_not_found:
        missing["missing file"] = False

      if nfo_not_found:
        missing["missing nfo"] = False

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

      if "file" in item:
        mFAIL = "; ".join([x for x in missing if missing[x] == True])
        mWARN = "; ".join([x for x in missing if missing[x] == False])
      else:
        mFAIL = ""
        mWARN = "; ".join(missing)

      msg = ""
      if mFAIL: msg = "%sFAIL (%s), " % (msg, mFAIL)
      if mWARN: msg = "%sWARN (%s), " % (msg, mWARN)
      msg = msg [:-2]
      mediaitems.append("%-8s [%-50s]: %s" % (mtype, addEllipsis(50, name), msg))

      if "file" in item and mFAIL:
        dir = "%s;%s" % (mediatype, os.path.dirname(MyUtility.unstackFiles(item["file"])[0]))
        libraryids = workItems[dir] if dir in workItems else []
        libraryids.append({"id": libraryid, "name": name})
        workItems[dir] = libraryids

  if mitems is None:
    TOTALS.TimeEnd(mediatype, "Parse")
    gLogger.progress("")
    for m in mediaitems: gLogger.out("%s\n" % m)

  if rescan and mediatype in ["movies", "tags", "sets", "tvshows"]:
    TOTALS.TimeStart(mediatype, "Rescan")
    jcomms.rescanDirectories(workItems)
    TOTALS.TimeEnd(mediatype, "Rescan")

# Return True if an artwork item can be matched, this means we can
# FAIL the item and remove/re-scrape. If no artwork exists, then just
# WARN because removing/rescraping won't serve any purpose.
def qa_check_artfile_exists(jcomms, mediatype, item, artwork):
  if "file" not in item:
    return False

  filename = MyUtility.unstackFiles(item["file"], addcombinedfile=True)[0]
  dir = os.path.dirname(filename)
  data = jcomms.getDirectoryList(dir, mediatype="files", properties=["file", "lastmodified"])
  files = data.get("result", {}).get("files", [])

  if files:
    for art in get_qa_artworkcandidates(mediatype, filename, item, artwork):
      for file in files:
        if file["filetype"] == "file" and file["file"] == art:
          return True

  return False

# Construct a list of potential artwork candidates
# based on file name and artwork type.
def get_qa_artworkcandidates(mediatype, filename, item, artwork):
  art = []
  types = []

  fname = os.path.splitext(filename)[0]
  parent = os.path.dirname(filename)
  fs_bs = "\\" if filename.find("\\") != -1 else "/"

  types.append(artwork)

  if artwork == "poster":
    types.append("thumb")
  elif artwork == "clearlogo":
    types.append("logo")
  elif artwork == "discart":
    types.append("disc")

  for t in types:
    art.append("%s-%s.jpg" % (fname, t))
    art.append("%s-%s.png" % (fname, t))
    art.append("%s%s%s.jpg" % (parent, fs_bs, t))
    art.append("%s%s%s.png" % (parent, fs_bs, t))
    if mediatype in ["albums", "songs"] and t == "thumbnail":
      art.append("%s.jpg" % (fname))
      art.append("%s.png" % (fname))
      art.append("%s%s%s.jpg" % (parent, fs_bs, "folder"))
      art.append("%s%s%s.png" % (parent, fs_bs, "folder"))
      art.append("%s%s%s.jpg" % (parent, fs_bs, "cover"))
      art.append("%s%s%s.png" % (parent, fs_bs, "cover"))

  return art

def splitModifierToken(field):
  if field and field[:1] in ["?", "#", "!"]:
    m = field[:1]
    return (field[1:], m, (m in ["#", "!"]), (False if (m == "?" or m == "#") else True))
  else:
    return (field, "", False, True)

def missingFiles(mediatype, data, fileList, title_name, id_name, showName=None, season=None):
  gLogger.reset()

  if showName is None:
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

    gLogger.progress("Parsing %s: %s..." % (mediatype.capitalize(), name), every = 25)

    # Remove matched file from fileList - what files remain at the end
    # will be reported to the user
    if mediatype != "tvshows" and "file" in item:
      for file in MyUtility.unstackFiles(item["file"]):
        try:
          fileList.remove(file)
        except ValueError:
          pass

    if "seasons" in item:
      missingFiles("seasons", item["seasons"], fileList, "label", "season", showName=title)
    if "episodes" in item:
      missingFiles("episodes", item["episodes"], fileList, "label", "episodeid", showName=showName, season=title)
      season = None

  if showName is None:
    TOTALS.TimeEnd(mediatype, "Parse")
    gLogger.progress("")
    if fileList != []:
      gLogger.out("The following media files are not present in the \"%s\" media library:\n\n" % mediatype)
      for file in fileList: gLogger.out("%s\n" % file)

def queryLibrary(mediatype, query, data, title_name, id_name, work=None, mitems=None, showName=None, season=None, pvrGroup=None):
  gLogger.reset()

  if mitems is None:
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

    gLogger.progress("Parsing %s: %s..." % (mediatype.capitalize(), name), every = 25)

    RESULTS = []

    try:
      for field, field_split, condition, inverted, value, logic in tuples:
        temp = item
        for f in field_split:
          temp = searchItem(temp, f)
          if temp is None: break

        if temp is not None:
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
      elif logic is None:
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

  if mitems is None:
    TOTALS.TimeEnd(mediatype, "Parse")
    gLogger.progress("")
    for m in mediaitems:
      gLogger.out("Matched: [%-50s] %s" % (addEllipsis(50, m[0]), m[1]), newLine=True)

def addEllipsis(maxlen, aStr):
  if len(aStr) <= maxlen: return aStr

  ileft = int(maxlen/2) - 2
  iright = int(maxlen/2) - 1

  return "%s...%s" % (aStr[0:ileft], aStr[-iright:])

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
    MYLIST.append({"type": m.mtype, "name": m.name, "episode_year": m.episode_year,
                   "playcount": m.playcount, "lastplayed": m.lastplayed, "resume": m.resume})

  try:
    OUTPUTFILE = codecs.open(filename, "wb", encoding="utf-8")
    OUTPUTFILE.write(json.dumps(MYLIST, indent=2, ensure_ascii=True))
    OUTPUTFILE.close()
  except:
    gLogger.out("ERROR: failed to write the watched list to file [%s]" % filename, newLine=True)

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
    gLogger.out("ERROR: failed to read the watched list from file [%s]" % filename, newLine=True)
    return False

  return True

def watchedBackup(mediatype, filename, data, title_name, id_name, work=None, mitems=None, showName=None, season=None):
  gLogger.reset()

  if mitems is None:
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

    gLogger.progress("Parsing %s: %s..." % (mediatype.capitalize(), longName), every = 25)

    playcount = item.get("playcount", 0)
    lastplayed = item.get("lastplayed", "")
    resume = item.get("resume", {"position": 0.0, "total": 0.0})

    if playcount != 0 or lastplayed != "" or resume["position"] != 0.0:
      mediaitems.append(MyWatchedItem(mediatype, shortName, episode_year, playcount, lastplayed, resume))

    if "seasons" in item:
      watchedBackup("seasons", filename, item["seasons"], "label", "season", \
                    work=workItems, mitems=mediaitems, showName=title)
    if "episodes" in item:
      watchedBackup("episodes", filename, item["episodes"], "label", "episodeid", \
                    work=workItems, mitems=mediaitems, showName=showName, season=title)
      season = None

  if mitems is None:
    TOTALS.TimeEnd(mediatype, "Parse")
    gLogger.progress("")
    watchedWrite(filename, mediaitems)

def watchedRestore(mediatype, jcomms, filename, data, title_name, id_name, work=None, mitems=None, showName=None, season=None):
  gLogger.reset()

  if mitems is None:
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

    gLogger.progress("Parsing %s: %s..." % (mediatype.capitalize(), longName), every = 25)

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

  if mitems is None:
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
    gLogger.out("Watched List item summary: restored %d, unchanged %d, unmatched %d, failed %d\n" %
                (RESTORED, UNCHANGED, UNMATCHED, ERROR), newLine=True)

def watchedItemUpdate(jcomms, mediaitem, shortName):
  if mediaitem.mtype == "movies":
    method = "VideoLibrary.SetMovieDetails"
    mediaid = "movieid"
  else:
    method = "VideoLibrary.SetEpisodeDetails"
    mediaid = "episodeid"

  REQUEST = {"method": method,
             "params": {mediaid: mediaitem.libraryid,
                        "playcount": mediaitem.playcount,
                        "lastplayed": mediaitem.lastplayed
                       }}

  if gConfig.JSON_HAS_SETRESUME:
    REQUEST["params"]["resume"] = {"position": mediaitem.resume["position"]}

  gLogger.progress("Restoring %s: %s..." % (mediaitem.mtype[:-1], shortName))

  data = jcomms.sendJSON(REQUEST, "libWatchedList", checkResult=False)

  return ("result" in data and data["result"] == "OK")

def duplicatesList(mediatype, jcomms, data):
  imdblist = []
  dupelist = []

  # Iterate over movies, building up list of IMDb numbers
  # for movies that appear more than once...
  for movie in data:
    imdb = movie["imdbnumber"]
    if imdb:
      if imdb in imdblist:
        if not imdb in dupelist:
          dupelist.append(imdb)
      else:
        imdblist.append(imdb)

  # Iterate over the list of duplicate IMDb numbers,
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
  if mediatype == "movies":
    imdbfields = gConfig.IMDB_FIELDS_MOVIES
  else:
    imdbfields = gConfig.IMDB_FIELDS_TVSHOWS

  plotFull    = ("plot" in imdbfields)
  plotOutline = ("plotoutline" in imdbfields)
  movies250   = None

  if "top250" in imdbfields:
    movies250 = MyUtility.Top250MovieList()
    if movies250 is None:
      gLogger.err("WARNING: failed to obtain Top250 movies, check log for details", newLine=True)

  # Movies and TV shows
  worklist = _ProcessIMDB(mediatype, jcomms, data, plotFull, plotOutline, movies250, imdbfields)

  # Once we have verified TV shows, add the episodes and process them
  if mediatype == "tvshows":
    epsdata = []
    tvhash = {}
    for tvshow in worklist:
      tvhash[tvshow["libraryid"]] = tvshow

    for tvshow in data:
      if tvshow["tvshowid"] not in tvhash: continue
      if "seasons" not in tvshow: continue

      multipart = {}

      for season in tvshow["seasons"]:
        if season["season"] < 1: continue
        if "episodes" not in season: continue

        for episode in season["episodes"]:
          if "title" not in episode:
            episode["title"] = episode["label"]

          episode["imdbnumber"] = tvhash[tvshow["tvshowid"]]["imdbnumber"]

          SxE = re.sub("[0-9]*x([0-9]*)\..*", "\\1", episode["label"])
          if SxE == episode["label"] or int(SxE) < 1: continue

          file = episode.get("file", None)
          if file is not None:
            if file is not None and file in multipart:
              multipart_first = multipart[file]
            else:
              multipart[file] = (season["season"], int(SxE))
              multipart_first = None
          else:
            multipart_first = None

          epsdata.append({"ShowTitle": tvshow["title"],
                          "ShowYear":  tvshow["year"],
                          "OriginalShowTitle": tvshow["tc.title"],
                          "Season":    season["season"],
                          "Episode":   int(SxE),
                          "multipart_ep": multipart_first,
                          "item":      episode})

    # Add episodes requiring updates to the existing list of work items
    worklist.extend(_ProcessIMDB("episodes", jcomms, epsdata, plotFull, plotOutline, movies250, imdbfields))

  # Remove year fields from worklist, as they're not required
  # Remove anything without items
  for w in worklist:
    if "year" in w: del w["year"]

  # Create a new list without any workitems that have no work to perform (ie. items=={})
  newlist = [x for x in worklist if x["items"]]

  # Sort the list of items into title order, with libraryid to ensure consistency
  # when two or more movies share the same title.
  newlist.sort(key=lambda f: (f["title"], f.get("episodetitle", ""), f["libraryid"]))

  jcomms.dumpJSON(newlist, decode=True, ensure_ascii=True)

def _ProcessIMDB(mediatype, jcomms, data, plotFull, plotOutline, movies250, imdbfields):
  worklist = []
  input_queue = Queue.Queue()
  output_queue = Queue.Queue()

  # Load input queue
  # For tvshows, we need to perform some extra processing on the title and year of each show
  # so that it matches the title/year on OMDb
  if mediatype == "movies":
    for movie in data:
      input_queue.put({"item": movie})
  elif mediatype == "tvshows":
    re_ignore_titles = []
    re_map_titles = []
    re_trans_titles = []
    re_trans_years = []
    re_parenthesis = re.compile("\([a-zA-Z]*\)$")

    for ft in gConfig.IMDB_IGNORE_TVTITLES:
      re_ignore_titles.append(re.compile(ft, re.IGNORECASE))

    for ft in gConfig.IMDB_MAP_TVTITLES:
      ftsplit = ft.split("=")
      if len(ftsplit) == 2:
        re_map_titles.append((re.compile(ftsplit[0], re.IGNORECASE), ftsplit[1]))

    for ft in gConfig.IMDB_TRANSLATE_TVTITLES:
      ftsplit = ft.split("=")
      if len(ftsplit) == 2:
        re_trans_titles.append((re.compile(ftsplit[0], re.IGNORECASE), ftsplit[1]))

    for ft in gConfig.IMDB_TRANSLATE_TVYEARS:
      ftsplit = ft.split("=")
      if len(ftsplit) == 2 and ftsplit[1]:
        re_trans_years.append((re.compile(ftsplit[0], re.IGNORECASE), int(ftsplit[1])))

    for tvshow in data:
      ignoreShow = False
      tvshow["tc.title"] = tvshow["title"]
      tvshow["tc.year"] = tvshow["year"]

      for ignore in re_ignore_titles:
        if ignore.search(tvshow["title"]):
          gLogger.log("Pre-processing #1 OMDb: Title: [%s] ignoring TV show - matched [%s] in imdb.ignore.tvtitles" % (tvshow["title"], ignore.pattern))
          ignoreShow = True
          break

      if not ignoreShow:
        # Map to imdbnumber?
        for trans in re_map_titles:
          if trans[0].search(tvshow["title"]):
            gLogger.log("Pre-processing #2 OMDb: Title: [%s] mapped to imdbnumber for pattern [%s], assigning [%s]" % (tvshow["title"], trans[0].pattern, trans[1]))
            tvshow["imdbnumber"] = trans[1]
            break

        # If we've got an imdbnumber don't bother with remaining translations
        if "imdbnumber" in tvshow:
          input_queue.put({"OriginalShowTitle": tvshow["tc.title"], "item": tvshow})
          continue

        # Translate year
        for trans in re_trans_years:
          if trans[0].search(tvshow["title"]):
            gLogger.log("Pre-processing #2 OMDb: Title: [%s] translating TV show year for pattern [%s], replacing [%d] with [%d]" % (tvshow["title"], trans[0].pattern, tvshow["year"], trans[1]))
            tvshow["year"] = trans[1]

        # Translate title
        for trans in re_trans_titles:
          if trans[0].search(tvshow["title"]):
            before_title = tvshow["title"]
            tvshow["title"] = trans[0].sub(trans[1], tvshow["title"]).strip()
            gLogger.log("Pre-processing #3 OMDb: Title: [%s] translating TV show title for pattern [%s], replacing with [%s], giving [%s]" % (before_title, trans[0].pattern, trans[1], tvshow["title"]))

        # Remove original year from end of title
        if tvshow["tc.year"] is not None and tvshow["title"].endswith("(%d)" % tvshow["tc.year"]):
          before_title = tvshow["title"]
          tvshow["title"] = re.sub("\(%d\)$" % tvshow["tc.year"], "", tvshow["title"]).strip()
          gLogger.log("Pre-processing #4 OMDb: Title: [%s] removing year from title, giving [%s]" % (before_title, tvshow["title"]))

        # Remove trailing parenthesis (...) from end of title - most likely to be a country code
        if gConfig.IMDB_DEL_PARENTHESIS:
          re_find = re_parenthesis.search(tvshow["title"])
          if re_find:
            before_title = tvshow["title"]
            tvshow["title"] = tvshow["title"][:re_find.start() - 1].strip()
            gLogger.log("Pre-processing #5 OMDb: Title: [%s] removing trailing parenthesis from title, giving [%s]" % (before_title, tvshow["title"]))

        input_queue.put({"OriginalShowTitle": tvshow["tc.title"], "item": tvshow})

  elif mediatype == "episodes":
    for episode in data:
      input_queue.put(episode)

  if input_queue.qsize() == 0:
    return worklist

  # Create threads to process input queue
  threadcount = input_queue.qsize() if input_queue.qsize() <= gConfig.IMDB_THREADS else gConfig.IMDB_THREADS
  threads = []
  for i in range(threadcount):
    t = MyIMDBLoader(gConfig, gLogger, input_queue, output_queue, plotFull, plotOutline, movies250, imdbfields)
    threads.append(t)
    t.setDaemon(True)

  # Start the threads...
  for t in threads: t.start()

  # Process results from output queue
  # An empty qItem signifies end of thread
  # Once all threads have ended, exit loop
  while threadcount > 0:
    qItem = output_queue.get(block=True)
    output_queue.task_done()

    if qItem is None:
      threadcount -= 1
      continue

    item = qItem["item"]
    if "OriginalShowTitle" in qItem:
      title = qItem["OriginalShowTitle"]
    else:
      title = item["title"]

    imdbnumber = item.get("imdbnumber", "")
    year = item.get("year", None)

    if "episodeid" in item:
      infotitle = "%s S%02dE%02d" % (title, qItem["Season"], qItem["Episode"])
    else:
      infotitle = title

    gLogger.progress("Processing IMDb: %s..." % infotitle)

    newimdb = qItem["newimdb"]

    if mediatype == "movies":
      libid = item["movieid"]
    elif mediatype == "tvshows":
      libid = item["tvshowid"]
      imdbnumber = newimdb.get("id", "")
    elif mediatype == "episodes":
      libid = item["episodeid"]
      imdbnumber = newimdb.get("id", "")

    # Truncate rating to 1 decimal place
    # Keep existing value if difference is likely to be due to platform
    # precision error ie. Python2 on OpenELEC where 6.6 => 6.5999999999999996.
    if "rating" in imdbfields and newimdb.get("rating",None) is not None:
      item["rating"] = float("%.1f" % item.get("rating", 0.0))
      newimdb["rating"] = float("%.1f" % newimdb.get("rating", 0.0))
      if abs(item["rating"] - newimdb["rating"]) < 0.01:
        newimdb["rating"] = item["rating"]

    # Sort genre lists for comparison purposes
    if "genre" in imdbfields and "genre" in newimdb:
      item["genre"] = sorted(item.get("genre", []))
      newimdb["genre"] = sorted(newimdb.get("genre", []))

    olditems = {"items": {}}
    workitem = {"type": mediatype[:-1],
                "libraryid": libid,
                "imdbnumber": imdbnumber,
                "title": title,
                "items": {}}

    if year is not None:
      workitem["year"] = year,

    if mediatype == "episodes":
      workitem["episodetitle"] = item["title"]

    for field in imdbfields:
      # Don't attempt to change title of tvshows
      if mediatype == "tvshows" and field in ["title"]: continue

      # Don't attempt to set genre for episodes - only works at the tvshow level
      if mediatype == "episodes" and field in ["genre"]: continue

      # Don't overwrite a movie rating if the movie already has a rating (eg. foreign movie with manually assigned rating)
      if mediatype == "movies" and field == "mpaa":
        if item.get(field, None) not in ["Rated Not Rated", "Not Rated", "Rated Unrated", "Unrated", "NR", "null"]: continue

      if field in newimdb:
        if field not in item or item[field] != newimdb[field] and newimdb[field] is not None:
          workitem["items"][field] = newimdb[field]
          olditems["items"][field] = item.get(field, None)

    # Always append tvshows - we use this to validate the show when deciding to process episodes.
    # TVshows without any changes will be dropped at the end.
    if workitem["items"] or mediatype == "tvshows":
      worklist.append(workitem)
      if gLogger.LOGGING:
        with lock: # Grab threading lock to prevent threads intermingling their output with our main thread
          gLogger.log("Workitem for id: %d, type: %s, title: %s" %
                      (workitem["libraryid"], workitem["type"], infotitle))
          gLogger.log("  Old items: %s" % olditems["items"])
          gLogger.log("  New items: %s" % workitem["items"])

  gLogger.progress("")

  return worklist

def getIntFloatStr(aField, aValue):
  # Some fields can only be strings...
  if aField in ["title", "plot", "plotoutline", "votes", "studio", "description",
                "artist", "album", "albumartist", "theme", "mood", "style", "comment",
                "lyrics", "director", "tagline", "originaltitle", "writer", "mpaa",
                "country", "imdbnumber", "set", "showtitle", "tag", "sorttitle",
                "premiered", "dateadded", "lastplayed"]:
    if (aValue.startswith('"') and aValue.endswith('"')) or \
       (aValue.startswith("'") and aValue.endswith("'")):
      return aValue[1:-1]
    else:
      return "%s" % aValue

  # For everything else, try to work out the data type from the value
  isString = (type(aValue) == str if MyUtility.isPython3 else type(aValue) in [str, unicode])
  if isString:
    if (aValue.startswith('"') and aValue.endswith('"')) or \
       (aValue.startswith("'") and aValue.endswith("'")):
      return aValue[1:-1]

    if aValue == "null":
      return None

  try:
    if int(aValue) == float(aValue):
      return int(aValue)
  except:
    pass

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
    setDetails_worker(jcomms, item["type"], item["libraryid"], kvpairs, item.get("title", None), dryRun, i, len(jdata), typeconversion=False)

  gLogger.progress("")

def setDetails_single(mtype, libraryid, kvpairs, dryRun=True):
  # Fix Unicode backslash mangling from the command line...
  ukvpairs = []
  for kv in kvpairs:
    ukvpairs.append(MyUtility.toUnicode(kv).replace("\\n","\n"))

  jcomms = MyJSONComms(gConfig, gLogger) if not dryRun else None
  setDetails_worker(jcomms, mtype, libraryid, ukvpairs, None, dryRun, None, None, typeconversion=True)
  gLogger.progress("")

def setDetails_worker(jcomms, mtype, libraryid, kvpairs, title, dryRun, itemnum, maxitems, typeconversion):
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
      if pair is None:
        pairs[KEY] = None
      elif type(pair) is list:
        pairs[KEY] = []
        for item in pair:
          if item: pairs[KEY].append(getIntFloatStr(KEY, item) if typeconversion else item)
      elif (isinstance(pair, basestring)) and pair.startswith("[") and pair.endswith("]"):
        pairs[KEY] = []
        for item in [x.strip() for x in pair[1:-1].split(",")]:
          if item: pairs[KEY].append(getIntFloatStr(KEY, item) if typeconversion else item)
      else:
        pairs[KEY] = getIntFloatStr(KEY, pair) if typeconversion else pair

      if (pairs[KEY] is None or pairs[KEY] == "") and \
         (KEY.startswith("art.") or KEY in ["fanart", "thumbnail", "thumb"]) and \
         not gConfig.JSON_HAS_SETNULL:
        value = "null" if pairs[KEY] is None else "\"%s\"" % pairs[KEY]
        gLogger.out("WARNING: cannot set null/empty string value on field with " \
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
        if pairs[pair] is None or pairs[pair] == "":
          R[field] = None
        else:
          R[field] = pairs[pair]
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
    SQL = []

    ESCAPE_CHAR = "`" if not database.usejson else ""
    ESCAPE = " ESCAPE '%s'" % ESCAPE_CHAR if ESCAPE_CHAR else ""

    if search != "":
      SQL.append("WHERE t.url LIKE '%%%s%%' ORDER BY t.cachedurl ASC" % search.replace("'","''"))

      # Aide-memoire: Why we have to do the following nonsense: http://trac.kodi.tv/ticket/14905
      if gConfig.SEARCH_ENCODE:
        search2 = urllib2.quote(search, "()")
        if search2 != search:
          if ESCAPE_CHAR:
            search2 = search2.replace("%", "%s%%" % ESCAPE_CHAR)
          SQL.append("WHERE t.url LIKE '%%%s%%'%s ORDER BY t.cachedurl ASC" % (search2, ESCAPE))
    elif filter != "":
      SQL.append("%s " % filter)

    FSIZE = 0
    FCOUNT = 0
    ROWS = []

    gLogger.progress("Loading database items...")
    dbrows = []

    if SQL:
      for sql in SQL:
        rows = database.getRows(filter=sql, allfields=True)
        gLogger.log("EXECUTED SQL: queried %d rows" % len(rows))
        dbrows.extend(rows)
    else:
      rows = database.getRows(allfields=True)
      gLogger.log("EXECUTED SQL: queried %d rows" % len(rows))
      dbrows.extend(rows)

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
          elif os.path.getsize(gConfig.getFilePath(row["cachedurl"])) == 0:
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
      for row in ROWS:
        database.dumpRow(row)

    if ACTION == "STATS":
      gLogger.out("\nFile Summary: %s files; Total size: %s KB\n\n" % (format(FCOUNT, ",d"), format(int(FSIZE/1024), ",d")))

    if (search != "" or filter != "") and not delete and not silent:
      gLogger.progress("Matching row ids: %s\n" % " ".join("%d" % r["textureid"] for r in ROWS))

# Delete row by id, and corresponding file item
def sqlDelete(ids=[]):
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

      # If it's a DDS file, it should be associated with another
      # file with the same hash, but different extension. Find
      # this other file in the ddsmap - if it's there, ignore
      # the DDS file, otherwise leave the DDS file to be reported
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
    gLogger.out("Orphaned file found: name [%s], created [%s], size [%s]%s\n" % \
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

  localfiles = []

  (libraryFiles, mediaFiles) = getAllFiles(keyFunction=getKeyFromFilename)

  re_search = []
  # addons
  re_search.append(re.compile(r"^.*[/\\]\.kodi[/\\]addons[/\\].*"))
  re_search.append(re.compile(r"^.*[/\\]\.xbmc[/\\]addons[/\\].*"))
  # mirrors
  re_search.append(re.compile(r"^http://mirrors.kodi.tv/addons/.*"))
  re_search.append(re.compile(r"^http://mirrors.xbmc.org/addons/.*"))

  database = MyDB(gConfig, gLogger)

  if gConfig.CHUNKED:
    pruneCache_chunked(database, libraryFiles, mediaFiles, localfiles, re_search)
  else:
    pruneCache_fast(database, libraryFiles, mediaFiles, localfiles, re_search)

  # Prune, with optional remove...
  if localfiles != []:
    if remove_nonlibrary_artwork:
      gLogger.out("Pruning cached images from texture cache...", newLine=True)
    else:
      gLogger.out("The following items are present in the texture cache but not the media library:", newLine=True)
    gLogger.out("", newLine=True)

  FSIZE = 0
  GOTSIZE = gConfig.HAS_THUMBNAILS_FS
  localfiles.sort(key=lambda row: row["url"])

  with database:
    for row in localfiles:
      database.dumpRow(row)
      if GOTSIZE and os.path.exists(gConfig.getFilePath(row["cachedurl"])):
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


def pruneCache_fast(database, libraryFiles, mediaFiles, localfiles, re_search):
  gLogger.progress("Loading texture cache...")

  dbfiles = {}

  with database:
    for r in database.getRows(allfields=True):
      dbfiles[r["cachedurl"]] = r

  totalrows = len(dbfiles)

  gLogger.log("Loaded %d rows from texture cache" % totalrows)

  gLogger.progress("Processing texture cache...")

  for rownum, hash in enumerate(dbfiles):
    gLogger.progress("Processing texture cache... %d%%" % (100 * rownum / totalrows), every=25)
    pruneCache_processrow(dbfiles[hash], libraryFiles, mediaFiles, localfiles, re_search)

  gLogger.progress("")

def pruneCache_chunked(database, libraryFiles, mediaFiles, localfiles, re_search):
  gLogger.progress("Loading Textures DB items...")

  with database:
    folders = database.getTextureFolders()

    for fnum, folder in enumerate(folders):
      gLogger.progress("Loading Textures DB: chunk %2d of %d..." % (fnum+1, len(folders)))

      dbfiles = []
      dbrows = database.getRows(database.getTextureFolderFilter(folder), allfields=True)

      i = 0
      j = len(dbrows)

      for dbrow in dbrows:
        i += 1

        gLogger.progress("Processing artwork: chunk %2d of %d (%d%%)" %
          (fnum+1, len(folders), (100 * i / j)), every=25, finalItem=(i == j))

        pruneCache_processrow(dbrow, libraryFiles, mediaFiles, localfiles, re_search)

  gLogger.progress("")

def pruneCache_processrow(row, libraryFiles, mediaFiles, localfiles, re_search):

  URL = row["url"]
  isRetained = False

  if gConfig.PRUNE_RETAIN_TYPES:
    for retain in gConfig.PRUNE_RETAIN_TYPES:
      if retain.search(URL):
        gLogger.log("Retained image due to rule [%s]" % retain.pattern)
        isRetained = True
        break
    if isRetained: return

  if URL in libraryFiles:
    del libraryFiles[URL]
    return

  if gConfig.PRUNE_RETAIN_CHAPTERS and URL.startswith("chapter://"):
    if getMediaForChapter(URL) in mediaFiles:
      return

  if re_search:
    # Ignore add-on/mirror related images
    for r in re_search:
      if r.search(URL):
        isRetained = True
        break

  # Not an addon or mirror...
  if not isRetained:
    localfiles.append(row)

def getMediaForChapter(filename):
  offset = 1
  while offset < len(filename):
    if filename[-offset] in ["/", "\\"]: break
    offset += 1
  return filename[10:-offset]

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
# doesn't work well with Unicode strings (returns wrong hash).
# Fortunately, using the encoded URL/filename as the key (next
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

  afiles = {}
  mfiles = {}
  UCAST = {}

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
                         "properties":["title", "cast", "art", "file"]}},

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

    gLogger.progress("Loading %s..." % mediatype)
    data = jcomms.getDataProxy(mediatype, r, uniquecast=UCAST)

    for items in data.get("result", {}):
      if items != "limits":
        if mediatype in ["MovieSets","Addons","Genres"]:
          interval = 0
        else:
          interval = int(int(data["result"]["limits"]["total"])/10)
          interval = 50 if interval > 50 else interval
        title = ""
        for i in data["result"][items]:
          title = i.get("title", i.get("artist", i.get("name", None)))
          gLogger.progress("Loading %s: %s..." % (mediatype, title), every=interval)
          if "fanart" in i: afiles[keyFunction(i["fanart"])] = "fanart"
          if "thumbnail" in i: afiles[keyFunction(i["thumbnail"])] = "thumbnail"

          for a in i.get("art", {}):
            afiles[keyFunction(i["art"][a])] = a

          for c in i.get("cast", []):
            if "thumbnail" in c:
              afiles[keyFunction(c["thumbnail"])] = "cast.thumb"

          if mediatype in ["Artists", "Albums", "Movies"]:
            for file in jcomms.getExtraArt(i):
              afiles[keyFunction(file["file"])] = file["type"]

          if "file" in i: mfiles[i["file"]] = "media"

        if title != "": gLogger.progress("Parsing %s: %s..." % (mediatype, title))

    # Free memory used to cache any GetDirectory() information
    MyUtility.invalidateDirectoryCache(mediatype)

  gLogger.progress("Loading TV shows...")

  REQUEST = {"method":"VideoLibrary.GetTVShows",
             "params": {"sort": {"order": "ascending", "method": "title"},
                        "properties":["title", "cast", "art"]}}

  if gConfig.CACHE_EXTRA:
    jcomms.addProperties(REQUEST, "file")

  tvdata = jcomms.getDataProxy("tvshows", REQUEST, uniquecast=UCAST)

  if "result" in tvdata and "tvshows" in tvdata["result"]:
    for tvshow in tvdata["result"]["tvshows"]:
      gLogger.progress("Loading TV show: %s..." % tvshow["title"])
      tvshowid = tvshow["tvshowid"]

      for a in tvshow.get("art", {}):
        afiles[keyFunction(tvshow["art"][a])] = a

      for c in tvshow.get("cast", []):
        if "thumbnail" in c:
          afiles[keyFunction(c["thumbnail"])] = "cast.thumb"

      for file in jcomms.getExtraArt(tvshow):
        afiles[keyFunction(file["file"])] = file["type"]

      REQUEST = {"method":"VideoLibrary.GetSeasons",
                 "params":{"tvshowid": tvshowid,
                           "sort": {"order": "ascending", "method": "season"},
                           "properties":["season", "art"]}}

      seasondata = jcomms.getDataProxy("seasons", REQUEST, uniquecast=UCAST)

      if "seasons" in seasondata["result"]:
        SEASON_ALL = True
        for season in seasondata["result"]["seasons"]:
          seasonid = season["season"]
          if seasonid < 0:
            gLogger.err("WARNING: TV show [%s] has invalid season (%d) - ignored" % (tvshow["title"], seasonid), newLine=True)
            continue

          gLogger.progress("Loading TV show: %s, season %d..." % (tvshow["title"], seasonid))

          for a in season.get("art", {}):
            if SEASON_ALL and a in ["poster", "tvshow.poster", "tvshow.fanart", "tvshow.banner"]:
              SEASON_ALL = False
              (poster_url, fanart_url, banner_url) = jcomms.getSeasonAll(season["art"][a])
              if poster_url: afiles[keyFunction(poster_url)] = "poster"
              if fanart_url: afiles[keyFunction(fanart_url)] = "fanart"
              if banner_url: afiles[keyFunction(banner_url)] = "banner"
            afiles[keyFunction(season["art"][a])] = a

          REQUEST = {"method":"VideoLibrary.GetEpisodes",
                     "params":{"tvshowid": tvshowid, "season": seasonid,
                               "properties":["cast", "art", "file"]}}

          episodedata = jcomms.getDataProxy("episodes", REQUEST, uniquecast=UCAST)
          if "episodes" not in episodedata["result"]:
            continue # ignore seasons without episodes

          for episode in episodedata["result"]["episodes"]:
            episodeid = episode["episodeid"]

            mfiles[episode["file"]] = "media"

            for a in episode.get("art", {}):
              afiles[keyFunction(episode["art"][a])] = a

            for c in episode.get("cast", []):
              if "thumbnail" in c:
                afiles[keyFunction(c["thumbnail"])] = "cast.thumb"

      # Free memory used to cache any GetDirectory() information
      MyUtility.invalidateDirectoryCache("TVShows")

  # Pictures
  gLogger.progress("Loading Pictures...")
  pictures = jcomms.getPictures(addPreviews=gConfig.PRUNE_RETAIN_PREVIEWS, addPictures=gConfig.PRUNE_RETAIN_PICTURES)
  for picture in pictures:
    afiles[keyFunction(picture["thumbnail"])] = "thumbnail"
  del pictures
  # Free memory used to cache any GetDirectory() information
  MyUtility.invalidateDirectoryCache("Pictures")

  # PVR Channels
  if gConfig.HAS_PVR:
    gLogger.progress("Loading PVR channels...")
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
              afiles[keyFunction(channel["thumbnail"])] = "pvr.thumb"

    # Free memory used to cache any GetDirectory() information
    MyUtility.invalidateDirectoryCache("PVR")

  return (afiles, mfiles)

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
    gLogger.out("ERROR: does not exist - media type [%s] libraryid [%d]" % (mtype, libraryid), newLine=True)

# Remove artwork URLs containing specified patterns, with or without lasthaschcheck
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

    for items in data.get("result", {}):
      if items != "limits":
        if mediatype == "set":
          interval = 0
        else:
          interval = int(int(data["result"]["limits"]["total"])/10)
          interval = 50 if interval > 50 else interval
        title = ""
        for i in data["result"][items]:
          title = i.get("title", i.get("artist", i.get("name", None)))
          gLogger.progress("Parsing %s: %s..." % (mediatype, title), every=interval)
          addItems(i, mtype, idname)
        if title != "": gLogger.progress("Parsing %s: %s..." % (mediatype, title))

  gLogger.progress("Loading TV shows...")

  REQUEST = {"method":"VideoLibrary.GetTVShows",
             "params": {"sort": {"order": "ascending", "method": "title"},
                        "properties":["title", "art"]}}

  tvdata = jcomms.sendJSON(REQUEST, "libTV")

  if "result" in tvdata and "tvshows" in tvdata["result"]:
    for tvshow in tvdata["result"]["tvshows"]:
      gLogger.progress("Loading TV show: %s..." % tvshow["title"])

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
          if seasonid < 0:
            gLogger.err("WARNING: TV show [%s] has invalid season (%d) - ignored" % (tvshow["title"], seasonid), newLine=True)
            continue

          gLogger.progress("Loading TV show: [%s, season %d]..." % (tvshow["title"], seasonid))

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

def getDirectory(path, recurse=False):
  getDirectoryFiles(MyJSONComms(gConfig, gLogger), path, nodirmsg=True, recurse=recurse)

def getDirectoryFiles(jcomms, path, nodirmsg=True, recurse=False):
  data = jcomms.getDirectoryList(path, use_cache=False)

  # Invalid path
  if "result" not in data:
    if nodirmsg:
      gLogger.out("Directory \"%s\" not found." % path, newLine=True)
    return

  # Empty path
  if "files" not in data["result"]:
    if nodirmsg:
      gLogger.out("Directory \"%s\" is empty." % path, newLine=True)
    return

  for file in sorted(data["result"]["files"], key=(lambda x: x["file"]), reverse=False):
    if "file" in file:
      ftype = file["filetype"]
      fname = file["file"]

      if ftype == "directory":
        FTYPE = "DIR"
        FNAME = os.path.dirname(fname)
      else:
        FTYPE = "FILE"
        FNAME = fname

      gLogger.out("%-4s: %s" % (FTYPE, FNAME), newLine=True)
      if recurse and FTYPE == "DIR":
        getDirectoryFiles(jcomms, FNAME, nodirmsg=False, recurse=recurse)

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

  if gConfig.JSON_HAS_PROFILE_SUPPORT:
    STATUS.append("Current Profile: %s" % gConfig.CURRENT_PROFILE["label"])

  REQUEST = {"method": "XBMC.GetInfoBooleans",
             "params": {"booleans": ["System.ScreenSaverActive", "Library.IsScanningMusic", "Library.IsScanningVideo", "System.HasShutdown", "System.CanSuspend"]}}
  data = jcomms.sendJSON(REQUEST, "libSSaver")
  if "result" in data:
    STATUS.append("Scanning Music: %s" % ("Yes" if data["result"].get("Library.IsScanningMusic", False) else "No"))
    STATUS.append("Scanning Video: %s" % ("Yes" if data["result"].get("Library.IsScanningVideo", False) else "No"))
    STATUS.append("ScreenSaver Active: %s" % ("Yes" if data["result"].get("System.ScreenSaverActive", False) else "No"))
    STATUS.append("Suspend Supported: %s" % ("Yes" if data["result"].get("System.CanSuspend", False) else "No"))
    STATUS.append("Idle Timer Enabled: %s" % ("Yes" if data["result"].get("System.HasShutdown", False) else "No"))

  property = "System.IdleTime(%s) " % idleTime
  REQUEST = {"method": "XBMC.GetInfoBooleans", "params": {"booleans": [property]}}
  data = jcomms.sendJSON(REQUEST, "libIdleTime")
  if "result" in data:
    STATUS.append("System Idle > %ss: %s" % (idleTime, ("Yes" if data["result"].get(property, False) else "No")))

  STATUS.append("PVR Enabled: %s" % ("Yes" if gConfig.HAS_PVR else "No"))

  REQUEST = {"method":"Player.GetActivePlayers"}
  data = jcomms.sendJSON(REQUEST, "libGetPlayers")
  if "result" in data:
    if data["result"] == []:
      STATUS.append("Player: None")
    else:
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

            if libraryId is None and "label" in item:
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

            REQUEST = {"method": "Player.GetProperties", "params": {"playerid": pId, "properties": ["percentage", "time", "totaltime", "speed"]}}
            data = jcomms.sendJSON(REQUEST, "libGetProps", checkResult=False)
            if "result" in data:
              eTime = getSeconds(data["result"].get("time",0))
              tTime = getSeconds(data["result"].get("totaltime",0))
              elapsed = getHMS(eTime)
              pcnt = data["result"].get("percentage", 0)
              remaining = getHMS(tTime - eTime)
              if data["result"].get("speed",0) == 0:
                STATUS.append("Progress: %s (%4.2f%%, %s remaining, paused)" % (elapsed, pcnt, remaining))
              elif data["result"].get("speed",0) != 1:
                STATUS.append("Progress: %s (%4.2f%%, %s remaining, seeking)" % (elapsed, pcnt, remaining))
              else:
                STATUS.append("Progress: %s (%4.2f%%, %s remaining)" % (elapsed, pcnt, remaining))

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

  RETRIES = gConfig.RPC_RETRY
  ATTEMPTS = 0

  cmdqueue = Queue.Queue()
  hdmimgr = MyHDMIManager(gConfig, gLogger, cmdqueue, hdmidelay=delay)
  hdmimgr.setDaemon(True)
  hdmimgr.start()

  gLogger.debug("Connecting to Kodi on %s..." % gConfig.KODI_HOST)
  while True:
    try:
      MyJSONComms(gConfig, gLogger).sendJSON({"method": "JSONRPC.Ping"}, "libListen", callback=rbphdmi_listen, checkResult=False)
      if RETRIES != 0:
        gLogger.debug("Kodi exited - waiting for restart...")
        time.sleep(15.0)
        ATTEMPTS = 0
      else:
        gLogger.debug("Kodi exited")
        break
    except socket.error as e:
      gLogger.debug("Kodi not responding, retries remaining %d" % (RETRIES - ATTEMPTS))
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

  if gConfig.JSON_HAS_PROFILE_SUPPORT:
    gLogger.out("%-11s: %s" % ("Profile", gConfig.CURRENT_PROFILE["label"]), newLine=True)

  for m in METHODS:
    media = re.search(".*Get(.*)", m).group(1)
    if not lmedia_list or media.lower() in lmedia_list:
      REQUEST = {"method": m, "params": {"limits": {"start": 0, "end": 1}}}
      if media == "Artists": REQUEST["params"]["albumartistsonly"] = False
      data = jcomms.sendJSON(REQUEST, "libStats")
      if "result" in data and "limits" in data["result"]:
        gLogger.out("%-11s: %d" % (media, data["result"]["limits"]["total"]), newLine=True)

def ProcessInput(args):
  ACTIONS = ["Back", "ContextMenu", "Down",
             "ExecuteAction", "Home", "Info",
             "Left", "Right", "Select",
             "SendText", "ShowOSD",
             "Up", "Pause"]

  if not gConfig.JSON_CODEC_INFO_REMOVED:
    ACTIONS.append("ShowCodec")

  if gConfig.JSON_PLAYER_PROCESS_INFO:
    ACTIONS.append("ShowPlayerProcessInfo")

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

def StressTest(viewtype, numitems, pause, repeat, cooldown):
  MOVES = numitems - 1

  COMMANDS = "executeaction firstpage pause 1.5 "
  if viewtype == "thumbnail":
    TOTAL_ROWS = int(MOVES/gConfig.POSTER_WIDTH)
    LAST_COLS = MOVES % gConfig.POSTER_WIDTH
    d=""
    if TOTAL_ROWS > 0:
      for i in range(0, TOTAL_ROWS):
        d = "left" if d == "right" else "right"
        COMMANDS = "%s%s" % (COMMANDS, st_move_horizontal(d, (gConfig.POSTER_WIDTH - 1), pause))
        if i < TOTAL_ROWS or LAST_COLS >= 0:
          COMMANDS = "%s%s" % (COMMANDS, st_move_down(pause))

    if LAST_COLS > 0:
      d = "left" if d == "right" else "right"
      COMMANDS = "%s%s" % (COMMANDS, st_move_horizontal(d, LAST_COLS, pause))
  elif viewtype in ["listright", "horizontal"]:
    COMMANDS = "%s%s" % (COMMANDS, st_list_move("right", MOVES, pause))
  elif viewtype in ["listdown", "vertical"]:
    COMMANDS = "%s%s" % (COMMANDS, st_list_move("down", MOVES, pause))
  else:
    gLogger.err("%s is not a valid viewtype for stress-test" % viewtype, newLine=True)
    sys.exit(2)

  command_list = COMMANDS.strip().split(" ")
  for i in range(0, repeat):
    start_time = time.time()
    gLogger.out("Loop %4d of %d, %s over %d GUI items with %s second pause..." % (i+1, repeat, viewtype, numitems, pause), padspaces=False)
    ProcessInput(command_list)
    gLogger.out(" %d seconds" % (time.time() - start_time), newLine=True)
    if cooldown > 0:
      gLogger.out("Cooldown period: %s seconds..." % cooldown, padspaces=False)
      time.sleep(cooldown)
      gLogger.out(" complete", newLine=True)

def st_move_horizontal(direction, count, pause):
  cmd = ""
  for i in range(0, count):
    cmd = "%s%s pause %s " % (cmd, direction, pause)
  return cmd

def st_move_right(count, pause):
  return "right pause %s " % pause if count == 1 else st_move_horizontal("right", count, pause)

def st_move_left(count, pause):
  return st_move_horizontal("left", count, pause)

def st_move_down(pause):
  return "down pause %s " % pause

def st_list_move(direction, count, pause):
  cmd = ""
  if count > 0:
    for i in range(0, count):
      cmd = "%s%s" % (cmd, st_move_down(pause) if direction == "down" else st_move_right(1, pause))
  return cmd

def showVolume():
  REQUEST = {"method": "Application.GetProperties", "params": {"properties": ["volume", "muted"]}}

  data = MyJSONComms(gConfig, gLogger).sendJSON(REQUEST, "libVolume")

  if "result" in data:
    mute = "muted" if data["result"]["muted"] else "unmuted"
    gLogger.out("%s %d" % (mute, data["result"]["volume"]), newLine=True)

def setVolume(volume):
  if volume == "mute":
    REQUEST = {"method": "Application.SetMute", "params": {"mute": True}}
  elif volume == "unmute":
    REQUEST = {"method": "Application.SetMute", "params": {"mute": False}}
  else:
    try:
      REQUEST = {"method": "Application.SetVolume", "params": {"volume": int(volume)}}
    except:
      gLogger.err("ERROR: volume level [%s] is not a valid integer" % volume, newLine=True)
      return

  data = MyJSONComms(gConfig, gLogger).sendJSON(REQUEST, "libVolume", checkResult=False)
  if "result" not in data:
    gLogger.err("ERROR: volume change failed - valid values: 0-100, mute and unmute", newLine=True)

def readFile(infile, outfile):
  jcomms = MyJSONComms(gConfig, gLogger)

  url = jcomms.getDownloadURL(infile)
  if url:
    try:
      PAYLOAD = jcomms.sendWeb("GET", url, "readFile", rawData=True)
      if outfile == "-":
        os.write(sys.stdout.fileno(), PAYLOAD)
        sys.stdout.flush()
      else:
        f = open(outfile, "wb")
        f.write(PAYLOAD)
        f.flush()
        f.close()
    except httplib.HTTPException as e:
      gLogger.err("ERROR not authorised access to file: %s" % infile, newLine=True)
      sys.exit(2)
    except Exception as e:
      gLogger.err("ERROR while creating output file: %s" % str(e), newLine=True)
      sys.exit(2)
  else:
    gLogger.err("ERROR file does not exist: %s" % infile, newLine=True)
    sys.exit(2)

  return

def ShowGUINotification(title, message, displaytime, image):
  REQUEST = {"method": "GUI.ShowNotification",
             "params": {"title": title, "message": message}}

  if displaytime:
    REQUEST["params"]["displaytime"] = displaytime
  if image:
    REQUEST["params"]["image"] = image

  MyJSONComms(gConfig, gLogger).sendJSON(REQUEST, "libNotification")

def setSettingVariable(name, value):
  REQUEST = {"method": "Settings.SetSettingValue", "params": {"setting":name, "value": value}}
  MyJSONComms(gConfig, gLogger).sendJSON(REQUEST, "libSetSetting", checkResult=True)

def getSettingVariable(name):
  REQUEST = {"method": "Settings.GetSettingValue", "params": {"setting": name}}
  data = MyJSONComms(gConfig, gLogger).sendJSON(REQUEST, "libGetSetting", checkResult=True)
  return data["result"]["value"]

def WriteSetting(name, rawvalue):
  try:
    value = eval(rawvalue)
  except:
    value = rawvalue
  setSettingVariable(name, value)

def ReadSetting(name):
  try:
    gLogger.out("%s: %s" % (name, getSettingVariable(name)), newLine=True)
  except:
    pass

def ReadSettings(pattern=None):
  REQUEST = {"method": "Settings.GetSettings", "params": {"level": "expert"}}
  data = MyJSONComms(gConfig, gLogger).sendJSON(REQUEST, "libSettings", checkResult=True)
  if pattern:
    newdata = []
    for item in data["result"]["settings"]:
      if item["id"].find(pattern) != -1:
        newdata.append(item)
    gLogger.out(json.dumps(newdata, indent=2, ensure_ascii=True, sort_keys=True), newLine=True)
  else:
    gLogger.out(json.dumps(data["result"]["settings"], indent=2, ensure_ascii=True, sort_keys=True), newLine=True)

def playerPlay(afile, playerid=None, withWait=False):
  def _playlisten(id, method, params):
    return True if method == "Player.OnStop" else False

  REQUEST = {"method": "Player.Open", "params": {"item": {"file": afile}}}
  if playerid is not None:
    playercoreid = playerid
    if playercoreid == "null":
      playercoreid = None
    elif playercoreid == "default":
      if not gConfig.JSON_HAS_OPEN_PLAYERCORE_DEFAULT:
        gLogger.err("WARNING: 'default' is not supported by current JSON API", newLine=True)
        playercoreid = None
    else:
      try:
        playercoreid = int(playerid)
      except:
        pass
    REQUEST["params"]["options"] = {"playercoreid": playercoreid}
  MyJSONComms(gConfig, gLogger).sendJSON(REQUEST, "libPlayer", checkResult=True, callback=_playlisten if withWait else None)

def playerStop(playerid=None):
  doplayeraction("Player.Stop", playerid)

def playerPause(playerid=None):
  doplayeraction("Player.PlayPause", playerid)

def doplayeraction(action, playerid=None):
  jcomms = MyJSONComms(gConfig, gLogger)

  if playerid is None:
    REQUEST = {"method": "Player.GetActivePlayers"}
    data = jcomms.sendJSON(REQUEST, "libPlayers", checkResult=False)
    players = data.get("result", [])
    for player in players:
      REQUEST = {"method": action, "params": {"playerid": player["playerid"]}}
      jcomms.sendJSON(REQUEST, "libPlayer", checkResult=True)
  else:
    REQUEST = {"method": action, "params": {"playerid": playerid}}
    jcomms.sendJSON(REQUEST, "libPlayer", checkResult=True)

#---

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
          imdb movies [filter] | imdb tvshows [filter] | \
          purge hashed;unhashed;all pattern [pattern [pattern]] | \
          purgetest hashed;unhashed;all pattern [pattern [pattern]] | \
          fixurls | \
          remove mediatype libraryid | \
          watched class backup <filename> [filter] | \
          watched class restore <filename> [filter] | \
          duplicates | \
          set | testset | set class libraryid key1 value 1 [key2 value2...] | \
          missing class src-label [src-label]* | ascan [path] |vscan [path] | aclean | vclean | \
          sources [media] | sources media [label] | directory path | rdirectory path | readfile infile [outfile ; -] | \
          notify title message [displaytime [image]] | \
          status [idleTime] | monitor | power <state> | exec [params] | execw [params] | wake | \
          rbphdmi [seconds] | stats [class]* | \
          input action* [parameter] | screenshot | \
          volume [mute;unmute;#] | \
          stress-test view-type numitems [pause] [repeat] [cooldown] | \
          setsetting name value | getsetting name | getsettings [pattern] | debugon | debugoff | \
          play item [playerid] | playw item [playerid] | stop [playerid] | pause [playerid] | \
          profiles | \
          config | version | update | fupdate")
  print("")
  print("  s          Search URL column for partial movie or TV show title. Case-insensitive.")
  print("  S          Same as \"s\" (search) but will validate cachedurl file exists, displaying only those that fail validation")
  print("  x          Extract details, using optional SQL filter")
  print("  X          Same as \"x\" (extract) but will validate cachedurl file exists, displaying only those that fail validation")
  print("  Xd         Same as \"x\" (extract) but will DELETE those rows for which no cachedurl file exists")
  print("  f          Same as x, but includes file summary (file count, accumulated file size)")
  print("  F          Same as f, but doesn't include database rows")
  print("  d          Delete rows with matching ids, along with associated cached images")
  print("  c          Re-cache missing artwork. Class can be movies, tags, sets, tvshows, artists, albums or songs.")
  print("  C          Re-cache artwork even when it exists. Class can be movies, tags, sets, tvshows, artists, albums or songs. Class and filter both mandatory unless allow.recacheall=yes.")
  print("  nc         Same as c, but don't actually cache anything (ie. see what is missing). Class can be movies, tags, sets, tvshows, artists, albums or songs.")
  print("  lc         Like c, but only for content added since the modification date of the file specficied in property lastrunfile")
  print("  lnc        Like nc, but only for content added since the modification date of the file specficied in property lastrunfile")
  print("  lC         Like C, but only for content added since the modification date of the file specficied in property lastrunfile")
  print("  j          Query library by class (movies, tags, sets, tvshows, artists, albums or songs) with optional filter, return JSON results.")
  print("  J          Same as \"j\", but includes extra JSON audio/video fields as defined in properties file.")
  print("  jd, Jd     Functionality equivalent to j/J, but all URLs are decoded")
  print("  jr, Jr     Functionality equivalent to j/J, but all URLs are decoded and non-ASCII characters output (ie. \"raw\")")
  print("  qa         Run QA check on movies, tags and tvshows, identifying media with missing artwork or plots")
  print("  qax        Same as qa, but remove and rescan those media items with missing details.")
  print("             Configure with qa.zero.*, qa.blank.* and qa.art.* properties. Prefix field with ? to render warning only.")
  print("  p          Display files present in texture cache that don't exist in the media library")
  print("  P          Prune (automatically remove) cached items that don't exist in the media library")
  print("  r          Reverse search to identify \"orphaned\" Thumbnail files that are not present in the texture cache database")
  print("  R          Same as \"r\" (reverse search) but automatically deletes \"orphaned\" Thumbnail files")
  print("  imdb       Update IMDb fields (default: ratings and votes) on movies or tvshows - pipe output into set to apply changes to media library. Specify alternate or additional fields with @imdb.fields.movies and @imdb.fields.tvshows")
  print("  purge      Remove cached artwork with URLs containing specified patterns, with or without hash")
  print("  purgetest  Dry-run version of purge")
  print("  fixurls    Output new URLs for movies, sets and TV shows that have URLs containing both forward and backward slashes. Output suitable as stdin for set option")
  print("  remove     Remove a library item - specify type (movie, tvshow, episode or musicvideo) and libraryid")
  print("  watched    Backup or restore movies and tvshows watched status and restore points, to/from the specified text file")
  print("  duplicates List movies with multiple versions as determined by imdb number")
  print("  set        Set values on objects (movie, tvshow, episode, musicvideo, album, artist, song) eg. \"set movie 312 art.fanart 'http://assets.fanart.tv/fanart/movies/19908/hdmovielogo/zombieland-5145e97ed73a4.png'\"")
  print("  testset    Dry run version of set")
  print("  missing    Locate media files missing from the specified media library, matched against one or more source labels, eg. missing movies \"My Movies\"")
  print("  ascan      Scan entire audio library, or specific path")
  print("  vscan      Scan entire video library, or specific path")
  print("  aclean     Clean audio library")
  print("  vclean     Clean video library")
  print("  sources    List all sources, or sources for specific media type (video, music, pictures, files, programs) or label (eg. \"My Movies\")")
  print("  directory  Retrieve list of files in a specific directory (see sources)")
  print("  rdirectory Recursive version of directory")
  print("  readfile   Read contents of a remote file, writing output to stdout (\"-\", but not suitable for binary data) or the named file (suitable for binary data)")
  print("  notify     Send notification to Kodi GUI. Requires title and message arguments, with optional displaytime in milliseconds (default 5000) and image/icon location")
  print("  status     Display state of client - ScreenSaverActive, SystemIdle (default 600 seconds), active Player state etc.")
  print("  monitor    Display client event notifications as they occur")
  print("  power      Control power state of client, where state is one of suspend, hibernate, shutdown, reboot and exit")
  print("  wake       Wake (over LAN) the client corresponding to the MAC address specified by property network.mac")
  print("  exec       Execute specified addon, with optional parameters")
  print("  execw      Execute specified addon, with optional parameters and wait (although often wait has no effect)")
  print("  rbphdmi    Manage HDMI power saving on a Raspberry Pi by monitoring Screensaver notifications. Default power-off delay is 900 seconds after screensaver has started.")
  print("  stats      Output media library stats")
  print("  input      Send keyboard/remote control input to client, where action is back, left, right, up, down, executeaction, sendtext etc.")
  print("  volume     Set volume level 0-100, mute or unmute, or display current mute state and volume level")
  print(" stress-test Stress GUI by walking over library items. View type: thumbnail, horizontal, vertical. Default pause 0.25, repeat 1, cooldown (in seconds) 0.")
  print("  screenshot Take a screen grab of the current display")

  print("  setsetting Set the value of the named setting, eg. 'setsetting locale.language English'")
  print("  getsetting Get the current value of the named setting, eg. 'getsetting locale.language'")
  print(" getsettings View details of all settings, or those where pattern is contained within id, eg. 'getsettings debug' to view details of all debug-related settings")
  print("  debugon    Enable debugging")
  print("  debugoff   Disable debugging")

  print("  play       Play the specified item (on the specified player: null, default, #)")
  print("  playw      Play the specified item (on the specified player: null, default, #), and wait until playback ends")
  print("  stop       Stop playback of the specified player, or all currently active players")
  print("  pause      Toggle pause/playback of the specified player, or all currently active players")

  print("  profiles   List available profiles")

  print("")
  print("  config     Show current configuration")
  print("  version    Show current version and check for new version")
  print("  update     Update to new version (if available)")
  print("")
  print("Valid media classes: addons, pvr.tv, pvr.radio, artists, albums, songs, movies, sets, tags, tvshows")
  print("Valid meta classes:  audio (artists + albums + songs) and video (movies + sets + tvshows) and all (audio + video + addons + pvr.tv + pvr.radio)")
  print("Meta classes can be used in place of media classes for: c/C/nc/lc/lnc/j/J/jd/Jd/qa/qax options.")
  print("")
  print("SQL Filter fields:")
  print("  id, cachedurl, height, width, usecount, lastusetime, lasthashcheck, url")

  sys.exit(EXIT_CODE)

# Return the path if not defined (eg. cleared by user) or it exists
# Otherwise find it, returning undefined if cannot be found
def findexepath(cmd, path):
  if not path or os.path.exists(path):
    return path
  else:
    try:
      response = subprocess.check_output(["which", cmd], stderr=subprocess.STDOUT)
      response = response[:-1] if response.endswith("\n") else response
      return response
    except:
      return None

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

  gLogger.setLogFile(gConfig)

  gLogger.log("Command line args: %s" % sys.argv)
  gLogger.log("Current version #: v%s" % gConfig.VERSION)
  gLogger.log("Current platform : %s" % sys.platform)
  gLogger.log("Python  version #: v%d.%d.%d.%d (%s)" % (sys.version_info[0], sys.version_info[1], \
                                               sys.version_info[2], sys.version_info[4], sys.version_info[3]))
def checkConfig(option):

  jsonNeedVersion = 6

  # Web server access
  optWeb = ["c", "C", "readfile"]

  # Socket (JSON RPC) access
  optSocket = ["c", "C", "nc", "lc", "lnc", "lC", "j", "J", "jd", "Jd", "jr", "Jr",
                "qa","qax","query", "p","P",
                "remove", "vscan", "ascan", "vclean", "aclean",
                "directory", "rdirectory", "sources",
                "status", "monitor", "power", "rbphdmi", "stats", "input", "screenshot", "stress-test",
                "exec", "execw", "missing", "watched", "duplicates", "set", "testset",
                "volume", "readfile", "notify",
                "setsetting", "getsetting", "getsettings", "debugon", "debugoff",
                "play", "playw", "stop", "pause",
                "fixurls", "imdb", "profiles"]

  # Database access (could be SQLite, could be JSON - needs to be determined later)
  optDb = ["s", "S", "x", "X", "Xd", "f", "F",
           "c", "C", "nc", "lc", "lnc", "lC", "d",
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

  wcomms     = None
  jcomms     = None

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
      wcomms = MyJSONComms(gConfig, gLogger, connecttimeout=gConfig.WEB_CONNECTTIMEOUT)
      REQUEST = {"method": "JSONRPC.Ping"}
      data = wcomms.sendJSON(REQUEST, "libPing", checkResult=False, useWebServer=True)
      gotWeb = ("result" in data and data["result"] == "pong")
    except socket.error:
      pass

  if needWeb and not gotWeb:
    MSG = "FATAL: The task you wish to perform requires that the web server is\n" \
          "       enabled and running on the Kodi system you wish to connect.\n\n" \
          "       A connection cannot be established to the following webserver:\n" \
          "       %s:%s\n\n" \
          "       Check settings in properties file %s\n" % (gConfig.KODI_HOST, gConfig.WEB_PORT, gConfig.CONFIG_NAME)
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

      if gLogger.VERBOSE and gLogger.LOGGING:
        gLogger.log("JSON CAPABILITIES: %s" % gConfig.dumpJSONCapabilities())

      if gConfig.JSON_HAS_PROFILE_SUPPORT:
        gConfig.ALL_PROFILES = getallprofiles(jcomms)
        gConfig.CURRENT_PROFILE = getcurrentprofile(jcomms)
        gLogger.log("CURRENT PROFILE: %s" % gConfig.CURRENT_PROFILE)
        if gConfig.PROFILE_ENABLED and gConfig.CURRENT_PROFILE["label"] != gConfig.PROFILE_NAME and option != "profiles":
          if not switchprofile(jcomms): return False
          jcomms = MyJSONComms(gConfig, gLogger)

      REQUEST = {"method": "PVR.GetProperties",
                 "params": {"properties": ["available"]}}
      data = jcomms.sendJSON(REQUEST, "libPVR", checkResult=False)
      gConfig.HAS_PVR = ("result" in data and data["result"].get("available", False))

    except socket.error:
      pass

  if needSocket and not gotSocket:
    MSG = "FATAL: The task you wish to perform requires that the JSON-RPC server is\n" \
          "       enabled and running on the Kodi system you wish to connect.\n\n" \
          "       In addition, ensure that the following options are ENABLED on the\n" \
          "       Kodi client in Settings -> Services -> Remote control:\n\n" \
          "            Allow programs on this system to control Kodi\n" \
          "            Allow programs on other systems to control Kodi\n\n" \
          "       A connection cannot be established to the following JSON-RPC server:\n" \
          "       %s:%s\n\n" \
          "       Check settings in properties file %s\n" % (gConfig.KODI_HOST, gConfig.RPC_PORT, gConfig.CONFIG_NAME)
    gLogger.err(MSG)
    return False

  if needSocket and jsonGotVersion  < jsonNeedVersion :
    MSG = "FATAL: The task you wish to perform requires that a JSON-RPC server with\n" \
          "       version %d or above of the Kodi JSON-RPC API is provided.\n\n" \
          "       The JSON-RPC API version of the connected server is: %d (0 means unknown)\n\n" \
          "       Check settings in properties file %s\n" % (jsonNeedVersion, jsonGotVersion, gConfig.CONFIG_NAME)
    gLogger.err(MSG)
    return False

  # If auto detection enabled, when API level insufficient to read Textures DB
  # using JSON, fall back to SQLite3 calls
  if needDb and gConfig.DBJSON == "auto":
    # Able to use JSON for Textures DB access, no need to check DB availability
    if gConfig.JSON_HAS_TEXTUREDB:
      gConfig.USEJSONDB = True
      gLogger.log("JSON Textures DB API available and will be used to access the Textures DB")
    else:
      gConfig.USEJSONDB = False
      gLogger.log("JSON Textures DB API not supported - will use SQLite to access the Textures DB")

  # If JSON Textures API is to be used...
  if gConfig.USEJSONDB:
    # Don't access Textures database using SQLite
    # Don't access file system either
    needDb = needFS2 = False

  # If DB access required, import SQLite3 module
  if needDb:
    global lite
    try:
      import sqlite3 as lite
      try:
        database = MyDB(gConfig, gLogger)
        con = database.getDB()
        if database.DBVERSION < 13:
          MSG = "WARNING: The SQLite3 database pre-dates Frodo (v12), some problems may be encountered!"
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
          "       access to the Kodi SQLite3 Texture Cache database.\n\n" \
          "       The following SQLite3 database could not be opened:\n" \
          "       %s\n\n" \
          "       Check settings in properties file %s,\n" \
          "       or upgrade your Kodi client to use a more recent\n" \
          "       version that supports Textures JSON API.\n" \
                  % (gConfig.getDBPath(), gConfig.CONFIG_NAME)
    gLogger.err(MSG)
    return False

  if (needFS1 or needFS2) and not gConfig.HAS_THUMBNAILS_FS:
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

  if option == "rbphdmi" or option == "config":
    gConfig.BIN_TVSERVICE = findexepath("tvservice", gConfig.BIN_TVSERVICE)
    gConfig.BIN_VCGENCMD = findexepath("vcgencmd", gConfig.BIN_VCGENCMD)

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
    gLogger.log("CONFIG VALUES: \n%s" % gConfig.dumpMemberVariables())

  return True

def loadprofile(jcomms):
  REQUEST = {"method": "Profiles.LoadProfile", "params": {"profile": gConfig.PROFILE_NAME, "prompt": False}}
  if gConfig.PROFILE_PASSWORD != "":
    REQUEST["params"]["password"] = {"value": gConfig.PROFILE_PASSWORD}
    REQUEST["params"]["password"]["encryption"] = "md5" if gConfig.PROFILE_ENCRYPTED else "none"

  if jcomms is None: jcomms = MyJSONComms(gConfig, gLogger)

  data = jcomms.sendJSON(REQUEST, "libProfile", checkResult=False, ignoreSocketError=True)
  if "result" not in data:
    return False
  else:
    return True

def getallprofiles(jcomms):
  REQUEST = {"method": "Profiles.GetProfiles", "params": {"properties": ["thumbnail", "lockmode" ]}}
  if gConfig.JSON_HAS_PROFILE_DIRECTORY:
    REQUEST["params"]["properties"].extend(["directory"])

  data = jcomms.sendJSON(REQUEST, "libProfile", ignoreSocketError=True)

  profiles = {}

  if "result" in data:
    master = [p for p in data["result"]["profiles"] if p["label"] == gConfig.PROFILE_MASTER]
    master = None if master == [] else master[0]
    for profile in data["result"]["profiles"]:
      setProfileDirectory(master, profile)
      profiles[profile["label"]] = profile

  return profiles

def getcurrentprofile(jcomms):
  REQUEST = {"method": "Profiles.GetCurrentProfile", "params": {"properties": ["thumbnail", "lockmode" ]}}
  if gConfig.JSON_HAS_PROFILE_DIRECTORY:
    REQUEST["params"]["properties"].extend(["directory"])

  data = jcomms.sendJSON(REQUEST, "libProfile", ignoreSocketError=True)

  if "result" in data:
    profile = data["result"]
    master = gConfig.ALL_PROFILES.get(gConfig.PROFILE_MASTER, gConfig.ALL_PROFILES.get("Master user", None))
    setProfileDirectory(master, profile)
    return profile
  else:
    return gConfig.CURRENT_PROFILE

def setProfileDirectory(master, profile):
  if gConfig.JSON_HAS_PROFILE_DIRECTORY:
    master_dir = master["directory"] if master else "special://masterprofile/"
    if profile["directory"].startswith(master_dir):
      mdir = MyUtility.PathToHostOS(master_dir)
      pdir = MyUtility.PathToHostOS(profile["directory"])
      profile["tc.profilepath"] = pdir[len(mdir):]
    else:
      profile["tc.profilepath"] = profile["directory"]
  else:
    profile["directory"] = ""
    profile["tc.profilepath"] = gConfig.PROFILE_DIRECTORY

  # Prefix with KODI_BASE if profile path is not an absolute path
  if os.path.isabs(profile["tc.profilepath"]) == False:
    profile["tc.profilepath"] =  os.path.join(gConfig.KODI_BASE, profile["tc.profilepath"])

def switchprofile(jcomms):
  if gConfig.CURRENT_PROFILE["label"] == gConfig.PROFILE_NAME:
    return True
  elif gConfig.PROFILE_AUTOLOAD:
    gLogger.log("SWITCHING PROFILE FROM \"%s\" to \"%s\"" % (gConfig.CURRENT_PROFILE["label"], gConfig.PROFILE_NAME))
    gLogger.progress("Switching profile from \"%s\" to \"%s\"..." % (gConfig.CURRENT_PROFILE["label"], gConfig.PROFILE_NAME))

    if jcomms is None: jcomms = MyJSONComms(gConfig, gLogger)

    if not loadprofile(jcomms):
      gLogger.err("ERROR: Profile \"%s\" is not valid!" % gConfig.PROFILE_NAME, newLine=True)
      return False

    i = 0
    bounce = False
    while i <= gConfig.PROFILE_RETRY:
      try:
        i += 1
        time.sleep(1.0)
        jcomms = MyJSONComms(gConfig, gLogger, connecttimeout=1.0)
        gConfig.CURRENT_PROFILE = getcurrentprofile(jcomms)
        if gConfig.CURRENT_PROFILE["label"] == gConfig.PROFILE_NAME:
          gLogger.log("SWITCHED TO PROFILE: %s" % gConfig.CURRENT_PROFILE)
          if gConfig.PROFILE_WAIT != 0:
            gLogger.log("Waiting %d seconds for server to stabilise after loading profile..." % gConfig.PROFILE_WAIT)
            time.sleep(gConfig.PROFILE_WAIT)
          break
        elif bounce:
          loadprofile(jcomms)
          bounce = False
      except Exception as e:
        bounce = True
        jcomms = None
        pass
    else:
      gLogger.err("ERROR: Failed to load profile %s" % gConfig.PROFILE_NAME, newLine=True)
      return False
    gLogger.progress("")
  else:
    gLogger.err("ERROR: Need to switch profiles from \"%s\" to \"%s\", but profile.autoload is not enabled" % (gConfig.CURRENT_PROFILE["label"], gConfig.PROFILE_NAME), newLine=True)
    return False

  return True

def listProfiles():
  print("%s  %s  %-20s  %-50s  %s" % ("Active", "Lock", "Name", "Device Path", "Local Path"))
  for p in gConfig.ALL_PROFILES:
    profile = gConfig.ALL_PROFILES[p]
    active = "Yes" if profile["label"] == gConfig.CURRENT_PROFILE["label"] else "No "
    lockmode = "Yes" if profile["lockmode"] != 0 else "No "
    print(" %s     %s  %-20s  %-50s  %s" % (active, lockmode, profile["label"], profile["directory"], profile["tc.profilepath"]))

def checkUpdate(argv, forcedCheck=False):
  (remoteVersion, remoteHash) = getLatestVersion(argv)

  if forcedCheck:
    gLogger.out("Current Version: v%s" % gConfig.VERSION, newLine=True)
    gLogger.out("Latest  Version: %s" % ("v" + remoteVersion if remoteVersion else "Unknown"), newLine=True)
    gLogger.out("", newLine=True)

  if remoteVersion and MyUtility.getVersion(remoteVersion) > MyUtility.getVersion(gConfig.VERSION):
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
  if argv[0] in ["c", "C", "nc", "lc", "lnc", "lC"]:
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
  elif argv[0] == "stress-test":
    USAGE  = "stress"
  elif argv[0] in ["play", "playw", "stop", "pause"]:
    USAGE  = "transport"
  elif argv[0] in ["query", "missing", "watched",
                   "power", "wake", "status", "monitor", "rbphdmi",
                   "directory", "rdirectory", "sources", "remove",
                   "vscan", "ascan", "vclean", "aclean",
                   "duplicates", "fixurls", "imdb", "stats",
                   "input", "screenshot", "volume", "readfile", "notify",
                   "setsetting", "getsetting", "getsettings", "debugon", "debugoff",
                   "version", "update", "fupdate", "config", "profiles"]:
    USAGE  = argv[0]

  analytics_url = gConfig.ANALYTICS_GOOD

  HEADERS = []
  HEADERS.append(("User-agent", user_agent))
  HEADERS.append(("Referer", "http://www.%s" % USAGE))

  remoteVersion = remoteHash = None

  # Try checking version via Analytics URL
  (remoteVersion, remoteHash) = getLatestVersion_ex(analytics_url, headers = HEADERS)

  # If the Analytics call fails, go direct to Github
  if remoteVersion is None or remoteHash is None:
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

    if MyUtility.isPython3:
      data = response.read().decode("utf-8")
    else:
      data = response.read()

    items = data.replace("\n","").split(" ")

    if len(items) == 2:
      ITEMS = items
    else:
      gLogger.log("Bogus data in getLatestVersion_ex(): URL [%s], data [%s]" % (url, data), maxLen=512)
  except Exception as e:
    gLogger.log("Exception in getLatestVersion_ex(): URL [%s], text [%s]" % (url, e))

  socket.setdefaulttimeout(GLOBAL_TIMEOUT)
  return ITEMS

def downloadLatestVersion(argv, force=False, autoupdate=False):
  (remoteVersion, remoteHash) = getLatestVersion(argv)

  if autoupdate and (not remoteVersion or MyUtility.getVersion(remoteVersion) <= MyUtility.getVersion(gConfig.VERSION)):
    return False

  if not remoteVersion:
    gLogger.err("FATAL: Unable to determine version of the latest file, check Internet access and github.com are available.", newLine=True)
    sys.exit(2)

  if not force and MyUtility.getVersion(remoteVersion) <= MyUtility.getVersion(gConfig.VERSION):
    gLogger.err("Current version is already up to date - no update required.", newLine=True)
    sys.exit(2)

  try:
    response = urllib2.urlopen("%s/%s" % (gConfig.GITHUB, "texturecache.py"))
    data = response.read()
  except Exception as e:
    gLogger.log("Exception in downloadLatestVersion(): %s" % e)
    if autoupdate: return False
    gLogger.err("FATAL: Unable to download latest file, check Internet access and github.com are available.", newLine=True)
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
    gLogger.err("FATAL: Might be updating version in Git repository... Abandoning update!", newLine=True)
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
      path = os.path.realpath(__file__)
      dir = os.path.dirname(path)
      if os.access(dir, os.W_OK):
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

  elif argv[0] in ["c", "C", "nc", "lc", "lnc", "lC",
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

    _force      = True if argv[0] in ["C", "lC"] else False
    _rescan     = True if argv[0] == "qax" else False
    _lastRun    = True if argv[0] in ["lc", "lnc", "lC"] else False
    _nodownload = True if argv[0] in ["nc", "lnc"] else False
    _decode     = True if argv[0] in ["jd", "Jd", "jr", "Jr"] else False
    _ensure_ascii=False if argv[0] in ["jr", "Jr"] else True
    _extraFields= True if argv[0] in ["J", "Jd", "Jr"] else False

    _filter     = ""
    _query      = ""
    _drop_items = {}

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

    if _action == "imdb" and _multi_call != []:
      usage(1)

    if _action == "imdb" and not gConfig.OMDB_API_KEY:
      gLogger.err("ERROR: imdb functionality is no longer available without a valid API key.", newLine=True)
      gLogger.err("Visit www.omdbapi.com to sign up for an API key, then add", newLine=True)
      gLogger.err("  omdb.apikey=<yourkey>", newLine=True)
      gLogger.err("to texturecache.cfg", newLine=True)
      sys.exit(2)

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
                  extraFields=_extraFields, query=_query, drop_items=_drop_items)
      if _action == "cache": dump_drop_items(_drop_items)
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
    getDirectory(argv[1], recurse=False)
  elif argv[0] == "rdirectory" and len(argv) == 2:
    getDirectory(argv[1], recurse=True)

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

  elif argv[0] == "watched" and argv[2] in ["backup", "restore"] and len(argv) in [4, 5]:
    _filter = "" if len(argv) == 4 else argv[4]
    if argv[2] == "backup":
      jsonQuery(action="watched", mediatype=argv[1], filename=argv[3], wlBackup=True, filter=_filter)
    elif argv[2] == "restore":
      jsonQuery(action="watched", mediatype=argv[1], filename=argv[3], wlBackup=False, filter=_filter)
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

  elif argv[0] == "stress-test" and len(argv) >= 3:
    viewtype = argv[1]
    numitems = int(argv[2])
    pause = float(argv[3]) if len(argv) > 3 else 0.25
    repeat = int(argv[4]) if len(argv) > 4 else 1
    cooldown = float(argv[5]) if len(argv) > 5 else 0
    StressTest(viewtype, numitems, pause, repeat, cooldown)

  elif argv[0] == "volume" and len(argv) == 1:
    showVolume()
  elif argv[0] == "volume" and len(argv) == 2:
    setVolume(argv[1])

  elif argv[0] == "readfile" and len(argv) >= 2:
    infile = argv[1]
    outfile = argv[2] if len(argv) == 3 else "-"
    readFile(infile, outfile)

  elif argv[0] == "notify" and len(argv) >= 3:
    _title      = argv[1]
    _message    = argv[2]
    _displaytime= int(argv[3]) if len(argv) >= 4 else None
    _image      = argv[4] if len(argv) >= 5 else None
    ShowGUINotification(_title, _message, _displaytime, _image)

  elif argv[0] == "setsetting" and len(argv) == 3:
    WriteSetting(argv[1], argv[2])

  elif argv[0] == "getsetting" and len(argv) == 2:
    ReadSetting(argv[1])

  elif argv[0] == "getsettings" and len(argv) == 1:
    ReadSettings()
  elif argv[0] == "getsettings" and len(argv) == 2:
    ReadSettings(argv[1])

  elif argv[0] == "debugon" and len(argv) == 1:
    setSettingVariable("debug.showloginfo", True)
    if gConfig.JSON_HAS_DEBUG_EXTRA_LOG:
      setSettingVariable("debug.extralogging", True)

  elif argv[0] == "debugoff" and len(argv) == 1:
    setSettingVariable("debug.showloginfo", False)
    if gConfig.JSON_HAS_DEBUG_EXTRA_LOG:
      setSettingVariable("debug.extralogging", False)

  elif argv[0] == "play" and len(argv) in [2, 3]:
    playerPlay(argv[1], argv[2] if len(argv) == 3 else None, False)
  elif argv[0] == "playw" and len(argv) in [2, 3]:
    playerPlay(argv[1], argv[2] if len(argv) == 3 else None, True)
  elif argv[0] == "stop" and len(argv) in [1, 2]:
    playerStop(int(argv[1]) if len(argv) == 2 else None)
  elif argv[0] == "pause" and len(argv) in [1, 2]:
    playerPause(int(argv[1]) if len(argv) == 2 else None)

  elif argv[0] == "profiles":
    listProfiles()

  else:
    usage(1)

  MyUtility.logDirectoryCacheStats(totals=True)
  gLogger.log("Successful completion")

  sys.exit(EXIT_CODE)

if __name__ == "__main__":
  #https://mail.python.org/pipermail/python-list/2015-October/697689.html - threading bug in Python2
  tmp = datetime.datetime.strptime('01-01-1970', '%d-%m-%Y')

  try:
    stopped = threading.Event()
    main(sys.argv[1:])
  except (KeyboardInterrupt, SystemExit) as e:
    if type(e) == SystemExit: sys.exit(int(str(e)))
  except Exception:
    if "gLogger" in globals() and gLogger.LOGGING:
      import logging
      gLogger.flush()
      logging.basicConfig(filename=gLogger.LOGFILE.name, level=logging.DEBUG)
      logging.exception("** Terminating due to unexpected exception **")
    raise
