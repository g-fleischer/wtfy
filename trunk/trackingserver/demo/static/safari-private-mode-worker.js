(function()
 {
     var original;
     self.addEventListener("message", function(e) {
	     var data = e.data;
	     if ("set-cookie" == data.cmd) {
		 original = data.msg;
	     } else if ("get-cookie" == data.cmd) {
		 self.postMessage({cmd : 'cookie' , msg : original});
	     }
	 }
 }
 )()