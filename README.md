texturecache.py
===============

Utility to manage and update the local Kodi texture cache (Texture##.db and Thumbnails folder), view content of the Kodi media library using JSON calls (so works with MySQL too), and also cross reference cache with library to identify space saving opportunities or problems.

## Summary of features

*Typically a lower case option is harmless, an uppercase version may delete/modify data*

**[c, C]** Automatically re-cache missing artwork, with option to force download of existing artwork (remove first, then re-cache). Can use multiple threads (default is 2)

**[nc]** Identify those items that require caching (and would be cached by **c** option)

**[lc, lnc]** Same as `c` and `nc`, but only considers those media (movies, tvshows/episodes) added since the modification timestamp of the file identified by the property `lastrunfile`

**[p, P]** Prune texture cache by removing accumulated **cruft** such as image previews, previously deleted movies/tvshows/music and whose artwork remains in the texture cache even after cleaning the media library database. Essentially, remove any cached file that is no longer associated with an entry in the media library, or an addon

**[s, S]** Search texture cache for specific files and view database content, can help explain reason for incorrect artwork. **S** will only return database results for items that no longer exist in the filesystem.

**[x, X, f]** Extract rows from texture cache database, with optional SQL filter.  **X** will only return database results for items that no longer exist in the filesystem. **f** will display basic stats (file count, total size).

**[Xd]** Delete rows from texture cache database, with optional SQL filter, when item associated with row no longer exists in the filesystem.

**[d]** Delete specific database rows and corresponding files from the texture cache using database row identifier (see **s/S**)

**[r, R]** Reverse query cache, identifying any "orphaned" files no longer referenced by texture cache database, with option to auto-delete files

**[j, J, jd, Jd, jr, Jr]** Query media library using JSON API, and output content using JSON notation (and suitable for further external processing). The **jd** and **Jd** options will decode (unquote) all artwork urls. **jr** and **Jr** options will not guarantee ASCII output of decoded urls (ie. the data will be "raw"). **J**, **Jd** and **Jr** options will include additional user configurable fields when querying media library (see [properties file](#optional-properties-file))

**[qa]** Perform QA check on media library items, identifying missing properties (eg. plot, mpaa certificate, artwork etc.). Default QA period is previous 30 days, configurable with [qaperiod](#optional-properties-file). Define QA properties using `qa.zero.*`, `qa.blank.*` and `qa.art.*` properties. Enable "[qa.file = yes](#optional-properties-file)" for file validation during QA. Specify a period (`today` or a relative number of days) or date/time (eg. 2014-01-11 01:02:03) for `qa.nfo.refresh` to refresh any media item with an NFO file modified since the specified date.

**[qax]** Like the **qa **option, but also performs a library remove and then library rescan of any media folder found to contain media items that fail a QA test

**[set, testset]** Set values on `movie`, `tvshow`, `episode`, `musicvideo`, `artist`, `album` and `song`. Pass parameters on the command line, or as a batch of data read from stdin. `testset` will perform a dry-run. See [setting fields](#setting-fields-in-the-media-library) for more details.

**[remove]** Remove specified library item from media library, ie. "remove movie 123"

**[imdb]** Update IMDb fields on movies and tvshows. Pipe output into `set` option to apply changes to the media library using JSON. Uses http://www.omdbapi.com to query latest IMDb details based on `imdbnumber` (movies) or `title` and `season`/`episode` # (tvshows). Movies without `imdbnumber` will not be updated. Specify movie fields to be updated with the property `@imdb.fields.movies` from the following: `top250`, `title`, `rating`, `votes`, `year`, `runtime`, `genre`, `plot` and `plotoutline` - the default value is: `rating, votes, top250`. Specify tvshow fields to be updated with the property `@imdb.fields.tvshows` from the following: `title`, `rating`, `votes`, `year`, `runtime`, `genre`, `plot` and `plotoutline`. Specify additional fields to the default by prefixing the list with `+`, eg. `@imdb.fields.movies=+year,genre` to update movie ratings, votes, top250, year and genre. See log for old/new values. See [announcement](http://forum.kodi.tv/showthread.php?tid=158373&pid=2120793#pid2120793) for further important details

**[purge hashed|unhashed|all]** Delete cached artwork containing specified patterns, with or without lasthashcheck, or if it doesn't matter `all` eg. `purge unhashed youtube iplayer imdb.com`

**[purgetest hashed|unhashed|all]** Dry-run version of `purge` - will show what would be removed during an actual `purge`

**[watched]** Backup and restore movie and tvshow watched lists to a text file. Watched list will be restored keeping more recent playcount, lastplayed and resume points unless  `@watched.overwrite=yes` is specified, in which case the watched list will be restored exactly as per the backup.

**[duplicates]** List movies that appear more than once in the media library with the same IMDb number

**[missing]** Locate media files missing from the specified media library and source label, eg. `missing movies "My Movies"`

**[ascan, vscan]** Initiate audio/video library scan, either entire library or a specific path (see **sources**). The exit status is the number of items added during each scan, ie. 0 or +n.

**[aclean, vclean]** Clean audio/video library

**[directory, rdirectory]** Obtain directory listing for a specific path (see **sources**). Use **rdirectory** for a recursive listing.

**[readfile]** Read contents of the named file, outputting contents to stdout (`-`, not suitable for binary data) or the named file (suitable for binary data).

**[sources]** List of sources for a specific media class (video, music, pictures, files, programs), optionally filtered by label (eg. "My Movies")

**[status]** Display status of client - ScreenSaver active, IsIdle (default period 600 seconds, or user specified) and active Player type (audio or video), plus title of any media currently being played.

**[monitor]** Display client event notifications as they occur

**[rbphdmi]** Manage Raspberry Pi HDMI power state. Specify power-off delay in seconds as second argument (default is 900 seconds). Requires `xbmc.host` set to localhost. Specify location of tvservice executable (to turn HDMI on and off) in `bin.tvservice` property (default is `/usr/bin/tvservice`). Activate debug diagnostics with `@debug=yes`, otherwise expect no output.

**[stats]** Output media library stats. Optionally filter by media class, eg. `stats tvshows episodes` or `stats audio`

**[input]** Send keyboard/remote control input to client, eg. `input back left left select`. See [JSON API](http://kodi.wiki/view/JSON-RPC_API/v6#Input) for more details

**[volume]** Show mute state and volume level (no args), or set volume level `0`-`100`, `mute`, `unmute`, eg. `volume mute` or `volume 100`

**[stress-test]** Stress system by iterating over GUI items. eg. `stress-test thumbnail 444 0.1 9` to iterate over 444 items in a thumbnail (5 x 2 poster) view with a 0.1 second delay between each movement. Repeat 9 times. Other supported view types: `horizontal` and `vertical`. Default pause is 0.25, default repeat is 1. A sixth argument, cooldown, can be specified to pause each traversal for the specified number of seconds (default is 0, no cooldown).

**[screenshot]** Take screen grab of the current display

**[power]** Set power state of client - `suspend`, `hibernate`, `shutdown`, `reboot` or `exit`.

**[wake]** Use Wake Over LAN to wake a suspended/hibernating remote client. Specify the MAC address of the remote client in the `network.mac` property (ie. `network.mac=xx:xx:xx:xx:xx:xx`). When the client is no longer required, suspend or hibernate it with the `power` option.

**[exec, execw]** Execute the specified addon, with optional parameters. eg. `exec script.artwork.downloader silent=true mediatype=tvshow`. Use `execw` to wait, but this rarely has any effect (possibly not implemented by JSON?)

**[setsetting]** Set the value of the named setting, eg. `setsetting locale.language English`
**[getsetting]** Get the current value of the named setting, eg. `getsetting locale.language`
**[getsettings]** View details of all settings, or those where pattern is contained within `id`, eg. `getsettings debug` to view details of all debug-related settings

**[debugon, debugoff]** Enable/Disable debugging

**[play, playw]** Play specified item (local file, playlist, internet stream etc.), optionally waiting until playback is ended
**[stop]** Stop playback
**[pause]** Toggle pause/playback of currently playing media

**[config]** View current configuration

**[version]** View current installed version

**[update]** Manually update to latest available version if not already installed. Only required if `checkupdate` or `autoupdate` properties are set to `no` as by default the script will automatically update itself (if required) to the latest version whenever it is executed.

## Installation instructions

#### Installation from distro packages

* ![logo](http://www.monitorix.org/imgs/archlinux.png "arch logo")Arch: in the [AUR](https://aur.archlinux.org/packages/xbmc-texturecache).

#### Installation from source
Download the single Python file required from Github. A default properties file is available on Github, rename this to texturecache.cfg in order to use it.

To download the script at the command line:

```bash
wget https://raw.githubusercontent.com/MilhouseVH/texturecache.py/master/texturecache.py -O texturecache.py
chmod +x ./texturecache.py
```

If you experience a certificate error, try adding "--no-check-certificate" to the wget command line.

If you are using OpenELEC which has a pretty basic wget that doesn't support HTTPS downloads, instead use `curl`:

```bash
curl https://raw.githubusercontent.com/MilhouseVH/texturecache.py/master/texturecache.py -o texturecache.py
chmod +x ./texturecache.py
```

##### ATV2 (iOS) users

Python 2.6+ is required to run this script, and although Python can be installed on iOS using `apt-get install python`, the version installed (typically v2.5.1 - check with `python --version`) is very old and lacks language features required by the script. It is possible to install a more recent [Python 2.7.3 package](http://code.google.com/p/yangapp/downloads/detail?name=python_2.7.3-3_iphoneos-arm.deb&can=2&q=) as follows:

#### Code:

```bash
ssh root@YOUR.ATV2.IP.ADDRESS
rm -f python*.deb
wget http://yangapp.googlecode.com/files/python_2.7.3-3_iphoneos-arm.deb
dpkg -i python*.deb
rm python*.deb
```

## Basic Example usage
Let's say the poster image for the "Dr. No" movie is corrupted, and it needs to be deleted so that Kodi will automatically re-cache it (hopefully correctly) next time it is displayed:

1) Execute: `./texturecache.py s "Dr. No"` to search for my Dr. No related artwork

2) Several rows should be returned from the datbase, relating to different cached artwork - one row will be for the poster, the other fanart, and there may also be rows for other image types too (logo, clearart etc.). This is what we get for Dr. No:

```
000226|5/596edd13.jpg|0720|1280|0011|2013-03-05 02:07:40|2013-03-04 21:27:37|nfs://192.168.0.3/mnt/share/media/Video/Movies/James Bond/Dr. No (1962)[DVDRip]-fanart.jpg
000227|6/6f3d0d94.jpg|0512|0364|0003|2013-03-05 02:07:40|2013-03-04 22:26:38|nfs://192.168.0.3/mnt/share/media/Video/Movies/James Bond/Dr. No (1962)[DVDRip].tbn
Matching row ids: 226 227
```

3) Since only the poster (.tbn) needs to be removed, executing `./texturecache.py d 227` will remove both the database row *and* the cached poster image. If we wanted to remove both images, we would simply execute `./texturecache.py d 226 227` and the two rows and their corresponding cached images would be removed.

Now it's simply a matter of browsing the Dr. No movie in the Kodi GUI, and the image should be re-cached correctly.

But wait, there's more... another method is to force images to be re-cached, automatically. `./texturecache.py C movies "Dr. No"` will achieve the same result as the above three steps, including re-caching the deleted items so that it is already there for you in the GUI.

## Media Classes

The utility has several options that operate on media library items grouped into classes:

* addons
* agenres _(audio genres)_
* vgenres _(video genres: aggregated list of movie, tvshow and musicvideo genres)_
* pvr.tv
* pvr.radio
* albums
* artists
* songs
* movies
* sets
* tags
* tvshows

The following "meta" media classes can also be used in place of one of the above media classes:
* music _(equivalent to: `albums` + `artists` + `songs`)_
* video _(equivalent to: `movies` + `sets` + `tvshows`)_
* all _(equivalent to: `addons` + `agenres` + `vgenres` + `pvr.tv` + `pvr.radio` + `albums` + `artists` + `songs` + `movies` + `sets` + `tvshows`)_

In most cases, when performing an operation it is possible to specify a filter to further restrict processing/selection of particular items, for example, to extract the default media library details for all movies whose name contains "zombie":

```bash
./texturecache.py j movies zombie
```

## Tag Support
When using the tags media class, you can apply a filter that uses logical operators such as `and` and `or` to restrict the selection criteria.

For example, to cache only those movies tagged with either action and adventure:

```bash
./texturecache.py c tags "action and adventure"
```

Or, only those movies tagged with either comedy or family:

```bash
./texturecache.py c tags "comedy or family"
```

If no filter is specified, all movies with a tag will be selected.


## Format of database records

When displaying rows from the texture cache database, the following fields (columns) are shown:

```csv
rowid, cachedurl, height, width, usecount, lastusetime, lasthashcheck, url
```

## Additional usage examples

##### Caching all of the artwork for your TV shows

```bash
./texturecache.py c tvshows
```

##### Viewing your most recently accessed artwork
```bash
./texturecache.py x | sort -t"|" -k6
```

or

```bash
./texturecache.py x "order by lastusetime asc"
```

##### Viewing your Top 10 accessed artwork

```bash
./texturecache.py x | sort -t"|" -k5r | head -10
```
or
```bash
./texturecache.py x "order by usecount desc" 2>/dev/null | head -10
```

##### Identifying cached artwork for deletion

Use texturecache.py to identify artwork for deletion, then cutting and pasting the matched ids into the "d" option or via a script:

For example, to delete those small remote thumbnails you might have viewed when downloading artwork (and which still clutter up your cache):

```bash
./texturecache.py s "size=thumb"
```

then cut & paste the ids as an argument to `./texturecache.py d id [id id]`

And the same, but automatically:

```bash
IDS=$(./texturecache.py s "size=thumb" 2>&1 1>/dev/null | cut -b19-)
[ -n "$IDS" ] && ./texturecache.py d $IDS
```

Or when removing artwork that is no longer needed, simply let texturecache.py work it all out:

```./texturecache.py P```

##### Delete artwork that has not been accessed after a particular date

```
./texturecache.py x "where lastusetime <= '2013-03-05'"
```

or hasn't been accessed more than once:
#### Code:

```
./texturecache.py x "where usecount <= 1"
```

##### Query the media library, returning JSON results

First, let's see the default fields for a particular media class (movies), filtered for a specific item (avatar):

```
./texturecache.py jd movies "avatar"
```
#### Result:
```json
[
  {
    "movieid": 22,
    "title": "Avatar",
    "art": {
      "fanart": "image://nfs://192.168.0.3/mnt/share/media/Video/MoviesSD/Avatar (2009)[DVDRip]-fanart.jpg/",
      "poster": "image://nfs://192.168.0.3/mnt/share/media/Video/MoviesSD/Avatar (2009)[DVDRip]-poster.jpg/",
      "clearart": "image://http://assets.fanart.tv/fanart/movies/19995/hdmovieclearart/avatar-51290d15d6163.png/",
      "clearlogo": "image://http://assets.fanart.tv/fanart/movies/19995/hdmovielogo/avatar-51290d0678d4e.png/"
    },
    "label": "Avatar"
  }
]
```

With `extrajson.movies = trailer, streamdetails, file` in the properties file, here is the same query but now returning the extra fields too:

```
./texturecache.py Jd movies "Avatar"
```
#### Result:
```json
[
  {
    "movieid": 22,
    "title": "Avatar",
    "label": "Avatar",
    "file": "nfs://192.168.0.3/mnt/share/media/Video/Movies/Avatar (2009)[DVDRip].m4v",
    "art": {
      "fanart": "image://nfs://192.168.0.3/mnt/share/media/Video/MoviesSD/Avatar (2009)[DVDRip]-fanart.jpg/",
      "poster": "image://nfs://192.168.0.3/mnt/share/media/Video/MoviesSD/Avatar (2009)[DVDRip]-poster.jpg/",
      "clearart": "image://http://assets.fanart.tv/fanart/movies/19995/hdmovieclearart/avatar-51290d15d6163.png/",
      "clearlogo": "image://http://assets.fanart.tv/fanart/movies/19995/hdmovielogo/avatar-51290d0678d4e.png/"
    },
    "trailer": "",
    "streamdetails": {
      "video": [
        {
          "duration": 9305,
          "width": 720,
          "codec": "avc1",
          "aspect": 1.7779999971389771,
          "height": 576
        }
      ],
      "audio": [
        {
          "channels": 6,
          "codec": "aac",
          "language": "eng"
        }
      ],
      "subtitle": []
    }
  }
]
```

## Setting fields in the media library

Specify values on the command line to set fields for a single media library item. For example:
```shell
./texturecache.py set movie 312 art.clearlogo "nfs://myserver/movies/thismovie-logo.png" \
                                art.clearart "nfs://myserver/movies/thismovie-clearart.png" \
                                playcount 12 \
                                trailer "http://www.totaleclips.com/Player/Bounce.aspx?eclipid=e121648&bitrateid=449&vendorid=102&type=.mp" \
                                tag "['horror', 'zombies']"
```

Specify a value of null or None for a field value to remove that field from the database.

Updates may also be batched. Create an input file using JSON notation, for example:
```json
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

then pipe the file as input to texturecache.py with the set or testset option (no other parameters required - all additional information will be read from stdin).

```bash
cat /tmp/movies.dat | ./texturecache.py set
```

Required fields are `libraryid`, `type` and `items`. `title` is optional. Fields within `items` will be updated in the media library as per the command line equivalent.

## Directory Paths
In addition to physical (smb://, nfs:// etc.) paths, the following virtual paths (or their sub-directories) can be used when calling the `directory` and `rdirectory` options:
* virtualpath://upnproot/
* musicdb://
* videodb://
* library://video
* sources://video
* special://musicplaylists
* special://profile/playlists
* special://videoplaylists
* special://skin
* special://profile/addon_data
* addons://sources
* upnp://
* plugin://

## Optional Properties File

By default the script will run fine on distributions where the `.xbmc/userdata` folder is within the users Home folder (ie. `userdata=~/.xbmc/userdata`). To override this default, specify a properties file with a different value for the `userdata` property.

The properties file should be called `texturecache.cfg`, and will be looked for in the current working directory, then in the same directory as the texturecache.py script. What follows is an example properties file showing the default values:

```properties
sep = |
userdata = ~/.xbmc/userdata
dbfile = Database/Textures13.db
thumbnails = Thumbnails
xbmc.host = localhost
webserver.port = 8080
webserver.username =
webserver.password =
rpc.port = 9090
download.threads = 2
singlethread.urls = assets\.fanart\.tv
extrajson.addons =
extrajson.albums =
extrajson.artists =
extrajson.songs =
extrajson.movies =
extrajson.sets =
extrajson.tvshows.tvshow =
extrajson.tvshows.season =
extrajson.tvshows.episode =
qaperiod = 30
qa.file = no
qa.nfo.refresh = 
qa.fail.urls = ^video, ^music
qa.warn.urls =
qa.art.addons =
qa.art.albums =
qa.art.artists =
qa.art.movies = fanart, poster
qa.art.sets = fanart, poster
qa.art.songs =
qa.art.tvshows.episode = thumb
qa.art.tvshows.season =
qa.art.tvshows.tvshow = fanart, banner, poster
qa.blank.addons =
qa.blank.albums =
qa.blank.artists =
qa.blank.movies = plot, mpaa
qa.blank.sets =
qa.blank.songs =
qa.blank.tvshows.episode = plot
qa.blank.tvshows.season =
qa.blank.tvshows.tvshow = plot
qa.zero.addons =
qa.zero.albums =
qa.zero.artists =
qa.zero.movies =
qa.zero.sets =
qa.zero.songs =
qa.zero.tvshows.episode =
qa.zero.tvshows.season =
qa.zero.tvshows.tvshow =
cache.castthumb = no
cache.hideallitems = no
cache.artwork =
cache.ignore.types = ^video, ^music
cache.extrafanart = no
cache.extrathumbs = no
cache.videoextras = no
prune.retain.types =
prune.retain.previews = yes
prune.retain.pictures = no
logfile =
logfile.verbose = yes
checkupdate = yes
autoupdate = yes
lastrunfile =
orphan.limit.check = yes
purge.minlen = 5
picture.filetypes =
video.filetypes =
audio.filetypes =
subtitle.filetypes =
watched.overwrite = no
network.mac =
imdb.fields.movies = rating, votes, top250
imdb.fields.tvshows = rating, votes
bin.tvservice = /usr/bin/tvservice
hdmi.force.hotplug = no
```

The `dbfile` and `thumbbnails` properties represent folders that are normally relative to the `userdata` property, however full paths can be specified.

Set values for `webserver.username` and `webserver.password` if you require webserver authentication.

The `extrajson.*` properties allow the specification of additional JSON audio/video fields to be returned by the J/Jd query options. See the Kodi [JSON-RPC API Specification](http://kodi.wiki/view/JSON-RPC_API/v6) for details.

The `qa.art.*`, `qa.blank.*` and `qa.zero.*` files can be used to replace or add additional fields for qa (not zero, not blank, and present in art list). Add to default fields by prefixing with +, so `qa.blank.movies = +director` will QA mpaa, plot and director for movies (failing QA if any are blank).

Cast thumbnails will not be cached by default, so specify `cache.castthumb = yes` if you require cast artwork to be re-cached, or considered when pruning.

Extrafanart and extrathumbs will not be cached by default or considered when pruning. Specify `cache.extra = yes` to cache/prune both extrafanart and extrathumbs, or `cache.extrafanart = yes` or `cache.extrathumbs = yes` to enable just extrafanart or just extrathumbs.

Filtering will default to the title field in most cases, such that `jd movies avatar` will return only movies where the title contains the text "avatar". However, you may specify an alternate field on which to filter with `@filter=<field>`. For example, should you wish to select only movies directed by James Cameron, use `jd movies "james cameron" @filter=director`.

The default filter operator is `contains`, but this can be changed to any one of the [standard filter operators](http://kodi.wiki/view/JSON-RPC_API/v6#List.Filter.Operators) using `@filter.operator=<operator>`. For example, `jd movies 21 @filter.operator=is` will return only the movie "21", but not "21 Jump Street".

Cache specific artwork types by specifying a comma-delimited list of artwork types for `cache.artwork`, eg. `cache.artwork=poster, fanart` to cache only posters and fanart. By default this list is empty, which will ensure that all artwork types are cached.

Ignore specific URLs when pre-loading the cache (c/C/nc options), by specifying comma delimited regex patterns for the `cache.ignore.types` property. Default values are `^video` and `^music` (not that these patterns are applied after the image:// prefix has been removed from the url). Set to none (no argument) to process all URLs. Any URL that matches one of the ignore types will not be considered for re-caching (and will be counted as "ignored").

Prevent caching of "Season All" posters/fanart/banners by enabling `cache.hideallitems` - default is to cache these items. Corresponds with similar hideallitems value in advancedsettings.xml.

Retain specific URLs when pruning the texture cache, eg. `prune.retain.types = ^http://www.wiziwig.tv/` to keep all artwork relating to wizwig.tv (as used by the SportsDevil addon).

Specify a filename for the `logfile` property, to log detailed processing information. Prefix the filename with + to force flushing. Enable logfile.verbose for increased level of logging.

Use `download.threads` to vary the number of threads used when downloading and caching data. Class specific values can also be used, eg. `download.threads.movies`. Any class without a specific value will use `download.threads`.

Specify a comma delimited list of pattherns in `singlethread.urls` to force downloads corresponding with those URLs on a single thread, necessary for sites that limit the number of concurrent requests. One such site is fanart.tv, hence the default value includes `assets\.fanart\.tv`.

When identifying `missing` media files (ie. files that are not present in the media library), additional audio and video file types can be included by specifying a comma delimited list of file extensions for `audio.filetypes` and `video.filetypes` respectively (eg. `wmv, ogg`). All current Kodi audio and video file extensions are supported by default.

## Command Line Properties

As an alterantive or in addition to a properties file, properties may be specified on the command line, using the syntax `@<key>=<value>` - such command line property values will override any matching property retrieved from the properties file.

In addition, the name of the properties file may be specified using the `@config` command line property, eg. `@config=./myconfig.cfg`.

Also, a specific property section may be used, `@section=name`, allowing multiple clients to be configured within a single property file, sharing a "global" (default, un-named) section with unique properties specified within each section. For example:

```ini
webserver.port = 8080
webserver.username = username
webserver.password = password
extrajson.movies = streamdetails, file, mpaa, rating, plot

[lounge]
xbmc.host = 192.168.0.4
download.threads = 10
cache.castthumb = yes
lastrunfile=/tmp/lrf_lounge.dat

[bedroom]
xbmc.host = 192.168.0.8
download.threads = 2
cache.castthumb = no
lastrunfile=/tmp/lrf_bedroom.dat</pre>
```
then: 
```bash
texturecache.py lc movies @config=/home/user/cache.cfg @section=lounge
```

Run the script without arguments for basic usage, and with `config` option to view current configuration information.

See [texturecache.py @ Kodi Forums](http://forum.xbmc.org/showthread.php?tid=158373).
=====
