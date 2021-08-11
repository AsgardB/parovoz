chrome.runtime.onMessage.addListener(
	async function(request, sender, sendResponse) {
		if (request[0] == -1) {
			chrome.tabs.remove(sender.tab.id)
			return console.log(sender.tab.id)
		} 
		chrome.debugger.attach({tabId:sender.tab.id}, "1.2", async function() {
			chrome.debugger.sendCommand({tabId:sender.tab.id}, "Input.dispatchMouseEvent", {type: 'mousePressed', x: request[0], y: request[1],
				button: 'left', clickCount: 1})
    		chrome.debugger.sendCommand({tabId:sender.tab.id}, "Input.dispatchMouseEvent", {type: 'mouseReleased', x: request[0], y: request[1], 
    			button: 'left', clickCount: 1})
		})
	}
);
