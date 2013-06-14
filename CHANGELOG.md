#Changelog

##Version 0.7.8 (14/06/2013)
* Add: `cache.hideallitems` property (default: no) to mimic hideallitems advancedsettings property. When enabled, "Season All" posters/banners/fanart will not be cached.

##Version 0.7.7 (14/06/2013)
* Fix: `version` check in Python3

##Version 0.7.6 (14/06/2013)
* Use os.path.split() to determine season-all filename
* Fix: When parsing season-all artwork, use the correct "Season All" label instead of appending "Season All" to whatever season is currently being parsed

##Version 0.7.5 (13/06/2013)
* Add invalid source warning when no files are read from filesystem during `missing` operation

##Version 0.7.4 (13/06/2013)
* Simplify webserver check

##Version 0.7.3 (11/06/2013)
* Fix: Python3 incompatibility when loading configuration with a duplicate section
* Fix: Exception when `query`ing int datatypes

##Version 0.7.2 (07/06/2013)
* Add: version field to `addons` JSON query
* Add: `section` property, specifying the default section to be used unless an alternative `@section` name is included on the command line
* Add: Always decode image urls during `query` option

##Version 0.7.1 (28/05/2013)
* Fix: missing parameter on libraryStats()

##Version 0.7.0 (28/05/2013)
* Fix: extrajson properties - again
* Fix: QA field processing

##Version 0.6.9 (26/05/2013)
* Add: Inverted logic for `query` option

##Version 0.6.8 (26/05/2013)
* Fix: Duplicate extrajson properties

##Version 0.6.7 (26/05/2013)
* Fix broken command line @properties when also using named @section
* Add PVR channel artwork support for cache pre-load (`c`, `C`, `nc`, `lc`, `lnc`), dump (`j`, `jd`, `J`, `Jd`) and QA (`qa`) with new media classes `pvr.tv` and `pvr.radio`
* Add PVR channel artwork support for prune options (`p`, `P`)
* Add PVR support for `status` option

##Version 0.6.6 (23/05/2013)
* Fix: Incorrect default `format` property

##Version 0.6.5 (22/05/2013)
* Added `@config=filename` so that alternative property files can be specified at run time. Specify either an absolute path and filename, or just the filename to be searched in current directory and then the directory of the script.
* Added `@section=name` so that properties from a specific property section will be used. Sections are processed in addition to the "global" (default, un-named) section.

  `@config` and `@section` can be used in conjunction.

  #####Example properties file:
  <pre>webserver.port = 8080
  webserver.username = username
  webserver.password = password
  extrajson.movies = streamdetails, file, mpaa, rating, plot
  
  [lounge]
  xbmc.host = htpc
  download.threads = 10
  cache.castthumb = yes
  lastrunfile=/tmp/lrf_lounge.dat
  
  [bedroom]
  xbmc.host = rpi1
  download.threads = 2
  cache.castthumb = no
  lastrunfile=/tmp/lrf_bedroom.dat</pre>

  eg. `lc movies @config=./cache.cfg @section=lounge`

##Version 0.6.4 (22/05/2013)
* Added support for properties as command line arguments - eg. @xbmc.host=192.168.0.8. Each property must be prefixed with @ and be a key=value pair. Properties can appear anywhere in the command line, and will be processed from left to right. Command line properties will be appeneded to those properties retrieved from the properties file.

##Version 0.6.3 (21/05/2013)
* Added additional default non-media filetypes (.cue, .log, .sub, .idx, .zip, .rar etc.)
* Added `video`, `music` and `all` meta media-classes to `c`/`C`, `nc`, `lc`/`lnc`, `j`/`J`/`jd`/`Jd` and `qa`/`qax` options - eg. `c video` will cache movies+sets+tvshows, while `c music` will cache artists+albums+songs. `all` is addons+music+video.
* `missing` now supports multiple sources, eg. `missing movies "New Movies" "Archive Movies" "Yet another movie source"`

##Version 0.6.2 (19/05/2013)
* Added: `sources` can now be filtered by label (case insensitive). Each corresponding label is now displayed in the `sources` list.
* Added: `missing` option, listing those media files that are not present in your media library, for example:

  `texturecache.py missing songs "My Music"`
  `texturecache.py missing movies "My Movies"`
  `texturecache.py missing tvshows "My TV Shows"`

  where "My Music" etc. is the label name of one of my sources.
  
  Valid media libraries for the `missing` option are: `songs`, `movies` and `tvshows`.
  
  Non-media files (eg. artwork, NFO files etc.) are identified by their file extension and excluded from the comparison. Additional non-media file extensions can be added using the `nonmedia.filetypes` property (commad delimited list).

##Version 0.6.1 (16/05/2013)
* Add `exec` and `execw` options to execute XBMC addon, with optional parameters.

##Version 0.6.0 (16/05/2013)
* Add "poster" to `qa.art.tvshows.season`

##Version 0.5.9 (12/05/2013)
* Add "Scanning Video" and "Scanning Music" entries to `status`
* Make regex property patterns additive with "+" prefix (`singlethread.urls`, `qa.fail.urls`, `cache.ignore.types`, etc.).

##Version 0.5.8 (04/05/2013)
* Fix utf-8 console output in Python 3.x

##Version 0.5.7 (02/05/2013)
* Don't check for error during title lookup - if an OnRemove notification is received, the item being removed may already have been removed from the media library before the lookup is executed (but sometimes not). Return `None` for the title whenever an item no longer exists.
* Add `power` option, supporting states of `suspend`, `hibernate`, `reboot` or `shutdown`. This allows the XBMC client to be rebooted, shutdown etc.
* Add `albums`, `artists` and `songs` support to `qa` option (but no `qax` support as music items can't be removed from the media library).
* Add QA checks for artwork urls during `qa`/`qax`, failing/warning QA if found. Default fail urls are "image://video, image://music", there is no default "warn" url. Specify alternative urls using `qa.fail.urls` and `qa.warn.urls` properties (comma delimited patterns). Rescan will be triggered only for fail, not warn.
* Ignore JSON encode errors

##Version 0.5.6 (22/04/2013)
* Change: Use local time and not UTC for `lastrunfile` timestamp (media library dateadded appears to be using local time, so this is more consistent)

##Version 0.5.5 (21/04/2013)
* Fix: Not processing all seasons correctly during `lnc` and `lc`
* Modified `lnc`/`lc` to discard tvshow seasons that do not have a new episode - previously considered for caching all seasons of any tvshow with a new episode
* Show summary of recently added movies/tvshows (`lnc`, `lc`)
* Added `lastrunfile` date/time to stats summary information (`lnc`, `lc`)
* Fix: "Need to cache" message not appearing (`lnc`, `nc`)

##Version 0.5.4 (20/04/2013)
* Fixed sqlite3 characterset decode issue
* Default value for `singlethread.urls` is now `assets\.fanart\.tv`, to avoid hammering fanart.tv (logos, clearart, discart, etc.) as this site appears to reject multiple concurrent requests
* Write command line args and current version to logfile (if logfile is enabled)
* Added `orphan.limit.check` property to allow disabling of safety check when removing orphan files - default value is `yes` (safety check enabled).
* Updated directory traversing code to traverse an arbitrary number of directory levels (`r`, `R`, `p`, `P`) - previously limited to 2-3 directory levels.
* Fix base64.encodestring() in Python3.

##Version 0.5.3 (17/04/2013)
* Add Python3 support (should now work with Python 2.7.3 and Python 3.2.3)

##Version 0.5.2 (16/04/2013)
* Clean up comms logging
* Remove re-entrant lookup
* Add `monitor` option

##Version 0.5.1 (15/04/2013)
* Always include  basic system state (ScreenSaverActive, SystemIdle, Player) for `status`

##Version 0.5.0 (14/04/2013)
* Improve JSON Notification handling while concurrent GUI initiated scan is taking place.
* Added `status` option to determine if client is idle or active etc.

##Version 0.4.9 (14/04/2013)
* Slightly more robust socket comms.

##Version 0.4.8 (14/04/2013)
* Lookup song/movie/tvshow/episode title when new items are scanned into media library
* `vscan`/`ascan` exit status will reflect the number of new items scanned in - 0 when no new items, +n whenever items are added
* Update json socket communication to better handle concatenated messages (response + notification(s))

##Version 0.4.7 (11/04/2013)
* Added `lastrunfile` property. Modification time of this file will be used to restrict cache updates for movies and tvshows (other media classes, while valid, do not support the `dateadded` filter so its not possible to restricty by date). With this property enabled, only new content added since the file was last modified will be considered for re-caching. The new options `lc` and `lnc` will respect the `lastrunfile` property. If the file is missing or unreadable, no `dateadded` filter will be applied. Manually `touch` the `lastrunfile` to advance the modification date, the script will only ever read the details of this file, and never update it.

##Version 0.4.6 (09/04/2013)
* Fix running totals for "Not in Cache" when `nc` run for multiple media classes.

##Version 0.4.5 (09/04/2013)
* Added DDS support for `r`, `R`, `p` and `P` options.
* Added `logfile.verbose` to control amount of information written to logfile. Default `no`. Significant amounts of data will be output when enabled.
* Added `singlethread.urls` property, to force download of content on a single thread. Use this for sites that appear to disallow multiple requests from the same address - fanart.tv seems to be one example of this (clearart/clearlogos etc.).

  eg. `singlethread.urls = assets.fanart.tv, some.othersite.com`
  
  would result in all content requests for files matching any of the above patterns to be performed sequentially on a single thread. This thread will be in addition to any other threads.
* Added `ascan [path]`, `vscan [path]`, `aclean`, `vclean`, `directory path` and `sources [media]` options. Update, clean and interrogate a remote media library from the command line.

##Version 0.4.4 (07/04/2013)
* Add fupdate option to ignore version number when updating
* Added extra logging and exception handling to json communication

##Version 0.4.3 (07/04/2013)
* Add support for BDMV/VIDEO_TS folder structures during `qax`
* Rescan entire library whenever a media item is in root folder - workaround for bug in rescan directory method
* Refactor QA (`qa`,`qax`) and json query (`j`,`jd`,`Jd`,`Jd`) implementation, eliminating duplicate code
* Added extensible QA rules: `qa.zero.<mediaclass>`, `qa.blank.<mediaclass>` and `qa.art.<mediaclass>`

  eg.
  
      `qa.zero.movies = rating, runtime`
  
      `qa.blank.movies = studio, director, writer`
      
      `qa.art.movies = clearart, clearlogo`
      
  will result in movies failing QA if:
  
      * rating or runtime is zero (or missing)
     
      * studio, or director or writer is blank (or otherwise missing), or
     
      * clearart/clearlogo artwork is not present

  If the QA fields are prefixed with a +, they will be added to the default QA fields, eg.

      `qa.blank.movies = + studio, director, writer`

  will QA: plot, mpaa, studio, director and writer. Without the +, the defaults will be replaced.
     
  By default, fields that fail QA will trigger a rescan whenever using the `qax` option. However, if a field is prefixed with a ?, eg. `?clearart` then it will become informational only and will not trigger a rescan.

  <mediaclass> follows the same rules as for `extrajson` fields.

* Property `qa.rating` is no longer supported - add `rating` field to `qa.zero.*` property if required.
* Change name of `qa.file` property to `qafile`

##Version 0.4.2 (03/04/2013)
* Another empty library crash fix (who has no tv shows...?), this time when pruning...

##Version 0.4.1 (03/04/2013)
* Fix crash when library is empty

##Version 0.4.0 (03/04/2013)
* More cumulative elapsed time stat fixes.

##Version 0.3.9 (03/04/2013)
* Elapsed time stats were not correct across image types when caching multiple media classes (ie. `c` or `C` without specifying a media class)

##Version 0.3.8 (02/04/2013)
* Add "addons" as media class, filtered by `name` (`c`, `nc`, `C`, `j`, `jd`, `J`, `Jd`)

##Version 0.3.7 (02/04/2013)
* Use correct image type when discarding duplicate cast thumbnails (affected stats only)

##Version 0.3.6 (02/04/2013)
* Show class-specific thread limits in `config` when not using default (`downloads.threads`) value
* Detect sqlite3 database locked, and retry
* Fix carriage-return/linefeed problem when auto-updating on Windows

##Version 0.3.5 (31/03/2013)
* Added timing and performance data to statistical summary on `c`, `C` and `nc` options
* Added `prune.retain.types` property to retain specific URLs when pruning (`p`, `P`) the texture cache
* Added additional JSON artwork queries for Genres and Addons when pruning the texture cache

##Version 0.3.4 (30/03/2013)
* Add version check/update support. Check version with `version` option, and update with `update`.

  An automatic version check will always occur, unless disabled by `checkupdate = no` in properties.

##Version 0.3.3 (29/03/2013)
* Fix length bug in `MyLogger.progress()`
* Change `print` to `print()`
* Use `MyLogger.out` to replace `print()` where necessary.

##Version 0.3.2 (29/03/2013)
* Return large data objects for garbage collection
* Disabled logging of "Duplicate" items - can be excessive, and rarely useful.

##Version 0.3.1 (28/03/2013)
* Changed cache options (`c` and `C`) to be muli-threaded. Increase number of download threads by modifying `download.threads` in properties. Default is 2.
* Added `nc` option, dry-run version of `c`.
* Better error detection - will determine at startup what resources are required by each option, and abort when not available.
* Moved to github.

##Version 0.3.0 (26/03/2013)
* Added support for multiple tags, combine with "and"/"or".

  Example: `c tags "comedy and standup"`

  Example: `c tags "action or adventure"`

  Combinations of "and" and "or" will be accepted, but may or may not return valid results.

##Version 0.2.9 (26/03/2013)
* Added tag support.

  Tag supporting options: `j`, `J`, `jd`, `Jd`, `c`, `C`, `qa` and `qax`.

  For example `c tags live-comedy` to re-cache movies with the "live-comedy" tag. Partial tag matches will also succeed.

##Version 0.2.8 (25/03/2013)
* Add URL decode functionality (`jd`, `Jd`)

##Version 0.2.7 (25/03/2013)
* Add "Duplicate" statistic for images that are cached more than once - only first cache attempt will succeed, subsequent attempts will be ignored and accounted for as a duplicate.
* Use classes for configuration and logging.
* Allow absolute paths to be used for `thumbnails` and `dbfile` properties.
* Add `qa.file = yes/no` (default:no) property, to verify existence of media file (will not initiate remove/rescan in `qax` option, obviously).

##Version 0.2.6 (24/03/2013)
* Remove media items (movies, episodes) that fail QA when during `qax` operation - this should result in the items being correctly re-scraped.

##Version 0.2.5 (24/03/2013)
* Fix hash calculation error in `R` option (sorry charrua!)
* Apply 5% limit when identifying orphaned files (option `R`). Abort orphaned file removal if limit is exceeded.

##Version 0.2.4 (24/03/2013)
* Added `cache.ignore.types` property, to ignore (don't delete, don't cache) certain image types, such as image://video and image://music (both the default). Use comma delimited patterns, eg. "image://video, ^nfs.*". Set to None to process all URLs. Matches anywhere within URL.
* Added extra QA rule, "[artwork] (uncached)", which is a warning only, and won't cause a directory re-scan by itself.

##Version 0.2.3 (24/03/2013)
* Add `logfile` property, eg. `logfile=/tmp/cache.log`

##Version 0.2.2 (24/03/2013)
* Fix pre-Python 2.6.6 incompatibility.

##Version 0.2.1 (23/03/2013)
* Added `webserver.username` and `webserver.password` authentication properties
* Add summary of processing for `c` and `C` options

##Version 0.2.0 (23/03/2013)
* Auto-detect `webserver.singleshot` - unless already enabled in properties, will be automatically enabled when first web connection request fails, with the request being attempted a second time. Best to leave disabled, and only used when required.

##Version 0.1.9 (23/03/2013)
* Add `webserver.singleshot = yes/no` property to prevent web server connection from being reused, as this seems to cause a problem for some users. Default behaviour is to reuse the connection.

##Version 0.1.8 (22/03/2013)
* Optionally cache cast thumbnails - add `cache.castthumb = yes/no` to properties file. Default is no.

##Version 0.1.7 (21/03/2013)
* When pruning the texture cache, don't consider files that are stored in the local filesystem as these are most likely add-on related.

##Version 0.1.6 (20/03/2013)
* Add support for season-all-(fanart|banner).

##Version 0.1.5 (17/03/2013)
* Add prune `p` option.
* Significantly improved performance of `r`/`R` option

##Version 0.1.4 (16/03/2013)
* Refactor connection code
* Add keyboard interrupt exception handler

##Version 0.1.3 (15/03/2013)
* Switch JSON to use tcp sockets.
* Add `xbmc_host` (localhost) and `rpc_port` (9090) properties

##Version 0.1.2 (13/03/2013)
* Restrict `qa` to consider only movies/tvshows added within `qaperiod` days.

##Version 0.1.1 (13/03/2013)
* Add `qa` option to identify missing artwork and plots (movies and tvshows only)

##Version 0.1.0 (13/03/2013)
* Add JSON additional field support
* Use File.PrepareDownload method to obtain correct image download URL

##Version 0.0.9 (10/03/2013)
* Add JSON query option `j`

##Version 0.0.8 (10/03/2013)
* Clarify licensing with addition of GPLv2 license

##Version 0.0.7 (10/03/2013)
* Default value of `userdata` property changed to ~/.xbmc/userdata, with user expansion

##Version 0.0.6 (09/03/2013)
* Add option `C` to forcibly cache artwork, even when already present in texture cache
* Add season-all.[tbn|png|jpg] TV Sshow poster support

##Version 0.0.5 (08/03/2013)
* Add option `c` to cache artwork missing from texture cache

##Version 0.0.4 (06/03/2013)
* Improve unicode handling

##Version 0.0.3 (06/03/2013)
* Add file summary option `f`

##Version 0.0.2 (05/03/2013)
* Add support for older Dharma version 6 database
* Fix unicode conversion

##Version 0.0.1 (05/03/2013)
* First release
