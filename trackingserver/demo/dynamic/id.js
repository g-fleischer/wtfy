var trackid = window.trackid = '${trackid}';
var s = document.createElement('script');
s.type = 'text/javascript';
s.src = '//${domain}/track.js';
s.async = true;
s['defer'] = 'defer';
var t = document.getElementsByTagName('script')[0];
t.parentNode.insertBefore(s, t)
