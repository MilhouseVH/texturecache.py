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
# Simple utility to download remote artwork to a local folder, and optionally replace
# remote artwork with the new local urls.
#
# https://github.com/MilhouseVH/texturecache.py/blob/master/tools/mklocal.py
#
# Usage:
#
#  See built-in help (run script with --help parameter).
#
#  For details on artwork naming conventions supported by this script:
#     http://kodi.wiki/view/Frodo_FAQ#Local_images
#
################################################################################

#version 0.2.6

from __future__ import print_function
import sys, os, codecs, json, argparse, re, shutil

if sys.version_info >= (3, 0):
  import urllib.request as urllib2
else:
  import urllib2

# Helper class...
class MyUtility(object):
  isPython3 = (sys.version_info >= (3, 0))

  # Convert filename into consistent UTF-8
  # representation for both Python2 and Python3
  @staticmethod
  def toutf8(value):
    if not value: return value

    if not MyUtility.isPython3:
      try:
        value = value.encode("utf-8")
      except UnicodeDecodeError:
        pass
      except UnicodeEncodeError:
        pass

    return value

  # Quote unquoted filename
  @staticmethod
  def fromUnicode2(value):
    if not MyUtility.isPython3:
      try:
        value = bytes(value.encode("utf-8"))
      except UnicodeDecodeError:
        pass

    return value

  @staticmethod
  def toUnicode(value):
    if MyUtility.isPython3: return value

    if isinstance(value, basestring):
      if not isinstance(value, unicode):
        try:
          value = unicode(value, encoding="utf-8", errors="ignore")
        except UnicodeDecodeError:
          pass

    return value

  # Used to extract # from fanart# or thumb#
  @staticmethod
  def extract_index(atype, value):
    try:
      return int(value[len(atype) - 1:])
    except:
      return 0

def printout(msg, newline=True):
  endchar = "\n" if newline else ""
  print(MyUtility.toUnicode(msg), file=sys.stdout, end=endchar)
  sys.stderr.flush()

def printerr(msg, newline=True):
  endchar = "\n" if newline else ""
  print(MyUtility.toUnicode(msg), file=sys.stderr, end=endchar)
  sys.stderr.flush()

def info(args, msg, atype, title, reason = None, url = None, target = None):
  line = "DRYRUN " if args.dryrun else ""
  if reason or url:
    line = "%s%-15s - %-10s - %-45s" % (line, msg, atype.center(10), addEllipsis(45, MyUtility.toUnicode(title)))
    if reason: line = "%s [%s]" % (line, reason)
    if url:    line = "%s %s" % (line, MyUtility.toUnicode(url))
  elif target:
    line = "%s%-15s - %-10s - %-45s -> %s" % (line, msg, atype.center(10), addEllipsis(45, MyUtility.toUnicode(title)), MyUtility.toUnicode(target))
  else:
    line = "%s%-15s - %-10s - %s" % (line, msg, atype.center(10), MyUtility.toUnicode(title))

  printout(line) if args.info else printerr(line)

def warning(args, msg, atype, title, reason = None, url = None, target = None):
  if not args.quiet:
    info(args, msg, atype, title, reason, url, target)

def debug(indent, msg):
  global VERBOSE
  if VERBOSE: printerr("##DEBUG## %s%s" % (" "*(indent*2), msg))

def debug2(atype, msg, value1="", value2=""):
  global VERBOSE
  if VERBOSE:
    if value1:
      debug(2, "[%-10s] %-40s %s%s" % (atype, msg, MyUtility.toUnicode(value1), MyUtility.toUnicode(value2)))
    else:
      debug(2, "[%-10s] %s" % (atype, MyUtility.toUnicode(msg)))

def addEllipsis(maxlen, aStr):
  if len(aStr) <= maxlen: return aStr

  ileft = int(maxlen/2) - 2
  iright = int(maxlen/2) - 1

  return "%s...%s" % (aStr[0:ileft], aStr[-iright:])

def fixSlashes(path):
  # Share (eg. "smb://", "nfs://" etc.)
  if re.search("^.*://.*", path):
    return path.replace("\\", "/")
  else:
    return path.replace("\\", os.sep).replace("/", os.sep)

def pathToLocal(infile):
  global LOCAL_DIR, XBMC_PATH

  if not infile: return infile
  if not XBMC_PATH: return infile
  if not LOCAL_DIR: return infile

  if infile.startswith(XBMC_PATH):
    return fixSlashes("%s%s" % (LOCAL_DIR, infile[len(XBMC_PATH):]))
  else:
    return infile

def pathToAltLocal(infile):
  global LOCAL_ALT, XBMC_PATH

  if not infile: return infile
  if not XBMC_PATH: return infile
  if not LOCAL_ALT: return infile

  if infile.startswith(XBMC_PATH):
    return fixSlashes("%s%s" % (LOCAL_ALT, infile[len(XBMC_PATH):]))
  else:
    return infile

def pathToXBMC(infile):
  global LOCAL_DIR, XBMC_PATH

  if not infile: return infile
  if not LOCAL_DIR: return infile
  if not XBMC_PATH: return infile

  if infile.startswith(LOCAL_DIR):
    return fixSlashes("%s%s" % (XBMC_PATH, infile[len(LOCAL_DIR):]))
  else:
    return infile

def itemList(aList):
  newList = []
  if aList:
    for aname in aList:
      (aname, value) = (aname, aname) if aname.find(":") == -1 else aname.split(":")
      newList.append({"type": aname, "suffix": value})
  return newList

def unstack(filename, remove_discpart=False):
  if not filename: return filename

  if filename.startswith("stack://"):
    fname = filename[8:].split(" , ")[0]

    if remove_discpart:
      # <cd/dvd/part/pt/disk/disc/d> <0-N>
      parts = re.search(r"(.*[\\/])(.*?)([ _.-]*(?:cd|dvd|p(?:ar)?t|dis[ck]|d)[ _.-]*[0-9]+)(.*?)(\.[^.]+)$", fname)
      if parts and parts.lastindex == 5:
        return "%s%s%s" % (parts.group(1), parts.group(2), parts.group(5))

      # <cd/dvd/part/pt/disk/disc/d> <a-d>
      parts = re.search(r"(.*[\\/])(.*?)([ _.-]*(?:cd|dvd|p(?:ar)?t|dis[ck]|d)[ _.-]*[a-d])(.*?)(\.[^.]+)$", fname)
      if parts and parts.lastindex == 5:
        return "%s%s%s" % (parts.group(1), parts.group(2), parts.group(5))

    return fname
  else:
    return filename

def getSlash(filename):
  # Share (eg. "smb://", "nfs://" etc.)
  if re.search("^.*://.*", filename):
    return "/"
  else:
    bslash = filename.find("\\")
    fslash = filename.find("/")
    if bslash == -1: bslash = len(filename)
    if fslash == -1: fslash = len(filename)
    if bslash < fslash:
      return "\\"
    else:
      return "/"

def findSetParent(setname, members, level=0):
#  parent = findTitleSetParent(setname, members)
#  if not parent:
#    parent = findMostCommonSetParent(setname, members)
#  return parent
  return findMostFrequentSetParent(setname, members)

def findTitleSetParent(setname, members):
  for member in members:
    file = os.path.dirname(unstack(member["file"]))
    pos = file.rfind(setname)
    if pos != -1:
      return "%s%s" % (file[:pos + len(setname)], getSlash(file))
  else:
    return None

# Use this method if unable to find parent based on title, will
# try to match based on a common parent
def findCommonSetParent(setname, members, level=0):
  commonparent = os.path.dirname(unstack(members[0]["file"]))
  for i in range(0, level):
    commonparent = os.path.dirname(commonparent)
    if commonparent == "": return ""

  sameparent = True
  for member in members:
    file = unstack(member["file"])
    if not file.startswith(commonparent):
      sameparent = False
      break

  if sameparent:
    return "%s%s" % (commonparent, getSlash(commonparent))
  else:
    return findCommonSetParent(setname, members, level+1)

# Use this method if unable to find parent based on title, will
# find the most commonly referenced parent folder within the set.
# Uses recursion to build up a list of path frequencies, then returns
# the longest instance of the most frequently used path.
def findMostFrequentSetParent(setname, members, level=0, counts=None):
  # Kodi sets will either be together in one shared folder, or individual
  # folders below a shared parent, so only need to consider two levels (the file
  # folder and the parent)
  if level > 1: return

  if not counts: counts = {}

  # Walk "back" up the path for each level, counting frequency
  for member in members:
    parent = os.path.dirname(unstack(member["file"]))
    for i in range(0, level):
      parent = os.path.dirname(parent)
      if not parent: break
    if parent != "":
      counts[parent] = counts.get(parent, 0) + 1

  findMostFrequentSetParent(setname, members, level+1, counts)

  if level == 0:
    # Sort paths into descending order of frequency
    sorted_counts = sorted(counts, key=counts.get, reverse=True)

    maxfreq = counts[sorted_counts[0]]

    # Now sort just the most frequently used paths by descending length
    sorted_counts = [x for x in sorted(counts, key=len, reverse=True) if counts[x] == maxfreq]

    return "%s%s" % (sorted_counts[0], getSlash(sorted_counts[0]))

def formatArtworkFilename(args, mediatype, filename, suffix, season, singleFolder=False):
  joinchar = getSlash(filename)

  if mediatype == "movie":
    if suffix == "fanart#":
      parent = args.extrafanart if args.extrafanart else "%s%s%s" % (os.path.dirname(filename), joinchar, "extrafanart")
      if singleFolder and args.extrafanart is None:
        return "%s%s%s" % (parent, joinchar, suffix)
      else:
        return "%s%s%s-%s" % (parent, joinchar, os.path.basename(filename), suffix)
    elif suffix == "thumb#":
      parent = args.extrathumbs if args.extrathumbs else "%s%s%s" % (os.path.dirname(filename), joinchar, "extrathumbs")
      if singleFolder and args.extrathumbs is None:
        return "%s%s%s" % (parent, joinchar, suffix)
      else:
        return "%s%s%s-%s" % (parent, joinchar, os.path.basename(filename), suffix)
    else:
      if singleFolder:
        return "%s%s%s" % (os.path.dirname(filename), joinchar, suffix)
      else:
        return "%s-%s" % (filename, suffix)
  elif mediatype == "episode":
    return "%s-%s" % (filename, suffix)
  elif mediatype == "season":
    if season == 0:
      season_name = "season-specials"
    else:
      season_name = "season%02d" % season
    return "%s%s-%s" % (filename, season_name, suffix)
  else:
    return "%s%s" % (filename, suffix)

def processItem(args, mediatype, media, download_items, showTitle=None, showPath=None):
  global XBMC_PATH, COUNT, TOTAL

  COUNT += 1
  printerr("Progress: %d of %d\r" % (COUNT, TOTAL), newline=False)

  workitem = {}
  workitem["items"] = {}
  previtems = {}

  # Use first file in files[] for "set"
  if mediatype == "set":
    mediafile = findSetParent(media["title"], media["tc.members"])
  else:
    mediafile = unstack(media.get("file", showPath), remove_discpart=True)

  mediatitle = "%s %s" % (showTitle, media["label"]) if showTitle else media["label"]

  debug(0, "mediatype [%s]; mediatitle [%s]" % (mediatype, mediatitle))
  debug(1, "mediafile is [%s]" % mediafile)

  if XBMC_PATH and not mediafile.startswith(XBMC_PATH):
    if not args.ignorebadprefix:
      warning(args, "** SKIPPING **", "Bad prefix", mediatitle, "Kodi path does not match prefix", mediafile)
    return workitem

  filename = os.path.splitext(pathToLocal(mediafile))[0]

  filename = MyUtility.toutf8(filename)

  debug(1, "local root name would be [%s]" % (filename))

  # seasonid requires JSON API v6.10.0+
  libraryid = "%sid" % mediatype
  if libraryid in media:
    workitem["type"] = mediatype
    workitem["title"] = mediatitle
    workitem["libraryid"] = media[libraryid]

  art = media["art"]

  for artitem in download_items:
    if artitem["type"] in previtems:
      debug(1, "already found a value for artwork type [%s] - ignoring repeated item" % artitem["type"])
      continue

    artpath_m = formatArtworkFilename(args, mediatype, filename, artitem["suffix"], media.get("season", None), singleFolder=False)
    artpath_s = formatArtworkFilename(args, mediatype, filename, artitem["suffix"], media.get("season", None), singleFolder=True)

    if artitem["type"] in ["fanart#", "thumb#"]:
      if mediatype not in ["movie", "tvshow"]:
        debug(1, "invalid artwork type [%s] for media [%s] - ignoring" % (artitem["type"], mediatype))
        continue

      m_regex = re.compile("%s[0-9]+" % artitem["type"][:-1])
      m_max = args.extrafanartmax + 1 if artitem["type"] == "fanart#" else args.extrathumbsmax + 1

      m_items = {}
      for index in range(1, m_max):
        m_items[index] = False
      for aitem in [MyUtility.extract_index(artitem["type"], x) for x in art if m_regex.match(x)]:
        if aitem not in m_items:
          m_items[aitem] = True

      for m_index in sorted(m_items):
        m_type = "%s%d" % (artitem["type"][:-1], m_index)

        if m_type in previtems:
          debug(1, "already found a value for artwork type [%s] - ignoring repeated item (expanded from %s)" % (m_type, artitem["type"]))
          continue

        m_artpath_m = re.sub("%s$" % artitem["suffix"], m_type, artpath_m)
        m_artpath_s = re.sub("%s$" % artitem["suffix"], m_type, artpath_s)

        oldname = art.get(m_type, None)
        if oldname: oldname = MyUtility.toutf8(oldname[8:-1])

        newname = processArtwork(args, mediatype, media, mediatitle, m_type, mediafile, oldname, m_artpath_m, m_artpath_s, is_excess=m_items[m_index])
        updateworkitem(args, m_type, mediatitle, workitem, oldname, newname)

        previtems[m_type] = True
    else:
      oldname = art.get(artitem["type"], None)
      if oldname: oldname = MyUtility.toutf8(oldname[8:-1])
      newname = processArtwork(args, mediatype, media, mediatitle, artitem["type"], mediafile, oldname, artpath_m, artpath_s, is_excess=False)
      updateworkitem(args, artitem["type"], mediatitle, workitem, oldname, newname)

    previtems[artitem["type"]] = True

  if args.check:
    clist = args.check if args.check != ["all"] else [x for x in art if not x.startswith("tvshow.") ]
    for artitem in clist:
      if artitem in art:
        aname = art[artitem][8:-1]
        if aname.startswith("http://") or aname.startswith("https://"):
          info(args, "**REMOTE FILE**", artitem, mediatitle, "Remote URL found", aname)

  return workitem

def updateworkitem(args, art_type, mediatitle, workitem, oldname, newname):
  label = "art.%s" % art_type

  if not newname and oldname:
    debug2(art_type, "Assigning null value to library item")
    workitem["items"][label] = None
    if args.info:
      info(args, "Removing", art_type, mediatitle)
  else:
    if newname and newname != oldname:
      debug2(art_type, "Changing library value to:", newname)
      workitem["items"][label] = newname
      if args.info:
        info(args, "Replacing", art_type, mediatitle)
    else:
      if label in workitem["items"]: del workitem["items"][label]
      debug2(art_type, "No library change required, keeping:", oldname)

def processArtwork(args, mediatype, media, title, atype, filename, currentname, pathname_multi, pathname_single, is_excess):
  debug(1, "artwork type [%s] known by Kodi as [%s]" % (atype, currentname))

  # if this is an excess fanart# or thumb#, return nothing
  if is_excess:
    return None if args.nokeep else currentname

  # See if we already have a file of the desired artwork type, either in
  # jpg or png format. If found, use it as the source for this artwork type.

  existinglocal = False

  # First, check folder using single-file naming convention (if enabled)
  if args.singlefolders:
    for source_type in [".png", ".jpg"]:
      target = "%s%s" % (pathname_single, source_type)
      if os.path.exists(target):
        debug2(atype, "Found pre-existing local file:", target)
        if args.overwrite:
          existinglocal = True
          break
        else:
          target = pathToXBMC(target)
          debug2(atype, "Converting local filename to Kodi path:", target)
          return target

  if not existinglocal:
    # Next, check folder using multi-file naming convention
    for source_type in [".png", ".jpg"]:
      target = "%s%s" % (pathname_multi, source_type)
      if os.path.exists(target):
        debug2(atype, "Found pre-existing local file:", target)
        if args.overwrite:
          break
        else:
          target = pathToXBMC(target)
          debug2(atype, "Converting local filename to Kodi path:", target)
          return target

  # If we don't currently have a remote source, return nothing
  if not currentname: return None

  # If we're not downloading, just return the current file name
  if args.readonly:
    if args.nokeep:
      return None
    else:
      warning(args, "**  NEEDED  **", atype, title, "readonly enabled", currentname)
      return currentname

  # We're going to create a new file.
  # We have a remote source (currentname) and a partial
  # name for the target - need to append the file format type.
  pathname = pathname_single if args.singlefolders else pathname_multi
  target = "%s%s" % (pathname, os.path.splitext(currentname)[1].lower())

  # Download the new artwork and convert the name of the new file
  # back into a valid Kodi path.
  fname = pathToXBMC(getImage(args, mediatype, media, title, atype, filename, currentname, target))
  debug2(atype, "Converting local filename to Kodi path:", fname)
  return fname

def getImage(args, mediatype, media, title, atype, filename, source, target):
  global NOT_AVAILABLE_CACHE, LOCAL_ALT

  orig_source = source

  # If it's not a remote file, maybe we just need to copy it from
  # the alt local folder to our output folder?
  if LOCAL_ALT and not source.startswith("http://") and not source.startswith("https://"):
    source = pathToAltLocal(source)

  # We've already failed to download this URL before, so fail quickly
  if source in NOT_AVAILABLE_CACHE:
    NOT_AVAILABLE_CACHE[source] += 1
    warning(args, "**UNAVAILABLE**", atype, title, "Prior download failed: %4d" % NOT_AVAILABLE_CACHE[source], source)
    return None

  # Try the filesystem copy if not http/https...
  if not source.startswith("http://") and not source.startswith("https://"):
    newsource = source
    found_file = os.path.exists(newsource)
    debug2(atype, "Lookup non-HTTP file using current URL:", newsource, (" [%s]" % ("SUCCESS" if found_file else "FAIL")))

    # Try using name of file plus artwork type and same extension as
    # alternative source
    if LOCAL_ALT and not found_file:
      currentsource = newsource

      newsource = formatArtworkFilename(mediatype, pathToAltLocal(os.path.splitext(filename)[0]),
                                        atype, media.get("season", None), singleFolder=args.singlefolders)
      newsource = "%s%s" % (newsource, os.path.splitext(source)[1])

      if newsource != currentsource:
        found_file = os.path.exists(newsource)
        debug2(atype, "Lookup non-HTTP file using altlocal path:", newsource, (" [%s] (based on media filename)" % ("SUCCESS" if found_file else "FAIL")))

    if found_file:
      if not args.dryrun:
        if newsource != target:
          debug2(atype, "Copying to local file:", target)
          dtarget= os.path.dirname(target)
          if not os.path.exists(dtarget): os.makedirs(dtarget)
          shutil.copyfile(newsource, target)
          debug2(atype, ("Copied %d bytes of data:" % os.path.getsize(target)), target)
        else:
          debug2(atype, "WARNING: Target is same as source - skipping copy:", target)
      else:
        debug2(atype, "Dry run, skipping file creation:", target)

      info(args, "%9d bytes" % os.path.getsize(newsource), atype, title, None, None, target=target)
      return target

    # Couldn't copy anything and don't have an alternative source, so stay with
    # current local file unless args.nokeep.
    if not LOCAL_ALT:
      result = None if args.nokeep else pathToLocal(orig_source)
      debug2(atype, "No alt source for non-HTTP files, using:", result)
      return result

    warning(args, "**UNAVAILABLE**", atype, title, "Source not available", source)
    NOT_AVAILABLE_CACHE[source] = 0
    return None

  # Download from the web site...
  idata = ""
  try:
    debug2(atype, "Downloading URL", source)
    response = urllib2.urlopen(source)
    idata = response.read()
    debug2(atype, ("Downloaded %d bytes of data:" % len(idata)), source)
  except Exception as e:
    debug2(atype, "Failure to download!", str(e))
    warning(args, "**UNAVAILABLE**", atype, title, str(e), source)
    NOT_AVAILABLE_CACHE[source] = 0
    return None

  if not args.dryrun:
    try:
      dtarget= os.path.dirname(target)
      if not os.path.exists(dtarget): os.makedirs(dtarget)

      ifile = open(target, "wb")
      ifile.write(idata)
      ifile.flush()
      os.fsync(ifile.fileno())
      ifile.close()
      debug2(atype, "Downloaded file written to:", target)
    except:
      raise
  else:
      debug2(atype, "Dry run, skipping file creation:", target)

  info(args, "%9d bytes" % len(idata), atype, title, None, None, target=target)
  return target

def getJSONdata(args):
  global COUNT, TOTAL

  if args.input != "-":
    inputfile = codecs.open(args.input, "rb", encoding="utf-8")
    data= inputfile.read()
    inputfile.close()
    jdata = json.loads(data)
  else:
    data=[]
    for line in sys.stdin: data.append(line)
    jdata = json.loads("".join(data))

  COUNT = 0
  TOTAL = len(jdata)
  for t in jdata:
    if "tvshowid" in t:
      if args.season and "seasons" in t:
        TOTAL += len(t["seasons"])
      if args.episode and "seasons" in t:
        for s in t["seasons"]:
          TOTAL += len(s["episodes"])

  return jdata

def showConfig(args, download_items, season_items, episode_items):
  global LOCAL_DIR, LOCAL_ALT, XBMC_PATH

  def _blank(value):
    return (value if value else "Not specified")

  printerr("Current configuration:")
  printerr("")
  printerr("  Local Path    : %s" % _blank(LOCAL_DIR))
  printerr("  Alt Local     : %s" % _blank(LOCAL_ALT))
  printerr("  Kodi Path     : %s" % _blank(XBMC_PATH))
  printerr("  Extra Fanart  : %s (max: %d)" % (_blank(args.extrafanart), args.extrafanartmax))
  printerr("  Extra Thumbs  : %s (max: %d)" % (_blank(args.extrathumbs), args.extrathumbsmax))
  printerr("  Read Only     : %s" % ("Yes" if args.readonly else "No"))
  printerr("  Dry Run       : %s" % ("Yes" if args.dryrun else "No"))
  printerr("  Single Folder : %s" % ("Yes" if args.singlefolders else "No"))
  printerr("")
  printerr("  Artwork       : %s" % listToString(download_items, translate=True))
  if args.season:
    printerr("")
    printerr("  TV seasons    : %s" % listToString(season_items, translate=True))
  if args.episode:
    printerr("")
    printerr("  TV episodes   : %s" % listToString(episode_items, translate=True))
  printerr("")
  printerr("  Checking      : %s" % listToString(args.check))
  printerr("")

def listToString(aList, translate=False):
  if not aList: return "Not specified"

  tmpStr = ""

  for artitem in aList:
    if tmpStr != "": tmpStr = "%s\n%s" % (tmpStr, " " * 18)

    if "type" in artitem:
      atype = artitem["type"]
      asuffix = artitem["suffix"]
    else:
      atype = asuffix = artitem

    if translate:
      tmpStr = "%s%-12s as %s.[png,jpg]" % (tmpStr, atype, asuffix)
    else:
      tmpStr = "%s%s" % (tmpStr, atype)

  return tmpStr

def init():
  global NOT_AVAILABLE_CACHE, LOCAL_DIR, LOCAL_ALT, XBMC_PATH, VERBOSE

  if sys.version_info >= (3, 1):
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
  else:
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout)
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr)

  NOT_AVAILABLE_CACHE = {}

  parser = argparse.ArgumentParser(description="Downloads specific artwork types (default: clearart, clearlogo) \
                                                based on URLs in media library (ie. original source) creating local \
                                                versions. Avoids retrieving artwork from Kodi texture cache as this is \
                                                often resized, resampled and of lower quality. Optionally output data \
                                                that can be used to update the media library to use new local versions of \
                                                artwork, replacing any current remote versions. The same data will \
                                                also remove invalid remote artwork from the library.", \
                    formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=25,width=90))

  parser.add_argument("-l", "--local", metavar="DIRECTORY", \
                      help="Local DIRECTORY into which artwork will be WRITTEN, eg. /freenas/media/")

  parser.add_argument("-p", "--prefix", metavar="PATH", \
                      help="Kodi PATH prefix (eg. nfs://192.168.0.3/mnt/share/media/) that \
                            will be substituted by --local DIRECTORY when traversing media files. \
                            This is typically the root of the media source as defined in sources.xml")

  parser.add_argument("-A", "--altlocal", metavar="PATH", \
                      help="Alternate local directory which may contain artwork that can be READ \
                            and copied to --local, could be the original source folder")

  parser.add_argument("-i", "--input", default="-", const="-", nargs="?", metavar="FILENAME", \
                      help="Optional FILENAME containing JSON movie/tvshow data for processing. \
                            Read from stdin if FILENAME is - or not specified")

  parser.add_argument("-o", "--output", const="-", nargs="?", metavar="FILENAME", \
                      help="Output a data structure suitable for consumption by texturecache.py [test]set, \
                            used to update an Kodi media library converting remote URLs into \
                            local URLs. Written to stdout if FILENAME is - or not specified")

  parser.add_argument("--dryrun", action="store_true", \
                      help="Attempt downloads, but don't create any new files")

  parser.add_argument("-r", "--readonly", action="store_true", \
                      help="Don't download (or, if specified, copy from --altlocal) any new artwork, \
                            only use existing --local artwork. Warn about artwork that needs to be \
                            copied or downloaded, unless --nokeep is enabled in which case such artwork \
                            will be removed.")

  parser.add_argument("--ignorebadprefix", action="store_true", \
                      help="Don't display a warning for media files with a path that does not match \
                            that set by --prefix")

  parser.add_argument("--overwrite", action="store_true", \
                      help="Overwrite existing local artwork if the remote file download is successful")

  parser.add_argument("-a", "--artwork", nargs="+", metavar="TYPE", \
                      help="Artwork TYPE(s) for download, eg. \"--artwork  discart banner\" \
                            Specify TYPE:SUFFIX if SUFFIX differs from TYPE, \
                            eg. \"--artwork thumb:poster\" would create \"thumb\" library items \
                            with a \"-poster\" filename suffix")

  parser.add_argument("-c", "--check", nargs="+", metavar="TYPE", \
                      help="Check the named artwork TYPE(s) - or \"all\" - and warn if any internet \
                            (http/https) URLs are detected")

  parser.add_argument("-s", "--season", nargs="*", metavar="TYPE", \
                      help="For TV shows, process season items (default: poster banner landscape)")

  parser.add_argument("-e", "--episode", nargs="*", metavar="TYPE", \
                      help="For TV shows, process episode items (default: thumb)")

  parser.add_argument("-1", "--singlefolders", action="store_true", \
                      help="Movies are in individual folders so don't use the movie-name as a prefix")

  parser.add_argument("-nk", "--nokeep", action="store_true", \
                      help="Don't keep artwork if not able to match with pre-existing local artwork")

  parser.add_argument("-xf", "--extrafanart", metavar="PATH", \
                      help="Local directory path to a single shared extrafanart folder. If not specified, \
                            alongside media will be assumed for fanart# artwork")

  parser.add_argument("-xfm", "--extrafanartmax", type=int, default=4, metavar="#", \
                      help="Maximum number of fanart# items to process - default is 4. A value of 0 will clear all items.")

  parser.add_argument("-xt", "--extrathumbs", metavar="PATH", \
                      help="Local directory path to a single shared extrathumb folder. If not specified, \
                            alongside media will be assumed for thumb# artwork")

  parser.add_argument("-xft", "--extrathumbsmax", type=int, default=4, metavar="#", \
                      help="Maximum number of thumb# items to process - default is 4. A value of 0 will clear all items.")

  parser.add_argument("--info", action="store_true", \
                      help="Display informational output to stdout")

  group = parser.add_mutually_exclusive_group()
  group.add_argument("-q", "--quiet", action="store_true", \
                      help="Silence warnings about missing artwork (NEEDED etc.)")
  group.add_argument("-v", "--verbose", action="store_true", \
                      help="Display diagnostic output")

  args = parser.parse_args()

  VERBOSE = args.verbose

  if args.season == []: args.season = ["poster", "banner", "landscape"]
  if args.episode == []: args.episode = ["thumb"]

  LOCAL_DIR = args.local
  if LOCAL_DIR and LOCAL_DIR[-1] not in ["/", "\\"]: LOCAL_DIR += getSlash(LOCAL_DIR)

  LOCAL_ALT = args.altlocal
  if LOCAL_ALT and LOCAL_ALT[-1] not in ["/", "\\"]: LOCAL_ALT += getSlash(LOCAL_ALT)

  XBMC_PATH = args.prefix
  if XBMC_PATH and XBMC_PATH[-1] not in ["/", "\\"]: XBMC_PATH += getSlash(XBMC_PATH)

  # Disable downloading if output path not set, or prefix not known
  # as then impossible to create valid output filenames
  if not LOCAL_DIR: args.readonly = True
  if not XBMC_PATH: args.readonly = True

  if LOCAL_DIR and not os.path.exists(LOCAL_DIR):
    parser.error("local DIRECTORY %s does not exist!" % LOCAL_DIR)
  if LOCAL_ALT and not os.path.exists(LOCAL_ALT):
    parser.error("alternate local PATH %s does not exist!" % LOCAL_ALT)

  if args.extrafanart and not os.path.exists(args.extrafanart):
    parser.error("extrafanart local PATH %s does not exist!" % args.extrafanart)

  if args.extrathumbs and not os.path.exists(args.extrathumbs):
    parser.error("extrathumbs local PATH %s does not exist!" % args.extrathumbs)

  if args.input != "-" and not os.path.exists(args.input):
    parser.error("input FILENAME %s does not exist!" % args.input)

  return args

def main(args):

  download_items = itemList(args.artwork)
  season_items = itemList(args.season)
  episode_items = itemList(args.episode)

  if args.verbose: showConfig(args, download_items, season_items, episode_items)

  # If --readonly and no --local or --prefix specified, don't download anything
  # as without anywhere to look for existing art there's no point...
  if args.readonly and not (args.local and args.prefix):
    download_items = []
    season_items = []
    episode_items = []

  data = getJSONdata(args)

  workitems = []

  for media in data:
    if "movieid" in media:
      mediatype = "movie"
    elif "setid" in media:
      mediatype = "set"
    elif "tvshowid" in media:
      mediatype = "tvshow"
    else:
      printerr("FATAL: Unsupported input data - movie, sets and tvshow data for now!")
      sys.exit(1)

    mediatitle = media["label"]

    if mediatype == "tvshow":
      workitem = processItem(args, "tvshow", media, download_items)
      if args.output and workitem["items"]: workitems.append(workitem)

      mediafile = media["file"]

      for season in media.get("seasons",[]):
        if args.season:
          workitem = processItem(args, "season", season, season_items, showTitle=mediatitle, showPath=mediafile)
          if args.output and workitem["items"]: workitems.append(workitem)

        if args.episode:
          for episode in season.get("episodes", []):
            workitem = processItem(args, "episode", episode, episode_items, showTitle=mediatitle)
            if args.output and workitem["items"]: workitems.append(workitem)
    else:
      workitem = processItem(args, mediatype, media, download_items)
      if args.output and workitem["items"]: workitems.append(workitem)

  printerr("")

  if args.output:
    data = json.dumps(workitems, indent=2, ensure_ascii=True, sort_keys=True)
    if args.output == "-":
      printout(data)
    else:
      outfile = codecs.open(args.output, "wb", encoding="utf-8")
      outfile.write(data)
      outfile.close()

  sys.exit(0)

try:
  main(init())
except (KeyboardInterrupt, SystemExit) as e:
  if type(e) == SystemExit: sys.exit(int(str(e)))
