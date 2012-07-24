using System;
using System.Collections.Generic;
using System.Linq;
using System.Net;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Shapes;
using System.Windows.Interop;
using System.Windows.Browser;
using System.Text;
using System.Reflection;
using System.Diagnostics;
using System.Configuration;
using System.IO;
using System.IO.IsolatedStorage;
using System.Net.Sockets;

namespace Tracking
{
    public partial class MainPage : UserControl
    {
        private string host;
        private int port;
        private bool https;

        private string socket_data;

        public MainPage()
        {
            InitializeComponent();
        }

        private void UserControl_Loaded(object sender, RoutedEventArgs e) {
            trace("loaded silverlight");

            SilverlightHost silverlight = new SilverlightHost();
            if (!silverlight.InitParams.TryGetValue("host", out this.host)) {
                this.host =  this.getBaseHost();
            }
            string tmpport;
            if (!silverlight.InitParams.TryGetValue("port", out tmpport))
            {
                tmpport = "4502";
            }
            if (!int.TryParse(tmpport, out this.port))
            {
                this.port = 4502;
            }
            this.https = HtmlPage.Document.DocumentUri.Scheme == "https" ? true : false;

            string trackid = this.getCookie("trackid");
            string embedded_trackid = this.getEmbedded("id.txt");
            string existing_trackid = this.readIsolatedStorage();
            trace("read tid: " + trackid);
            if (existing_trackid == null || 0 == existing_trackid.Length)
            {
                this.writeIsolatedStorage(trackid);
            }
            this.processResults(trackid, existing_trackid);
        }

        private string getBaseHost()
        {
            return HtmlPage.Document.DocumentUri.DnsSafeHost;
        }
        private string getCookie(string cookieName) {
            try {
                string search = cookieName + "=";
                string cookie = HtmlPage.Document.Cookies;
                int n = cookie.IndexOf(search);
                if (n > -1) {
                    string tmp = cookie.Substring(n);
                    n = tmp.IndexOf(";");
                    if (n > -1)
                    {
                        tmp = tmp.Substring(0, n);
                    }
                    return tmp;
                }   
            } catch (Exception ex) {
                trace("getCookie: ex=" + ex.Message);
            }
            return "";
        }

        private void processResults(string trackid, string existing_trackid)
        {
            StringBuilder results = new StringBuilder();
            results.Append("<Results type=\"silverlight\" version=\"1.0\">");
            results.AppendFormat("<Tracking trackid=\"{0}\" existing=\"{1}\" />", trackid, existing_trackid);
            this.readInformation(results);
            results.Append("<Fingerprints>");
            this.readEnvironment(results);
            this.readFonts(results);
            this.readGpu(results);
            this.readTimeZoneInfo(results);
            this.readAudioCapture(results);
            this.readVideoCapture(results);
            this.readVideoOutputConnectors(results);
            results.Append("</Fingerprints>");
            results.Append("</Results>");

            string data = results.ToString();
            this.sendBinary(data);
            this.sendHttp(data);
        }

        private string xmlEncode(string m)
        {
            return m;
        }

        private void readInformation(StringBuilder builder)
        {
            StringBuilder data = new StringBuilder();
            try
            {
                data.Append("<Info ");
                data.AppendFormat("Version=\"{0}\" ", xmlEncode(System.Environment.Version.ToString()));
                data.AppendFormat("TickCount=\"{0}\" ", System.Environment.TickCount);
                data.Append(" />");
                builder.Append(data.ToString());
            }
            catch (Exception ex)
            {
                trace("readInformation: " + ex.Message);
            }
        }

        private void readEnvironment(StringBuilder builder)
        {
            StringBuilder data = new StringBuilder();
            try
            {
                data.Append("<Environment><Data ");
                data.AppendFormat("OSVersion=\"{0}\" ", xmlEncode(System.Environment.OSVersion.ToString()));
                data.AppendFormat("Platform=\"{0}\" ", xmlEncode(System.Environment.OSVersion.Platform.ToString()));
                data.AppendFormat("Version=\"{0}\" ", xmlEncode(System.Environment.OSVersion.Version.ToString()));
                data.AppendFormat("ProcessorCount=\"{0}\" ", System.Environment.ProcessorCount);
                data.AppendFormat("IPv4=\"{0}\" ", System.Net.Sockets.Socket.OSSupportsIPv4);
                data.AppendFormat("IPv6=\"{0}\" ", System.Net.Sockets.Socket.OSSupportsIPv6);
                data.AppendFormat("FormatProvider=\"{0}\" ", System.Console.Out.FormatProvider.ToString());
                data.AppendFormat("CurrentCulture=\"{0}\" ", System.Threading.Thread.CurrentThread.CurrentCulture);
                data.AppendFormat("CurrentUICulture=\"{0}\" ", System.Threading.Thread.CurrentThread.CurrentUICulture);
                data.Append(" /></Environment>");
                builder.Append(data.ToString());
            }
            catch (Exception ex)
            {
                trace("readEnvironment: " + ex.Message);
            }
        }

        private void readTimeZoneInfo(StringBuilder builder)
        {
            StringBuilder data = new StringBuilder();
            try
            {
                var tzi = System.TimeZoneInfo.Local;
                data.Append("<TimeZoneInfo><Data ");
                data.AppendFormat("DisplayName=\"{0}\" ", tzi.DisplayName);
                data.AppendFormat("StandardName=\"{0}\" ", tzi.StandardName);
                data.AppendFormat("DaylightName=\"{0}\" ", tzi.DaylightName);
                data.AppendFormat("BaseUtcOffset=\"{0}\" ", tzi.BaseUtcOffset);
                data.AppendFormat("SupportsDaylightSavingTime=\"{0}\" ", tzi.SupportsDaylightSavingTime);
                data.Append(" /></TimeZoneInfo>");
                builder.Append(data.ToString());

            }
            catch (Exception ex)
            {
                trace("readTimeZone: " + ex.Message);
            }
        }

        private void readFonts(StringBuilder builder)
        {
            StringBuilder data = new StringBuilder();
            try
            {
                data.Append("<Fonts>");
                foreach (var st in System.Windows.Media.Fonts.SystemTypefaces)
                {
                    GlyphTypeface gt = null;
                    if (st.TryGetGlyphTypeface(out gt))
                    {
                        data.AppendFormat("<Font FontFileName=\"{0}\" Version=\"{1}\" />", xmlEncode(gt.FontFileName), gt.Version.ToString());
                    }
                }
                data.Append("</Fonts>");
                builder.Append(data.ToString());
            }
            catch (Exception ex)
            {
                trace("readFonts: " + ex.Message);
            }
        }

        private void readAudioCapture(StringBuilder builder)
        {
            StringBuilder data = new StringBuilder();
            try
            {
                data.Append("<AudioCaptureDevices>");

                foreach (var acd in System.Windows.Media.CaptureDeviceConfiguration.GetAvailableAudioCaptureDevices())
                {
                    data.AppendFormat("<AudioCaptureDevice FriendlyName=\"{0}\" IsDefaultDevice=\"{1}\">", acd.FriendlyName, acd.IsDefaultDevice);
                    foreach (var sf in acd.SupportedFormats)
                    {
                        data.AppendFormat("<SupportedFormats BitsPerChannel=\"{0}\" Channels=\"{1}\" SamplersPerSecond=\"{2}\" WaveFormat=\"{3}\" />",
                            sf.BitsPerSample,
                                sf.Channels,
                            sf.SamplesPerSecond,
                            xmlEncode(sf.WaveFormat.ToString()));
                    }
                    data.Append("</AudioCaptureDevice>");
                }

                data.Append("</AudioCaptureDevices>");
                builder.Append(data.ToString());
            }
            catch (Exception ex)
            {
                trace("readAudioCapture: " + ex.Message);
            }
        }

        private void readGpu(StringBuilder builder)
        {
            StringBuilder data = new StringBuilder();
            try
            {
                data.Append("<GpuDevices>");

                var analytics = new System.Windows.Analytics();
                foreach (var gpu in analytics.GpuCollection) {
                    data.AppendFormat("<Gpu DeviceId=\"{0}\" DriverVersion=\"{1}\" VendorId=\"{2}\" />",
                        gpu.DeviceId, xmlEncode(gpu.DriverVersion), gpu.VendorId);
                }

                data.Append("</GpuDevices>");
                builder.Append(data.ToString());
            }
            catch (Exception ex)
            {
                trace("readGpu: " + ex.Message);
            }
        }

        private void readVideoCapture(StringBuilder builder)
        {
            StringBuilder data = new StringBuilder();
            try
            {
                data.Append("<VideoCaptureDevices>");

                foreach (var vcd in System.Windows.Media.CaptureDeviceConfiguration.GetAvailableVideoCaptureDevices())
                {
                    data.AppendFormat("<VideoCaptureDevice FriendlyName=\"{0}\" IsDefaultDevice=\"{1}\">", vcd.FriendlyName, vcd.IsDefaultDevice);
                    foreach (var sf in vcd.SupportedFormats)
                    {
                        data.AppendFormat("<SupportedFormats FramesPerSecond=\"{0}\" PixelFormat=\"{1}\" PixelHeight=\"{2}\" PixelWidth=\"{3}\" Stride=\"{4}\" />",
                            sf.FramesPerSecond,
                            sf.PixelFormat,
                            sf.PixelHeight,
                            sf.PixelWidth,
                            sf.Stride);
                    }
                    data.Append("</VideoCaptureDevice>");
                }
                data.Append("</VideoCaptureDevices>");
                builder.Append(data.ToString());
            }
            catch (Exception ex)
            {
                trace("readVideoCapture: " + ex.Message);
            }
        }

        private void readVideoOutputConnectors(StringBuilder builder)
        {
            StringBuilder data = new StringBuilder();
            try
            {
                data.Append("<VideoOutputConnectors>");

                foreach (var voc in System.Windows.Media.LicenseManagement.VideoOutputConnectors)
                {
                    data.AppendFormat("<VideoOutputConnector ConnectorType=\"{0}\" CanEnableHdcp=\"{1}\" CanEnableCgmsa=\"{2}\" />", 
                        voc.ConnectorType, voc.CanEnableHdcp, voc.CanEnableCgmsa);
                }

                data.Append("</VideoOutputConnectors>");
                builder.Append(data.ToString());
            }
            catch (Exception ex)
            {
                trace("readVideoOutputConnectors: " + ex.Message);
            }
        }

        private string getEmbedded(string name)
        {
            string etrackid = "";
            try
            {
                var stream0 = Application.GetResourceStream(new Uri(name, UriKind.Relative)).Stream;
                etrackid = new StreamReader(stream0).ReadToEnd();
            }
            catch (Exception ex)  {
                trace("getEmbedded: " + ex.Message);
            }
            return etrackid;
        }

        private bool sendBinary(string data)
        {
            bool successful = false;
            try
            {
                this.socket_data = data;
                DnsEndPoint ep = new DnsEndPoint(this.host, this.port);
                Socket sock = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
                SocketAsyncEventArgs socketEventArgs = new SocketAsyncEventArgs();
                socketEventArgs.SocketClientAccessPolicyProtocol = SocketClientAccessPolicyProtocol.Http; // TODO: try both?
                socketEventArgs.Completed += new EventHandler<SocketAsyncEventArgs>(socketEventArgs_Completed);
                socketEventArgs.RemoteEndPoint = ep;
                socketEventArgs.UserToken = sock; // TODO: create class to store user context

                successful = sock.ConnectAsync(socketEventArgs);
            }
            catch (Exception ex)
            {
                trace("sendBinary: ex=" + ex.Message);
            }
            return successful;
        }

        void socketEventArgs_Completed(object sender, SocketAsyncEventArgs e)
        {
            if (SocketError.Success == e.SocketError)
            {
                var sock = e.UserToken as Socket;
                if (e.LastOperation == SocketAsyncOperation.Connect)
                {
                    // connected
                    byte[] data1 = UTF8Encoding.UTF8.GetBytes(this.socket_data);
                    byte[] data2 = new byte[data1.Length + 1];
                    Array.Copy(data1, data2, data1.Length);
                    data2[data1.Length] = 0;
                    e.SetBuffer(data2, 0, data2.Length);
                    sock.SendAsync(e);
                }
                else if (e.LastOperation == SocketAsyncOperation.Send)
                {
                    // TODO: receive is not working properly
                    sock.ReceiveBufferSize = 2;
                    sock.ReceiveAsync(e);
                }
                else if (e.LastOperation == SocketAsyncOperation.Receive)
                {
                    byte[] data = new byte[e.BytesTransferred - 1];
                    Array.Copy(e.Buffer, data, e.BytesTransferred - 1);
                    string response = UTF8Encoding.UTF8.GetString(data, 0, data.Length);
                    Console.WriteLine(response);
                    sock.Close();
                }
            }
        }

        private bool sendHttp(string data)
        {
            bool successful = false;
            try
            {
                // http://blogs.msdn.com/b/silverlight_sdk/archive/2008/04/01/using-webclient-and-httpwebrequest.aspx
                Uri targetUri = new Uri((this.https ? "https://" : "http://") + this.host + "/flash-results");
                var webRequest = WebRequest.Create(targetUri);
                webRequest.ContentType = "application/x-www-form-urlencoded";
                webRequest.Method = "POST";
//                webRequest.Headers["X-TrackID"] = this.trackid;
                webRequest.BeginGetRequestStream((asyncResult) =>
                {
                    webRequest = asyncResult.AsyncState as WebRequest;
                    Stream requestStream = webRequest.EndGetRequestStream(asyncResult);
                    byte[] buf = UTF8Encoding.UTF8.GetBytes("data="+data);
                    requestStream.Write(buf, 0, buf.Length);
                    requestStream.Close();
                    webRequest.BeginGetResponse((asyncResult2) =>
                    {
                        String str = "";
                        try
                        {
                            webRequest = asyncResult2.AsyncState as WebRequest;
                            WebResponse webResponse = webRequest.EndGetResponse(asyncResult2);
                            using (StreamReader sr = new StreamReader(webResponse.GetResponseStream()))
                            {
                                str += sr.ReadToEnd();
                            }
                        }
                        catch (Exception ex1)
                        {
                            str = ex1.Message;
                        }
                        Console.Error.WriteLine(str);
                    }, webRequest);

                }, webRequest);

            }
            catch (Exception ex)
            {
                trace("sendHttp: ex=" + ex.Message);
            }
            return successful;
        }

        private void trace(string msg)
        {
            textBlock1.Text += msg + "\n";
        }
        private string readIsolatedStorage()
        {
            try
            {
                if (IsolatedStorageFile.IsEnabled)
                {
                    var userSettings = IsolatedStorageSettings.ApplicationSettings;
                    if (userSettings.Contains("trackid"))
                    {
                        string trackid;
                        if (userSettings.TryGetValue<string>("trackid", out trackid))
                        {
                            return trackid;
                        }
                    }

                }
            }
            catch (Exception ex)
            {
                trace("readIsolatedStorage: " + ex.Message);       
            }
            return "";
        }

        private void writeIsolatedStorage(string trackid)
        {
            try
            {
                if (IsolatedStorageFile.IsEnabled)
                {
                    var userSettings = IsolatedStorageSettings.ApplicationSettings;
                    userSettings["trackid"] = trackid;
                }
            }
            catch (Exception ex)
            {
                trace("writeIsolatedStorage: " + ex.Message);
            }
        }

    }
}
