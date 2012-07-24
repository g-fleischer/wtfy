import java.io.*;
import java.net.*;
import java.awt.*;
import java.util.*;

public class TrackingLib {
    String _host;
    int _port;
    int _timeout = 10; // 10 second timeout
    boolean _https = true;
    String _trackid;
    public TrackingLib(String host, int port, String trackid) {
	this._host = host;
	this._port = port;
	this._trackid = trackid;
    }

    private void log(String s) {
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
		log("got response: " + response.toString());
		successful = true;
		socket.close();
	    }
	} catch (Exception e) {
	    log("sendBinary: " + e);
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
	    c.addRequestProperty("X-Trackid", this._trackid);	
	    //	    c.addRequestProperty("Content-Length", ""+request.length());

	    OutputStreamWriter ows = new OutputStreamWriter(c.getOutputStream());
	    log(request);
	    ows.write(request);
	    ows.close();

	    BufferedReader reader = new BufferedReader(new InputStreamReader(c.getInputStream()));
	    String line;
	    StringBuffer response = new StringBuffer();
	    while ( (line = reader.readLine()) != null) {
		response.append(line);
		response.append("\r\n");
	    }

	    log("got response: " + response.toString());

	    successful = true;
	    reader.close();

	} catch (Exception e) {
	    log("sendHttp: " + e);
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
	    log("readGraphicsEnvironment: " + e);
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
	    log("readFonts: " + e);
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
	    log("readFonts: " + e);
	}
    }

    private void readNetworkInterface(NetworkInterface ni, StringBuilder data) {

	StringBuilder report = new StringBuilder();
	try {
	    report.append("<NetworkInteface Name=\"");
	    report.append(xmlEncode(ni.getName()));
	    report.append("\" DisplayName=\"");
	    report.append(xmlEncode(ni.getDisplayName()));

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
	    /* very slow, must be attempting reverse lookups
	       or depends on crossdomain.xml
	     */
	    report.append("<InetAddresses>");
	    for (Enumeration<InetAddress> it = ni.getInetAddresses(); it.hasMoreElements(); ) {
		InetAddress a = it.nextElement();
		report.append("<Address HostAddress=\"");
		report.append(xmlEncode(a.getHostAddress()));
		report.append("\" />");
	    }
	    report.append("</InetAddresses>");
	    report.append("</NetworkInterface>");
	    data.append(report.toString());
	} catch (Exception e) {
	    log("readNetworkInterface: " + e);
	}
    }

    public void process() {
	StringBuilder builder = new StringBuilder();
	builder.append("<Results>");
	GraphicsEnvironment ge = GraphicsEnvironment.getLocalGraphicsEnvironment();
	tl.readFonts(GraphicsEnvironment.getLocalGraphicsEnvironment(), builder);
	tl.readGraphicsEnvironment(ge, builder);
	tl.readNetworkInterfaces(builder);
	builder.append("</Results>");
	String data = builder.toString();
	System.out.println(data);
	System.out.println("sendBinary: " + tl.sendBinary(data));
	boolean successful = tl.sendHttp(data);
	System.out.println("sendHttp (with https): " + successful);
	if (!successful) {
	    tl.setUseHttps(false);
	    System.out.println("sendHttp: " + tl.sendHttp(data));
	}
    }

    public static void main(String[] args) {
	try {
	    String host = args[0];
	    int port = Integer.parseInt(args[1]);
	    TrackingLib tl = new TrackingLib(host, port, "1234.abcd");
	    tl.process();
	} catch (Exception e) {
	    System.out.println("Error: " + e);
	}
    }

}