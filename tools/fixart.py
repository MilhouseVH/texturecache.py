#!/usr/bin/env python
# -*- coding: utf-8 -*-

################################################################################
#
#  Copyright (C) 2015 Neil MacLeod (texturecache@nmacleod.com)
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
# Simple utility to fix artwork URLs.
#
# https://github.com/MilhouseVH/texturecache.py/blob/master/tools/fixart.py
#
# Usage:
#
#  See built-in help (run script with --help parameter).
#
#  For details on artwork naming conventions supported by this script:
#     http://kodi.wiki/view/Frodo_FAQ#Local_images
#
################################################################################

#version 0.0.1

from __future__ import print_function
import os, sys, re, codecs, json, argparse

# Helper class...
class MyUtility(object):
  isPython3 = (sys.version_info >= (3, 0))

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

def printout(msg, newline=True):
  endchar = "\n" if newline else ""
  print(MyUtility.toUnicode(msg), file=sys.stdout, end=endchar)
  sys.stderr.flush()

def printerr(msg, newline=True):
  endchar = "\n" if newline else ""
  print(MyUtility.toUnicode(msg), file=sys.stderr, end=endchar)
  sys.stderr.flush()

def init():
  if sys.version_info >= (3, 1):
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
  else:
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout)
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr)

  parser = argparse.ArgumentParser(description="Fix artwork URLs, replacing \"--from url\" with \"--to url\". \
                                                Reads input from stdin (which should be the output from \"texturecache jd <movies|sets|tvshows> [item]\")", \
                    formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=25,width=90))

  parser.add_argument("-f", "--from", metavar="URL", required=True, dest="urlfrom", \
                      help="URL prefix to be replaced")

  parser.add_argument("-t", "--to", metavar="URL", required=True, dest="urlto", \
                      help="URL prefix to be used for replacement")

  args = parser.parse_args()

  return args

def getdata():
  data=[]
  for line in sys.stdin: data.append(line)
  return json.loads("".join(data))

def processitem(mediatype, media, urlfrom, urlto):
  item = {"type": mediatype, "libraryid": media["%sid" % mediatype], "title": media["label"], "items": {}}

  for art in media.get("art", []):
    if mediatype in ["tvshow", "season", "episode"] and art.startswith("tvshow."): continue
    if media["art"][art].startswith(urlfrom):
      item["items"]["art.%s" % art] = media["art"][art].replace(urlfrom, urlto)

  return item

def main():
  args = init()

  URL_FROM = "image://%s" % args.urlfrom
  URL_TO = "image://%s" % args.urlto

  data = []

  for media in getdata():
    if "movieid" in media:
      mediatype = "movie"
    elif "setid" in media:
      mediatype = "set"
    elif "tvshowid" in media:
      mediatype = "tvshow"
    else:
      printerr("FATAL: Unsupported input data - movie, sets and tvshow data for now!")
      sys.exit(1)

    newitem = processitem(mediatype, media, URL_FROM, URL_TO)
    if newitem["items"] != {}: data.append(newitem)

    if mediatype in "tvshow":
      for season in media.get("seasons",[]):
        newitem = processitem("season", season, URL_FROM, URL_TO)
        if newitem["items"] != {}: data.append(newitem)

        for episode in season.get("episodes", []):
          newitem = processitem("episode", episode, URL_FROM, URL_TO)
          if newitem["items"] != {}: data.append(newitem)

  workitems = json.dumps(data, indent=2, ensure_ascii=True, sort_keys=False)
  printout(workitems)

try:
  main()
except (KeyboardInterrupt, SystemExit) as e:
  if type(e) == SystemExit: sys.exit(int(str(e)))
