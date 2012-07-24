
function do_tracker_1(tracking_id) {
    var exists = false;
    try {
	var name = "tracking_id1";
	if ('undefined' != typeof(global[name])) {
	    return global[name];
	} else {
	    global[name] = tracking_id;
	    global.setPersistent(name, true);
	    app.alert("setting tracking_id: [" + global[name] + "]");
	    return null;
	}
    } catch (e) {
	app.alert("error: setting storage: " + e);
    }
}

function do_tracker_2(tracking_id) {
    var exists = false;
    try {
	if ('undefined' != typeof(global.tracking_id2)) {
	    exists = true;
	    return global.tracking_id2;
	}
    } catch (e) {
        try { delete global.tracking_id2; } catch (e) {}
    }
    try {
	if (!exists) {
	    global.tracking_id2 = tracking_id;
	    global.setPersistent("tracking_id", true);
	    app.alert("setting tracking_id: [" + global.tracking_id2 + "]");
	    return null;
	}
    } catch (e) {
	app.alert("error: setting storage: " + e);
    }
}

function init() {
    try {
	var tracking_id = "${trackid}";
	var found1 = do_tracker_1(tracking_id);
	if (found1) {
	    tracking_id = found1;
	}
	var found2 = do_tracker_2(tracking_id);
	if (found1 || found2) {
	    app.alert("found tracking_id: [" + found1 + "], [" + found2 + "]");
	}
    } catch (e) {
	app.alert("error ===> " + e);
    }
}

init();