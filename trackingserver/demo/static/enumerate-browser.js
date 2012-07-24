var __all_objects = {};
var __max_depth = 5;

function __enumerate() {
    __walk('window', window, 0);
}
function __report(type, name) {
    // # TODO:
    if ('object' == type)
    __log(name + ":" + type);
}

function __walk(name, obj, depth) {
    if (depth > __max_depth) {
	return;
    }
    //    log(name);
    var props = [];
    try {
	for (var prop in obj) {
	    if (("prototype" != prop) && ("__" != prop.substring(0,2))) {
		props.push(prop);
	    }
	}
    } catch(e) {}
	
    for (var i = 0; i < props.length; ++i) {
	var prop = props[i];
	var v = null;
	try {
	    v = obj[prop];
	} catch(e) {}
	if (v != null) {
	    var pname = name + '[\"' + prop + '\"]';
	    var t = typeof(v);
	    if ('function' == t) {
		__report('function', pname);
	    } else if ('object' == t) {
		if (v != self && v != document) {
		    __report('object', pname);
		    var exclude = true;
		    try {
			exclude = (depth > __max_depth) || (('length' in v)&&('item' in v));
			if (v in __all_objects) {
			    exclude = true;
			} else {
			    __all_objects[obj] = true;
			}
		    } catch (e) {
			__log("bad obj: " + pname + ": (" + e + ")");
		    }
		    if (!exclude) {
			__walk(pname, v, depth + 1);
		    }
		}
	    } else {
		__report(t, pname);
		//		log(name + '.' + prop + ': ' + v);
	    }
	}
    }
}
