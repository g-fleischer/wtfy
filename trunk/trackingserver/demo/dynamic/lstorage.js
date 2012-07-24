(function () {
    try {
	var w = window, d = document;
	var cb = function(event) {
	    try {
		var tid = event.data.toString(), ctid = null;
		var cleaned = event.origin.toString().replace(/\W+/g, '_');
		if (document.cookie) {
		    var lookup = cleaned + '_tid=';
		    var cookies = document.cookie.toString();
		    var content = null;
		    var n = cookies.indexOf(lookup);
		    if (n >= 0) {
			var content = cookies.slice(n+lookup.length);
			n = content.indexOf(';');
			if (n >= 0) {
			    content = content.substring(0, n);
			}
			ctid = unescape(content);
		    }
		}
		document.cookie = cleaned + '_tid='+ escape(tid)+';path=/;expires='+(new Date(1666666666666)).toGMTString();
		event.source.postMessage(ctid, event.origin);
	    } catch(e){alert(e.message)}
	};
	if (w.addEventListener) {
	    w.addEventListener("message", cb, false);
	} else {
	    w.attachEvent("onmessage", cb);
	}
	var i = d.createElement("iframe");
	i.heigth = i.width = 0;
	i.frameBorder = 0;
	i.top = i.left = "-1234px";
	i.src = "//${domain}/lstorage.html";
	d.body.appendChild(i);
    } catch(e) {alert(e)}
})();
