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

def warning(msg, atype, title, reason = None, url = None, dryrun=False, target=None):
  line = "DRYRUN " if dryrun else ""
  if reason or url:
    line = "%s%-15s - %-10s - %-45s" % (line, msg, atype.center(10), addEllipsss(45, title))
    if reason: line = "%s [%s]" % (line, reason)
    if url:    line = "%s %s" % (line, url)
  elif target:
    line = "%s%-15s - %-10s - %-45s -> %s" % (line, msg, atype.center(10), addEllipsss(45, title), target)
  else:
    line = "%s%-15s - %-10s - %s" % (line, msg, atype.center(10), title)
  printerr(line)

def debug(indent, msg):
  global VERBOSE
  if VERBOSE: printerr("##DEBUG## %s%s" % (" "*(indent*2), msg))

def addEllipsss(maxlen, aStr):
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

def itemListToDict(aList):
  newDict = {}
  if aList:
    for aname in aList:
      (aname, value) = (aname, aname) if aname.find(":") == -1 else aname.split(":")
      if aname == "clearlogo" and value == "clearlogo": value = "logo"
      newDict.update({aname: value})
  return newDict

def processItem(args, mediatype, media, download_items, showTitle=None, showPath=None):
  global XBMC_PATH, COUNT, TOTAL

  COUNT += 1
  printerr("Progress: %d of %d\r" % (COUNT, TOTAL), newline=False)

  workitem = {}
  workitem["items"] = {}

  mediafile = media.get("file", showPath)
  mediatitle = "%s %s" % (showTitle, media["label"]) if showTitle else media["label"]

  debug(0, "mediatype [%s]; mediatitle [%s]" % (mediatype, mediatitle))
  debug(1, "mediafile is [%s]" % mediafile)

  if XBMC_PATH and not mediafile.startswith(XBMC_PATH):
    if not args.ignorebadprefix:
      warning("** SKIPPING **", "Bad Prefix", mediatitle, "XBMC path does not match prefix", mediafile, args.dryrun)
    return workitem

  filename = os.path.splitext(pathToLocal(mediafile))[0]

  debug(1, "local root name would be [%s]" % (filename))

  if mediatype != "season":
    workitem["type"] = mediatype
    workitem["title"] = mediatitle
    workitem["libraryid"] = media["%sid" % mediatype]

  art = media["art"]

  for aitem in download_items:
    oldname = art.get(aitem, None)
    if oldname: oldname = oldname[8:-1]

    if mediatype in ["movie", "episode"]:
      artpath = "%s-%s" % (filename, download_items[aitem])
    elif mediatype == "season":
      if media["season"] == 0:
        season_num = "season-specials"
      else:
        season_num = "season%02d" % media["season"]
      artpath = "%s%s-%s" % (filename, season_num, download_items[aitem])
    else:
      artpath = "%s%s" % (filename, download_items[aitem])

    newname = processArtwork(mediatype, mediatitle, aitem, mediafile, oldname, artpath, nodownload=args.nodownload, dryrun=args.dryrun)

    if mediatype == "season":
      debug(2, "[%s] Can't assign values to library for season artwork, ignoring [%s]" % (aitem, newname))
    else:
      if not newname and oldname:
        debug(2, "[%s] Assigning null value to library (removal)" % (aitem))
        workitem["items"]["art.%s" % aitem] = None
      else:
        if newname and newname != oldname:
          debug(2, "[%s] Changing library value to [%s]" % (aitem, newname))
          workitem["items"]["art.%s" % aitem] = newname
        else:
          debug(2, "[%s] No library change required, keeping: [%s]" % (aitem, oldname))

  if args.check:
    clist = args.check if args.check != ["all"] else [x for x in art if not x.startswith("tvshow.") ]
    for aitem in clist:
      if aitem in art:
        aname = art[aitem][8:-1]
        if aname.startswith("http"):
          warning("**REMOTE FILE**", aitem, mediatitle, "Convert remote URL to local", aname, args.dryrun)

  return workitem

def processArtwork(mediatype, title, atype, filename, currentname, pathname, nodownload=False, dryrun=False):
  debug(1, "artwork type [%s] known by XBMC as [%s]" % (atype, currentname))

  # See if we already have a file of the desired artwork type, either in
  # jpg or png format. If found, use it as the source for this artwork type.
  for source_type in [".png", ".jpg"]:
    target = "%s%s" % (pathname, source_type)
    if os.path.exists(target):
      debug(2, "[%s] Found pre-existing local: [%s]" % (atype, target))
      target = pathToXBMC(target)
      debug(2, "[%s] Converting filename to XBMC path: [%s]" % (atype, target))
      return target

  # If we don't currently have a remote source, return nothing
  if not currentname: return None

  # We're going to create a new file.
  # We have a remote source (currentname) and a partial
  # name for the target - need to append the file format type.
  target = "%s%s" % (pathname, os.path.splitext(currentname)[1].lower())

  # If we're not downloading, just return the current file name
  if nodownload:
    warning("**  NEEDED  **", atype, title, "Downloading is disabled", currentname, dryrun)
    target = pathToXBMC(target)
    debug(2, "[%s] Not downloading, using: [%s]" % (atype, target))
    return target

  # Download the new artwork and convert the name of the new file
  # back into a valid XBMC path.
  fname = pathToXBMC(getImage(title, atype, filename, currentname, target, dryrun))
  debug(2, "[%s] Converting filename to XBMC path: [%s]" % (atype, fname))
  return fname

def getImage(title, atype, filename, source, target, dryrun):
  global NOT_AVAILABLE_CACHE, LOCAL_ALT

  # If it's not a remote file, maybe we just need to copy it from
  # the alt local folder to our output folder?
  if LOCAL_ALT and not source.startswith("http://"):
    source = pathToAltLocal(source)

  # We've already failed to download this url before, so fail quickly
  if source in NOT_AVAILABLE_CACHE:
    NOT_AVAILABLE_CACHE[source] += 1
    warning("**UNAVAILABLE**", atype, title, "Prior download failed: %4d" % NOT_AVAILABLE_CACHE[source], source, dryrun)
    return None

  # Try the filesystem copy if not http...
  if not source.startswith("http://"):
    newsource = source
    found_file = os.path.exists(newsource)
    debug(2, "[%s] Lookup non-HTTP file [%s] [%s]" % (atype, newsource, "SUCCESS" if found_file else "FAIL"))

    # Try using name of file plus artwork type and same extension as
    # alternative source
    if LOCAL_ALT and not found_file:
      newsource = "%s-%s%s" % (pathToAltLocal(os.path.splitext(filename)[0]), atype, os.path.splitext(source)[1])
      found_file = os.path.exists(newsource)
      debug(2, "[%s] Lookup non-HTTP file [%s] [%s] (based on media filename)" % (atype, newsource, "SUCCESS" if found_file else "FAIL"))

    if found_file:
      if not dryrun:
        debug(2, "[%s] Copying to local: [%s]" % (atype, target))
        dtarget= os.path.dirname(target)
        if not os.path.exists(dtarget): os.makedirs(dtarget)
        shutil.copyfile(newsource, target)
        debug(2, "[%s] Copied to local %d bytes: [%s]" % (atype, os.path.getsize(target), target))
      else:
        debug(2, "[%s] (DRYRUN) Skipping copy to local: [%s]" % (atype, target))

      warning("%9d bytes" % os.path.getsize(newsource), atype, title, None, None, dryrun, target=target)
      return target

    # Couldn't copy anything and don't have an alternative source, so stay with current local file
    if not LOCAL_ALT:
      debug(2, "[%s] No alternate source for non-HTTP files, using: [%s]" % (atype, target))
      return target

    warning("**UNAVAILABLE**", atype, title, "Source not readable", source, dryrun)
    NOT_AVAILABLE_CACHE[source] = 0
    return None

  # Download from the web site...
  idata = ""
  try:
    debug(2, "[%s] Downloading URL [%s]" % (atype, source))
    response = urllib2.urlopen(source)
    idata = response.read()
    debug(2, "[%s] Successfully downloaded %d bytes of data" % (atype, len(idata)))
  except Exception as e:
    debug(2, "[%s] Failure to download [%s]" % (atype, str(e)))
    warning("**UNAVAILABLE**", atype, title, str(e), source, dryrun)
    NOT_AVAILABLE_CACHE[source] = 0
    return None

  if not dryrun:
    try:
      dtarget= os.path.dirname(target)
      if not os.path.exists(dtarget): os.makedirs(dtarget)

      ifile = open(target, "wb")
      ifile.write(idata)
      ifile.flush()
      os.fsync(ifile.fileno())
      ifile.close()
      debug(2, "[%s] Download written to [%s]" % (atype, target))
    except:
      raise
  else:
      debug(2, "[%s] (DRYRUN) Skipping file creation: [%s]" % (atype, target))

  warning("%9d bytes" % len(idata), atype, title, None, None, dryrun, target=target)
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
      TOTAL += len(t["seasons"]) if args.season else 0
      for s in t["seasons"]:
        TOTAL += len(s["episodes"]) if args.episode else 0

  return jdata

def showConfig(args, mDownload):
  global LOCAL_DIR, LOCAL_ALT, XBMC_PATH

  printerr("Current configuration:")
  printerr("")
  printerr("  Local Path : %s" % LOCAL_DIR)
  printerr("  Alt Local  : %s" % LOCAL_ALT)
  printerr("  XBMC Path  : %s" % XBMC_PATH)
  printerr("  Downloading: %s" % ("No" if args.nodownload else "Yes"))
  printerr("  Dry Run    : %s" % ("Yes" if args.dryrun else "No"))
  printerr("")
  printerr("  Downloading: %s" % listToString(mDownload, translate=True))
  if args.season:
    printerr("")
    printerr("  TV Seasons : %s" % listToString(args.season))
  if args.episode:
    printerr("")
    printerr("  TV Episodes: %s" % listToString(args.episode))
  printerr("")
  printerr("  Checking   : %s" % listToString(args.check))
  printerr("")

def listToString(aList, translate=False):
  if not aList: return "None"

  tmpStr = ""

  for aname in aList:
    if tmpStr != "": tmpStr = "%s\n%s" % (tmpStr, " " * 15)
    if translate:
      tmpStr = "%s%-12s as %s.[png,jpg]" % (tmpStr, aname, aList[aname])
    else:
      tmpStr = "%s%s" % (tmpStr, aname)

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

  parser = argparse.ArgumentParser(description='Downloads specific artwork types (default: clearart, clearlogo) \
                                                based on urls in media library (ie. original source) creating local \
                                                versions. Avoids retrieving artwork from XBMC Texture Cache as this is \
                                                often resized, resampled and of lower quality. Optionally output data \
                                                that can be used to update the media library to use new local versions of \
                                                artwork, replacing any current remote versions. The same data will \
                                                also remove invalid remote artwork from the library.', \
                    formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=25,width=90))

  parser.add_argument("-l", "--local", metavar="DIRECTORY", \
                      help="Local DIRECTORY into which artwork will be WRITTEN, eg. /freenas/media/Images/")
  parser.add_argument("-p", "--prefix", metavar="PATH", \
                      help="XBMC PATH prefix (eg. nfs://192.168.0.3/mnt/share/media/) that \
                            will be substituted by --local DIRECTORY when traversing media files. \
                            This is typically the root of the media source as defined in sources.xml")
  parser.add_argument("-A", "--altlocal", metavar="PATH", \
                      help="Alternate local directory which may contain artwork that can be READ \
                            and copied to --local, could be the original source folder.")
  parser.add_argument("-i", "--input", default="-", const="-", nargs="?", metavar="FILENAME", \
                      help="Optional FILENAME containing JSON movie/tvshow data for processing. \
                            Read from stdin if FILENAME is - or not specified.")
  parser.add_argument("-o", "--output", const="-", nargs="?", metavar="FILENAME", \
                      help="Output a data structure suitable for consumption by texturecache.py [test]set, \
                            used to update an XBMC media library converting remote urls into \
                            local urls. Written to stdout if FILENAME is - or not specified.")
  parser.add_argument("--dryrun", action="store_true", \
                      help="Don't create anything (although downloads will be attempted)")
  parser.add_argument("-n", "--nodownload", action="store_true", \
                      help="Don't download (or, if specified, copy from --altlocal) new artwork, \
                            only use existing --local artwork")
  parser.add_argument("--ignorebadprefix", action="store_true", \
                      help="Don't display a warning for media files with a path that does not match \
                            that set by --prefix")
  parser.add_argument("-a", "--add", nargs="+", metavar="TYPE", \
                      help="Add additional named artwork TYPE(s) for download, eg. --add discart banner landscape. \
                            Specify TYPE:NAME if NAME differs from TYPE, eg. \"clearlogo:logo\"")
  parser.add_argument("-d", "--del", nargs="+", metavar="TYPE", dest="remove", \
                      help="Remove named artwork TYPE(s) from list of artwork types to be downloaded, eg. --del clearlogo")
  parser.add_argument("-c", "--check", nargs="+", metavar="TYPE", \
                      help="Check the named artwork TYPE(s) - or all - and warn if any internet \
                            (http) URLs are detected")

  parser.add_argument("-s", "--season", nargs="*", metavar="TYPE", \
                      help="For TV Shows, process season items (default: poster banner landscape). \
                            Not possible to modify media library due to non-existent \"VideoLibrary.SetSeasonDetails\" method.")
  parser.add_argument("-e", "--episode", nargs="*", metavar="TYPE", \
                      help="For TV Shows, process episode items (default: thumb)")

  parser.add_argument("-v", "--verbose", action="store_true", \
                      help="Display diagnostic output")

  args = parser.parse_args()

  VERBOSE = args.verbose

  if args.season == []: args.season = ["poster","banner","landscape"]
  if args.episode == []: args.episode = ["thumb"]

  LOCAL_DIR = args.local
  if LOCAL_DIR and LOCAL_DIR[-1] not in ["/", "\\"]: LOCAL_DIR += "/"

  LOCAL_ALT = args.altlocal
  if LOCAL_ALT and LOCAL_ALT[-1] not in ["/", "\\"]: LOCAL_ALT += "/"

  XBMC_PATH = args.prefix
  if XBMC_PATH and XBMC_PATH[-1] not in ["/", "\\"]: XBMC_PATH += "/"

  # Disable downloading if output path not set, or prefix not known
  # as then impossible to create valid output filenames
  if not LOCAL_DIR: args.nodownload = True
  if not XBMC_PATH: args.nodownload = True

  if not args.nodownload and not os.path.exists(LOCAL_DIR):
    printerr("ERROR: Local path %s does not exist!" % LOCAL_DIR)
    sys.exit(1)

  if not args.nodownload:
    if not os.path.exists(LOCAL_DIR):
      printerr("ERROR: Local path %s does not exist!" % LOCAL_DIR)
      sys.exit(1)
    if LOCAL_ALT and not os.path.exists(LOCAL_ALT):
      printerr("ERROR: Alternate Local path %s does not exist!" % LOCAL_ALT)
      sys.exit(1)

  if args.input != "-" and not os.path.exists(args.input):
    printerr("ERROR: Input file %s does not exist!" % args.input)
    sys.exit(1)

  return args

def main(args):

  download_items = itemListToDict(["clearlogo:logo", "clearart"])
  download_items.update(itemListToDict(args.add))

  # If running just a simple --check, remove all download items
  if not (args.local and args.prefix) and args.nodownload:
    download_items = {}
    season_items = {}
    episode_items = {}
  else:
    # Remove any artwork types that should not be downloaded
    if args.remove:
      for aname in args.remove:
        if aname in download_items: del download_items[aname]

    # Load season and episode artwork download items
    season_items = itemListToDict(args.season)
    episode_items = itemListToDict(args.episode)

  if args.verbose: showConfig(args, download_items)

  data = getJSONdata(args)

  workitems = []

  for media in data:
    if "movieid" in media:
      mediatype = "movie"
    elif "tvshowid" in media:
      mediatype = "tvshow"
    else:
      printerr("FATAL: Unsupported input data - movie and tvshow data for now!")
      sys.exit(1)

    mediatitle = media["label"]
    mediafile = media["file"]

    if mediatype == "tvshow":
      workitem = processItem(args, "tvshow", media, download_items)
      if args.output and workitem["items"]: workitems.append(workitem)

      for season in media["seasons"]:
        if args.season:
          workitem = processItem(args, "season", season, season_items, showTitle=mediatitle, showPath=mediafile)
          if args.output and workitem["items"]: workitems.append(workitem)

        if args.episode:
          for episode in season["episodes"]:
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
  pass