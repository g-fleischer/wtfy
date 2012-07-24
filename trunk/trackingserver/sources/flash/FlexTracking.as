package {
    import flash.display.Sprite;
    import flash.text.*;
    import flash.display.*;
    import flash.media.*;
    import flash.sensors.*;
    import flash.net.*;
    import flash.net.drm.*;
    import flash.system.*;
    import flash.events.*;
    import flash.external.ExternalInterface;
    import flash.security.X509Certificate;
    import flash.globalization.*;
    import flash.printing.*;
    import flash.ui.*;

    public class FlexTracking extends Sprite {
	private var host : String;
	private var port : Number;
	private var https : Boolean;
	private var txt : TextField;
	private var socket : XMLSocket;
	private var data : String;
	private var callback : Function;

	public function FlexTracking() : void {
	    this.host = this.loaderInfo.parameters['host'] || getBaseHost();
	    this.port = parseInt(this.loaderInfo.parameters['port'] || '2345');
	    this.https = this.loaderInfo.url.indexOf("https://") == 0 ? true : false;

	    this.txt = new TextField();
	    this.txt.wordWrap = true;
	    this.txt.height = 600;
	    this.txt.width = 800;
	    this.txt.border = true;
	    addChild(txt);

	    log("loaded from: " + this.loaderInfo.url);
	    log("using target=" + this.host + ":" + this.port);

	    var trackid : String = this.loaderInfo['trackid'] as String;
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

	private function log(msg: String) : void {
	    this.txt.appendText(msg + "\n");
	}

	private function getBaseHost():String {
	    var basehost:String = this.loaderInfo.url;
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

	private function readExternal() : String{
	    var etrackid : String = "";
	    try {
		log('ExternalInterface.available='+ExternalInterface.available);
		if (ExternalInterface.available) {
		    var ret : Object = ExternalInterface.call("WTFY.get_tracking_id");
		    log('external returned: ' + ret);
		    if ('undefined' != typeof(ret) && ret) {
			etrackid = ret.toString();
		    }
		}
	    } catch (ex:Error) {
		trace('readExternal: ex=' + ex);
	    }
	    return etrackid;
	}

	private function readLSO() : String {
	    var trackid : String = "";
	    try {
		var so:SharedObject = SharedObject.getLocal("trackid", "/", false);
		if (null == so) {
		    log("readLSO: null sharedobject");
		    return null;
		} else {
		    if ('undefined' != typeof(so.data.trackid) && so.data.trackid) {
			trackid = so.data.trackid;
			log('LSO: read trackid=' + trackid);
		    } else {
			log('LSO: trackid is blank');
		    }
		}
	    } catch (ex:Error) {
		log('readLSO: ex=' + ex);
	    }
	    return trackid;
	}

	private function writeLSO(trackid:String) : void {
	    try {
		var so:SharedObject = SharedObject.getLocal("trackid", "/", false);
		if (null == so) {
		    log("writeLSO: null sharedobject");
		} else {
		    so.data.trackid = trackid;
		    var flushed : Object = so.flush();
		    log('LSO: wrote trackid=' + trackid + ', flush=' + flushed);
		}
	    } catch (ex:Error) {
		log('readLSO: ex=' + ex);
	    }
	}

	private function sendCompleted(success:Boolean) : void {
	}

	private function processResults(trackid:String, existing_trackid:String) : void {
	    var results:String = "<Results type=\"flash_as3\" version=\"1.0\">";
	    results += "<Tracking trackid=\"" + trackid + "\" existing=\"" + existing_trackid + "\" />";
	    results += this.getInformation();
	    results += "<Fingerprints>";
	    results += this.getCapabilities();
	    results += this.getSupported();
	    results += this.getFonts();
	    results += this.getCameras();
	    results += this.getMicrophones();
	    results += this.getMultitouch();
	    results += this.getMouse();
	    results += this.getKeyboard();
	    results += this.getLocales();
	    results += "</Fingerprints>";
	    results += "</Results>";

	    if (!this.sendBinary(results, this.sendCompleted)) {
	    }
	    this.sendHttp(results, this.sendCompleted);
	}

	private function xmlEncode(m:String) : String {
	    return m;
	}

	private function getInformation() : String {
	    var results : String = "";
	    try {
		var now : Date = new Date();
		var data : String = "<Info version=\"" 
		    + xmlEncode(Capabilities.version) 
		    + "\" Date=\"" + xmlEncode(now.toString())
		    + "\" UTC=\"" + xmlEncode(now.toUTCString())
		    + "\" />";
		results = data;
	    } catch (ex:Error) {
		log('getVersion: ex=' + ex);
	    }
	    return results;
	}
	private function getCapabilities() : String {
	    var results : String = "";
	    try {
		var caps : Object = Capabilities;
		var now : Date = new Date();
		var data : String = "<Capabilities serverString=\"" 
		    + xmlEncode(caps.serverString) 
		    + "\" />";
		results = data;
	    } catch (ex:Error) {
		log('getVersion: ex=' + ex);
	    }
	    return results;
	}

	private function getSupported() : String {
	    var results : String = "";
	    try {
		var data : String = "<Supported ";
		try { data += "Accelerometer=\"" + Accelerometer.isSupported + "\" " } catch (ex:Error) {}
		try { data += "PrintJob=\"" + PrintJob.isSupported + "\" " } catch (ex:Error) {}
		try { data += "Geolocation=\"" + Geolocation.isSupported + "\" " } catch (ex:Error) {}
		try { data += "DRMManager=\"" + DRMManager.isSupported + "\" " } catch (ex:Error) {}
		try { data += "LocalConnection=\"" + LocalConnection.isSupported + "\" " } catch (ex:Error) {}
		try { data += "ContextMenu=\"" + ContextMenu.isSupported + "\" " } catch (ex:Error) {}
		data += " />";
		results = data;
	    } catch (ex:Error) {
		log('getSupported: ex=' + ex);
	    }
	    return results;
	}

	private function getMultitouch() : String {
	    var results : String = "";
	    try {
		var data : String = "<Multitouch ";
		data += "inputMode=\"" + Multitouch.inputMode + "\" ";
		data += "maxTouchPoints=\"" + Multitouch.maxTouchPoints + "\" ";
		data += "supportedGestures=\"" + Multitouch.supportedGestures + "\" ";
		data += "supportsGestureEvents=\"" + Multitouch.supportsGestureEvents + "\" ";
		data += "supportsTouchEvents=\"" + Multitouch.supportsTouchEvents + "\" ";
		data += " />";
		results = data;
	    } catch (ex:Error) {
		log('getMultitouch: ex=' + ex);
	    }
	    return results;
	}

	private function getMouse() : String {
	    var results : String = "";
	    try {
		var data : String = "<Mouse ";
		data += "cursor=\"" + Mouse.cursor + "\" ";
		data += "supportsCursor=\"" + Mouse.supportsCursor + "\" ";
		data += "supportsNativeCursor=\"" + Mouse.supportsNativeCursor + "\" ";
		data += " />";
		results = data;
	    } catch (ex:Error) {
		log('getMouse: ex=' + ex);
	    }
	    return results;
	}

	private function getKeyboard() : String {
	    var results : String = "";
	    try {
		var data : String = "<Keyboard ";
		data += "isAccessible=\"" + Keyboard.isAccessible() + "\" ";
		if (Keyboard.isAccessible()) {
		    data += "capsLock=\"" + Keyboard.capsLock + "\" ";
		    data += "numLock=\"" + Keyboard.numLock + "\" ";
		    data += "hasVirtualKeyboard=\"" + Keyboard.hasVirtualKeyboard + "\" ";
		    data += "physicalKeyboardType=\"" + Keyboard.physicalKeyboardType + "\" ";
		}
		data += " />";
		results = data;
	    } catch (ex:Error) {
		log('getKeyboard: ex=' + ex);
	    }
	    return results;
	}

	private function addLocaleNames(allNames : Array, available : Vector.<String>) : Array {
	    for(var i : Number = 0; i < available.length; ++i) {
		var localeID : String = available[i];
		if (allNames.indexOf(localeID) == -1) {
		    allNames.push(localeID);
		}
	    }
	    return allNames;
	}
	private function getAllLocales() : Array {
	    var allNames : Array = new Array();
	    allNames = addLocaleNames(allNames, StringTools.getAvailableLocaleIDNames());
	    allNames = addLocaleNames(allNames, NumberFormatter.getAvailableLocaleIDNames());
	    allNames = addLocaleNames(allNames, CurrencyFormatter.getAvailableLocaleIDNames());
	    allNames = addLocaleNames(allNames, DateTimeFormatter.getAvailableLocaleIDNames());
	    allNames = addLocaleNames(allNames, Collator.getAvailableLocaleIDNames());
	    return allNames;
	}
	private function getLocales() : String {
	    var results : String = "";
	    try {
		var data : String = "<Locales>";
		data += getLocale(LocaleID.DEFAULT);
		var allNames : Array = getAllLocales();
		for (var i : Number = 0; i < allNames.length; ++i) {
		    data += getLocale(allNames[i]);
		}
		data += "</Locales>";
		results = data;
	    } catch (ex:Error) {
		log('getLocale: ex=' + ex);
	    }
	    return results;
	}
	private function getLocale(localeID : String) : String {
	    var results : String = "";
	    try {
		var allNames : Array = new Array();
		try { } catch(ex:Error) {}

		var data : String = "<Locale ";
		var myLocale:LocaleID = new LocaleID(localeID);
		data += "language=\"" + myLocale.getLanguage() + "\" ";
		data += "region=\"" + myLocale.getRegion() + "\" ";

		var localeData:Object = myLocale.getKeysAndValues();
		for (var propertyName:String in localeData) {
		    data += propertyName + "=\"" + localeData[propertyName] + "\" ";
		}
		data += " />";
		results = data;
	    } catch (ex:Error) {
		log('getLocale: ex=' + ex);
	    }
	    return results;
	}

	private function getFonts() : String {
	    var results : String = "";
	    try {
		var data : String = "<Fonts>";
		var fonts : Array =  Font.enumerateFonts(true);
		for (var i:Number = 0; i < fonts.length; ++i) {
		    data += "<Font Name=\"" + xmlEncode(fonts[i].fontName) 
			+ "\" Style=\"" + xmlEncode(fonts[i].fontStyle) 
			+ "\" Type=\"" + xmlEncode(fonts[i].fontType) 
			+"\" />";
		}
		data += "</Fonts>";
		results = data;
	    } catch (ex:Error) {
		log('getFonts: ex=' + ex);
	    }
	    return results;
	}

	private function getCameras() : String {
	    var results : String = "";
	    if (!Camera.isSupported) {
		return results;
	    }
	    try {
		var data : String = "<Cameras>";
		var names : Array = Camera.names;
		for (var i:Number = 0; i < names.length; ++i) {
		    data += "<Camera Name=\"" + xmlEncode(names[i]) + "\" />";
		}
		data += "</Cameras>";
		results = data;
	    } catch (ex:Error) {
		log('getCameras: ex=' + ex);
	    }
	    return results;
	}

	private function getMicrophones() : String{
	    var results : String = "";
	    if (!Microphone.isSupported) {
		return results;
	    }
	    try {
		var data : String = "<Microphones>";
		var names : Array = Microphone.names;
		for (var i:Number = 0; i < names.length; ++i) {
		    data += "<Microphone Name=\"" + xmlEncode(names[i]) + "\" />";
		}
		data += "</Microphones>";
		results = data;
	    } catch (ex:Error) {
		log('getMicrophones: ex=' + ex);
	    }
	    return results;
	}

	private function sendBinary(data:String, callback:Function) : Boolean {
	    log('sendBinary');
	    var successful: Boolean = false;
	    try {
		this.data = data;
		socket = new XMLSocket();
		socket.addEventListener(Event.CONNECT, this.socketConnected);
		socket.addEventListener(Event.CLOSE, this.socketClose);
		socket.addEventListener(DataEvent.DATA, this.socketData);
		socket.addEventListener(IOErrorEvent.IO_ERROR, this.socketError);
		socket.addEventListener(SecurityErrorEvent.SECURITY_ERROR, this.socketSecurityError);

		socket.connect(this.host, this.port);

	    } catch(ex:Error) {
		log("sendBinary: error=" + ex);
	    }
	    log('sendBinary: successful=' + successful);
	    return successful;
	}

	private function socketConnected(event:Event) : void {
	    log('socketConnected');
	    socket.send(this.data);
	}
	private function socketClose(event:Event) : void {
	    log('socketClose');
	}
	private function socketData(event:DataEvent) : void {
	    log('socketData');
	    log(event.data);
	    socket.close();
	}
	private function socketError(event:IOErrorEvent) : void {
	    log('socketError');
	}
	private function socketSecurityError(event:SecurityErrorEvent) : void {
	    log('socketSecurityError');
	}

	private function sendHttp(data:String, callback:Function) : Boolean {
	    log('sendHttp');
	    var successful: Boolean = false;
	    try {
		this.data = data;
		this.callback = callback;

		var url:String = (this.https ? "https://" : "http://") + this.host + "/flash-results";

		var request:URLRequest = new URLRequest(url);
		var loader:URLLoader = new URLLoader();
		var vars:URLVariables = new URLVariables();

		loader.addEventListener(IOErrorEvent.IO_ERROR, this.loaderError);
		loader.addEventListener(Event.COMPLETE, this.loaderComplete);

		vars.data = data;
		request.method = URLRequestMethod.POST;
		request.data = vars;
		loader.load(request);
	    } catch (ex:Error) {
		log('sendHttp: ex=' + ex);
	    }
	    log('sendHttp: successful=' + successful);
	    return successful;
	}

	private function loaderComplete(event:Event) : void {
	}
	private function loaderError(event:IOErrorEvent) : void {
	}
    }
}