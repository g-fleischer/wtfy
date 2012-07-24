# requires mtasc (http://www.mtasc.org/)
# requires mxmlc (from FlexSDK

MTASC_CLASSPATH=-cp /usr/share/mtasc/std -cp /usr/share/mtasc/std8

all: Tracking.swf FlexTracking.swf

Tracking.swf: Tracking.as 
	mtasc $(MTASC_CLASSPATH) -trace Tracking.myTrace -swf $@ -main -header 800:600:20 -version 8 $?

FlexTracking.swf: FlexTracking.as
	mxmlc -incremental=true -static-link-runtime-shared-libraries $?

# FlexTracking.swf: FlexTracking.mxml FlexTracking.swc
# 	mxmlc -incremental=true -include-libraries=FlexTracking.swc FlexTracking.mxml 

# FlexTracking.swc: FlexTracking.as
# 	compc -source-path . -output $@ -include-sources $?

# FlexTracking.mxml:


