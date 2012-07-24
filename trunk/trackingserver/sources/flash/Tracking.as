import flash.external.ExternalInterface;

class Tracking {

    static var app : Tracking;
    var host:String;
    var port:Number;
    var https:Boolean;
    var tf:TextField = null;

    static function myTrace(msg:String) {
	if ('undefined' == typeof(_root.tf) || !_root.tf == null) {
	    _root.tf = _root.createTextField("tf",0,0,0,800,600);
	}
	_root.tf.text += msg + "\n";
    }

    function Tracking() {
	this.host = _root.host || getBaseHost();
	this.port = parseInt(_root.port || '2345');
	this.https = _root._url.indexOf("https://") == 0 ? true : false;

	trace("loaded from: " + _root._url);
	trace("using target=" + host + ":" + port);
	readLSO();
	var trackid : String = _root.trackid;
	if (!trackid) {
	    trackid = readExternal();
	}
	var existing_trackid : String = readLSO();
	if (!existing_trackid) {
	    // TODO: decide if to write or keep existing?
	    writeLSO(trackid);
	}

	this.processResults(trackid, existing_trackid);
    }

    function getBaseHost():String {
	var basehost:String = _root._url;
	var n:Number = basehost.indexOf("//");
	basehost = basehost.substring(n + 2);
	n = basehost.indexOf('/');
	basehost = basehost.substring(0, n);
	n = basehost.indexOf(':');
	if (n > -1) {
	    basehost = basehost.substring(0, n);
	}
	return basehost;
    }

    function readExternal() {
	var etrackid : String = "";
	try {
	    trace('ExternalInterface.available='+ExternalInterface.available);
	    if (ExternalInterface.available) {
		var ret = ExternalInterface.call("WTFY.get_tracking_id");
		trace('external returned: ' + ret);
		if ('undefined' != typeof(ret) && ret) {
		    etrackid = ret.toString();
		}
	    }
	} catch (ex:Error) {
	    trace('readExternal: ex=' + ex);
	}
	return etrackid;
    }

    function readLSO() {
	var trackid = "";
	try {
	    var so:SharedObject = SharedObject.getLocal("trackid", "/", false);
	    if (null == so) {
		trace("readLSO: null sharedobject");
		return;
	    }
	    so.onStatus = function (infoObject:Object) {
		var msg:String = "";
		for (var i in infoObject) {
		    msg += i + ": " + infoObject[i] + ", ";
		}
		trace("onStatus: " + msg);
	    }
	    if ('undefined' != typeof(so.data.trackid) && so.data.trackid) {
		trackid = so.data.trackid;
		trace('LSO: read trackid=' + trackid);
	    } else {
		trace('LSO: trackid is blank')
	    }
	} catch (ex:Error) {
	    trace('readLSO: ex=' + ex);
	}
	return trackid;
    }

    function writeLSO(trackid:String) {
	try {
	    var so:SharedObject = SharedObject.getLocal("trackid", "/", false);
	    if (null == so) {
		trace("writeLSO: null sharedobject");
		return;
	    }
	    so.onStatus = function (infoObject:Object) {
		var msg:String = "";
		for (var i in infoObject) {
		    msg += i + ": " + infoObject[i] + ", ";
		}
		trace("onStatus: " + msg);
	    }
	    so.data.trackid = trackid;
	    var flushed : Object = so.flush();
	    trace('LSO: wrote trackid=' + trackid + ', flush=' + flushed);
	} catch (ex:Error) {
	    trace('readLSO: ex=' + ex);
	}
    }

    function processResults(trackid:String, existing_trackid:String) {
	var results:String = "<Results type=\"flash_as2\" version=\"1.0\">";
	results += "<Tracking trackid=\"" + trackid + "\" existing=\"" + existing_trackid + "\" />";
	results += this.getInformation();
	results += "<Fingerprints>";
	results += this.getCapabilities();
	results += this.getFonts();
	results += this.getCameras();
	results += this.getMicrophones();
	results += "</Fingerprints>";
	results += "</Results>";
	if (!this.sendBinary(results, this.sendCompleted)) {
	}
	if (!this.sendHttp(results, this.sendCompleted)) {
	}
    }

    function xmlEncode(m:String) : String {
	return m;
    }

    function getInformation() {
	var results : String = "";
	try {
	    var now : Date = new Date();
	    var data : String = "<Info version=\"" 
		+ xmlEncode(getVersion()) 
		+ "\" Date=\"" + xmlEncode(now.toString())
		+ "\" TimezoneOffset=\"" + now.getTimezoneOffset()
		+ "\" />";
	    results = data;
	} catch (ex:Error) {
	    trace('getVersion: ex=' + ex);
	}
	return results;
    }

    function getCapabilities() {
	var results : String = "";
	try {
	    var caps : Object = System.capabilities;
	    var now : Date = new Date();
	    var data : String = "<Capabilities serverString=\"" 
		+ xmlEncode(caps.serverString) 
		+ "\" />";
	    results = data;
	} catch (ex:Error) {
	    trace('getVersion: ex=' + ex);
	}
	return results;
    }

    function getFonts() {
	var results : String = "";
	try {
	    var data : String = "<Fonts>";
	    var fonts : Array = TextField.getFontList();
	    for (var i:Number = 0; i < fonts.length; ++i) {
		data += "<Font Name=\"" + xmlEncode(fonts[i]) + "\" />";
	    }
	    data += "</Fonts>";
	    results = data;
	} catch (ex:Error) {
	    trace('getFonts: ex=' + ex);
	}
	return results;
    }

    function getCameras() {
	var results : String = "";
	try {
	    var data : String = "<Cameras>";
	    var names : Array = Camera.names;
	    for (var i:Number = 0; i < names.length; ++i) {
		data += "<Camera Name=\"" + xmlEncode(names[i]) + "\" />";
	    }
	    data += "</Cameras>";
	    results = data;
	} catch (ex:Error) {
	    trace('getCameras: ex=' + ex);
	}
	return results;
    }

    function getMicrophones() {
	var results : String = "";
	try {
	    var data : String = "<Microphones>";
	    var names : Array = Microphone.names;
	    for (var i:Number = 0; i < names.length; ++i) {
		data += "<Microphone Name=\"" + xmlEncode(names[i]) + "\" />";
	    }
	    data += "</Microphones>";
	    results = data;
	} catch (ex:Error) {
	    trace('getMicrophones: ex=' + ex);
	}
	return results;
    }

    function sendCompleted(success:Boolean) {
	trace("completed: " + success);
    }

    function sendBinary(data:String, callback:Function) {
	var successful:Boolean = false;
	try {
	    trace('sendBinary');
	    var socket:XMLSocket = new XMLSocket();
	    socket.onData = function(src:String) {
		trace('sendBinary: src=' + src);
		socket.close();
	    }
	    socket.onConnect = function(success:Boolean) {
		trace('sendBinary: success=' + success);
		if (success) {
		    socket.send(data);
		} else {
		    // try again with HTTP
		    this.sendHttp(data, callback);
		}
	    }
	    socket.onClose = function() {
		trace('sendBinary: onClose');
		callback(true);
	    }
	    successful = socket.connect(this.host, this.port);
	} catch(ex:Error) {
	    trace("sendBinary: error=" + ex);
	}
	trace('sendBinary: successful=' + successful);
	return successful;
    }

    function sendHttp(data:String, callback:Function) {
	trace('sendHttp');
	var successful: Boolean = false;
	try {
	    var url:String = (this.https ? "https://" : "http://") + this.host + "/flash-results";
	    var result_lv:LoadVars = new LoadVars();
	    var send_lv:LoadVars = new LoadVars();
	    result_lv.onData = function(src:String) {
		trace(src);
	    }
	    result_lv.onLoad = function(success:Boolean) {
		trace('sendHttp: onLoad=' + success);
		if (success) {
		    // okay
		    callback(true);
		} else {
		    callback(false);
		}
	    }
	    result_lv.onHTTPStatus = function(httpStatus:Number) {
		trace('sendHttp: onHTTPStatus=' + httpStatus);
	    }
	    send_lv.data = data;
	    successful = send_lv.sendAndLoad(url, result_lv, "POST");
	} catch (ex:Error) {
	    trace('sendHttp: ex=' + ex);
	}
	trace('sendHttp: successful=' + successful);
	return successful;
    }

    static function main(mc) {
	app = new Tracking();
    }

}
