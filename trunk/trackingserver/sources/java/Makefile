all: Tracking.jar

Tracking.jar: Tracking.class
	jar cvmf Tracking.manifest $@ $?

Tracking.class: Tracking.java
	javac -cp MRJPlugin.jar -source 1.5 -target 1.5 $?

