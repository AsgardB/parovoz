from email.header import decode_header
from imaplib import IMAP4_SSL
from header import *

def dotrades(ntrades):
	havepurchase = 0
	havedup = 0
	atrades = []
	ids = []
	amounts = []
	
	for trade in ntrades:
		if trade['paymethod'] not in enabledpaymethods or trade['currency']['code'] != 'RUB': continue
		print(trade['partner'], trade['status'], trade['type'])
		print('\x1b[K', end='')
		atrades.append(trade)
		ids.append(trade['id'])
		amo = int(float(trade['currency']['amount']))
		if trade['type'] == 'selling':
			for a in set((amo, amo + (1 if float(trade['currency']['amount']) % 1 else 0))):
				if a in amounts: havedup += 1
				amounts.append(a)
		if trade['type'] == 'purchase' and trade['status'] not in ('payment', 'dispute'): havepurchase += 1
	
	for wa in gl.wpending.copy():
		if gl.wpending[wa] not in ids: del gl.wpending[wa]
	
	for trade in atrades:
		if trade['status'] == 'trade_created':
			log(trade)
			
			if trade['type'] == 'selling':
				amo = int(float(trade['currency']['amount']))
				amoset = set((amo, amo + (1 if float(trade['currency']['amount']) % 1 else 0)))
				
				if trade['cryptocurrency']['code'] == 'BTC':
					gl.btcmax -= float(trade['currency']['amount'])
					if gl.btcmax < 0: continue
				
				for w in wselect(trade['currency']['amount']):
					for a in amoset:
						if w+'/'+str(a) in gl.wpending: break
					else:
						break
					continue
				else:
					log('wallet not choosed', gl.wpending)
					continue
				
				for a in amoset:
					gl.wpending[w+'/'+str(a)] = trade['id']
				log('choosed', w)
				log(query('trade/'+str(trade['id']), {'details': w}))
				gl.ymbal[w] += float(trade['currency']['amount'])
			
			log('! confirm-trade', trade['id'])
			itrade = query('trade/'+str(trade['id']), {"type":"confirm-trade"}, 'POST')
			log(itrade)
			
			if itrade['type'] == 'purchase' and itrade['status'] == 'confirm_trade':
				makepayment(itrade)
				log('waitout', gl.waitout)
		
		if trade['type'] == 'purchase' and trade['status'] == 'confirm_trade':
			hr = getapm(trade['id'])
			if 'READY' in hr:
				log('! payment', trade['id'])
				log(query('trade/'+str(trade['id']), {"type":"payment"}, 'POST'))
			elif 'bad' in hr:
				log('! bad', trade['id'])
				log(query('trade/'+str(trade['id']), {"type":"cancel"}, 'POST'))
				changebidamount(gl.bidmaxamount + float(trade['currency']['amount']) * 1.02)
				rv = gl.undodata[trade['id']]
				gl.ymbal[rv['mywallet']] += float(trade['currency']['amount']) * 1.02
				gl.waitout -= 1 + rv['extraparts']
		
		if trade['type'] == 'selling' and trade['status'] == 'payment':
			itrade = query('trade/'+str(trade['id']))
			log(itrade)
			w = itrade['details'].strip()
			if not w or w not in ym.wallets:
				log('incorrect details')
				continue
			
			checkmail(w)
			
			found = False
			bfile = datadir + '/found' + str(int(trade['id']))
			if os.access(bfile, os.R_OK):
				found = bfile
			else:
				amo = int(itrade['currency']['amount'])
				for a in set((itrade['currency']['amount'], amo, amo + (1 if itrade['currency']['amount'] % 1 else 0))):
					for fn in os.listdir(datadir + '/incoming-' + w):
						tfile = datadir + '/incoming-' + w + '/' + fn
						acheck = float(open(tfile, 'r').read().split('\n')[1])
						if acheck == a:
							found = tfile
							break
					if found: break
			
			if found:
				log('found', found, bfile)
				if found != bfile:
					os.rename(found, bfile)
					found = bfile
				log('! confirm-payment', trade['id'])
				
				r = query('trade/'+str(trade['id']), {"type":"confirm-payment"}, 'POST', 'X-Code-2FA', twofa(True))
				log(r)
				if 'status' in r and r['status'] == 'confirm_payment':
					os.unlink(found)
					print('confirm_payment')
					print('\x1b[K', end='')
	
	if str(atrades) != str(gl.atrades):
		if not atrades:
			clearincoming()
		gl.bal = {}
		
		for trade in gl.atrades: 
			if trade['id'] not in ids:
				log('closed', trade)
				itrade = query('trade/'+str(trade['id']))
				log(itrade)
				if itrade['status'] == 'confirm_payment':
					if 'feedback' in itrade['availableActions']:
						log('feedback')
						log(query('trade/'+str(itrade['id'])+'/feedback', {"rate": "thumb_up"}))
						itrade['availableActions'] = []
				open(datadir + '/history/' + str(itrade['id']), 'w').write(str(itrade))
				
		gl.atrades = atrades
	
	if havepurchase < 2:
		havepurchase = 0
			
	if not gl.enbid and not havepurchase: log('bid enabled')
	if gl.enbid and havepurchase: log('bid disabled')
	gl.enbid = not havepurchase
	
	if not gl.enask and not havedup: log('ask enabled')
	if gl.enask and havedup: log('ask disabled')
	gl.enask = not havedup
	
	if not gl.bwrited: writetotal()

def fetchmail(w):
	ms = ym.wallets[w]
	M = IMAP4_SSL(ms['hostname'])
	M.login(ms['myemail'], ms['password'])
	for folder in ('INBOX',):
		M.select(folder)
		typ, data = M.search(None, 'ALL')
		count = 0
		for num in data[0].split():
			typ, data = M.fetch(num, '(RFC822)')
			msg = data[0][1]
			h = hashlib.sha256(msg).hexdigest()
			open(datadir + '/inbox-' + w + '/' + h + '.eml', 'wb').write(msg)
			M.store(num, '+FLAGS', '\\Deleted')
			log('fetchmail', h)
			count += 1
		if count:
			M.expunge()
		M.close()
	M.logout()

def parsemail(w):
	savedbal = maybebal = float(open(datadir + '/balance-' + w, 'r').read())
	inbox = datadir + '/inbox-' + w
	transactions = datadir + '/transactions-' + w
	bal = -1
	changed = False
	for tr in range(22): 
		files = os.listdir(inbox)
		if not files: break
		for fn in files:
			try:
				afn = inbox + '/' + fn
				if os.access(transactions + '/' + fn, os.R_OK):
					log('dup', fn)
					os.unlink(afn)
					continue
					
				msg = email.message_from_bytes(open(afn, 'rb').read())
				subject = decode_header(msg['Subject'])[0][0].decode()
				body = msg.get_payload(decode=True).decode()
				amounts = []
				tpl = [
					{'t': 'in', 's1': 'На ваш счет ', 's2': 'поступил перевод со счета ', 'b1': 'Перевод от другого пользователя', 'b2': 'Сумма'},
					{'t': 'in', 's1': 'Ваш кошелек ', 's2': ' пополнен', 'b1': 'Деньги успешно зачислены', 'b2': 'Сумма'},
					{'t': 'out', 's1': 'Вы заплатили из кошелька ', 's2': '', 'b1': 'Платеж успешно выполнен', 'b2': 'Списано'},
				]
				for tp in tpl:
					if subject.startswith(tp['s1']): break
				
				assert tp['s2'] in subject
				parts = body.split(tp['b1'])[1].split(tp['b2'])[1].replace('RUB', 'руб.').split('Доступно')
				assert len(parts) == 2
				amounts = []
				sr = 'руб.</font>'
				for n in range(2):
					for p in parts[n].split('<font color="#000000" face="Arial" size="3">'):
						if sr in p: break
					amounts.append(float(p.split(sr)[0].replace('&#160;', '').replace(',', '.')))
				
				amo, bal = amounts
				t = tp['t']
	
				assert w.endswith(subject.split(tp['s1'])[1][:5].replace('*', ''))
				assert amo > 0
				assert bal > 0
				newbal = round(savedbal + amo * (-1 if t == 'out' else 1), 2)
				if tr == 21:
					log('bypass', newbal)
					bal = newbal
				if bal == newbal:
					savedbal = newbal
					log(t, amo, bal)
					print(t, amo, bal)
					print('\x1b[K', end='')
					ts = '\n'.join([t, str(amo), str(bal)])
					open(transactions + '/' + fn, 'w').write(ts)
					if t == 'in':
						open(datadir + '/incoming-' + w + '/' + fn, 'w').write(ts)
					else:
						gl.waitout -= 1
					os.rename(afn, datadir + '/parsed-' + w + '/' + fn)
					open(datadir + '/balance-' + w, 'w').write(str(bal))
					changed = True
				else:
					log('not match', amo, bal)
					if tr == 20:
						maybebal = round(maybebal + amo * (-1 if t == 'out' else 1), 2)
						log(amo, bal, maybebal)
					
			except:
				log('unknown', subject, fn)
				gl.newemails +=1
				os.rename(afn, datadir + '/unknown-' + w + '/' + fn)
		if tr == 20:
			if maybebal != bal:
				gl.unparsed += len(files)
				log('unparsed', len(files))
				break
	return changed

def checkmail(w=''):
	numexc = 0
	rea = False
	if time.time() >= gl.checktime: rea = True
	if rea: gl.checktime = time.time() + 30
	gl.unparsed = 0
	for k in [w] if w else ym.wallets:
		if ym.wallets[k]:
			if rea:
				log('@', k)
				print('@')
				print('\x1b[K', end='')
				try:
					fetchmail(k)
				except:
					print('err fetchmail')
					log('err fetchmail')
					numexc += 1
			changed = parsemail(k)
		else:
			transactions = datadir + '/transactions-' + k
			ld = os.listdir(transactions)
			changed = len(ld) + len(os.listdir(datadir + '/incoming-' + k))
			for tfn in ld:
				gl.waitout -= 1
				os.unlink(transactions + '/' + tfn)
			if w and rea:
				getapm(0, w)
		
		if changed:
			setbidamount()
	if gl.waitout < 0: gl.waitout = 0
	gl.errmail = numexc

def checkdir():
	gl.newemails = 0
	for w in ym.wallets:
		if ym.wallets[w]:
			gl.newemails += len(os.listdir(datadir + '/unknown-' + w))

def wselect(amount):
	wallets = {}
	amount = float(amount) * 1.1
	for w in ym.wallets:
		if gl.ymbal[w] + amount < 55000 and w in ym.payin:
			wallets[w] = gl.ymbal[w]
	return sorted(wallets, key=lambda a: wallets[a])

def setbidamount():
	if gl.waitout > 0:
		log('bidmaxamount not updated, waitout', gl.waitout)
		return
	gl.bidmaxamount = 0
	for w in ym.wallets:
		savedbal = float(open(datadir + '/balance-' + w, 'r').read())
		gl.ymbal[w] = savedbal
		log(w, savedbal)
		if savedbal > gl.bidmaxamount: gl.bidmaxamount = savedbal
	gl.bidmaxamount /= 1.02
	roundbidamount()
	log('updated bidmaxamount', gl.bidmaxamount)
	wallets = {}
	for w in ym.wallets:
		if w in ym.payin:
			wallets[w] = gl.ymbal[w]
	mywallet = sorted(wallets, key=lambda a: wallets[a])[0]
	gl.askmaxamount = defaultmaxamount - gl.ymbal[mywallet]

def getbal(c):
	r = query('wallets/'+c)
	log(r)
	return r

def clearincoming():
	gl.bwrited = 0
	for w in ym.wallets:
		for fn in os.listdir(datadir + '/incoming-' + w):
			tfile = datadir + '/incoming-' + w + '/' + fn
			os.unlink(tfile)
			print('cleared', tfile)
			print('\x1b[K', end='')

def initialize():
	gl.runtime = open(datadir + '/.lockf', 'w')
	os.lockf(gl.runtime.fileno(), os.F_TLOCK, 1)
	try:
		os.unlink(cleanmark)
	except:
		pass
	os.makedirs(datadir + '/history/', exist_ok=True)
	for w in ym.wallets:
		if not os.access(datadir + '/balance-' + w, os.R_OK):
			open(datadir + '/balance-' + w, 'w').write('0.0')
		ae = os.access(datadir + '/actions-' + w, os.R_OK)
		if ym.wallets[w] and ae: os.unlink(datadir + '/actions-' + w)
		if not ym.wallets[w] and not ae: open(datadir + '/actions-' + w, 'w').write('')
		for f in ('transactions', 'incoming') + (('unknown', 'inbox', 'parsed') if ym.wallets[w] else ()):
			os.makedirs(datadir + '/' + f + '-' + w + '/', exist_ok=True)
	clearincoming()
	checkdir()
	setbidamount()
	
	for k in cfg.copy():
		cfg[k.split('-')[0]+'-UM'] = cfg[k].copy()

def isexiting():
	r = os.access(cleanmark, os.R_OK)
	if r:
		print('isexiting')
		print('\x1b[K', end='')
	return r

def writetotal():
	try:
		if len(gl.atrades):
			return len(gl.atrades)
	except:
		pass
	
	fname = datadir+'/united.csv'
	
	try:
		ymrub = 0
		for w in gl.ymbal:
			ymrub += gl.ymbal[w]
		
		corub = {}
		ul = ''
		for c in listorder:
			b = gl.bal[c]
			ul += '","'+str(b)
			corub[c] = b * float(cfg[c+'-YM']['ask']) / 1.005
		
		btcbid = cfg['BTC-YM']['bid'] * 1.01
		btcbal = gl.bal['BTC']
				
		totalrub = twrub = ymrub
		totalbtc = ymrub / btcbid
		twbtc = totalbtc
		for c in corub:
			totalrub += corub[c]
			if c == 'BTC':
				totalbtc += btcbal
				twbtc += btcbal
				twrub += corub[c]
			else:
				totalbtc += corub[c] / btcbid
		
		open(fname, 'a').write('"'+time.strftime('%d.%m.%Y %H:%M:%S')+'","'+str(round(totalbtc, 8))+'","'+str(round(totalrub, 2))+'","'
			+str(round(twbtc, 8))+'","'+str(round(twrub, 2))+'","'+str(round(ymrub, 2))+ul+'"\n')
		gl.bwrited = 1
	except:
		pass
