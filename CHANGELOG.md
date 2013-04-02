#Changelog

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
* Add "Duplicate" statistic for images that are cached more than once - only first cache attempt will succeed, subsequent attempts will be ignored and account for as a duplicate.
* Use classes for configuration and logging.
* Allow absolute paths to be used for `thumbnails` and `dbfile` properties.
* Add `qa.file = yes/no` (default:no) property, to verify existence of media file (will not initiate remove/rescan in `qax` option, obviously).

##Version 0.2.6 (24/03/2013)
* Remove media items (movies, episodes) that fail QA when during `qax` operation - this should result in the items being correctly re-scraped.

##Version 0.2.5 (24/03/2013)
* Fix hash calculation error in `R` option (sorry charrua!)
* Apply 5% limit when identifying orphaned files (option `R`). Abort file orphaned file removal if limit is exceeded.

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
