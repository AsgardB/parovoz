from trader import *

def mainloop():
	if not cycle: return 0
	if cycle == 2: print("\x1b[2J")
	if cycle >= 2: print("\x1b[H", end='')
	
	fsleep = 5
	ktime = time.time()
	for my in myadv:
		print('\x1b[K', end='')
		if time.time() >= ktime:
			dotrades(checktrades())
			ktime = time.time() + 5
		
		if my['paymethod'] not in enabledpaymethods: continue
		id = my['id']
		
		myrate = float(my['rateValue'])
		type = my['type']
		stype = 'ask' if type == 'selling' else 'bid'
		
		k = (my['cryptocurrency'] + '-' + my['paymethod_currency'] + '-' + my['paymethod_description']
			).replace('-RUB-Yandex.Money', '-YM').replace('-RUB-YooMoney', '-UM').replace('-RUB-Sim-card balance', '-SI')
		nk = k.replace('-SI', '-YM')
		if k not in cfg:
			cfg[k] = {}
		if nk not in cfg:
			cfg[nk] = {}
		cf = cfg[k]
		ncf = cfg[nk]
		spreadmin = ncf['spreadmin']
		if k != nk and spreadmin < 3.5:
			spreadmin = 3.5
		
		nb = my['cryptocurrency'] not in ('BTC', 'LTC') and gl.btcmax and gl.bidmaxamount + gl.btcmax + gl.btchl < defaultmaxamount
		if k != nk and not (12 <= time.localtime().tm_hour <= 18): nb = True
		disabled = (type == 'selling' and (not gl.enask or 'noask' in ncf)) or (type == 'purchase' and (not gl.enbid or 'nobid' in ncf or nb))
		
		if disabled or (type == 'selling' and float(my['maxAmount']) < minamount) or (type == 'purchase' and gl.bidmaxamount < minamount):
			if my['status'] == 'active':
				r = query('dsa/'+str(id), {'status': 'pause'})
				print('off', k, type)
				print('\x1b[K', end='')
				if 'status' in r: my['status'] = r['status']
			if (type == 'selling' and 'ask' in cf) or (type == 'purchase' and 'bid' in cf):
				if cycle % 20 not in (18 + int(type == 'purchase'), 19):
					continue
		
		if id in gl.times and gl.times[id] < time.time() - 300:
			if my['status'] == 'active' and not (type == 'selling' and my['cryptocurrency'] == 'BTC'):
				if cycle % 20 not in (18 + int(type == 'purchase'), 19):
					if 'inf'+type in cf: print(cf['inf'+type], '>>')
					continue
		
		qs = {
			'skip': '0',
			'limit': '15',
			'type': 'purchase' if type == 'selling' else 'selling',
			'currency': my['paymethod_currency'],
			'cryptocurrency': my['cryptocurrency'],
			'isOwnerVerificated': 'true',
			'isOwnerTrusted': 'false',
			'isOwnerActive': 'false',
			'paymethod': my['paymethod'],
			'lang': 'ru'
		}
		
		l = query('exchange/dsa/?'+urlencode(qs))
		
		if id not in gl.riv: gl.riv[id] = {}
		if id not in gl.watch: gl.watch[id] = {}
		
		wlist = []
		for t in gl.riv[id]:
			if gl.riv[id][t] > 50: wlist.append(t)
		if len(gl.riv[id]) > 20: wlist = []
		
		adv = None
		targets =  []
		ntargets = []
		pos = 0
		mypos = 0
		lasta = {}
		
		for a in l['data']:
			pos += 1
			oldadv = adv
			owner = a['owner']
			
			if oldadv:
				if type == 'purchase' and float(a['rate']) > float(oldadv['rate']): adv = None
				if type == 'selling' and float(a['rate']) < float(oldadv['rate']): adv = None
			
			if not adv:
				adv = a
				
				if owner == usr.nickname: adv = None
				elif pos >= 2 and pos <= 10 : lasta = a
				
				if float(a['limitCurrency']['min']) >= (8000 if my['cryptocurrency'] != 'BTC' else 3000) or float(a['limitCurrency']['max']) <= 8000:
					adv = None
				
				if adv: ntargets.append(owner)
				
				if owner in wlist:
					if owner in gl.watch[id] and a['rate'] == gl.watch[id][owner]:
						adv = None
					else:
						gl.riv[id][owner] = 30
			
			if not adv and oldadv: adv = oldadv
			
			if owner == usr.nickname:
				targets = ntargets.copy()
				mypos = pos
			
			gl.watch[id][owner] = a['rate']
		
		if not adv and lasta: adv = lasta
		
		newrate = myrate
		
		st = 1
		if my['cryptocurrency'] == 'USDT': st = 0.01
		if my['cryptocurrency'] == 'DOGE': st = 0.0001
		
		if adv: newrate = float(adv['rate']) + (st if type == 'purchase' else -st)
		
		if type == 'purchase':
			cf['bid'] = newrate
			if 'ask' in ncf:
				bidmax = ncf['ask'] / 1.02
				spread = ncf['ask'] / newrate
				if newrate > bidmax: newrate = bidmax
			else:
				print(k, 'bid ?')
				continue
			if 'bidmax' in cf and newrate > cf['bidmax']: newrate = cf['bidmax']
		else:
			cf['ask'] = newrate
			if 'bid' in ncf:
				askmin = ncf['bid'] * 1.02
				spread = newrate / ncf['bid']
				if newrate < askmin: newrate = askmin
			else:
				print(k, 'ask ?')
				continue
			if 'askmin' in cf and newrate < cf['askmin']: newrate = cf['askmin']
		
		spread = round((spread-1)*100, 2)
		
		if spread < spreadmin:
			newrate *= (1 + (spreadmin - spread)/100 * (1 if type=='selling' else -1))
			pspread = str(spread) + '!'
			gl.riv[id] = {}
		else:
			pspread = '' if spread > 35 and k.endswith('-UM') else str(spread) + '%'
		
		if spread > 38 and k.endswith('-UM'):
			newrate = cfg[my['cryptocurrency']+'-YM'][stype]
			newrate *= (1 + 3/100 * (1 if type=='selling' else -1))
			gl.riv[id] = {}
		
		nac = False
		if newrate / myrate > 1.09:
			newrate = myrate * 1.09
			nac = True
		if newrate / myrate < 0.91:
			newrate = myrate * 0.91
			nac = True
		newrate = round(newrate, 5)
		
		for t in gl.riv[id]:
			if t not in targets:
				if gl.riv[id][t] > 1:
					gl.riv[id][t] -= 1
		for t in targets:
			if t not in gl.riv[id]:
				gl.riv[id][t] = 2
			else:
				if gl.riv[id][t] < 150:
					gl.riv[id][t] += 2
		
		if not mypos: mypos = ''
		
		inf = ' ' * 50 + ' %7s %3s %8s %15s %2s %7s' % (k, stype,
			str(newrate) if st < 1 else str(int(newrate)),
			adv['owner'][:15] if adv else '', mypos, pspread)
		
		maxamount = newmaxamount = int(float(my['maxAmount']))
		
		if type == 'purchase': newmaxamount = gl.bidmaxamount
		
		if type == 'selling':
			balres = None
			if my['cryptocurrency'] not in gl.bal:
				balres = getbal(my['cryptocurrency'])
				gl.bal[my['cryptocurrency']] = float(balres['balance'])
			bal = gl.bal[my['cryptocurrency']]
			newmaxamount = (bal - (0.004 if my['cryptocurrency'] == 'BTC' else 0)) * newrate / 1.02
			if my['cryptocurrency'] == 'BTC':
				gl.btcmax = newmaxamount
				if balres:
					gl.btchl = float(balres['holdBalance']) * newrate
			if newmaxamount > gl.askmaxamount: newmaxamount = gl.askmaxamount
			newmaxamount = int(newmaxamount / 100) * 100
		
		if cycle % 20 == 19:
			open(datadir + '/rates.csv', 'a').write('"'+time.strftime('%d.%m.%Y %H:%M:%S')+'","'+k+'","'+type+'","'+str(newrate)+
				'","'+(adv['owner'][:15] if adv else '')+'","'+str(mypos)+
				'","'+str(spread)+'","'+str(newmaxamount)+'"\n')
		
		if newmaxamount < minamount:
			my['maxAmount'] = 0
			print(inf, '---')
			continue
		
		if type == 'purchase' and newmaxamount > 3800:
			newmaxamount = 3800
		
		inf += ' %6s' % str(newmaxamount)
		inf += ' ' + ' '.join(wlist)
		
		if type == 'selling': inf = "\x1b[1m" + inf + "\x1b[0m"
		cf['inf'+type] = inf
		
		if myrate != newrate or my['status'] != 'active' or maxamount != newmaxamount:
			if id in gl.times and gl.times[id] < 0: gl.times[id] = -gl.times[id]
			if id in gl.times and gl.times[id] > time.time():
				sec = gl.times[id] - time.time()
				if sec <= 2:
					if sec > 0: time.sleep(sec)
				else:
					if sec <= 10: fsleep = 1
					print(inf, str(round(sec))+'s')
					continue
			
			param = {'rateValue':newrate}
			
			if my['status'] != 'active':
				if disabled or isexiting():
					print(inf, '--')
					continue
				inf += ' @' if not nac else ' *'
				if not nac: param['status'] = 'active'
			
			if maxamount != newmaxamount: param['maxAmount'] = newmaxamount
			
			r = query('dsa/'+str(id), param)
			if 'rateValue' in r:
				print(inf, '=' if newrate == myrate else '+' if newrate > myrate else '-')
				my['rateValue'] = newrate
			else:
				if 'code' in r:
					print(inf, r['code'])
					if r['code'] == 'AdsUpdatedToOften' and newmaxamount < maxamount:
						r2 = disableadv(id)
						print('dis', k, type)
						print('\x1b[K', end='')
						if 'status' in r2: my['status'] = r2['status']
				else: print(r)
			
			if my['status'] != 'active' and 'status' in param and 'status' in r: my['status'] = r['status']
			
			if 'maxAmount' in param and 'maxAmount' in r: my['maxAmount'] = r['maxAmount']
			
			gl.times[id] = (time.time() + 30) * (1 if myrate != newrate else -1)
		else:
			print(inf, '==')
		
		if id not in gl.times: gl.times[id] = 0
	
	return fsleep

initialize()

cycle = 0
while True:
	try:
		stime = time.time()
		
		try:
			fsleep = mainloop()
			ok1 = True
		except Exception:
			traceback.print_exc()
			ok1 = False
		
		try:
			ntrades = checktrades()
			
			print("\x1b[J")
			
			dotrades(ntrades)
			
			if gl.waitout:
				checkmail()
				print('waitout', gl.waitout)
			
			if gl.newemails: 
				checkdir()
				print(gl.newemails, 'new email')
			
			if gl.unparsed:
				print(gl.unparsed, 'unparsed email')
				
			ok2 = True
		except Exception:
			log(traceback.format_exc())
			ok2 = False
		
		if ok1 and ok2 and not gl.errmail:
			tochecker('/everything-is-ok')
		
		print(str(int(time.time() - stime))+"s", cycle)
		time.sleep(fsleep)
		cycle += 1
	except KeyboardInterrupt:
		print("\x1b[37H")
		exit(1)
