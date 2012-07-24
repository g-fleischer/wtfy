function do_read(persitsent) {
    process("read", persistent);
}

function do_write(persistent, tid) {
    process("write", persistent, tid);
}

function test() {
    var xsize = -1;
    window.webkitStorageInfo.requestQuota(
	PERSISTENT, xsize, 
	function(grantedBytes) {
	}
    );
}

function test_persistent_negative() {
    var xsize = -1;
    window.webkitStorageInfo.requestQuota(
	PERSISTENT, xsize, function(grantedBytes) {
	    log('persistent with negative quota granted: ' + grantedBytes);
	    window.window.webkitRequestFileSystem(
		PERSISTENT, grantedBytes, 
		function(fs)  {
		    log('working on file: ' + fs.name);
		}, errorHandler);
	}, function(e){ log('permanent with negative request failed with: ' + e.code);});
}

function test_temporary() {
    var size = 1024*1024;
    window.window.webkitRequestFileSystem(
	TEMPORARY, size, 
	function(fs)  {
	    log('working on file: ' + fs.name);
	}, function(e){ log('temporay request failed with: ' + e.code);}
    );
}

function do_operation(file_type, size, mode, tid) {
    if ('webkitRequestFileSystem' in window) {
	window.window.webkitRequestFileSystem(file_type, size, function(fs) { 
	    log('Opened file system: ' + fs.name);
	    if ("read" == mode) {
		fs.root.getFile('track.txt', {}, function(fileEntry) {
		    log(fileEntry.toURL());
		    fileEntry.file(function(file) {
			var reader = new FileReader();
			reader.onloadend = function(e) {
			    var txtArea = document.createElement('textarea');
			    txtArea.value = this.result;
			    document.body.appendChild(txtArea);
			};
			reader.readAsText(file);
		    }, errorHandler);
		}, errorHandler);
	    }
	    if ("write" == mode) {
		fs.root.getFile('track.txt', {create: true}, function(fileEntry) {
		    log(fileEntry.toURL());
		    fileEntry.createWriter(function(fileWriter) {
			fileWriter.onwriteend = function(e) {
			    log('Write completed.');
			};

			fileWriter.onerror = function(e) {
			    log('Write failed: ' + e.toString());
			};
			var bb = new WebKitBlobBuilder();
			bb.append(
			    JSON.stringify({'tid': tid, 'datetime' : (new Date()).toGMTString()})
			);
			fileWriter.write(bb.getBlob('text/plain'));
		    }, errorHandler);
		}, errorHandler);
	    }
	}, errorHandler);
    }
}
function process(mode, persistent, tid) {
    if (!persistent) {
	var file_type = window.TEMPORARY;
	var size = 1024*1024;
	do_operation(file_type, size, mode, tid);
    } else {
	var file_type = window.PERSISTENT;
	var xsize = -1;
	window.webkitStorageInfo.requestQuota(
	    file_type, xsize, function(grantedBytes) {
		log('persistent with negative quota granted: ' + grantedBytes);
		do_operation(file_type, grantedBytes, mode, tid);
	    }, function(e){ log('permanent with negative request failed with: ' + e.code);});
    }

}
function errorHandler(e) {
    log('got error: ' + e.code);
    for(p in e){log(p + ":" + e[p])}
}
