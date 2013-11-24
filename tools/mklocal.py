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
# https://github.com/MilhouseVH/mklocal.py
#
# Usage:
#
#  See built-in help (run script without parameters).
#
#  For details on artwork naming conventions supported by this script:
#     http://wiki.xbmc.org/index.php?title=Frodo_FAQ#Local_images
#
################################################################################

#version 0.1.0

from __future__ import print_function
import sys, os, codecs, json, argparse, re, shutil

if sys.version_info >= (3, 0):
  import urllib.request as urllib2
else:
  import urllib2

def printout(msg, newline=True):
  endchar = "\n" if newline else ""
  print(msg, file=sys.stdout, end=endchar)
  sys.stderr.flush()

def printerr(msg, newline=True):
  endchar = "\n" if newline else ""
  print(msg, file=sys.stderr, end=endchar)
  sys.stderr.flush()

def info(args, msg, atype, title, reason = None, url = None, target = None):
  line = "DRYRUN " if args.dryrun else ""
  if reason or url:
    line = "%s%-15s - %-10s - %-45s" % (line, msg, atype.center(10), addEllipsis(45, title))
    if reason: line = "%s [%s]" % (line, reason)
    if url:    line = "%s %s" % (line, url)
  elif target:
    line = "%s%-15s - %-10s - %-45s -> %s" % (line, msg, atype.center(10), addEllipsis(45, title), target)
  else:
    line = "%s%-15s - %-10s - %s" % (line, msg, atype.center(10), title)
  printerr(line)

def warning(args, msg, atype, title, reason = None, url = None, target = None):
  if not args.quiet:
    info(args, msg, atype, title, reason, url, target)

def debug(indent, msg):
  global VERBOSE
  if VERBOSE: printerr("##DEBUG## %s%s" % (" "*(indent*2), msg))

def debug2(atype, msg, value1="", value2=""):
  if value1:
    debug(2, "[%-10s] %-40s %s%s" % (atype, msg, value1, value2))
  else:
    debug(2, "[%-10s] %s" % (atype, msg))

def addEllipsis(maxlen, aStr):
  if len(aStr) <= maxlen: return aStr

  ileft = int(maxlen/2) - 2
  iright = int(maxlen/2) - 1

  return "%s...%s" % (aStr[0:ileft], aStr[-iright:])

def pathToLocal(infile):
  global LOCAL_DIR, XBMC_PATH

  if not infile: return infile
  if not XBMC_PATH: return infile
  if not LOCAL_DIR: return infile
  return re.sub('^%s' % XBMC_PATH, LOCAL_DIR, infile)

def pathToAltLocal(infile):
  global LOCAL_ALT, XBMC_PATH

  if not infile: return infile
  if not XBMC_PATH: return infile
  if not LOCAL_ALT: return infile
  return re.sub('^%s' % XBMC_PATH, LOCAL_ALT, infile)

def pathToXBMC(infile):
  global LOCAL_DIR, XBMC_PATH

  if not infile: return infile
  if not LOCAL_DIR: return infile
  if not XBMC_PATH: return infile
  return re.sub('^%s' % LOCAL_DIR, XBMC_PATH, infile)

def itemList(aList):
  newList = []
  if aList:
    for aname in aList:
      (aname, value) = (aname, aname) if aname.find(":") == -1 else aname.split(":")
      if aname == "clearlogo" and value == "clearlogo": value = "logo"
      newList.append({"type": aname, "suffix": value})
  return newList

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
    file = os.path.dirname(member["file"])
    pos = file.rfind(setname)
    if pos != -1:
      return "%s%s" % (file[:pos + len(setname)], getSlash(file))
  else:
    return None

# Use this method if unable to find parent based on title, will
# try to match based on a common parent
def findCommonSetParent(setname, members, level=0):
  commonparent = os.path.dirname(members[0]["file"])
  for i in range(0, level):
    commonparent = os.path.dirname(commonparent)
    if commonparent == "": return ""

  sameparent = True
  for member in members:
    file = member["file"]
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
  # XBMC sets will either be together in one shared folder, or individual
  # folders below a shared parent, so only need to consider two levels (the file
  # folder and the parent)
  if level > 1: return

  if not counts: counts = {}

  # Walk "back" up the path for each level, counting frequency
  for member in members:
    parent = os.path.dirname(member["file"])
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

    # Now sort just the most frquently used paths by descending length
    sorted_counts = [x for x in sorted(counts, key=len, reverse=True) if counts[x] == maxfreq]

    return "%s%s" % (sorted_counts[0], getSlash(sorted_counts[0]))

def formatArtworkFilename(args, mediatype, filename, suffix, season):
  if mediatype == "movie":
    if args.singlefolders:
      return suffix
    else:
      return "%s-%s" % (filename, suffix)
  if mediatype == "episode":
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
  keepitem = {}
  keepitem["items"] = {}

  # Use first file in files[] for "set"
  if mediatype == "set":
    mediafile = findSetParent(media["title"], media["tc.members"])
  else:
    mediafile = media.get("file", showPath)

  mediatitle = "%s %s" % (showTitle, media["label"]) if showTitle else media["label"]

  debug(0, "mediatype [%s]; mediatitle [%s]" % (mediatype, mediatitle))
  debug(1, "mediafile is [%s]" % mediafile)

  if XBMC_PATH and not mediafile.startswith(XBMC_PATH):
    if not args.ignorebadprefix:
      warning(args, "** SKIPPING **", "Bad Prefix", mediatitle, "XBMC path does not match prefix", mediafile)
    return workitem

  filename = os.path.splitext(pathToLocal(mediafile))[0]

  debug(1, "local root name would be [%s]" % (filename))

  # seasonid requires JSON API v6.10.0+
  libraryid = "%sid" % mediatype
  if libraryid in media:
    workitem["type"] = mediatype
    workitem["title"] = mediatitle
    workitem["libraryid"] = media[libraryid]

  art = media["art"]

  for artitem in download_items:
    oldname = art.get(artitem["type"], None)
    if oldname: oldname = oldname[8:-1]

    artpath = formatArtworkFilename(args, mediatype, filename, artitem["suffix"], media.get("season", None))

    label = "art.%s" % artitem["type"]

    if label in keepitem["items"]:
      debug(1, "already found a value for artwork type [%s] - ignoring" % artitem["type"])
      continue

    newname = processArtwork(args, mediatype, media, mediatitle, artitem["type"], mediafile, oldname, artpath)

    if not newname and oldname:
      debug2(artitem["type"], "Assigning null value to library item")
      workitem["items"][label] = None
    else:
      if newname and newname != oldname:
        debug2(artitem["type"], "Changing library value to:", newname)
        workitem["items"][label] = newname
        keepitem["items"][label] = newname
      else:
        debug2(artitem["type"], "No library change required, keeping:", oldname)
        keepitem["items"][label] = newname

  if args.check:
    clist = args.check if args.check != ["all"] else [x for x in art if not x.startswith("tvshow.") ]
    for artitem in clist:
      if artitem in art:
        aname = art[artitem][8:-1]
        if aname.startswith("http"):
          info(args, "**REMOTE FILE**", artitem, mediatitle, "Remote URL found", aname)

  return workitem

def processArtwork(args, mediatype, media, title, atype, filename, currentname, pathname):
  debug(1, "artwork type [%s] known by XBMC as [%s]" % (atype, currentname))

  # See if we already have a file of the desired artwork type, either in
  # jpg or png format. If found, use it as the source for this artwork type.
  for source_type in [".png", ".jpg"]:
    target = "%s%s" % (pathname, source_type)
    if os.path.exists(target):
      debug2(atype, "Found pre-existing local file:", target)
      target = pathToXBMC(target)
      debug2(atype, "Converting local filename to XBMC path:", target)
      return target

  # If we don't currently have a remote source, return nothing
  if not currentname: return None

  # If we're not downloading, just return the current file name
  if args.readonly:
    warning(args, "**  NEEDED  **", atype, title, "readonly enabled", currentname)
    return currentname

  # We're going to create a new file.
  # We have a remote source (currentname) and a partial
  # name for the target - need to append the file format type.
  target = "%s%s" % (pathname, os.path.splitext(currentname)[1].lower())

  # Download the new artwork and convert the name of the new file
  # back into a valid XBMC path.
  fname = pathToXBMC(getImage(args, mediatype, media, title, atype, filename, currentname, target))
  debug2(atype, "Converting local filename to XBMC path:", fname)
  return fname

def getImage(args, mediatype, media, title, atype, filename, source, target):
  global NOT_AVAILABLE_CACHE, LOCAL_ALT

  # If it's not a remote file, maybe we just need to copy it from
  # the alt local folder to our output folder?
  if LOCAL_ALT and not source.startswith("http://"):
    source = pathToAltLocal(source)

  # We've already failed to download this url before, so fail quickly
  if source in NOT_AVAILABLE_CACHE:
    NOT_AVAILABLE_CACHE[source] += 1
    warning(args, "**UNAVAILABLE**", atype, title, "Prior download failed: %4d" % NOT_AVAILABLE_CACHE[source], source)
    return None

  # Try the filesystem copy if not http...
  if not source.startswith("http://"):
    newsource = source
    found_file = os.path.exists(newsource)
    debug2(atype, "Lookup non-HTTP file using altlocal path:", newsource, (" [%s]" % ("SUCCESS" if found_file else "FAIL")))

    # Try using name of file plus artwork type and same extension as
    # alternative source
    if LOCAL_ALT and not found_file:
      currentsource = newsource

      newsource = formatArtworkFilename(args, mediatype, pathToAltLocal(os.path.splitext(filename)[0]), atype, media.get("season", None))
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
          debug2(atype, "WARNING! target is same as source - skipping copy:", target)
      else:
        debug2(atype, "Dry run, skipping file creation:", target)

      info(args, "%9d bytes" % os.path.getsize(newsource), atype, title, None, None, target=target)
      return target

    # Couldn't copy anything and don't have an alternative source, so stay with current local file
    if not LOCAL_ALT:
      debug2(atype, "No alternate source for non-HTTP files, using:", target)
      return target

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
  print(args)
  printerr("Current configuration:")
  printerr("")
  printerr("  Local Path    : %s" % _blank(LOCAL_DIR))
  printerr("  Alt Local     : %s" % _blank(LOCAL_ALT))
  printerr("  XBMC Path     : %s" % _blank(XBMC_PATH))
  printerr("  Read Only     : %s" % ("Yes" if args.readonly else "No"))
  printerr("  Dry Run       : %s" % ("Yes" if args.dryrun else "No"))
  printerr("  Single Folder : %s" % ("Yes" if args.singlefolders else "No"))
  printerr("")
  printerr("  Artwork       : %s" % listToString(download_items, translate=True))
  if args.season:
    printerr("")
    printerr("  TV Seasons    : %s" % listToString(season_items, translate=True))
  if args.episode:
    printerr("")
    printerr("  TV Episodes   : %s" % listToString(episode_items, translate=True))
  printerr("")
  printerr("  Checking      : %s" % listToString(args.check))
  printerr("")

def listToString(aList, translate=False):
  if not aList: return "Not Specified"

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
                                                based on urls in media library (ie. original source) creating local \
                                                versions. Avoids retrieving artwork from XBMC Texture Cache as this is \
                                                often resized, resampled and of lower quality. Optionally output data \
                                                that can be used to update the media library to use new local versions of \
                                                artwork, replacing any current remote versions. The same data will \
                                                also remove invalid remote artwork from the library.", \
                    formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=25,width=90))

  parser.add_argument("-l", "--local", metavar="DIRECTORY", \
                      help="Local DIRECTORY into which artwork will be WRITTEN, eg. /freenas/media/Images/")

  parser.add_argument("-p", "--prefix", metavar="PATH", \
                      help="XBMC PATH prefix (eg. nfs://192.168.0.3/mnt/share/media/) that \
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
                            used to update an XBMC media library converting remote urls into \
                            local urls. Written to stdout if FILENAME is - or not specified")

  parser.add_argument("--dryrun", action="store_true", \
                      help="Don't create anything (although downloads will be attempted)")

  parser.add_argument("-r", "--readonly", action="store_true", \
                      help="Don't download (or, if specified, copy from --altlocal) new artwork, \
                            only use existing --local artwork")

  parser.add_argument("--ignorebadprefix", action="store_true", \
                      help="Don't display a warning for media files with a path that does not match \
                            that set by --prefix")

  parser.add_argument("-a", "--artwork", nargs="+", metavar="TYPE", \
                      help="Artwork TYPE(s) for download, eg. \"--artwork  discart banner\" \
                            Specify TYPE:SUFFIX if SUFFIX differs from TYPE, \
                            eg. \"--artwork thumb:poster\" would create \"thumb\" library items \
                            with a \"-poster\" filename suffix")

  parser.add_argument("-c", "--check", nargs="+", metavar="TYPE", \
                      help="Check the named artwork TYPE(s) - or \"all\" - and warn if any internet \
                            (http) URLs are detected")

  parser.add_argument("-s", "--season", nargs="*", metavar="TYPE", \
                      help="For TV Shows, process season items (default: poster banner landscape)")

  parser.add_argument("-e", "--episode", nargs="*", metavar="TYPE", \
                      help="For TV Shows, process episode items (default: thumb)")

  parser.add_argument("-1", "--singlefolders", action="store_true", \
                      help="Movies are in individual folders so don't use the movie-name as a prefix")

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
  if LOCAL_DIR and LOCAL_DIR[-1] not in ["/", "\\"]: LOCAL_DIR += "/"

  LOCAL_ALT = args.altlocal
  if LOCAL_ALT and LOCAL_ALT[-1] not in ["/", "\\"]: LOCAL_ALT += "/"

  XBMC_PATH = args.prefix
  if XBMC_PATH and XBMC_PATH[-1] not in ["/", "\\"]: XBMC_PATH += "/"

  # Disable downloading if output path not set, or prefix not known
  # as then impossible to create valid output filenames
  if not LOCAL_DIR: args.readonly = True
  if not XBMC_PATH: args.readonly = True

  if not args.readonly:
    if not os.path.exists(LOCAL_DIR):
      parser.error("local DIRECTORY %s does not exist!" % LOCAL_DIR)
    if LOCAL_ALT and not os.path.exists(LOCAL_ALT):
      parser.error("alternate local PATH %s does not exist!" % LOCAL_ALT)

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
    data = json.dumps(workitems, indent=2, ensure_ascii=True, sort_keys=False)
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
