#!/usr/bin/python3
import socket
import threading
import json
import time
import traceback
import subprocess
import os
import sys
import hashlib
import ctypes

datadir = '/mnt/var'
baseurl = 'https://yoomoney.ru/'

libx11=ctypes.CDLL('libX11.so.6')
libxtst=ctypes.CDLL('libXtst.so.6')
dis=libx11.XOpenDisplay(None)

def kpress(kcode, d=1, u=1):
	sy = libx11.XFlush
	if d: libxtst.XTestFakeKeyEvent(dis, kcode, True, 0)
	sy(dis)
	if u: libxtst.XTestFakeKeyEvent(dis, kcode, False, 0)
	sy(dis)

if 'early' in sys.argv:
	time.sleep(10)
	kpress(24)
	kpress(39)
	kpress(36)
	time.sleep(50)
	#kpress(71)
	#time.sleep(3)
	kpress(36)
	#time.sleep(5)
	kpress(37, 1, 0)
	kpress(64, 1, 0)
	kpress(28)
	kpress(37, 0, 1)
	kpress(64, 0, 1)
	time.sleep(15)
	kpress(56)
	kpress(28)
	kpress(36)
	exit()

token1 = '\r\nrqbxmvJKSsNevlZDlTkiBktCVNdYWp\r\n\r\n'
token2 = '/QINdbNFKeGGUmeAnbRhksGOTTZrATR'

query = []
payed = []
bad = []

class st:
	window = None
	capture = None
	mywallet = None
	paymethod = None
	id = None
	details = None
	amount = None
	renew = False

def popcode():
	yfile = '/mnt/uc/' + st.mywallet
	cl = open(yfile).readlines()
	c = cl[0].split(' ')[1].strip()
	open(yfile, 'w').writelines(cl[1:])
	print(len(cl), 'codes')
	st.renew = len(cl) < 7
	return c

def timer():
	while True:
		try:
			#if st.id and st.enter:
			#	time.sleep(3)
			#	if st.id and st.enter:
			#		kpress(71)
			#		time.sleep(2)
			#		kpress(36)
			#		time.sleep(3)
			#	if st.id and st.enter:
			#		kpress(36)
			#		time.sleep(2)
			#	time.sleep(5)
			process()
			if st.window and st.window.poll() is not None:
				st.window = None
				finish()
		except:
			pass
		time.sleep(2)

threading.Thread(target=timer).start()

def screenrec(id):
	os.system('xscreensaver-command -deactivate')
	st.capture = subprocess.Popen(['/usr/bin/ffmpeg', '-f', 'x11grab', '-draw_mouse', '1', '-framerate', '25', '-video_size', '1366x768',
		'-i', ':0+0,0', '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-preset', 'veryfast', '-q:v', '1', '-s', '1366x768', '-f', 'matroska', 
		'-v', '-8', '/mnt/screenrec/'+id+'.mkv'])

def process():
	if st.id or not query: return
	q = query.pop()
	a, st.mywallet, st.paymethod, st.id, st.details, st.amount = q
	if int(float(st.amount)) == float(st.amount):
		st.amount = str(int(float(st.amount)))
	if os.access(datadir + '/kpress', os.R_OK):
		kpress(int(open(datadir + '/kpress').read()))
		time.sleep(1)
	st.window = subprocess.Popen(['xmessage']+q)
	browser = 'c' + st.mywallet
	if st.paymethod == 'billing':
		subprocess.Popen([browser, baseurl+'main'])
	else:
		screenrec(st.id)
		subprocess.Popen([browser, {'wallet': baseurl+'transfer/a2w', 'phone': baseurl+'phone'}[st.paymethod]])
	st.enter = True

def finish(renew=True):
	if renew and st.renew:
		browser = 'c' + st.mywallet
		subprocess.Popen([browser, baseurl+'emergency-codes'])
	else:
		st.id = None
		st.details = None
		try:
			if st.window:
				st.window.terminate()
				st.window = None
			st.capture.terminate()
		except:
			pass
		print('finish')
	
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('127.0.0.1', 22222))
s.listen(1)
while True:
	try:
		res = ''
		c, a = s.accept()
		c.settimeout(5)
		req = b''
		while b'\r\n\r\n' not in req:
			p = c.recv(8192)
			if not p: break
			req += p
		q = req.decode()
		
		if token1 in q:
			q = q.replace(token1, '').split('\t')
			
			if q[0] == 'new':
				query.insert(0, q)
			
			if q[0] == 'search':
				if len(q) == 3:
					query.append(['new', q[2], 'billing', '-1', '0', '0'])
				else:
					if q[1] in payed:
						res = 'READY'
					if q[1] in bad:
						res = 'bad'
		
		if token2 in q:
			while b'<EOF>' not in req:
				p = c.recv(8192)
				if not p: break
				req += p
			q = json.loads(req.decode().split('\r\n\r\n')[1].replace('<EOF>', ''))
			if q['action'] == 'details' and st.id and q['paymethod'] == st.paymethod:
				res = {'details': st.details, 'amount': st.amount}
			
			if q['action'] == 'getcode' and st.id:
				if float(q['amount'].replace('\xa0', '').replace('\t', '').strip()) <= float(st.amount)*1.03 and q['details'].strip() in st.details:
					print('MATCH')
					res = {'ok': 1, 'c': popcode()}
					st.details = st.amount = None
				else:
					print(q)
			
			if q['action'] == 'confirm' and st.id and not st.details:
				payed.append(st.id)
				res = {'closed': 1, 
					'redir': os.access(datadir + '/actions-' + st.mywallet, os.R_OK) and len(open(datadir + '/actions-' + st.mywallet).read())}
				finish()
				
			if q['action'] == 'bad':
				bad.append(st.id)
				res = {'saved': 1}
				finish('codeused' in q)
			
			if q['action'] == 'acode':
				res = {'c': popcode()}
			
			if q['action'] == 'savecodes':
				yfile = '/mnt/uc/' + st.mywallet
				open(yfile, 'w').write(q['content'])
				res = {'saved': 1}
				os.system('e7z /mnt/uc; uz &')
				finish(False)
				open(datadir + '/codes-' + st.mywallet, 'w').write(q['content'])
			
			if q['action'] == 'loaded':
				st.enter = False
				res = 1
				print('loaded')
			
			if 'bal' in q and q['mywallet'].isdigit():
				rv = 0
				w = q['mywallet']
				if os.access(datadir + '/actions-' + w, os.R_OK):
					rv = 1
					assert q['bal'] is not None
					open(datadir + '/balance-' + w, 'w').write(str(q['bal']))
					old = open(datadir + '/actions-' + w).read().split('\n')
					newact = ''# if ''.join(old) else q['action']
					while old:
						if not old[-1].strip():
							old.pop()
							continue
						can = (q['action']+'\r\r').replace('\n'.join(old)+'\n\r\r', '')
						if '\r\r' not in can:
							newact = can
							break
						old.pop()
					open(datadir + '/actions-' + w, 'w').write(q['action'])
					for act in newact.split('\n'):
						print(act)
						if not act: continue
						fn = hashlib.sha256(act.encode()).hexdigest() + '.eml'
						act = act.split('\t')
						amo = str(float(act[1]))
						if act[0] == 'in':
							open(datadir + '/incoming-' + w + '/' + fn, 'w').write('in\n'+amo)
						if act[0] == 'out':
							open(datadir + '/transactions-' + w + '/' + fn, 'w').write('out\n'+amo)
					
				res = {'saved': rv}
				if st.paymethod == 'billing' and st.mywallet == w:
					finish(False)
		
		if res: res = json.dumps(res)
		c.sendall(('HTTP/1.1 200 OK\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\nContent-Length: '+str(len(res))+
			'\r\n\r\n'+res).encode())
		c.close()
	except Exception:
		traceback.print_exc()
