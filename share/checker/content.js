n = 1
u = 'https://bitzlato.com/ru/p2p'

function events() {
	be = document.getElementById('notA')
	if (be) {
		content = ''
		try {
			btn = be.parentElement.parentElement
			if (btn.parentElement.children[3].tagName != 'DIV') {
				btn.click()
			}
			content = btn.parentElement.children[3].innerHTML
		} catch {}
		fetch('http://127.0.0.1:22233/until', {method: 'POST', body: content + '{endmsg}'});
	}
}

function report(l) {
	return fetch('http://127.0.0.1:22233'+l);
}

async function alive() {
	if (document.getElementById('logoutA')) {
		if (location.href.startsWith(u)) {
			if (n < 0) {
				n = 1
			}
			n ++
			if (n > 10) {
				location.href = location.href.split('#')[0]
				n = 1
			}
		} else {
			if (n > 0) {
				n = -1
			}
			n --
		}
		if (n > -11) {
			report('/bt-updated-browser');
		}
	} else {
		if (location.href.startsWith('https://auth.bitzlato.bz/u/login')) {
			document.getElementById('username').value='******'
			document.getElementById('password').value='******'
			document.getElementsByName('action')[0].click()
		}
		if (location.href.startsWith('https://bitzlato.com/auth/antiPhishing')) {
			document.getElementsByClassName('ButtonComponent-button-8')[0].click()
		}
		if (location.href.startsWith('https://bitzlato.com/auth/2fa')) {
			inp = document.getElementById('code')
			inp.value = await (await report('/eWxFwhTinqpkyIkWDtGg')).text()
			inp.dispatchEvent(new Event('input'))
		}
		if (location.href.startsWith(u)) {
			if (document.body.innerHTML.search('/auth/login') != -1) {
				location.href = 'https://bitzlato.com/auth/login'
			} else {
				location.href = location.href.split('#')[0]
			}
		}
	}
}

window.onload = alive
setInterval(alive, 17000)
setInterval(events, 2000)
