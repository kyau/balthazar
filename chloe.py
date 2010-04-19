#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010, Sean Bruen. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions 
# are met:
#
#    1. Redistributions of source code must retain the above copyright 
#       notice, this list of conditions and the following disclaimer.
#    2. Redistributions in binary form must reproduce the above 
#       copyright notice, this list of conditions and the following 
#       disclaimer in the documentation and/or other materials provided 
#       with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and documentation 
# are those of the authors and should not be interpreted as 
# representing official policies, either expressed or implied, of the 
# Privatebox Networks.

__version__ = '$Revision$'


import ConfigParser
import MySQLdb
import re
import signal
import telnetlib
import threading
from sys import exit
from time import localtime, strftime

""" global variables """
chloe = telnetlib.Telnet()
ANSI_COLOR_REGEXP = re.compile(chr(27) + '\[[0-9;]*[m]')
ANSI_REGEXP = re.compile('( |[A-Z])\x08')
bbs = {}
menu = {}
mysql = {}
www = {}
""" debug variables """
debug = {}
_debug = 0

def main():
	""" initialize variables and config """
	global ANSI_REGEXP, ANSI_COLOR_REGEXP, bbs, chloe, debug, menu, start, www, _debug
	config()
	if (_debug): plog('intializing...')
	signal.signal(signal.SIGINT, quit)

	""" start telnet/threaded timer """
	t = threading.Timer(30.0, report)
	t.start()
	start = 1
	sql = _sql(mysql['host'],mysql['port'],mysql['user'],mysql['passwd'],mysql['db'])
	_telnet()
	chloe.write('\r\n')
	while 1:
		line = chloe.read_until('\r\n')
		line = line.strip('\r\n')
		line = ANSI_COLOR_REGEXP.sub('', line)
		line = ANSI_REGEXP.sub('', line)
		if (_debug): mlog('%s' % line)
	return 0

def config():
	""" populate lists with configuration information """
	global bbs, debug, menu, www, _debug
	cfg = ConfigParser.ConfigParser()
	cfg.read('bbs.cfg')
	bbs['host'] = cfg.get('BBS', 'host', 1)
	bbs['user'] = cfg.get('BBS','user', 1)
	bbs['passwd'] = cfg.get('BBS','passwd', 1)
	bbs['admin'] = cfg.get('BBS', 'admin', 1)
	menu['main'] = cfg.get('MENU', 'main', 1)
	menu['pause'] = cfg.get('MENU', 'pause', 1)
	menu['mud'] = cfg.get('MENU', 'mud', 1)
	menu['go'] = cfg.get('MENU', 'go', 1)
	mysql['host'] = cfg.get('MYSQL', 'host', 1)
	mysql['port'] = int(cfg.get('MYSQL', 'port', 1))
	mysql['user'] = cfg.get('MYSQL', 'user', 1)
	mysql['passwd'] = cfg.get('MYSQL', 'passwd', 1)
	mysql['db'] = cfg.get('MYSQL', 'db', 1)
	debug['log'] = int(cfg.get('DEBUG', 'log', 1))
	debug['logfile'] = cfg.get('DEBUG', 'logfile', 1)
	if not (_debug):
		_debug = int(cfg.get('DEBUG', 'verbose', 1))
	return 0

def plog(text):
	""" debug log """
	global debug
	if (debug['log']):
		log = open(debug['logfile'], 'a')
		time = strftime('%a, %d %b %Y %H:%M:%S %Z', localtime())
		log.write('%s chloe: %s\n' % (time, text))
	time = strftime('%H:%M:%S', localtime())
	print '%s chloe: %s' % (time, text)
	if (debug['log']): log.close()
	return 0

def mlog(text):
	""" debug mud log """
	global debug
	if (debug['log']):
		log = open(debug['logfile'], 'a')
		time = strftime('%a, %d %b %Y %H:%M:%S %Z', localtime())
		log.write('%s: %s\n' % (time, text))
	time = strftime('%H:%M:%S', localtime())
	print '%s: %s' % (time, text)
	if (debug['log']): log.close()
	return 0

def quit(signum, frame):
	""" stop telnet/threaded timer and exit """
	global chloe, _debug
	if (_debug): plog('%d terminating...\n' % threading.active_count())
	chloe.close()
	exit(0)

def _telnet():
	""" telnet connectivity """
	global bbs, chloe, menu, _debug
	try:
		chloe.open(bbs['host'])
		data = chloe.read_until('login:')
		chloe.write('%s\r\n' % bbs['user'])
		data = chloe.read_until('password:')
		chloe.write('%s\r\n' % bbs['passwd'])
	except:
		plog('telnet connection refused.\n - check config: bbs.cfg\n')
		exit(1)
	""" enter majormud """
	while 1:
		data = chloe.read_very_eager()
		if (menu['pause'] in data):
			chloe.write('\r\n')
		elif (menu['main'] in data):
			chloe.write('%s\r\n' % menu['go'])
		elif (menu['mud'] in data):
			chloe.write('E\r\n')
		elif ('[HP=' in data):
			bbs['conn'] = 1
			if (_debug): plog('character %s on %s connected.' % (bbs['user'], bbs['host']))
			break
	return 0

def _sql(DATABASE_HOST, DATABASE_PORT, DATABASE_USER, DATABASE_PASSWD, DATABASE_NAME):
	""" mysql database connectivity """
	try:
		db=MySQLdb.connect(host=DATABASE_HOST,user=DATABASE_USER,passwd=DATABASE_PASSWD, port=int(DATABASE_PORT))
	except MySQLdb.OperationalError:
		plog('error connecting to mysql database.\n - check config: bbs.cfg\n')
		exit(1)

	plog('database %s on %s connected.' % (DATABASE_NAME, DATABASE_HOST))
	return db.cursor()

def report():
	""" timer control """
	global bbs, chloe, debug, start, _debug
	if not (bbs['conn']): exit(0)
	if (_debug) and (start >= 1): plog('report #%d' % start)
	chloe.write('\r\n')
	start = start + 1
	t = threading.Timer(30.0, report)
	t.start()
	return 0

if __name__ == '__main__':
	main()
