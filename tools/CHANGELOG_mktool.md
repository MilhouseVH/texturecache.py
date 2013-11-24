
#Changelog

## 24/11/2013
* Add: Support movies in individual folders with `-1`/`--singlefolders` switch. With this switch enabled, artwork will not be created or located using the movie name as a prefix (ie. `poster.jpg` rather than `Zombieland(2009)-poster.jpg`). The default is to create and locate artwork using the movie name as a prefix!
* Fix: Regex on path mapping functions, re.sub() didn't like Windows backslashes...

## 09/11/2013
* Add: Movie sets support, finding common parent folder for each set (requires texturecache.py v1.0.5+)

## 04/11/2013
* Replace `--add` argument with `--artwork`
* Replace `--nodownload/-n` with `--readonly/-r`
* Fix: Foreign encoding in filenames

## 21/10/2013
* Remove `--del` option
* Remove default clearart and clearlogo artwork - now need to be specified using `--add`
