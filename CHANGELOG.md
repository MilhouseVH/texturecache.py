#Changelog

##Version 1.4.7 (24/02/2013)
* Add: Send GUI notification with `notify` option, eg. `notify "Title" "Message"`. Optionally, the display time (in milliseconds, default 5000) can be specified, as well as the location of a suitable image file (which must be accessible to the XBMC client)

##Version 1.4.6 (14/02/2013)
* Add: If an unhandled exception occurs and logging is enabled (`@logfile`), write the exception details to the log file.

##Version 1.4.5 (10/02/2013)
* Fix: Improve memory efficiency of JSON GetDirectory processing by limiting the directory cache to a fixed size - thanks @theowiesengrund for helping with testing
* Fix: Significantly improve memory efficiency of cast thumbnail processing - thanks @theowiesengrund for helping with testing

* Chg: Make `@chunked=yes` the default setting
* Chg: Enable HDMI with `tvservice --preferred` whenever xbmc quits, either normally or abnormally - this will ensure that HDMI is correctly re-enabled even after `killall xbmc.bin` etc.
* Chg: Alter `missing` behaviour to now consider only file types matching known audio or video file extensions (those supported by XBMC). This is to say the behaviour has changed from an exclusion to inclusion approach. Specify additional file extensions that should be included by adding comma-delimited values to `audio.filetypes` or `video.filetypes` properties. All standard XBMC audio and video file extensions are supported by default.
* Chg: Remove `nonmedia.filetypes` property as no longer has a purpose
* Chg: Display warning when a tv show with invalid season (season identifier < 0) is detected
* Chg: Search the texture cache database (`s` option) up to two 2 times, first with the non-encoded search term, and the second time after encoding the search term (and only then if the encoded term is different to the unencoded search term), then combining the results. This is necessary to find encoded urls used for embedded artwork (`music@`, `video@` and also picture thumbnails)

* Rev: Revert the change that made `@dbjson=no` the default setting on localhost, as this should no longer be necessary when using chunked queries. When available, the TextureDB JSON API should always be used by default (whether remote or local).

* Add: When filtering media library results, the default filter field is usually `title` (eg. `movies avatar` or `albums mothership`). However should you wish to filter on an alternate field then specify the field name in the `@filter` property, eg. `movies cameron @filter=director` or `albums "the beatles" @filter=artist`
* Add: Specify alternate filter operator, the default opertator being `contains`. Use `@filter.operator=<operator>` where `<operator>` is any one of the [standard filter operators](http://wiki.xbmc.org/index.php?title=JSON-RPC_API/v6#List.Filter.Operators). For example, `jd movies 21 @filter.operator=is` would return details only for the movie named "21", and not also "21 Jump Street" as would be the case when using the default `contains` operator.

##Version 1.4.4 (28/01/2013)
* Fix: Cosmetics

##Version 1.4.3 (28/01/2013)
* Add: Implement chunked queries to reduce memory consumption on client and server (which are often the same device). In testing, chunked queries significantly reduced XBMC memory consumption, by as much as 80MB or more (a big deal on a Pi with under 200MB free). This change will ensure that queries use a relatively fixed (and small) amount of server memory when responding to chunked queries, rather than unpredictable and sometimes very large amounts of memory when responding to unconstrained queries (for example when retrieving all movies with all cast members, or the entire texture cache database).

 Media library queries will be chunked using JSON API limits (start/end), with the chunk size varying according to the anticipated complexity of the query, eg. when caching cast thumbs a smaller chunk size will be used due to the significant increase in data per movie.

 The Textures13 db query will also be chunked, though not using limits as this isn't currently supported by the JSON API (nor obviously SQL, which is used when the Texture DB JSON API isn't available). Instead, data for each of the Thumbnail folders (0-9,a-f) will be retrieved in sequence (cachedurl like '0/%' etc.), which results in more manageable (but unfortunately still variable) amounts of data, and has required related functions (caching, pruning) to be re-written.

 In addition, chunking allows unnecessary query data to be eliminated sooner, reducing client memory consumption - for example, when caching artwork, details of cast members without thumbnails can be dropped as soon as each chunk is received which avoids storing often significant amounts of redundant information only to be processed and discarded later.

 Chunked queries is not currently enabled by default, but can be enabled with `@chunked=yes` - please do so and report any problems. If there are no problems reported in the next week or so I will enable chunked queries as the default setting. Other than a slight performance gain when not chunking (assuming you don't run out of memory), there should be no reason to disable this option and in fact I may also remove the non-chunked code at some point in the future.

 Other functions, such as texture database searches (`s`, `S`, `x`, `X` etc.) and orphan file checks (`r`/`R`) have not been updated to support chunked queries as it's not practical to do so, plus you are less likely to have memory problems when performing these operations.

* Add: `readfile` option to return content of the named file, outputting contents to stdout when the output filename is `-` (not suitable for binary data) or the named output file (which is suitable for binary data)

##Version 1.4.2 (25/01/2013)
* Fix: Using wrong type - list not dict - when directory not found

##Version 1.4.1 (25/01/2013)
* Fix: Typo

##Version 1.4.0 (25/01/2013)
* Add: For use with `C` and `nc` options, `@cache.refresh=YYYY-MM-DD HH:MM:SS|today|#`, to re-cache (`C`) or list (`nc`) stale cache items. Stale cache items are those local artwork files that have been modified since the specified date. Remote and inaccessible artwork will not classed as stale and instead ignored (skipped).
* Chg: `dbjson` will now default to `no` when the script is running on localhost, and `yes` when `xbmc.host` is a remote client.

##Version 1.3.9 (23/01/2013)
* Chg: Display current mute state (muted/unmuted) and volume level when no value passed to `volume` option

##Version 1.3.8 (21/01/2013)
* Add: Configuration property `rpc.retry` to control how many attempts are made to reconnect to XBMC RPC server when XBMC has restarted. Default is 12. If set to 0, no attempts will be made to reconnect and the script will exit immediately.

##Version 1.3.7 (18/01/2013)
* Fix: Incorrect type conversion during `set`

##Version 1.3.6 (17/01/2013)
* Chg: Support relative date periods for `qa.nfo.refresh`, eg. `qa.nfo.refresh=7` would be 7 days prior to today (from 00:00:00). `0` is therefore equivalent to `today`. View the computed date/time in `config`.

##Version 1.3.5 (15/01/2013)
* Add: `@qa.nfo.refresh="YYYY-MM-DD HH:MM:SS"`, or `qa.nfo.refresh=today` (time == 00:00:00). During `qax`, any movie/episode whose NFO has a modification date more recent than the specified date/time, will be re-scraped. Prior to JSON API v6.13.2, the lastmodified date [is ambiguous](http://trac.xbmc.org/ticket/14836) so prior to v6.13.2 it may be necessary to specify `@modifieddate.mdy=yes` if US-format (mm/dd/yyyy) last modified dates are being used - default is `no`, for dd/mm/yyyy dates.
* Add: `volume` option - set volume level `0`-`100`, `mute`, `unmute` eg. `volume mute`
* Chg: Clearly differentiate between QA failures (which will prompt a refresh during `qax`) and warnings (which won't prompt a refresh)

##Version 1.3.4 (11/01/2013)
* Chg: Ignore "total" property when setting resume point - not required and probably a little pointless so leave it out.

##Version 1.3.3 (08/01/2013)
* Chg: Allow full size pictures to be retained in cache when pruning, by enabling option `prune.retain.pictures`.

##Version 1.3.2 (07/01/2013)
* Chg: Add `horizontal` and `vertical` as synonyms for `listright` and `listdown`.

##Version 1.3.1 (07/01/2013)
* Add: cooldown period to `stress-test`

##Version 1.3.0 (07/01/2013)
* Add: `stress-test` option to iterate over GUI items in various skin views (`thumbnail`, `listright` and `listdown`) with customisable pauses and repeats

##Version 1.2.9 (07/01/2013)
* Add: When pruning (`p`/`P`), now also consider available picture sources containing artwork and retain associated folder and picture previews. Disable this behaviour with `@prune.retain.previews=no` and all previews associated with your pictures will be removed when pruning

##Version 1.2.8 (07/01/2013)
* Fix: Truncation of (photo thumbnail) url while querying texture cache database.with JSON as these urls don't have a trailing forward-slash
* Fix: Normalise (decode) urls when using SQLite. Photo thumbnail urls are stored in image:// encoded form within Textures##.db

##Version 1.2.7 (31/12/2013)
* Fix: Cosmetics

##Version 1.2.6 (26/12/2013)
* Fix: Revert SQLite to use iso-8859-1 text factory with speculative conversion to utf-8.

##Version 1.2.5 (13/12/2013)
* Chg: Use regex when processing `@argument` options on the command line. Terminate if specified `@section` is not valid.
* Add: tools/clean.py

##Version 1.2.4 (06/12/2013)
* Add: `input` option, to send keyboard/remote control input via JSON. eg. `input home`, `input back`, `input sendtext zombieland` or combine multiple actions `input home left left select pause 5.5 down select`. See [JSON API](http://wiki.xbmc.org/?title=JSON-RPC_API/v6#Input) for more details. `input executeaction screenshot` is handy if you don't have a keyboard connected and need a screenshot (also added synonym `screenshot` as a shortcut for this option).

##Version 1.2.3 (01/12/2013)
* Add: Add artwork support for [Video Extras addon](http://wiki.xbmc.org/index.php?title=Add-on:VideoExtras). Enable with `@cache.videoextras=yes` or `@cache.extra=yes`. Only artwork in the "extras" subdirectory is supported, not -extras- or any other folder.

* Add: Add "extras" artwork support (see [http://wiki.xbmc.org/index.php?title=Add-on:VideoExtras addon]), enable with `@cache.extravideo=yes` or `@cache.extra=yes`.

##Version 1.2.2 (01/12/2013)
* Add: `stats` option to output media library statistics. Optionally filter by class, eg. `stats tvshows episodes` or `stats audio`

##Version 1.2.1 (29/11/2013)
* Chg: Abstract `rbphdmi` event/state management
* Fix: Unicode conversion of quoted filenames

##Version 1.2.0 (28/11/2013)
* Fix: null being returned for files from Files.GetDirectory call on some systems - ensure centralised method used everywhere

##Version 1.1.9 (28/11/2013)
* Chg: Tweak `rbphdmi` logic slightly: Check HDMI has actually turned on/off; don't turn off HDMI if the TV/monitor has been powered off (if supported by TV/monitor - if not, assume "always on" with `@hdmi.force.hotplug=yes`).

##Version 1.1.8 (26/11/2013)
* Add: `rbphdmi` option to manage Raspberry Pi HDMI power saving. Default delay is 900 seconds after screensaver has activated, specify alternative delay in seconds as second argument. View event activity with `@debug=yes`. Specify location of tvservice binary with `@bin.tvservice` property (default is `/usr/bin/tvservice`). Due to nature of operation, requires `xbmc.host` to be localhost.

##Version 1.1.7 (25/11/2013)
* Add: Exit `monitor` mode cleanly when the socket dies, exiting with System.OnQuit() and exit status -1
* Add: "exit" as power option, quits application

##Version 1.1.6 (23/11/2013)
* Add: Ignore IOError on output due to broken pipe

##Version 1.1.5 (23/11/2013)
* Add: extrafanart and extrathumbs support when caching `artists`, `albums`, `movies`, `tags` and `tvshows`, and when pruning. Enable with `@cache.extra=yes` to cache and prune both extrafanart and extrathumbs, or `@cache.extrafanart=yes`/`@cache.extrathumbs=yes` to enable specific cache & prune support for fanart or thumbs. By default all three options are disabled (ie. `no`).

##Version 1.1.4 (23/11/2013)
* Fix: IMDb rating may sometimes be "N/A"

##Version 1.1.3 (22/11/2013)
* Add: `cache.artwork` property (comma-delimited list) to restrict caching of specific artwork types, eg. `@cache.artwork=poster,fanart` to cache only posters and fanart. Default is an empty list, which will cache all artwork types.

##Version 1.1.2 (19/11/2013)
* Add: Progress information to database extract options (`x`, `X`, `Xd`, `f` etc.)

##Version 1.1.1 (18/11/2013)
* Fix: Handle "N/A" runtime value from omdbapi.com
* Chg: Delay import of sqlite3 module until determined that sqlite access is required (@dbjson=no)

##Version 1.1.0 (17/11/2013)
* Add: `imdb movies [filter]` option to update a subset of imdb related fields on movies, all or filtered. Uses `imdbnumber` from the media library to query http://www.omdbapi.com. Specify the fields to be updated using the property `@imdb.fields`, the default fields being `rating` and `votes`. Available fields are: `title`, `year`, `runtime`, `genre`, `plot`, `plotoutline`, `rating`, `votes`.

Output should be piped into `set` for changes to be applied to the media library. For example, to update ratings, votes and also year on Avatar:

  `./texturecache.py imdb movies avatar @imdb.fields=+year | ./texturecache.py set`
  
Only if one or more fields requires updating will a work item be output for each movie. Old and new values will be written to the logfile for each workitem.

##Version 1.0.9 (15/11/2013)
* Add: Mac OS X and Android `userdata` defaults
* Chg: Restrict pattern length (excluding wildcards) on `purge`/`purgetest` to minimum length of 5 characters (override with @purge.minlen=n, value of zero will disable).

Specify `purge`/`purgetest` wildcards using %, ie. `pattern%` for startswith, or `%pattern` for endswith, otherwise `pattern` will be interpreted as `%pattern%` (contains).

##Version 1.0.8 (13/11/2013)
* Fix: Avoid using urllib2.quote() in getSeasonAll processing, which could fail with foreign codings ([forum post](http://forum.xbmc.org/showthread.php?tid=158373&pid=1549752#pid1549752)).

##Version 1.0.7 (12/11/2013)
* Add: Auto-update facility, rather than run `update` manually each time to update. If `@checkupdate=yes` and `@autoupdate=yes` (both being the defaults), at the beginning of each script execution the latest github version will be checked and, if a newer version is available, the script automatically updated before execution commences with the latest version. Disable by setting `@autoupdate=no`. If `@checkupdate` (which simply warns when the version is out of date) is disabled, auto-updating will also be disabled.
* Add: In addition to `hashed` and `unhashed` on `purge`/`purgetest`, added new filter `all`, being either `hashed` or `unhashed`.
* Fix: Not stripping leading "image://" from artwork in `qa`/`qax`.

##Version 1.0.6 (10/11/2013)
* Revert: Removed all attempts at fixing slashes on-the-fly, utterly pointless given the current front-end/back-end disconnect
* Add: Option `fixurls` to identify media library urls with mixed forward and backward slashes. Output can be piped into `texturecache.py set` to apply corrective changes to the media library, eg:

  `./texturecache.py fixurls | ./texturecache.py set`
  
Once corrective changes have been applied, pruning (to remove old mangled artwork from cache) and caching of new, unmangled artwork may be required. Subsequent execution of troublesome addons may re-apply mangled urls to the media library - contact the add-on author/maintainer to notify them of the problem.

Applying corrective changes for movie sets will require a recently nightly build of Gotham (requires JSON API v6.12.0+).

##Version 1.0.5 (09/11/2013)
* Add: Augment movie set dump (`j sets`, `J sets` etc.) with list of member movies. Movie entries will be ordered by `sorttitle` if present in media library. Suppress this behaviour with `@setmembers=no`. When using `J`, `Jd` and `Jr` options, specify additional *movie* fields with `@extrajson.movies`, otherwise default movie fields will be returned (`movieid`, `file`, `title` and `sorttile`).
* Add: `purge hashed site [site]` and `purge unhashed site [site]` options to remove artwork associated with sites, with or without hashes. Use `purgetest` in place of `purge` to see which artwork items would be selected for removal.
* Chg: If SQLite3 module not available, don't complain just force `@dbjson=yes` (should simplify ATV2/Gotham installations)
* Chg: Make `@logfile.verbose=yes` the default setting - has no impact unless logging is actually enabled with `@logfile=<filename>`
* Chg: If platform is darwin (ie. ATV2), use a better default `userdata` path
* Fix: Correct mangled slashes also in the quoted download url, so that the requested (and now unmangled) url creates an unmangled entry in the Textures db
* Fix: Correctly validate `streamdetails` during `qa`/`qax` if specified on `qa.blank.*`

##Version 1.0.4 (04/11/2013)
* Add: New Texture JSON API (requires JSON API v6.10.0+).

  Access the Textures*.db database using JSON rather than via SQLite. Use `@dbjson=no` to force old SQLite behaviour, `@dbjson=yes` to force JSON API, or leave `@dbjson` undefined for auto-selection (ie. use JSON API when available, fall back to SQLite when not).

  When using JSON to access Textures*.db, only the following options still require direct file system access to the `Userdata\Thumbnails` folder: `f`, `r`, `R`, `S`, `X`, `Xd`. All other options (including prune, `p` and `P`) now require only a valid `xbmc.host` and  no filesystem access so no need to mount a remote share while pruning a remote client.

  As pruning no longer has (or requires) access to the Thumbnails folder when using JSON API, I've had to remove the "orphan" warning at the end of the prune process.
* Add: Ability to remove artwork urls from the media library with `set` option by specifying url value of `"null"` (or `null`, or `""`) (requires JSON API v6.9.0+)
* Add: Support for setting of `season` fields (requires JSON API v6.10.0+)
* Add: Support for setting of `set` (movie set) fields (requires JSON API v6.12.0+)
* Add: `rdirectory` option, a recursive version of `directory`
* Add: `jr` and `Jr` options for "raw" JSON output that isn't guaranteed to be ASCII (urls will be decoded/unquoted, however)
* Chg: For reasons of consistency, `cache.ignore.types` patterns no longer need to specify `image://` prefix. Defaults are now: `^video, ^music`. Old patterns that include `^image://` will be automatically corrected to remove `image://`.
* Fix: Reworked charset encoding, hopefully saner than before, now with fewer conversions and increased consistency between Python2 & Python3.
* Fix: Added some memory optimisations to try and reduce memory consumption on low memory devices (eg. R-Pi)

##Version 1.0.3 (25/10/2013)
* Fix: [issue #9](https://github.com/MilhouseVH/texturecache.py/issues/9), error during prune when dds file already deleted

##Version 1.0.2 (18/10/2013)
* Add: New options, `set` and `testset`, to allow limited modification of `movie`, `tvshow`, `episode`, `musicvideo`, `artist`, `album` and `song` library items. Use `testset` to verify the request is valid before performing any update.

Example:

```
./texturecache.py set movie 312 art.clearlogo "nfs://myserver/movies/thismovie-logo.png" \
                                art.clearart "nfs://myserver/movies/thismovie-clearart.png" \
                                playcount 12 \
                                trailer "http://www.totaleclips.com/Player/Bounce.aspx?eclipid=e121648&bitrateid=449&vendorid=102&type=.mp" \
                                tag "['horror', 'zombies']"
```

to set clearlogo, clearart, playcount and tag fields for the movie with the movieid 312.

Most basic fields can be specified (eg. `plot`, `trailer`, `playcount`, `art` etc. - see JSON API v6 for details of which fields can be specified on the Set*Details calls). However modification of more complex fields - such as `cast`, `streamdetails` etc. - is not supported by JSON. Also, the `file` field cannot be modified.

In addition, for the sake of efficiency, batches of data can also be read from stdin. In the following example, the two movies and one tv show are to be updated. The fields being updated are specified by the `items` list within each movie or tv show (in the following example, setting new clearart and clearlogo artwork urls).

The file update.dat contains the following information:


```
[
  {
    "libraryid": 1,
    "items": {
      "art.clearart": "nfs://192.168.0.3/mnt/share/media/Video/MoviesSD/9 (2009)[DVDRip]-clearart.png",
      "art.clearlogo": "nfs://192.168.0.3/mnt/share/media/Video/MoviesSD/9 (2009)[DVDRip]-logo.png"
    },
    "type": "movie",
    "title": "9"
  },
  {
    "libraryid": 358,
    "items": {
      "art.clearart": "nfs://192.168.0.3/mnt/share/media/Video/MoviesHD/Classics/12 Angry Men (1957)[BDRip]-clearart.png",
      "art.clearlogo": "nfs://192.168.0.3/mnt/share/media/Video/MoviesHD/Classics/12 Angry Men (1957)[BDRip]-logo.png"
    },
    "type": "movie",
    "title": "12 Angry Men"
  },
  {
    "libraryid": 115,
    "items": {
      "art.clearart": "nfs://192.168.0.3/mnt/share/media/Video-Private/TVShows/Arrested Development/clearart.png",
      "art.clearlogo": "nfs://192.168.0.3/mnt/share/media/Video-Private/TVShows/Arrested Development/logo.png"
    },
    "type": "tvshow",
    "title": "Arrested Development"
  }
]
```
and to apply the update:
```
cat update.dat | ./texturecache.py set
```
* Added of tools/mktools.py which can read in the output from `texturecache.py jd movies` or `texturecache.py jd tvshows` and convert remote artwork to local. It will retrieve the original remote artwork from the web site and write it into your media directory. Output from mklocal.py can be fed into `texturecache,py set` to re-point your media library so that it now uses the local artwork. Run mklocal.py in different ways to download remote artwork, or just assign existing local artwork to your media library. See --help for more details. 


##Version 1.0.1 (03/10/2013)
* Add: New option, `duplicates`, to list movies present more than once in the media library with the same imdb number

##Version 1.0.0 (28/09/2013)
* Fix: Handle "internal error" during prune operation when no movie sets are defined

##Version 0.9.9 (27/09/2013)
* Chg: Don't include directory parameter on *Library.Scan call when path is not specified

##Version 0.9.8 (19/09/2013)
* Chg: Use decoded urls when applying url matching rules

##Version 0.9.7 (15/09/2013)
* Add: When removing artwork files, remove any matching dds file also

##Version 0.9.6 (05/09/2013)
* Fix: Doh, fix `query` which was broken by previous uppdate

##Version 0.9.5 (03/09/2013)
* Add: Option `remove` to remove from media library `musicvideo`, `movie`, `tvshow` or `episode` for a specific libraryid, eg. `remove movie 619`
* Add: Show player progress in `status`

##Version 0.9.4 (13/08/2013)
* Add: Option `Xd` to remove texture cache rows with no corresponding thumbnail file
* Add: Include referer on analytics

##Version 0.9.3 (12/08/2013)
* Add: Extra logging when restoring `watched` status

##Version 0.9.2 (12/08/2013)
* Fix: User agent on Analytics

##Version 0.9.1 (12/08/2013)
* Add: Analytics support for github.com usage.

##Version 0.9.0 (08/08/2013)
* Add: Summarise orphan results (`r`, `R`)
* Add: Notify when orphan files detected during prune (`p`, `P`)
* Add: Delete DDS files (when present) while pruning corresponding artwork
* Add: Show current version in `update` message
* Fix: Suppress "no result" error when processing `sets` if Movie Sets haven't been defined in the media library
* Fix: Handle github.com errors more gracefully

##Version 0.8.9 (05/08/2013)
* Fix: Swap back/forward slashes on JSON artwork paths whenever a slash is used incorrectly (see [here](http://forum.xbmc.org/showthread.php?tid=153502&pid=1477147#pid1477147) for details)

##Version 0.8.8 (04/08/2013)
* Fix: Better handle integer lists in `query`
* Fix: Revert payload download behaviour, as it's not consistent on all platforms - make `download.payload=yes` the default setting.
* Chg: Rename `music` meta class to `audio`, for consistency
* Chg: No longer fabricate a url for local content when Files.PrepareDownload fails
* Add: Extra information in JSON service message mentioning the options in Settings -> Remote Control which should be enabled
* Add: Use a workable default `userdata` property for win32

##Version 0.8.7 (21/07/2013)
* Add: `.strm` to default non-media files for `missing` option
* Add: Pre-delete artwork before starting download threads. Cache deletion functionality can now occur in the main thread to prevent database locking when accessing Textures13.db via a mounted filesystem. Pre-deletion will be the default if a mounted filesystem is detected. Disable/Enable with `download.predelete=yesno`. When disabled, deletions will take place in each download thread, but this may cause SQLite locks depending on the locking protocol used by the network filesystem (SMB/CIFS seems particularly prone to this problem, NFS less so). Pre-deletion should not be required for local file systems.
* Add: Artwork (payload) download is now optional when caching, as `Files.PrepareDownload` appears to be sufficient to populate the cache, rendering the actual download superfluous. Re-enable with `download.payload=yes`.
* Chg: Modify retry behaviour of failed artwork downloads - previously retried download 10 times, which is a little excessive. Specify number of retries (both Files.PrepareDownload and/or payload download) with `download.retry=n`. Default is now 3.

##Version 0.8.6 (04/07/2013)
* Fix: When looking for `missing` (unscraped) media items, allow for empty remote folders (no files)
* Add: Include `file` as a default field when dumping (`j`/`jd`/`J`/`Jd`) media library items
* Add: Stacked/multi-part movie support added to `missing` and `qa`/`qax` options
* Add: Group similar `prune` items together by sorting results on url

##Version 0.8.5 (01/07/2013)
* Fix: `watched` items will be restored in ascending movie name or tv show/episode name order, rather than an apparently random order
* Fix: Use absolute path when determining location of config file
* Fix: Locked database handling

##Version 0.8.4 (27/06/2013)
* Add: Added `wake` option to send a WOL magic packet to a suspended/hibernating remote client. Specify the MAC address of the remote client in the `network.mac` property (ie. `network.mac=xx:xx:xx:xx:xx:xx`). When the client is no longer required, suspend or hibernate it with the `power` option.
* Fix: Remove incorrect `qa`/`qax` dependency on Textures13.db

##Version 0.8.3 (17/06/2013)
* Fix: Improve item matching performance on `watched` option

##Version 0.8.2 (17/06/2013)
* Fix: Include year when matching movies for backup/restore of `watched` status.

##Version 0.8.1 (17/06/2013)
* Add: New option `watched`, allowing backup and restoration of movie and tvshow watched statuses (and in Gotham, resume points).

  When restoring a watched status/resume point, more recent playcount, lastplayed and (in Gotham) resume point positions will be retained unless the property `watched.overwrite=yes` is specified, in which case watched statuses and resume points will be restored exactly as per the backup.

  Watch statuses will be restored based on the name of the movie or tv show (and season/episode number), so if these properties change between when the backup is taken and when it is restored, some watch statuses may not be able to be restored.

  Examples:
  <pre>
  ./texturecache.py watched movies backup ./movies.dat
  ./texturecache.py watched movies restore ./movies.dat
  ./texturecache.py watched tvshows backup ./tvshows.dat
  ./texturecache.py watched tvshows restore ./tvshows.dat
  </pre>

##Version 0.8.0 (15/06/2013)
* Add: `agenres` and `vgenres` as audio and video genre classes, for use with cache (`c`, `C`, `nc`, `lc`, `lnc`), dump (`j, `J`, `jd`, `Jd`) and QA (`qa`) options
* Add: "Undefined" category to library stats, representing artwork that is blank (either not specified, or empty string/"")

##Version 0.7.9 (15/06/2013)
* Fix: Iterating over None type when there are no channels returned for pvr query

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
