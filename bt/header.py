minamount = 1000
defaultmaxamount = 7600
enabledpaymethods = (447, 8975, 464)

listorder = ('BTC', 'ETH', 'LTC', 'USDT', 'DOGE', 'BCH', 'DASH')
datadir = '/mnt/var'
cleanmark = '/mnt/var/exiting'

cfg = {
	"BTC-YM": {'spreadmin': 3},
	"ETH-YM": {'spreadmin': 3},
	"LTC-YM": {'spreadmin': 2, 'noask': 1},
	"USDT-YM": {'spreadmin': 3},
	"DOGE-YM": {'spreadmin': 5},
	"BCH-YM": {'spreadmin': 5},
	"DASH-YM": {'spreadmin': 5},
}

import sys
import os
import time
import traceback
import threading
import random
import http
import python_http_client
import base64
import json
import hashlib
import email
import socket
import ctypes

from jose import jws
from jose.constants import ALGORITHMS
from urllib.parse import urlencode

import usr
import vproxy
import ym

class gl:
	con = None
	unparsed = 0
	newemails = 0
	errmail = 0
	enbid = True
	enask = True
	atrades = []
	waitout = -1
	wpending = {}
	bal = {}
	ymbal = {}
	riv = {}
	watch = {}
	times = {}
	undodata = {}
	checktime = 1
	showtime = 0
	btcmax = 0
	btchl = 0

def log(*lns):
	open(datadir + '/trades.log', 'a').write(time.strftime('[%d.%m.%Y %H:%M:%S] ')+' '.join([ str(ln) for ln in lns ])+'\n')

def query(uri, data=None, method="PUT", k=None, v=None, ct='application/json'):
	claims = {
		"email": usr.email,
		"aud": "usr",
		"iat": int(time.time()),
		"jti": hex(random.getrandbits(64))
	}
	
	token = jws.sign(claims, usr.key, headers={"kid": usr.kid}, algorithm=ALGORITHMS.ES256)
	
	if not gl.con:
		gl.con = http.client.HTTPSConnection(vproxy.a, vproxy.p)
		gl.con.set_tunnel("bitzlato.com", 443, {'Proxy-Authorization': 'Basic ' + base64.b64encode(vproxy.u).decode()})
	
	q = {}
	if k: q[k] = v
	q['Authorization'] = "Bearer " + token
	if data: q['Content-Type'] = ct
	
	try:
		gl.con.request(method if data else "GET", '/api/p2p/'+uri, headers=q, body=json.dumps(data) if data else None)
		r1 = gl.con.getresponse()
		r = r1.read()
		try:
			return json.loads(r)
		except:
			return {}
	except Exception:
		gl.con = None
		raise

cstring = ctypes.c_char_p
libotp = ctypes.CDLL('libcotp.so.12')
libotp.get_totp.restype = cstring

def twofa(ret=False):
	c = libotp.get_totp(cstring(usr.secret), 6, 30, 2, None).decode()
	if ret:
		if os.access(datadir + '/confirm', os.R_OK):
			open(datadir + '/confirm', 'w').write(str(time.time()))
			return c
		else:
			raise RuntimeError('2FA disabled')
	else:
		print(c)

def disableadv(id):
	return query('dsa/'+str(id), {'status': 'pause'})

def getalladv():
	while True:
		try:
			r = sorted(sorted(query('dsa/all'), key=lambda a: a['type']), key=lambda a: listorder.index(a['cryptocurrency']))
			if r[0]: return r
		except:
			print('failed')

if len(sys.argv) == 1: myadv = getalladv()

def intsocket(hp, m):
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect(('127.0.0.1', hp))
	s.sendall(m.encode())
	res = b''
	while True:
		p = s.recv(8192)
		if not p: break
		res += p
	return res.decode()

def toapm(m):
	return intsocket(22222, m+'\r\nrqbxmvJKSsNevlZDlTkiBktCVNdYWp\r\n\r\n')

def getapm(id, w=None):
	return toapm('search\t'+str(id)+('\t'+w if w else ''))

def tochecker(m):
	return intsocket(22233, m)

def popup():
	if time.time() < gl.showtime: return
	gl.showtime = time.time() + 60
	tochecker('!')

def checktrades():
	ntrades = query('trade/')['data']
	
	minago = (time.time()  - 60) * 1000
	
	for trade in ntrades:
		if trade['status'] == 'trade_created' and trade['date'] < (time.time()  - 360) * 1000:
			log('! timeout', trade['id'])
			log(query('trade/'+str(trade['id']), {"type":"cancel"}, 'POST'))
	
	for trade in ntrades:
		if trade['date'] < minago and ((trade['type'] == 'selling' and trade['status'] == 'payment') or 
			(trade['type'] == 'purchase' and trade['status'] in ('confirm_trade', 'payment'))):
			if os.access(datadir + '/ignore' + str(trade['id']) , os.R_OK): continue
			r = query('trade/'+str(trade['id']))
			ldate = 0
			for h in r['history']:
				if h['date'] > ldate: ldate = h['date']
			if ldate < (time.time()  - (3600 if trade['type'] == 'purchase' and trade['status'] == 'payment' else 90)) * 1000:
				popup()
	
	return ntrades

def updatenow():
	for id in gl.times.copy():
		if gl.times[id] < time.time():
			del gl.times[id]

def roundbidamount():
	gl.bidmaxamount = int(gl.bidmaxamount / minamount) * minamount
	updatenow()

def changebidamount(a):
	gl.bidmaxamount = a
	roundbidamount()
	log('bidmaxamount', gl.bidmaxamount)

def sfilter(s, ar):
	for r in ar + [' ', '\r', '\n', '\xa0', ':', ',', '-', '+', '?', '.', '(', ')']:
		s = s.replace(r, '')
	s = s.strip()
	return s

def makepayment(trade):
	if trade['currency']['code'] != 'RUB': return
	paymethod = trade['currency']['paymethod']
	details = trade['details'].lower()
	
	amount = trade['currency']['amount']
	
	if paymethod in (447, 8975):
		paymethod = 'wallet'
		details = sfilter(details, [
			'номер', 'счёта', 'счёт', 'кошелька', 'этот', 'я. д.', 'юмонеу', 'юмоней', 'юmoney', 'яндекс', 'деньги', 'денег',
			'здравствуйте', 'перевода', 'перевод', 'аккаунт', 'только', 'yandex',
			'указания', 'комментария', 'комментариев', 'платежу', 'счета', 'счет',
			'рублях', 'внутри', 'системы',
			'кошелек', 'это не карта', 'кодов', 'привет', 'платеж', 'юмани', 'вот', 'кошелёк',
			'мне', 'сюда', 'жду', 'без', 'мой', 'для', 'яд', 'на', 'к', 'в'
			])
		if not details.isdigit():
			details = ''
			amount = 0
		if len(details) == 11 and details[0] == '8': details = '7' + details[1:]
	elif paymethod == 464:
		paymethod = 'phone'
		details = sfilter(details, ['билайн', 'beeline', 'мтс', 'mts', 'мегафон', 'москва', 'теле2', 'теле 2', 'tele2', 'tele 2', 't2', 'т2', 'урал',
			'мегафон', 'ростелеком', 'yota', 'йота', 'ета',  'пополнение', 'телефона', 'сим', 'карту', 'карелия', 'тинькофф', 'мобайл', 'оператор', 
			'номер', 'перевод', 'баланс', 'телефона', 'билл', 'билайе', 'менафон', 'здравствуйте', 'можно', 'пополнить', 'счёт', 'жду', 'на', 'а'])
		if len(details) == 11 and details[0] in ('7', '8'): details = details[1:]
		if not details.isdigit() or len(details) != 10:
			details = ''
			amount = 0
	else: return
	
	wallets = gl.ymbal
	mywallet = sorted(wallets, key=lambda a: wallets[a], reverse=True)[0]
	
	if gl.ymbal[mywallet] - amount * 1.02 < 0:
		details = ''
		amount = 0
	
	if not details or not amount or details in ym.wallets:
		log('! garbage', trade['id'])
		log(query('trade/'+str(trade['id']), {"type":"cancel"}, 'POST'))
		return
	
	id = trade['id']
	
	gl.ymbal[mywallet] -= amount * 1.02
	changebidamount(gl.bidmaxamount - amount * 1.02)
	gl.waitout += 1 if gl.waitout != -1 else 2
	
	newwait = 0
	for n in range(30):
		maxpayout = 3800
		if amount <= maxpayout:
			a = amount
			eid = ''
		else:
			gl.waitout += 1
			newwait += 1
			a = maxpayout - n * 100
			eid = '00000' + str(n)
		amount -= a
		q = ['new', mywallet, paymethod, str(id)+eid, details, str(a)]
		log(' '.join(q))
		toapm('\t'.join(q))
		if amount == 0: break
	
	gl.undodata[id] = {'extraparts': newwait, 'mywallet': mywallet}

actions = [twofa]
