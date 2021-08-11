import os
import time
import traceback

import string
import random

from imaplib import IMAP4_SSL
from email import message_from_bytes
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

hostname = 'imap.mail.ru'
myemail = 'example@mail.ru'
password = 'PASSWORD'

os.chdir('..')

for fn in os.listdir('upload'):
	while True:
		assert '"' not in fn
		assert '\\' not in fn
		try:
			rid = ''.join(random.choices(string.ascii_lowercase, k=15))
			
			f1 = os.path.join('upload', fn)
			f2 = os.path.join('/tmp', fn)
			subject = os.path.splitext(fn)[0]
			
			message = MIMEMultipart()
			message["From"] = myemail
			message["To"] = myemail
			message["Subject"] = subject + ' ' + rid
			
			message.attach(MIMEText(""))
			
			with open(f1, "rb") as attachment:
				part = MIMEBase("application", "octet-stream")
				part.set_payload(attachment.read())
			
			encoders.encode_base64(part)
			
			part.add_header(
				"Content-Disposition",
				f'attachment; filename="{fn}"',
			)
			
			for n, v in enumerate(part._headers):
				if v[0] == 'MIME-Version':
					del part._headers[n]
			
			message.attach(part)
			
			
			M = IMAP4_SSL(hostname)
			M.login(myemail, password)
			
			for rl in M.list()[1]:
				mf = rl.decode()
				if '\Drafts' in mf:
					folder = mf.split(' ')[-1]
			
			M.append(folder, '', None, message.as_bytes())
			
			M.logout()
			del message
			
			time.sleep(2)
			
			M = IMAP4_SSL(hostname)
			M.login(myemail, password)
			M.select(folder)
			
			typ, data = M.search(None, 'ALL')
			for num in data[0].split():
				typ, data = M.fetch(num, '(BODY.PEEK[HEADER])')
				for ln in data[0][1].decode().split('\r\n'):
					ls = ln.split(' ')
					if len(ls) == 3 and ls[0] == 'Subject:' and ls[1] == subject:
						if ls[2] == rid:
							typ, data = M.fetch(num, '(RFC822)')
							msg = message_from_bytes(data[0][1])
							
							for part in msg.walk():
								fn = part.get_filename()
								if not fn:
									continue
								print(fn)
								fp = open(f2, 'wb')
								fp.write(part.get_payload(decode=True))
								fp.close()
							del msg
						else:
							print('del', ls[1])
							M.store(num, '+FLAGS', '\\Deleted')
				
			M.expunge()
			M.close()
			M.logout()
			
			f3 = '"'+f1+'" "'+f2+'"'
			if os.system('cmp '+f3+' && rm '+f3) == 0:
				break
		except:
			traceback.print_exc()
