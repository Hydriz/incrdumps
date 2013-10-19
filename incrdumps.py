#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2012 Hydriz
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import re
import sys
import time
import urllib

import converter
import settings

# Settings are all at settings.py, thanks!
# Global configuration
userdate = ""
filelist = {
	'-md5sums.txt',
	'-pages-meta-hist-incr.xml.bz2',
	'-stubs-meta-hist-incr.xml.gz',
	'maxrevid.txt',
	'status.txt',
}
wikilist = ""
count = 0
start = ""
sitename = ""
curdate = ""
language = ""
wikifamily = ""
archivedate = ""
wikitoarchive = None

# Clone the settings in settings.py
tempdir = settings.tempdir
accesskey = settings.accesskey
secretkey = settings.secretkey
hosturl = settings.hosturl
rsynchost = settings.rsynchost
collection = settings.collection
mediatype = settings.mediatype
sizehint = settings.sizehint

def welcome():
	print "Welcome to the incremental dumps archiving script!"

def bye():
	print "Done uploading!"

def grablistofwikis():
	global wikilist
	directory = urllib.urlopen(hosturl)
	raw = directory.read()
	directory.close()
	wikis = re.compile(r'<strong>(?P<wiki>[^>]+)</strong>').finditer(raw)
	wikilisting = []
	for wiki in wikis:
		wikilisting.append([wiki.group('wiki')])
	wikilist = wikilisting
	for wiki in wikilist:
		thewiki = ''.join(wiki)
		os.system("echo %s >> %s-wikis.txt" % (thewiki, userdate))

def foreachwiki():
	global count, sitename, curdate, language, wikifamily, archivedate
	for thewiki in wikilist:
		curwiki = ''.join(thewiki)
		x = converter.ASConverter()
		x.convertdate(userdate)
		curdate = x.date
		d = datetime.strptime(curdate, '%Y%m%d')
		archivedate = d.strftime('%Y-%m-%d')
		if (curwiki == "Here's the big fat disclaimer."): # The only non-wiki string that is in bold
			continue
		else:
			downloaddump(curwiki)
			x.convertdb(curwiki)
			if (x.special):
				sitename = x.sitename
				if (curwiki.endswith("wikimedia")):
					language = x.sitename
					wikifamily = "Wikimedia"
				else:
					language = "English"
					wikifamily = "Wikimedia"
			elif (x.site == ""):
				sitename = curwiki
			else:
				sitename = "the %s" % (x.sitename)
				language = x.langname
				wikifamily = x.site
			upload(curwiki)
			rmdir(curwiki)
			count = 0 # Bringing it back down to 0 once its done uploading for the current wiki

def downloaddump(wiki):
	global rsynchost, tempdir
	os.system('rsync -av ' + rsynchost + '/' + wiki + '/' + userdate + ' ' + tempdir + '/' + wiki)

def upload(wiki):
	global count, filelist, tempdir, curdate, sitename, userdate, language, wikifamily, archivedate
	os.chdir(tempdir + '/' + wiki + '/' + userdate)
	for thefile in filelist:
		curfile = ''.join(thefile)
		if (curfile.startswith('-')):
			thedumpfile = wiki + '-' + userdate + curfile
		else:
			thedumpfile = curfile
		time.sleep(1) # Ctrl-C
		if (count == 0):
			curl = ['curl', '--retry 3', '--location',
					'--header', "'x-amz-auto-make-bucket:1'",
					'--header', "'x-archive-meta01-collection:%s'" % (collection),
					'--header', "'x-archive-meta-mediatype:%s'" % (mediatype),
					'--header', "'x-archive-meta-subject:wiki;incremental;dumps;%s;%s;%s'" % (wiki, language, wikifamily),
					'--header', "'x-archive-meta-date:%s'" % (archivedate),
					'--header', "'x-archive-queue-derive:0'",
					'--header', "'x-archive-size-hint:%s'" % (sizehint),
					'--header', "'x-archive-meta-title:Wikimedia incremental dump files for %s on %s'" % (sitename, curdate),
					'--header', "'x-archive-meta-description:This is the incremental dump files for %s that is generated by Wikimedia on %s.'" % (sitename, curdate),
					'--header', '"authorization: LOW %s:%s"' % (accesskey,secretkey),
					'--upload-file', "%s http://s3.us.archive.org/incr-%s-%s/%s" % (thedumpfile,wiki,userdate,thedumpfile),
					]
			os.system(' '.join(curl))
			time.sleep(60)
			count += 1
		else:
			curl = ['curl', '--retry 3', '--location',
					'--header', "'x-archive-queue-derive:0'",
					'--header', '"authorization: LOW %s:%s"' % (accesskey,secretkey),
					'--upload-file', "%s http://s3.us.archive.org/incr-%s-%s/%s" % (thedumpfile,wiki,userdate,thedumpfile),
					]
			os.system(' '.join(curl))

def rmdir(wiki):
	global tempdir
	os.chdir(tempdir)
	os.system('rm -rf ' + wiki)

def archiveone(wiki):
	global curdate, sitename, userdate
	x = converter.ASConverter()
	x.convertdate(userdate)
	downloaddump(wiki)
	x.convertdb(wiki)
	curdate = x.date
	if (x.special):
		sitename = x.sitename
	elif (x.site == ""):
		sitename = wiki
	else:
		sitename = "the %s" % (x.sitename)
	upload(wiki)
	rmdir(wiki)

def processopts():
	global userdate, wikitoarchive
	if (len(sys.argv) < 2):
		print "You are missing the date parameter! Please tell me which date to archive!"
		sys.exit(1)
	elif (len(sys.argv) == 2):
		userdate = sys.argv[1]
	elif (len(sys.argv) == 3):
		userdate = sys.argv[1]
		wikitoarchive = sys.argv[2]
	elif (len(sys.argv) > 3):
		print "Warning: More than 2 arguments detected, ignoring the extras..."
		userdate = sys.argv[1]
		wikitoarchive = sys.argv[2]

def process():
	global wikitoarchive
	welcome()
	processopts()
	if (wikitoarchive != None):
		archiveone(wikitoarchive)
	else:
		grablistofwikis()
		foreachwiki()
	bye()

if __name__ == "__main__":
	process()
