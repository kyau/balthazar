#!/usr/bin/env python
# -*- coding: utf-8 -*-

import MySQLdb
import configparser
import re
import os
import signal
import sys
import telnetlib
import threading
import time
from telnetlib import IAC, DO, DONT, WILL, WONT, GA, SB, SE, TTYPE
from time import localtime, sleep, strftime

""" global variables """
balthazar = telnetlib.Telnet()
ANSI_COLOR_REGEXP = re.compile(chr(27) + '\[[0-9;]*[m]')
ANSI_REGEXP = re.compile('( |[A-Z])\x08')
CONNECTED = False
sw = {'who': 0, 'top': 0, 'topg': 0}
threads = []
bbs = {}
debug = {}
menu = {}
mysql = {}
report = {}
sql = None
db = None
_debug = 1

def main():
  """ start telnet/threaded timer """
  global report, threads, db, sql
  config()
  if _debug: plog('intializing...')
  """ handle ctrl+c """
  signal.signal(signal.SIGINT, quit)
  """ start telnet/threaded timer """
  t1 = threading.Timer(30.0, threaded_timer_db)
  t1.start()
  threads.append(t1)
  t2 = threading.Timer(10.0, threaded_timer_announce)
  t2.start()
  threads.append(t2)
  report[0] = 1
  report[1] = 1
  """ database connection """
  db = _db(mysql['host'], mysql['port'], mysql['user'], mysql['passwd'], mysql['db'])
  sql = db.cursor()
  """ connect to telnet server """
  telnet()
  balthazar.write(b'\r\n')
  while 1:
    try:
      line = balthazar.read_until(b'\r\n')
    except EOFError:
      if (_debug): plog('character %s lost connection!' % bbs['user'])
      _quit()
    line = line.strip(b'\r\n')
    cleanline = line.decode("ascii")
    cleanline = ANSI_COLOR_REGEXP.sub('', cleanline)
    cleanline = ANSI_REGEXP.sub('', cleanline)
    if sw['who']: who_online(cleanline)
    elif sw['top']: top_users(cleanline)
    elif sw['topg']: top_gangs(cleanline)
    gossip_log(cleanline)
    # uncomment for line by line output
    if (_debug): mlog(cleanline)
  return 0

def plog(text):
  """ debug log """
  if debug['log']:
    log = open(debug['logfile'], 'a')
    time = strftime('%a, %d %b %Y %H:%M:%S %Z', localtime())
    log.write('%s balthazar: %s\n' % (time, text))
  time = strftime('%H:%M:%S', localtime())
  # remove for production
  print('\033[1;30m%s\033[0m: \033[36mbalthazar\033[0m: %s' % (time, text))
  if (debug['log']): log.close()
  return 0

def mlog(text):
  """ debug mud log """
  if 'Why are you telepathing to yourself?' in text: return 0
  if debug['log']:
    log = open(debug['logfile'], 'a')
    time = strftime('%a, %d %b %Y %H:%M:%S %Z', localtime())
    log.write('%s: %s\n' % (time, text))
  time = strftime('%H:%M:%S', localtime())
  # remove for production
  print('\033[1;30m%s\033[0m: \033[31m{\033[0m%s\033[31m}\033[0m' % (time, text))
  if debug['log']: log.close()
  return 0

def quit(signum, frame):
  _quit()

def _quit():
  """ stop telnet/threaded timer and exit """
  if _debug:
    print(' ')
    plog('%d terminating...' % threading.active_count())
  for t in threads:
    t.kill_received = True
  balthazar.close()
  sql.close()
  if _debug: plog('sql connection closed.\n')
  os._exit(1)

def config():
  """ populate lists with configuration information """
  global bbs, debug, menu, _debug
  cfg = configparser.ConfigParser()
  directory = os.path.dirname(os.path.realpath(__file__))
  cfg.read(directory+'/../bbs.cfg')
  bbs['host'] = cfg.get('BBS', 'host', raw=True)
  bbs['port'] = int(cfg.get('BBS', 'port', raw=True))
  bbs['user'] = bytes(cfg.get('BBS','user', raw=True), encoding='ascii')
  bbs['muduser'] = cfg.get('BBS','muduser', raw=True)
  bbs['passwd'] = bytes(cfg.get('BBS','passwd', raw=True), encoding='ascii')
  bbs['admin'] = cfg.get('BBS', 'admin', raw=True)
  menu['main'] = bytes(cfg.get('MENU', 'main', raw=True), encoding='ascii')
  menu['pause'] = bytes(cfg.get('MENU', 'pause', raw=True), encoding='ascii')
  menu['mud'] = bytes(cfg.get('MENU', 'mud', raw=True), encoding='ascii')
  menu['go'] = bytes(cfg.get('MENU', 'go', raw=True), encoding='ascii')
  mysql['host'] = cfg.get('MYSQL', 'host', raw=True)
  mysql['port'] = int(cfg.get('MYSQL', 'port', raw=True))
  mysql['user'] = cfg.get('MYSQL', 'user', raw=True)
  mysql['passwd'] = cfg.get('MYSQL', 'passwd', raw=True)
  mysql['db'] = cfg.get('MYSQL', 'db', raw=True)
  debug['log'] = int(cfg.get('DEBUG', 'log', raw=True))
  debug['logfile'] = cfg.get('DEBUG', 'logfile', raw=True)
  if not _debug:
    _debug = int(cfg.get('DEBUG', 'verbose', raw=True))
  return 0

def process_option(tsocket, command, option):
  name = ''
  if ord(option) == 1:
    name = 'ECHO'
  elif ord(option) == 3:
    name = 'SUPRESS GO AHEAD'
  if command == DO and option == TTYPE:
    tsocket.sendall(IAC + WILL + TTYPE)
    plog('telnet: setting terminal type "balthazar"')
    tsocket.sendall(IAC + SB + TTYPE + b'\0' + b'balthazar' + IAC + SE)
  elif (command == WILL or command == DO) and (ord(option) == 3 or ord(option) == 1):
    plog('telnet: sending code: IAC WILL ' + name)
    tsocket.sendall(IAC + WILL + option)
  elif command == DONT:
    tsocket.sendall(IAC + WONT + option)
    plog('telnet: sending code: IAC WONT ' + name)

def telnet():
  """ open connection to the bbs """
  global CONNECTED
  plog('connecting to: ' + bbs['host'] + ':' + str(bbs['port']))
  try:
    balthazar.open(bbs['host'], bbs['port'])
    # uncomment for telnet debug messages
    #balthazar.set_debuglevel(1)
    balthazar.set_option_negotiation_callback(process_option)
    data = balthazar.read_until(b'login:')
    balthazar.write(bbs['user'] + b'\r\n')
    data = balthazar.read_until(b'password:')
    balthazar.write(bbs['passwd'] + b'\r\n')
  except:
    plog('telnet connection refused.\n - check config: bbs.cfg\n')
    sys.exit(1)
  """ enter majormud """
  while 1:
    data = balthazar.read_very_eager()
    if (menu['pause'] in data):
      balthazar.write(b'\r\n')
    elif (menu['main'] in data):
      balthazar.write(menu['go'] + b'\r\n')
    elif (menu['mud'] in data):
      balthazar.write(b'E\r\n')
    elif (b'[HP=' in data):
      CONNECTED = True
      if _debug: plog('character %s on %s connected.' % (bbs['user'].decode('ascii'), bbs['host']))
      break
  return 0

def _db(DATABASE_HOST, DATABASE_PORT, DATABASE_USER, DATABASE_PASSWD, DATABASE_NAME):
  """ mysql database connectivity """
  try:
    db = MySQLdb.connect(host=DATABASE_HOST,user=DATABASE_USER,passwd=DATABASE_PASSWD, port=int(DATABASE_PORT), db=DATABASE_NAME)
  except MySQLdb.OperationalError:
    plog('error connecting to mysql database.\n - check config: bbs.cfg\n')
    exit(1)

  plog('database %s on %s connected.' % (DATABASE_NAME, DATABASE_HOST))
  return db

def _sql(SQL_STRING, RET = 0):
  data = None
  count = None
  try:
    count = sql.execute(SQL_STRING)
    if RET == 1: data=sql.fetchone()
    elif RET == 2: data=sql.fetchall()
    else: db.commit()
  except:
    db.rollback()
    if _debug: plog('db rollback')
  if RET > 0: return data
  else: return count

def threaded_timer_db():
  """ timer control """
  global report, threads
  if not (CONNECTED): _quit()
  """ debug: announce report loop number """
  if _debug and report[0] >= 1: plog('thread (1/%d) - report#%d' % (len(threads), report[0]))

  """ pull up who's online (30s) """
  sw['who'] = 1
  cmd = '/' + bbs['muduser'] + ' #who'
  try:
    _sql('TRUNCATE TABLE online')
    balthazar.write(b'who\r\n')
    sleep(0.5)
    balthazar.write(cmd.encode('ascii')+b'\r\n')
    sleep(2)
  except:
    if _debug: plog('character %s lost connection!' % bbs['user'])
    _quit()

  if report[1] == 10:
    """ pull up top 100 users (300s) """
    sw['top']=1
    cmd = '/'+bbs['muduser']+' #top'
    try:
      balthazar.write(b'top 100\r\n')
      sleep(2.5)
      balthazar.write(cmd.encode('ascii')+b'\r\n')
      sleep(2)
    except:
      if _debug: plog('character %s lost connection!' % bbs['user'])
      _quit()

    """ pull up top 100 gangs (300s) """
    sw['topg']=1
    cmd = '/' + bbs['muduser'] + ' #topgangs'
    try:
      balthazar.write(b'top 100 gangs\r\n')
      sleep(2.5)
      balthazar.write(cmd.encode('ascii')+b'\r\n')
    except:
      if _debug: plog('character %s lost connection!' % bbs['user'])
      _quit()
    report[1] = 0

  """ restart timer """
  report[0] = report[0] + 1
  report[1] = report[1] + 1
  t = threading.Timer(30.0, threaded_timer_db)
  t.start()
  threads.append(t)
  return 0

def threaded_timer_announce():
  balthazar.write(b'gos Balthazar Services *WIP*: @addlife @good @neutral @criminal @villain @fiend\r\n')
  t = threading.Timer(14400.0, threaded_timer_announce) # announce every 4 hours
  t.start()
  threads.append(t)
  return 0

def gossip_log(text):
  """ gossip chat logger """
  global db, sql, _debug
  line = text.split(' ')
  try:
    if not line[1] == 'gossips:': return 0
  except IndexError:
    return 0
  name = line[0]
  if name == bbs['muduser']: return 0
  #gossip = line[2:].join(' ')
  gossip = " ".join(line[2:])
  if (_debug): mlog('gossip: ('+name+') "'+gossip+'"')
  sqlstr = 'INSERT INTO gossip (name, text) VALUES (\'%s\',\'%s\')' % (name, gossip)
  _sql(sqlstr)
  return 0

def who_online(text):
  """ whos online """
  global bbs, sw
  if 'telepathing to yourself' in text: sw['who'] = 0
  if filtr(text):
    """ optional debug output """
    #if (_debug): mlog('who: ['+text+']')
    gang = None
    alignment = text[0:8].replace(" ","")
    schar = '-'
    postalign = text[9:]
    if ' -  ' in postalign:
      schar = '-'
    else:
      schar = 'x'
    tmp = postalign.split(' %s  ' % schar)
    if not len(tmp) > 1:
      return 0
    name = tmp[0].strip()
    other = tmp[1]
    other = other.split('  of ')
    if len(other) > 1:
      title = other[0].strip()
      gang = other[1].strip()
      """ print statement for website formatting """
#      print('%8s %-20s %s  %s  of %s' % (alignment, name, schar, title, gang))
    else:
      title = other[0].strip()
      gang = ''
      """ print statement for website formatting """
#      print('%8s %-20s %s  %s' % (alignment, name, schar, title))
    sqlstr = 'INSERT INTO online (user, busy) VALUES (\'%s\', \'%s\')' % (name, schar)
    tmp = _sql(sqlstr)
    sqlstr = 'SELECT id FROM users WHERE user LIKE \'%s%%\'' % name
    tmp = _sql(sqlstr, 1)
    if not tmp == None:
      sqlstr = 'UPDATE users SET alignment = \'%s\', title = \'%s\', gang = \'%s\' WHERE id = \'%d\'' % (alignment, title, gang, tmp[0])
      tmp = _sql(sqlstr)
    else:
      sqlstr = 'INSERT INTO users (user, alignment, title, gang) VALUES (\'%s\', \'%s\', \'%s\', \'%s\')' % (name, alignment, title, gang)
      tmp = _sql(sqlstr)
    return 0

def top_users(text):
  """ top 100 users """
  global bbs, sw
  if 'telepathing to yourself' in text: sw['top'] = 0
  if filtr(text):
    """ optional debug output """
    if _debug: mlog('top: "'+text+'"')
    rank = text[0:3].strip()
    name = text[5:26].strip()
    cls = text[27:37].strip()
    gang = text[38:57].strip()
    if gang == 'None': gang=''
    exp = text[58:].strip()
    """ add/update user in database """
    sqlstr = 'SELECT exp FROM users WHERE user LIKE \'%s%%\'' % name
    tmp = _sql(sqlstr, 1)
    if tmp == None:
      sqlstr = 'INSERT INTO users (user, class, exp, expold, gang) VALUES (\'%s\', \'%s\', %s, %s, \'%s\')' % (name, cls, exp, exp, gang)
    else:
      expold = tmp[0]
      if tmp[0] > 0:
        sqlstr = 'UPDATE users SET class = \'%s\', exp = %s, expold = %d, gang = \'%s\' WHERE user LIKE \'%s%%\'' % (cls, exp, expold, gang, name)
      else:
        sqlstr = 'UPDATE users SET class = \'%s\', exp = %s, expold = %s, gang = \'%s\' WHERE user LIKE \'%s%%\'' % (cls, exp, exp, gang, name)
    tmp = _sql(sqlstr)
    """ add/update gang in database """
    sqlstr = 'SELECT exp FROM gangs WHERE gang LIKE \'%s%%\'' % gang
    tmp = _sql(sqlstr, 1)
    if tmp == None and len(gang) > 1:
      sqlstr = 'INSERT INTO gangs (gang) VALUES (\'%s\')' % gang
      tmp=_sql(sqlstr)
    """ print statement for website formatting """
#    print '%3s. %-21s %-10s %-19s %-s' % (rank, name, cls, gang, exp)
  return 0

def top_gangs(text):
  """ top 100 users """
  global bbs, sw
  if 'telepathing to yourself' in text: sw['topg'] = 0
  if filtr(text):
    """ optional debug output """
    if _debug: mlog('topg: "'+text+'"')
    rank = text[0:3].strip()
    name = text[5:24].strip()
    leader = text[25:36].strip()
    members = text[37:44].strip()
    creation = text[45:57].strip()
    exp = text[58:].strip()
    sqlstr = 'SELECT exp FROM gangs WHERE gang LIKE \''+name+'%\''
    tmp = _sql(sqlstr, 1)
    if tmp == None:
      sqlstr = 'SELECT user FROM users WHERE user LIKE \''+leader+'%\''
      tmp = _sql(sqlstr, 1)
      if not tmp == None: leader = tmp[0]
      sqlstr = 'INSERT INTO gangs (gang, leader, members, exp, expold, creation) VALUES (\''+name+'\', \''+leader+'\', \''+members+'\', \''+exp+'\', \''+exp+'\', \''+creation+'\')'
      tmp = _sql(sqlstr)
    else:
      expold = tmp[0]
      if expold > 0:
        sqlstr = 'UPDATE gangs SET leader = \'%s\', members = \'%s\', exp = %s, expold = %d, creation = \'%s\' WHERE gang LIKE \'%s%%\'' % (leader, members, exp, expold, creation, name)
      else:
        sqlstr = 'UPDATE gangs SET leader = \'%s\', members = \'%s\', exp = %s, expold = %s, creation = \'%s\' WHERE gang LIKE \'%s%%\'' % (leader, members, exp, exp, creation, name)
      tmp = _sql(sqlstr)
    """ print statement for website formatting """
#    print '%3s. %-19s %-11s %-7s %-12s %s' % (rank, name, leader, members, creation, exp)
  return 0

def filtr(text):
  cmd = '/' + bbs['muduser'] + ' #who'
  if text == cmd: return 0
  cmd = '/' + bbs['muduser'] + ' #top'
  if text == cmd: return 0
  cmd = '/' + bbs['muduser'] + ' #topgangs'
  if text == cmd: return 0
  if 'Current Adventurers' in text: return 0
  elif '===================' in text: return 0
  elif 'Top Heroes of the Realm' in text: return 0
  elif 'Top Gangs of the Realm' in text: return 0
  elif '=-=-=-=-=-=-=-=-=-' in text: return 0
  elif 'Rank Name                  Class' in text: return 0
  elif 'Rank Gangname            Leader' in text: return 0
  elif text == 'top 100 gangs': return 0
  elif text == 'top 100': return 0
  elif text == 'who': return 0
  elif text == '': return 0
  elif ' gossips: ' in text: return 0
  elif ' says "' in text: return 0
  elif ' just disconnected!!!' in text: return 0
  elif ' just entered the Realm.' in text: return 0
  elif ' telepaths: ' in text: return 0
  elif 'Why are you telepathing to yourself?' in text: return 0
  elif 'There are no gangs currently established!' in text: return 0
  elif '[HP=' in text: return 0
  else: return 1

if __name__ == '__main__':
  main()