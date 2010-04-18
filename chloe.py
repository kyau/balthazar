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

__version__ = '$Id$'


import ConfigParser
import re
import signal
import sys
import telnetlib
import threading
import time

""" global variables """
chloe = telnetlib.Telnet()
ANSI_COLOR_REGEXP = re.compile(chr(27) + '\[[0-9;]*[m]')
bbs = {'host': '', 'login': '', 'pass': '', 'conn': 0}
menu = {'main': '', 'pause': '', 'go': ''}
www = {'dir': '', 'log': ''}
""" verbose output """
debug = 1

def main():
	""" start telnet/threaded timer """
	global ANSI_COLOR_REGEXP, bbs, chloe, debug, menu, start, www
	signal.signal(signal.SIGINT, quit)
	t = threading.Timer(30.0, report)
	t.start()
	start = 1
	config()
	telnet()
	chloe.write('\r\n')
	while 1:
		line = chloe.read_until('\r\n')
		line = line.strip('\r\n')
		line = ANSI_COLOR_REGEXP.sub('', line)
		if (debug): print 'chloe: bbs: ' + line
	return 0

def quit(signum, frame):
	""" stop telnet/threaded timer and exit """
	global chloe, debug
	if (debug): print 'chloe: exiting %d thread(s)' % (threading.active_count())
	chloe.close()
	sys.exit(0)

def config():
	""" populate lists with configuration information """
	global bbs, debug, menu, www
	cfg = ConfigParser.ConfigParser()
	cfg.read('bbs.cfg')
	bbs['host'] = cfg.get('MAIN', 'host', 1)
	bbs['login'] = cfg.get('MAIN','login', 1)
	bbs['pass'] = cfg.get('MAIN','password', 1)
	menu['main'] = cfg.get('MENU', 'main', 1)
	menu['pause'] = cfg.get('MENU', 'pause', 1)
	menu['mud'] = cfg.get('MENU', 'mud', 1)
	menu['go'] = cfg.get('MENU', 'go', 1)
	return 0

def telnet():
	""" open connection to the bbs """
	global bbs, chloe, debug, menu
	try:
		chloe.open(bbs['host'])
		start = time.time()
		data = chloe.read_until('login:')
		chloe.write(bbs['login'] + '\r\n')
		data = chloe.read_until('password:')
		chloe.write(bbs['pass'] + '\r\n')
	except:
		print 'telnet connection refused.\n - check config: bbs.cfg'
		sys.exit(1)
	""" enter majormud """
	while 1:
		data = chloe.read_very_eager()
		if (menu['pause'] in data):
			chloe.write('\r\n')
		elif (menu['main'] in data):
			chloe.write(menu['go'] + '\r\n')
		elif (menu['mud'] in data):
			chloe.write('E\r\n')
		elif ('[HP=' in data):
			bbs['conn'] = 1
			if (debug): print 'chloe: connection to %s established.' % (bbs['host'])
			break
	return 0

def report():
	""" timer control """
	global bbs, chloe, debug, start
	if not (bbs['conn']): sys.exit(0)
	if (debug) and (start >= 1): print 'chloe: timer pass #%d' % (start)
	start = start + 1
	t = threading.Timer(30.0, report)
	t.start()
	return 0

if __name__ == '__main__':
	main()
