from header import *

def setstatus(status):
	myadv = getalladv()
	for my in myadv:
		id = my['id']
		if my['status'] == status:
			print(id, my['status'])
			continue
		param = {'status': status}
		r = {}
		while 'status' not in r or r['status'] != status:
			try:
				if r: print(r, status)
				r = query('dsa/'+str(id), param)
				if 'code' in r and r['code'] == 'AdvertCannotBeActivated':
					break
			except:
				time.sleep(30)
		else:
			print(id, my['status'], '->', r['status'])

def of():
	open(datadir + '/exiting', 'w').close()
	setstatus('pause')
	while True:
		try:
			r = query('trade/')['total']
			print(r, 'active trades')
			if r == 0:	break
		except:
			print('trades ?')
		time.sleep(30)

actions += [of]

for act in actions:
	if act.__name__ == sys.argv[1]:
		act()
