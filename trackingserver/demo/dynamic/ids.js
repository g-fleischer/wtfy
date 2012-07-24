// global variable
var tracking_id = "${trackid}";

// functional approach
function get_tracking_id(){return "${trackid}";}

// callback approach
(function() {if('undefined'!=typeof(tracking_id_callback)){tracking_id_callback("${trackid}")}})();