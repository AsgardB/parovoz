#!/usr/bin/python3
import socket
import threading

import time
import os
import subprocess

ltimes = {}
names = ['/bt-updated-browser', '/everything-is-ok']
skipl = open('/mnt/checker/ignore.txt').readlines()

basedir = '/mnt/checker'
datadir = '/mnt/var'
cleanmark = '/mnt/var/exiting'

class r:
	ltime = 0
	rtime = 0

def popup():
	subprocess.Popen(['xterm', basedir+'/alert'])
	time.sleep(2)

def checker():
	calling = False
	while True:
		try:
			for y in range(25):
				if not calling and r.ltime > time.time() - 3:
					print('+', r.ltime)
					calling = True
					subprocess.Popen([basedir+'/ringer'])
				if calling and r.ltime < time.time() - 3:
					print('-', r.ltime)
					calling = False
					os.system('kill $(cat /dev/shm/alarmpid)')
				time.sleep(2)
			for n in names:
				if n not in ltimes or ltimes[n] < time.time() - 50:
					if not os.access(cleanmark, os.R_OK):
						if n == '/everything-is-ok' and n in ltimes and r.rtime < time.time() - 300:
							os.system('xterm rn &')
							r.rtime = time.time()
						else:
							popup()
		except:
			pass

threading.Thread(target=checker).start()


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.settimeout(None)
s.bind(('127.0.0.1', 22233))
s.listen(1)
while True:
	try:
		res = ''
		c, a = s.accept()
		c.settimeout(5)
		req = c.recv(8192)
		for n in names:
			if n.encode() in req:
				if open('/sys/class/power_supply/ACAD/online').read().startswith('1'):
					ltimes[n] = time.time()
				break
		else:
			if b'/until' in req:
				nopen = True
				try:
					while b'{endmsg}' not in req:
						p = c.recv(8192)
						if not p: break
						req += p
					req = req.decode()
					assert 'Пометить всё как прочитанное' in req
					found = False
					for m in req.split('<div>')[1:]:
						cl, me = m.split('<div class="')[1].split('">')
						if ' ' in cl: continue
						for sk in skipl:
							sk = sk.strip()
							if not sk: continue
							if sk in me: break
						else:
							print(me)
							na = me.split('Новое сообщение в сделке #')
							if len(na) >= 2:
								id = str(int(na[1].split('<')[0]))
								mdate, mtime = m.split('<')[0].split(' г., ')
								md, ms, my = mdate.split(' ')
								mh, mi = mtime.split(':')
								mm = {'янв.': 1, 'февр.': 2, 'мар.': 3, 'апр.': 4, 'мая': 5, 'июня': 6, 
									'июля': 7, 'авг.': 8, 'сент.': 9, 'окт.': 10, 'нояб.': 11, 'дек.': 12}[ms]
								mstamp = time.mktime((int(my), int(mm), int(md), int(mh), int(mi), 0, 0, 0, -1))
								if time.time() - mstamp < 120 or os.access(datadir + '/history/' + id, os.R_OK): continue
							found = True
							break
					if not found: nopen = False
				except:
					pass
				if nopen:
					r.ltime = time.time()
			else:
				if b'/eWxFwhTinqpkyIkWDtGg' in req:	
					res = os.popen('2f std').read()
				else:
					popup()
		res = res.strip()
		c.sendall(('HTTP/1.1 200 OK\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\nContent-Length: '+str(len(res))+
			'\r\n\r\n'+res).encode())
		c.close()
	except:
		pass
