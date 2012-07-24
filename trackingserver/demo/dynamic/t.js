(function() {
 var h = "//${domain}/"; 
 function cb(n,a) {var o = document.createElement(n);for (var p in a) {o[p]=a[p]};return document.body.appendChild(o);};
 var f = cb("iframe", {src:h+"id.html",width:1,height:1,frameBorder:0,style:"border:0;position:absolute;left:-10px;top:-10px"});
 alert("it worked: " + f);
})();
