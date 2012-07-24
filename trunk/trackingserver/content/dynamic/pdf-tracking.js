function trace(msg) {
//    app.alert(msg);
}

function xmlEncode(m) {
    // TODO: implement
    return m;
}

function readMonitors() {
    
    var results = "";
    try {
	if (app.monitors) {
	    var data = "<Monitors>";
	    var l = app.monitors.length;
	    for(var i = 0; i < l; ++i) {
		var m = app.monitors[i];
		data += '<Monitor ';
		data += 'colorDepth="' + m.colorDepth + '" ';
		data += 'isPrimary="' + m.isPrimary + '" ';
		data += 'rect="' + xmlEncode(m.rect.toString()) + '" ';
		data += 'workRect="' + xmlEncode(m.workRect.toString()) + '" ';
		data += ' />';
	    }
	    data += "</Monitors>";
	    results = data;
	}
    } catch (e) {
	trace("readMonitors: e=" + e);
    }

    return results;
}

function readPrinters() {
    
    var results = "";
    try {
	if (app.printerNames) {
	    var data = "<Printers>";
	    var l = app.printerNames.length;
	    for(var i = 0; i < l; ++i) {
		data += '<Printer Name="' + xmlEncode(app.printerNames[i]) + '" />';
	    }
	    data += "</Printers>";
	    results = data;
	}
    } catch (e) {
	trace("readPrinters: e=" + e);
    }

    return results;
}


function readPrintParams() {
    
    var results = "";
    try {
	var pp = this.getPrintParams();
	if (pp) {
	    var data = "<PrintParams>";
	    data += "</PrintParams>";
	    results = data;
	}
    } catch (e) {
	trace("readPrintParams: e=" + e);
    }

    return results;
}

function readPlugins() {
    
    var results = "";
    try {
	if (app.plugIns) {
	    var data = "<Plugins>";
	    var l = app.plugIns.length;
	    for(var i = 0; i < l; ++i) {
		var plugIn = app.plugIns[i];
		data += '<Plugin ';
		data += 'Name="' + xmlEncode(plugIn.name) + '" ';
		data += 'Path="' + xmlEncode(plugIn.path) + '" ';
		data += 'Version="' + xmlEncode(plugIn.version) + '" ';
		data += ' />';
	    }
	    data += "</Plugins>";
	    results = data;
	}
    } catch (e) {
	trace("readPrinters: e=" + e);
    }

    return results;
}

function readPlayers() {
    
    var results = "";
    try {
	if (app.media) {
	    var data = "<Players>";
	    var players = app.media.getPlayers();
	    var l = players.length;
	    for(var i = 0; i < l; ++i) {
		var player = players[i];
		data += '<Player ';
		data += 'Id="' + xmlEncode(player.id) + '" ';
		data += 'Name="' + xmlEncode(player.name) + '" ';
		data += 'Version="' + xmlEncode(player.version) + '" ';
		var mimeTypes = player.mimeTypes;
		if (mimeTypes && mimeTypes.length > 0) {
		    data += 'MimeTypes="' + xmlEncode(mimeTypes.toString()) + '" ';
		}
		data += ' />';
	    }
	    data += "</Players>";
	    results = data;
	}
    } catch (e) {
	trace("readPrinters: e=" + e);
    }

    return results;
}

function readInformation() {
    var results = "";
    try {
	var now = new Date();
	var data = "<Information ";
	data += 'Date="' + xmlEncode(now.toString()) + '" ';
	data += 'UTC="' + xmlEncode(now.toUTCString()) + '" ';
	data += ' />';
	results = data;
    } catch (e) {
	trace("readInformation: e=" + e);
    }

    return results;

}

function readEnvironment() {
    var results = "";
    try {
	var data = "<Environment><Data ";
	data += 'formsVersion="' + app.formsVersion + '" ';
	data += 'language="' + app.language + '" ';
	data += 'platform="' + app.platform + '" ';
	data += 'viewerVersion="' + xmlEncode(app.viewerVersion) + '" ';
	data += 'viewerType="' + xmlEncode(app.viewerType) + '" ';
	data += 'viewerVariation="' + xmlEncode(app.viewerVariation) + '" ';
	data += ' /></Environment>';
	results = data;
    } catch (e) {
	trace("readEnvironment: e=" + e);
    }

    return results;
}

function processResults(trackid, existing_trackid) {
    var results = '<Results type="pdf" version="1.0">';
    results += '<Tracking trackid="' + trackid + '" existing="' + existing_trackid + '" />';
    results += readInformation();
    results += '<Fingerprints>';
    results += readEnvironment();
    results += readMonitors();
    results += readPlugins();
    results += readPlayers();
    results += readPrinters();
    results += readPrintParams();
    results += '</Fingerprints>';
    results += '</Results>';
    sendForm(results);
    sendHostContainer(results);
}

function sendForm(data) {
    var successful = false;
    try {
	var xmlObj = XMLData.parse(data, false);

	this.submitForm({
	    cURL : "http:\/\/${domain}/echo-pdf-results",
	    cSubmitAs : "XML",
	    oXML : xmlObj
	});

    } catch(e) {
	trace("sendForm: e=" + e);
    }
    return succesful;
}

function sendHostContainer(data) {
    try {
	if ("undefined" != typeof(this.hostContainer)) {
	    this.hostContainer.postMessage([data]);
	}
    } catch(e) {
	trace("sendHostContainer: e=" + e);
    }
}

function readPersistent() {
    try {
	var pname = 'ptrackid';
	if (typeof(global[pname]) == 'undefined') {
	    return "";
	}
	return global[pname];
    } catch (e) {
	trace("storePersistent: e=" + e);
    }
}

function storePersistent(trackid) {
    try {
	var pname = 'ptrackid';
	global[pname] = trackid;
	global.ptrackid = trackid;
	var junk = global[pname];
	if (junk != trackid) {
	    trace("failed to set persistent; " + junk + "!=" + trackid);
	}
	global.setPersistent(pname, true);
    } catch (e) {
	trace("storePersistent: e=" + e);
    }
}

function init() {
    var trackid = "${trackid}";
    var existing_trackid = readPersistent();
	// TODO: decide if should store new or keep old...
//    if (existing_trackid != trackid) {
    if (!existing_trackid || "" == existing_trackid) {
	storePersistent(trackid);
    }
    processResults(trackid, existing_trackid);
}

init();