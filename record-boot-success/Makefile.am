recordbootsuccessdir = $(libexecdir)/record-boot-success
dist_recordbootsuccess_SCRIPTS = \
	record-boot-success \
	$(NULL)

dist_systemdunit_DATA = \
	record-boot-success.service \
	$(NULL)

dist_systembusservices_DATA = \
	com.endlessm.RecordBootSuccess.service \
	$(NULL)

dist_dbussystemconfig_DATA = \
	com.endlessm.RecordBootSuccess.conf \
	$(NULL)

xdgautostartdir = $(sysconfdir)/xdg/autostart
dist_xdgautostart_DATA = \
	record-boot-success.desktop \
	$(NULL)

gdmgreeterautostartdir = $(prefix)/share/gdm/greeter/autostart
dist_gdmgreeterautostart_DATA = \
	record-boot-success.desktop \
	$(NULL)
