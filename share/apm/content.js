function sleep(ms) {
	return new Promise(resolve => {
		setTimeout(resolve, ms);
	});
}

function runEvent(input, event) {
	input.dispatchEvent(new Event(event, { bubbles: true }))
}

function changeValue(input, value){
    Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set.call(input, value);
    runEvent(input, "input")
}

function keyPress(inp) {
	inp.dispatchEvent(new KeyboardEvent("keydown", {
		key: "v",
		keyCode: 118,
		code: "KeyV",
		which: 118,
		shiftKey: false,
		ctrlKey: true,
		metaKey: false,
		bubbles: true
	}))
}

function getElement(q, l=0) {
	var r = document.getElementsByClassName('qa-'+q)[0]
	for (var i = 0; i < l; i ++) {
		if (!r) return undefined
		r = r.children[0]
	}
	return r
}

function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight) &&
        rect.right <= (window.innerWidth)
    );
}

async function rclick(inp) {
	y = 0
	while (!isInViewport(inp) && y < 100000) {
		y = y + 10
		scroll(0, y)
		await sleep(50)
	}
	
	r = inp.getBoundingClientRect()
	chrome.runtime.sendMessage([Math.round(r.x)+7,Math.round(r.y)+3])
}

async function ask(content) {
	response = await fetch('http://127.0.0.1:22222/QINdbNFKeGGUmeAnbRhksGOTTZrATR', {method: 'POST', body: JSON.stringify(content) + '<EOF>'});
	return await response.json()
}

function tclose() {
	chrome.runtime.sendMessage([-1])
}

mainurl = 'https://yoomoney.ru/main'

async function amain() {
	if (location.href.startsWith('https://yoomoney.ru/transfer/a2w')) {
		q = await ask({action: 'details', paymethod: 'wallet'})
		await sleep(500)
		while (! (inp = getElement('form-destination-to-input', 3))) await sleep(1000)
		runEvent(inp, "focus")
		await sleep(500)
		changeValue(getElement('form-destination-to-input', 3), q.details)
		await sleep(300)
		runEvent(getElement('form-destination-to-input', 3), "blur")
		while (! (inp = getElement('form-amount-input', 3))) {
			if (getElement('form-destination-error-description')) {
				await ask({action: 'bad'})
				tclose()
			}
			await sleep(1000)
		}
		runEvent(inp, "focus")
		await sleep(500)
		changeValue(getElement('form-amount-input', 3), q.amount)
		await sleep(300)
		runEvent(getElement('form-amount-input', 3), "blur")
		while (! ( (a = getElement('form-submit')) && (b = a.children[1]) && (inp = b.children[0]) ) ) {
			if (document.getElementsByClassName('qa-accordion-option-reason').length == 2) {
				await ask({action: 'bad'})
				tclose()
			}
			await sleep(1000)
		}
		scroll(0, 265)
		if (document.body.innerText.search('получателя анонимный кошелёк') == -1) {
			inp.click()
		} else {
			await ask({action: 'bad'})
			tclose()
		}
		//  && document.body.innerText.search('другой кошелёк, укажите его номер') == -1
		while (! location.href.startsWith('https://yoomoney.ru/transfer/process/confirm?orderId=')) await sleep(1000)
	}
	
	if (location.href.startsWith('https://yoomoney.ru/transfer/process/confirm?orderId=')) {
		while (! (inp = getElement('confirm-sum-info-will-receive', 1))) await sleep(1000)
		amount = inp.textContent.replaceAll(',', '.').replaceAll(' ', '').replaceAll('₽', '')
		inp = getElement('recipient-phone-value')
		if (!inp) {
			while (! (inp = getElement('recipient-wallet-value'))) await sleep(1000)
		}
		details = inp.textContent
		q = await ask({action: 'getcode', amount: amount, details: details})
		if (q.ok) {
			while (! (inp = getElement('confirm-submit-button'))) await sleep(1000)
			inp.click()
			while (! (inp = getElement('go-to-emergency'))) await sleep(1000)
			inp.click()
			scroll(0, 265)
			await sleep(500)
			while (! (inp = getElement('code-input-field', 2))) await sleep(1000)
			runEvent(inp, "focus")
			await sleep(500)
			changeValue(getElement('code-input-field', 2), q.c)
			await sleep(300)
			runEvent(getElement('code-input-field', 2), "blur")
			while (! location.href.startsWith('https://yoomoney.ru/transfer/process/success?orderId=')) await sleep(1000)
		}
	}
	
	if (location.href.startsWith('https://yoomoney.ru/transfer/process/success?orderId=')) {
		while (! getElement('success-title-message') || 
			getElement('success-title-message').textContent != "Готово, отправили перевод") await sleep(1000)
		await sleep(2000)
		q = await ask({action: 'confirm'})
		await sleep(7000)
		if (q.closed) {
			if (q.redir) {
				location.href = mainurl
			} else {
				tclose()
			}
		}
	}
	
	if (location.href.startsWith('https://yoomoney.ru/transfer/a2c')) {
		await ask({action: 'bad'})
		tclose()
	}
	
	if (location.href.startsWith('https://yoomoney.ru/phone')) {
		q = await ask({action: 'details', paymethod: 'phone'})
		await sleep(500)
		while (! (inp = document.getElementsByName('customerNumber')[0])) await sleep(1000)
		runEvent(inp, "focus")
		await sleep(500)
		changeValue(document.getElementsByName('customerNumber')[0], q.details)
		await sleep(300)
		sel = 'sum'
		while (!document.getElementsByName(sel)[0]) {
			keyPress(document.getElementsByName('customerNumber')[0])
			await sleep(1000)
		}
		sel = 'netSum'
		if (!document.getElementsByName(sel)[0]) {
			sel = 'sum'
		}
		runEvent(document.getElementsByName(sel)[0], "focus")
		await sleep(300)
		changeValue(document.getElementsByName(sel)[0], q.amount)
		await sleep(300)
		while (document.getElementsByClassName('button_type_submit')[0].classList.contains('button_disabled')) {
			keyPress(document.getElementsByName(sel)[0])
			if (document.getElementsByClassName('lantern_id_operator-error')[0] &&
				document.getElementsByClassName('lantern_id_operator-error')[0].className.search('lantern_hidden_yes')==-1) {
				await ask({action: 'bad'})
				tclose()
			}
			if (document.getElementsByClassName('tooltip_theme_error')[0] &&
				document.getElementsByClassName('tooltip_theme_error')[0].className.search('tooltip_visible')!=-1) {
				await ask({action: 'bad'})
				tclose()
			}
			await sleep(1000)
		}
		runEvent(document.getElementsByName(sel)[0], "blur")
		await sleep(500)
		document.getElementsByClassName('button_type_submit')[0].click()
	}
	
	if (location.href.startsWith('https://yoomoney.ru/payments/internal/success')) {
		while (! document.getElementsByClassName('title_last_yes')[0] || 
			document.getElementsByClassName('title_last_yes')[0].textContent != "Платеж прошел") await sleep(1000)
		await sleep(2000)
		q = await ask({action: 'confirm'})
		await sleep(7000)
		if (q.closed) {
			if (q.redir) {
				location.href = mainurl
			} else {
				tclose()
			}
		}
	}
	
	if (location.href.startsWith('https://yoomoney.ru/payments/internal')) {
		while (! (inp = document.getElementsByClassName('payment-submit__forward-button-content')[0])) await sleep(1000)
		details = document.getElementsByClassName('payment-info2__table-value')[0].textContent
		amount = document.getElementsByClassName('price__amount')[0].textContent.replaceAll(',', '.').replaceAll(' ', '').replaceAll('₽', '')
		q = await ask({action: 'getcode', amount: amount, details: details})
		if (q.ok) {
			await rclick(inp)
			await sleep(1000)
			while (! (inp = document.getElementsByClassName('secure-auth__emergency-trigger-link')[0])) await sleep(1000)
			fn = 1
			if (inp.textContent != 'Использовать аварийный код') {
				while (! (inp = document.getElementsByClassName('secure-auth__emergency-trigger-link')[1])) await sleep(1000)
				fn = 0
			}
			inp.click()
			await sleep(1000)
			while (! (inp = document.getElementsByName('answer')[fn])) await sleep(1000)
			runEvent(inp, "focus")
			await sleep(1000)
			changeValue(document.getElementsByName('answer')[fn], q.c)
			await sleep(1000)
			runEvent(document.getElementsByName('answer')[fn], "blur")
			for (t = 1; t <= 7; t ++) {
				await sleep(1000)
				await rclick(document.getElementsByClassName('payment-submit__forward-button-content')[0])
			}
		}
	}
	
	if (location.href.startsWith('https://yoomoney.ru/emergency-codes')) {
		await sleep(2000)
		if (! document.getElementsByClassName('qa-code')[22]) {
			q = await ask({action: 'acode'})
			runEvent(getElement('submit'), "click")
			while (! (inp = getElement('go-to-emergency'))) await sleep(1000)
			inp.click()
			await sleep(500)
			while (! (inp = getElement('code-input-field', 2))) await sleep(1000)
			runEvent(inp, "focus")
			await sleep(500)
			changeValue(getElement('code-input-field', 2), q.c)
			await sleep(300)
			runEvent(getElement('code-input-field', 2), "blur")
		}
		while (! document.getElementsByClassName('qa-code')[22]) await sleep(1000)
		cl = ''; 
		for (n = 0; n < 25; n ++) {
			cl += document.getElementsByClassName('qa-code')[n].textContent + '\n'
		}
		q = await ask({action: 'savecodes', content: cl})
		if (q.saved) tclose()
	}
	
	if (location.href == 'https://yoomoney.ru/main') {
		ops = document.getElementsByClassName('qa-operation')
		lns = ''
		for (n = 0; n < ops.length; n ++) {
			op = ops[n].children[0]
			dn = op.children[0].children[1]
			des = (dn.children[0].textContent + ' ' + dn.children[1].textContent).replaceAll('\t', '').replaceAll('\n', '').replaceAll(',', '.')
			amo = op.children[1].textContent
			dir = 'out'
			if (amo.startsWith('+')) {
				dir = 'in'
				amo = amo.slice(1)
			}
			if (!amo.endsWith('₽')) {
				continue
			}
			amo = Number(amo.replaceAll('₽', '').replaceAll('\xa0', '').replaceAll(',', '.').trim())
			lns += dir + '\t' + amo + '\t' + des + '\n'
		}		
		bal = getElement('user-show-sidebar-balance').textContent
		if (!bal.endsWith('₽')) {
			return
		}
		bal = Number(bal.replaceAll('₽', '').replaceAll(',', '.').replaceAll('\xa0', '').trim())
		mywallet = getElement('accountId').textContent.replaceAll(' ', '').replaceAll('\xa0', '')
		q = await ask({action: lns, bal: bal, mywallet: mywallet})
		if (q.saved) tclose()
	}
	
}

window.onload = amain

ask({action: 'loaded'})
