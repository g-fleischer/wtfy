import java.applet.*;
import java.awt.*;
import java.net.*;
import java.io.*;
import java.util.*;
import java.text.*;
import java.lang.*;
import netscape.javascript.*;

public class Tracking extends Applet {

    public static void main(String[] args) {
	try {
	    String host = args[0];
	    int port = Integer.parseInt(args[1]);
	    Tracking tracking = new Tracking();
	    tracking.configure(host, port);
	    String trackid = "1234.abcd";
	    String existing_id = "98776.xyz";
	    tracking.processResults(trackid, existing_id);
	} catch (Exception e) {
	    System.out.println("Error: " + e);
	}
    }

    public void init() {
    }

    public void start() {
        try {
	    JSObject win = JSObject.getWindow(this);

            String codebase = getCodeBase().toString();
	    URL u = new URL(codebase);

	    String host = "";
	    int port = 2345;
	    try {
		host = getParameter("host");
		port = Integer.parseInt(getParameter("port"));
	    } catch (Exception e) {
	    }
	    if (null == host || 0 == host.length()) {
		host = u.getHost();
	    }
	    this._host = host;
	    this._port = port;

	    trace("host=" + this._host);
	    trace("port=" + this._port);

	    String trackid = getCookie(win, "trackid");
	    String existing_id = this.readResource("id.txt");

	    trace("trackid=" + trackid);
	    trace("existing_id=" + existing_id);

	    this.processResults(trackid, existing_id);

        } catch (Exception e) {
            trace("error: " + e.toString());
        }
    }

    private String getCookie(JSObject win, String cookieName) {
	try {
	    String search = cookieName + "=";
	    String cookie = (String)win.eval("document.cookie");
	    int n = cookie.indexOf(search);
	    if (n > -1) {
		String tmp = cookie.substring(n + search.length());
		n = tmp.indexOf(";");
		if (n > -1) {
		    tmp = tmp.substring(0, n);
		}
		return tmp;	    
	    }
	} catch (Exception e) {
	    trace("getCookie: e=" + e.toString());
	}
	return "";
    }

    public void paint(Graphics g) {
    }

    public String readResource(String entry) {
	String response = ""; // TOOD:
	try {
	    InputStream is = getClass().getResourceAsStream(entry);
	    BufferedReader br = new BufferedReader(new InputStreamReader(is));
	    String line;
	    while ( (line = br.readLine()) != null) {
		response += line;
	    }
	} catch (Exception e) {
	    trace("exception reading resource: " + e.toString());
	}
	return response;
    }

    String _host;
    int _port;
    int _timeout = 10; // 10 second timeout
    boolean _https = true;
    String _trackid;

    public Tracking() {
    }

    private void configure(String host, int port) {
	this._host = host;
	this._port = port;
    }

    private void trace(String s) {
	System.err.println(s);
    }

    public void setUseHttps(boolean useHttps) {
	this._https = useHttps;
    }
    public boolean sendBinary(String data) {
	boolean successful = false;
	try {

	    Socket socket = new Socket();
	    InetSocketAddress isa = new InetSocketAddress(this._host, this._port);
	    socket.connect(isa, this._timeout * 1000);
	    if (socket.isConnected()) {
		BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(socket.getOutputStream()));
		InputStreamReader reader = new InputStreamReader(socket.getInputStream());

		writer.write(data);
		writer.write("\0");
		writer.flush();

		int i;
		StringBuffer response = new StringBuffer();
		while ( (i = reader.read()) != 0) {
		    response.append((char)i);
		}
		trace("got response: " + response.toString());
		successful = true;
		socket.close();
	    }
	} catch (Exception e) {
	    trace("sendBinary: " + e);
	}
	return successful;
    }
    
    public boolean sendHttp(String data) {
	boolean successful = false;
	try {
	    String request = "data=" + URLEncoder.encode(data, "UTF-8");
	    URL u = new URL((this._https ? "https://" : "http://") + this._host + "/results");
	    URLConnection c = u.openConnection();
	    c.setDoOutput(true);
	    c.setAllowUserInteraction(false);
	    c.setUseCaches(false);
	    //	    c.addRequestProperty("X-Trackid", this._trackid);	
	    //	    c.addRequestProperty("Content-Length", ""+request.length());

	    OutputStreamWriter ows = new OutputStreamWriter(c.getOutputStream());
	    trace(request);
	    ows.write(request);
	    ows.close();

	    BufferedReader reader = new BufferedReader(new InputStreamReader(c.getInputStream()));
	    String line;
	    StringBuffer response = new StringBuffer();
	    while ( (line = reader.readLine()) != null) {
		response.append(line);
		response.append("\r\n");
	    }

	    trace("got response: " + response.toString());

	    successful = true;
	    reader.close();

	} catch (Exception e) {
	    trace("sendHttp: " + e);
	}
	return successful;
    }

    private String xmlEncode(String s) {
	return s;  // TODO: encode
    }
    public void readGraphicsEnvironment(GraphicsEnvironment ge, StringBuilder builder) {
	StringBuilder data = new StringBuilder();
	try {
	    data.append("<GraphicsEnvironment>");
	    Rectangle r = ge.getMaximumWindowBounds();
	    data.append("<MaximumWindowBounds height=\"");
	    data.append(r.height);
	    data.append("\" width=\"");
	    data.append(r.width);
	    data.append("\" />");

	    GraphicsDevice defaultScreenDevice = ge.getDefaultScreenDevice();
	    data.append("<DefaultScreenDevice IDstring=\"");
	    data.append(xmlEncode(defaultScreenDevice.getIDstring()));
	    data.append("\" />");

	    GraphicsDevice[] devices = ge.getScreenDevices();
	    data.append("<ScreenDevices>");
	    for(int i = 0; i < devices.length; ++i) {
		GraphicsDevice device = devices[i];

		data.append("<ScreenDevice IDstring=\"");
		data.append(xmlEncode(device.getIDstring()));
		data.append("\" AvailableAcceleratedMemory=\"");
		data.append(device.getAvailableAcceleratedMemory());
		data.append("\" DisplayChangeSupported=\"");
		data.append(device.isDisplayChangeSupported());
		data.append("\" FullScreenSupported=\"");
		data.append(device.isFullScreenSupported());
		data.append("\" />");

		DisplayMode currentDisplayMode = device.getDisplayMode();
		data.append("<CurrentDisplayMode BitDepth=\"");
		data.append(currentDisplayMode.getBitDepth());
		data.append("\" Height=\"");
		data.append(currentDisplayMode.getHeight());
		data.append("\" Width=\"");
		data.append(currentDisplayMode.getWidth());
		data.append("\" RefreshRate=\"");
		data.append(currentDisplayMode.getRefreshRate());
		data.append("\" />");
		data.append("<DisplayModes>");
		DisplayMode[] displayModes = device.getDisplayModes();
		for(int j = 0; j < displayModes.length; ++j) {
		    DisplayMode displayMode = displayModes[j];
		    data.append("<DisplayMode BitDepth=\"");
		    data.append(displayMode.getBitDepth());
		    data.append("\" Height=\"");
		    data.append(displayMode.getHeight());
		    data.append("\" Width=\"");
		    data.append(displayMode.getWidth());
		    data.append("\" RefreshRate=\"");
		    data.append(displayMode.getRefreshRate());
		    data.append("\" />");
		}
		data.append("</DisplayModes>");
	    }
	    data.append("</ScreenDevices>");

	    data.append("</GraphicsEnvironment>");
	    builder.append(data.toString());
	} catch (Exception e) {
	    trace("readGraphicsEnvironment: " + e);
	}
    }

    public void readFonts(GraphicsEnvironment ge, StringBuilder builder) {
	StringBuilder data = new StringBuilder();
	try {
	    data.append("<Fonts>");
	    Font[] fonts = ge.getAllFonts();
	    for(int i = 0; i < fonts.length; ++i) {
		Font font = fonts[i];
		data.append("<Font Name=\"");
		data.append(xmlEncode(font.getName()));
		data.append("\" PSName=\"");
		data.append(xmlEncode(font.getPSName()));
		data.append("\" />");
	    }
	    data.append("</Fonts>");
	    builder.append(data.toString());
	} catch (Exception e) {
	    trace("readFonts: " + e);
	}
    }

    public void readNetworkInterfaces(StringBuilder builder) {
	StringBuilder data = new StringBuilder();
	try {
	    data.append("<NetworkInterfaces>");
	    for (Enumeration<NetworkInterface> it = NetworkInterface.getNetworkInterfaces(); 
		 it.hasMoreElements(); ) {
		readNetworkInterface(it.nextElement(), data);
	    }
	    data.append("</NetworkInterfaces>");
	    builder.append(data.toString());
	} catch (Exception e) {
	    trace("readFonts: " + e);
	}
    }

    private void readNetworkInterface(NetworkInterface ni, StringBuilder data) {

	StringBuilder report = new StringBuilder();
	try {
	    /* some of these are very slow, must be attempting reverse lookups
	       or depends on crossdomain.xml
	     */
	    report.append("<NetworkInteface Name=\"");
	    report.append(xmlEncode(ni.getName()));
	    report.append("\" DisplayName=\"");
	    report.append(xmlEncode(ni.getDisplayName()));

	    // TODO: Move to Unmasking logic
	    /*
	    // XXX: must be a better way to do this
	    String macaddr = "";
	    StringBuilder sb = new StringBuilder();
	    byte[] b = ni.getHardwareAddress();
	    if (b != null) {
		for (int i = 0; i < b.length; ++i) {
		    String s = Integer.toHexString(b[i] & 0xff);
		    if (2 == s.length()) {
			sb.append(s);
		    } else {
			sb.append("0");
			sb.append(s);
		    }
		    if (b.length != i + 1) {
			sb.append(":");
		    }
		}
		macaddr = sb.toString();
	    }
	    report.append("\" HardwareAddress=\"");
	    report.append(macaddr);
	    */

	    report.append("\" MTU=\"");
	    report.append(ni.getMTU());
	    report.append("\" PtoP=\"");
	    report.append((ni.isPointToPoint() ? "true" : "false"));
	    report.append("\" Multicast=\"");
	    report.append((ni.supportsMulticast() ? "true" : "false"));
	    report.append("\" Up=\"");
	    report.append((ni.isUp() ? "true" : "false"));
	    report.append("\" Loopback=\"");
	    report.append((ni.isLoopback() ? "true" : "false"));
	    report.append("\" Virtual=\"");
	    report.append((ni.isVirtual() ? "true" : "false"));
	    report.append("\">");
	    report.append("<SubIntefaces>");
	    for (Enumeration<NetworkInterface> subni = ni.getSubInterfaces(); 
		 subni.hasMoreElements(); ) {
		readNetworkInterface(subni.nextElement(), report);
	    }
	    report.append("</SubIntefaces>");
	    // TODO: move to unmasking logic
	    /*
	    report.append("<InetAddresses>");
	    for (Enumeration<InetAddress> it = ni.getInetAddresses(); it.hasMoreElements(); ) {
		InetAddress a = it.nextElement();
		report.append("<Address HostAddress=\"");
		report.append(xmlEncode(a.getHostAddress()));
		report.append("\" />");
	    }
	    report.append("</InetAddresses>");
	    */
	    report.append("</NetworkInterface>");
	    data.append(report.toString());
	} catch (Exception e) {
	    trace("readNetworkInterface: " + e);
	}
    }

    private void readInformation(StringBuilder builder) {
	StringBuilder data = new StringBuilder();
	try {
	    Date now = new Date();
	    DateFormat df = new SimpleDateFormat("dd MMM yyyy kk:mm:ss z");
	    df.setTimeZone(TimeZone.getTimeZone("GMT"));
	    Date date = new Date();
	    data.append("<Information ");
	    data.append("Date=\"");
	    data.append(now.toString());
	    data.append("\" ");
	    data.append("GMT=\"");
	    data.append(df.format(now));
	    data.append("\" ");
	    data.append(" />");
	    builder.append(data.toString());
	} catch (Exception e) {
	    trace("readInformation: " + e);
	}
    }

    public void processResults(String trackid, String existing_trackid) {

	StringBuilder builder = new StringBuilder();
	builder.append("<Results type=\"java\" version=\"1.0\">");

	builder.append("<Tracking trackid=\"");
	builder.append(trackid);
	builder.append("\" existing=\"");
	builder.append(existing_trackid);
	builder.append("\" />");
	this.readInformation(builder);
	builder.append("<Fingerprints>");
	GraphicsEnvironment ge = GraphicsEnvironment.getLocalGraphicsEnvironment();
	this.readFonts(GraphicsEnvironment.getLocalGraphicsEnvironment(), builder);
	this.readGraphicsEnvironment(ge, builder);
	this.readNetworkInterfaces(builder);
	builder.append("</Fingerprints>");
	builder.append("</Results>");
	String data = builder.toString();
	System.out.println(data);
	System.out.println("sendBinary: " + this.sendBinary(data));
	boolean successful = this.sendHttp(data);
	System.out.println("sendHttp (with https): " + successful);
	if (!successful) {
	    this.setUseHttps(false);
	    System.out.println("sendHttp: " + this.sendHttp(data));
	}
    }


}