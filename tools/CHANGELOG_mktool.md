# Changelog

## 03/03/2019
* Add: `--overwrite` option to download then overwrite existing artwork files. Fixes #56.

## 15/05/2018
* Fix: `discart` and `clearlogo` artwork types now use `-discart` and `-clearlogo` suffix. Use `discart:disc`/`clearart:logo` mappings for old behaviour.

## 10/11/2017
* Add: Support for https

## 25/08/2015
* Add: Support extrafanart and extrathumbs artwork types (fanart# and thumb#, respectively). Specify the maximum number of items per artwork type with `--extrafanartmax` and `--extrathumbsmax` - both default to 4 (existing items in excess of this amount will be removed if `--nokeep` is specified). The assumed location of the `extrafanart` and `extrathumbs` directories will be alongside the corresponding media unless a shared local directory path is specified for either `--extrafanart` or `--extrathumbs`. See http://kodi.wiki/view/Extra_fanart for naming details.

## 28/11/2014
* Fix: Unicode issue when displaying urls

## 24/09/2014
* Fix: Assume titles and filenames are unicode in diagnostic output

## 17/03/2014
* Add: `--info` argument to redirect informational data to stdout instead of stderr

## 15/03/2014
* Fix: Filename encoding issue with foreign characters.

## 18/01/2014
* Add: `nokeep` option - don't keep artwork that cannot be matched to pre-existing local artwork

## 02/01/2014
* Chg: Verify existence of --local and --altlocal paths even when --readonly is specified.
* Fix: Use correct forward slash/backward slash when converting a network path to local Windows path and vice versa
* Fix: Map discart:discart -> discart:disc

## 25/11/2013
* Add: Support movies in individual folders with `-1`/`--singlefolders` switch. With this switch enabled, artwork will not be created or located using the movie name as a prefix (ie. `poster.jpg` rather than `Zombieland(2009)-poster.jpg`). The default is to create and locate artwork using the movie name as a prefix!
* Fix: Regex on path mapping functions, re.sub() didn't like Windows backslashes...
* Fix: Allow for mixed movie-name prefix when using `--singlefolder`, although non-movie-name takes priority. Only useful when local files already exist with a mixture of filenaming conventions."
* Add: stack support

## 09/11/2013
* Add: Movie sets support, finding common parent folder for each set (requires texturecache.py v1.0.5+)

## 04/11/2013
* Replace `--add` argument with `--artwork`
* Replace `--nodownload/-n` with `--readonly/-r`
* Fix: Foreign encoding in filenames

## 21/10/2013
* Remove `--del` option
* Remove default clearart and clearlogo artwork - now need to be specified using `--add`
