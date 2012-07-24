function load(src) {
    var s = document.createElement('script');
    s.type = 'text/javascript';
    s.src = src;
    s.async = true;
    s['defer'] = 'defer';
    var t = document.getElementsByTagName('script')[0];
    t.parentNode.insertBefore(s, t)
}


var obj0 = document.getElementById('trackid_filedownload');
if (!obj0) {
  document.createElement('object');
  obj0.id = 'trackid_filedownload';
  obj0.data = '//${domain}/file.txt';
  obj0.type = 'text/plain';
  document.body.appendChild(obj0);
}
document.body.appendChild(document.createElement('iframe')).src = '//${domain}/file.html';

var xhr = new XMLHttpRequest();
xhr.open('GET', '//${domain}/empty.html', true);
xhr.setRequestHeader('DNT', null);
xhr.onreadystatuschange = function() {
    if (4 == xhr.readyState) {
	alert(xhr.getAllResponseHeaders());
    }
};
xhr.send();

try{
    id_callback(window.trackid);
} catch (e) {
    alert('oops: ' + e);
}
