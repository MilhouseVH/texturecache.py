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
# Simple utility to match artwork url patterns and generate work items to
# remove (clean) those items from the XBMC media library.
#
# https://github.com/MilhouseVH/texturecache.py/blob/master/tools/clean.py
#
# Usage:
#
#  ./texturecache.py jd movies | ./clean.py --patterns [pattern]* --keep [type]*
#
# eg.
#
#  ./texturecache.py jd movies  | ./clean.py --patterns /movielogo/-51fd12c146bd9\.png
#  ./texturecache.py jd movies  | ./clean.py --patterns /moviethumb/ /moviedisc/ /moviebanner/
#  ./texturecache.py jd tvshows | ./clean.py --patterns assets\.fanart\.tv
#  ./texturecache.py jd tvshows | ./clean.py --keep fanart poster clearart clearlogo
#
#  Keep specific artwork types, but "clean" any other types that are remote:
#
#  ./texturecache.py jd tvshows | ./clean.py --keep fanart poster clearart clearlogo --patterns http://
#
################################################################################

#version 0.2.1

from __future__ import print_function
import sys, os, codecs, json, re, argparse

def printout(msg, newline=True):
  endchar = "\n" if newline else ""
  print(msg, file=sys.stdout, end=endchar)
  sys.stderr.flush()

def printerr(msg, newline=True):
  endchar = "\n" if newline else ""
  print(msg, file=sys.stderr, end=endchar)
  sys.stderr.flush()

def addEllipsis(maxlen, aStr):
  if len(aStr) <= maxlen: return aStr

  ileft = int(maxlen/2) - 2
  iright = int(maxlen/2) - 1

  return "%s...%s" % (aStr[0:ileft], aStr[-iright:])

def debug(msg):
  global VERBOSE
  if VERBOSE: printerr(msg)

def processitems(data, keepart, patterns):
  workitems=[]

  for item in data:
    items = {}
    for a in item.get("art", []):
      if not (a.startswith("tvshow.") or a.startswith("season.")) and a not in keepart:
        if not patterns:
          debug("Not Keep: [%-12s] %-50s [%s]" % (a, addEllipsis(50, item.get("title", item.get("label", None))), item["art"][a]))
          items["art.%s" % a] = None
        else:
          url = re.sub("^image://(.*)/", "\\1", item["art"][a])
          for pattern in patterns:
            if pattern.search(url):
              debug("Pattern:  [%-12s] %-50s [%s]" % (a, addEllipsis(50, item.get("title", item.get("label", None))), item["art"][a]))
              items["art.%s" % a] = None
              break

    if items:
      if "movieid" in item:
        workitems.append({"items": items, "libraryid": item["movieid"], "type": "movie", "title": item["title"]})
      elif "tvshowid" in item:
        workitems.append({"items": items, "libraryid": item["tvshowid"], "type": "tvshow", "title": item["title"]})
      elif "seasonid" in item:
        workitems.append({"items": items, "libraryid": item["seasonid"], "type": "season", "title": item["label"]})
      elif "episodeid" in item:
        workitems.append({"items": items, "libraryid": item["episodeid"], "type": "episode", "title": item["label"]})

    if "seasons" in item:  workitems.extend(processitems(item["seasons"], keepart, patterns))
    if "episodes" in item: workitems.extend(processitems(item["episodes"], keepart, patterns))

  return workitems

def getdata():
  data=[]
  for line in sys.stdin: data.append(line)
  jdata = json.loads("".join(data))
  del data
  return jdata

def init():
  global VERBOSE

  if sys.version_info >= (3, 1):
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
  else:
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout)
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr)

  parser = argparse.ArgumentParser(description="Generate instructions to remove artwork URLs matching specific patterns \
                                                or that are of a type that should not be retained", \
                    formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=25,width=90))

  parser.add_argument("-k", "--keepart", nargs="+", metavar="TYPE", \
                      help="Artwork TYPE(s) to be kept or retained, eg. \"--keepart fanart poster\"")

  parser.add_argument("-p", "--patterns", nargs="+", metavar="PATTERN", \
                      help="Regex pattern(s) to match against artwork URLs (unless artwork type is \
                            specified in --keepart)")

  parser.add_argument("-v", "--verbose", action="store_true", \
                      help="Display diagnostic output")

  args = parser.parse_args()

  VERBOSE = args.verbose

  if args.keepart == None and args.patterns == None:
    parser.error("At least --keepart or --patterns must be specified")

  return(args)

def main(args):

  keepart = []
  patterns = []

  if args.keepart:
    keepart = args.keepart

  if args.patterns:
    for arg in args.patterns:
      patterns.append(re.compile(arg))

  workitems = processitems(getdata(), keepart, patterns)

  sys.stdout.write(json.dumps(workitems, indent=2))
  sys.stdout.write("\n")
  sys.stdout.flush()

try:
  main(init())
except (KeyboardInterrupt, SystemExit) as e:
  if type(e) == SystemExit: sys.exit(int(str(e)))
