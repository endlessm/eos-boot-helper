#include <glib.h>
#include <udisks/udisks.h>

#define FILE_READ_CHUNK_SIZE (1024 * 256)
#define CHECKSUM_SIZE 64 /* SHA256 */
#define WISTRON_PATH "/var/wistron"
#define WISTRON_TEST_SUITE_START WISTRON_PATH "/start.sh"
#define WISTRON_TEST_SUITE_TAR "Wistron_Factory_Test.tar"

static UDisksClient *client = NULL;
static GDBusObjectManager *manager;

static void
check_home_dir(void)
{
	/* If a home directory has appeared, we're not in the factory any more,
	 * so abort. */
	GDir *home = g_dir_open("/home", 0, NULL);
	if (home) {
		const char *ent = g_dir_read_name(home);
		if (ent) {
			g_message("Home directory found - bailing.");
			_exit(0);
		}
		g_dir_close(home);
	}
}

static void
try_exec_test_suite(void)
{
	check_home_dir();

	if (!g_file_test(WISTRON_TEST_SUITE_START, G_FILE_TEST_IS_EXECUTABLE))
		return;

	g_message("Test suite found - loading");
	execl("/bin/systemctl", "systemctl", "isolate", "eos-factory-test.target",
		  NULL);
	g_critical("Failed to execute systemctl :(");
	_exit(1);
}

static UDisksObject *
get_object_by_path(const char *path)
{
	GDBusObject *object = g_dbus_object_manager_get_object(manager, path);
	if (!object)
		return NULL;

	return UDISKS_OBJECT(object);
}

static gboolean
read_checksum(GFile *mount, char **out_checksum)
{
	GFile *checksum_file;
	GError *err = NULL;
	gsize length;
	gboolean ret;

	checksum_file = g_file_get_child(mount, WISTRON_TEST_SUITE_TAR ".sha256");
	ret = g_file_load_contents(checksum_file, NULL, out_checksum, &length,
							   NULL, &err);
	g_object_unref(checksum_file);
	if (!ret) {
		g_warning("Failed to read checksum: %s", err->message);
		g_error_free(err);
		return FALSE;
	}

	if (length < CHECKSUM_SIZE) {
		g_warning("Short checksum read: %zu bytes", length);
		g_free(*out_checksum);
		*out_checksum = NULL;
		return FALSE;
	}

	(*out_checksum)[CHECKSUM_SIZE] = 0; /* NULL-terminate */
	g_message("Read reference checksum: %s", *out_checksum);

	return TRUE;
}

static GFile *
copy_test_suite(GFile *mount)
{
	GFile *wistron_dir = g_file_new_for_path(WISTRON_PATH);
	GFile *src_file = g_file_get_child(mount, WISTRON_TEST_SUITE_TAR);
	GFile *dst_file;
	GError *err = NULL;
	gboolean ret;

	g_message("Copying test suite to %s", WISTRON_PATH);
	g_file_make_directory_with_parents(wistron_dir, NULL, NULL);
	dst_file = g_file_get_child(wistron_dir, WISTRON_TEST_SUITE_TAR);
	ret = g_file_copy(src_file, dst_file, G_FILE_COPY_OVERWRITE, NULL, NULL,
					  NULL, &err);
	g_object_unref(src_file);
	g_object_unref(wistron_dir);
	if (!ret) {
		g_warning("Failed to copy test suite: %s", err->message);
		g_error_free(err);
		g_object_unref(dst_file);
		return NULL;
	}

	return dst_file;
}

static gboolean
verify_checksum(GFile *test_suite, const char *checksum_cmp)
{
	GChecksum *checksum = g_checksum_new(G_CHECKSUM_SHA256);
	GInputStream *input_stream;
	GError *err = NULL;
	unsigned char *buf;
	gssize bytes_read;
	gboolean ret = FALSE;
	const char *checksum_calc;

	input_stream = G_INPUT_STREAM(g_file_read(test_suite, NULL, &err));
	if (!input_stream) {
		g_warning("Failed to open test suite: %s", err->message);
		g_error_free(err);
		goto out;
	}

	buf = g_malloc(FILE_READ_CHUNK_SIZE);
	do {
		bytes_read = g_input_stream_read(input_stream, buf,
										 FILE_READ_CHUNK_SIZE, NULL, &err);
		if (bytes_read > 0) {
			g_checksum_update(checksum, buf, bytes_read);
		} else if (bytes_read < 0) {
			g_warning("Error reading test suite: %s", err->message);
			g_error_free(err);
		}
	} while (bytes_read > 0);
	g_object_unref(input_stream);
	g_free(buf);

	if (bytes_read < 0)
		goto out;

	checksum_calc = g_checksum_get_string(checksum);
	g_message("Calculated checksum %s", checksum_calc);
	ret = strcmp(checksum_calc, checksum_cmp) == 0;
	if (!ret)
		g_warning("Checksum mismatch!");

out:
	g_checksum_free(checksum);
	return ret;
}

static gboolean
extract_test_suite(GFile *test_suite)
{
	gchar *standard_output;
	gchar *standard_error;
	GError *err = NULL;
	char *cmdline;
	char *test_suite_path = g_file_get_path(test_suite);
	int exitcode;
	gboolean ret;

	cmdline = g_strdup_printf("tar -C %s -xf %s",
							  WISTRON_PATH, test_suite_path);
	g_free(test_suite_path);

	g_message("Spawning: %s", cmdline);
	ret = g_spawn_command_line_sync(cmdline, &standard_output, &standard_error,
									&exitcode, &err);
	g_free(cmdline);
	g_free(standard_output);
	if (!ret) {
		g_warning("tar exec failed: %s", err->message);
		goto error;
	}

	if (!g_spawn_check_exit_status(exitcode, &err)) {
		g_warning("tar error: %s", err->message);
		g_printerr("%s", standard_error);
		goto error;
	}

	g_message("Extract complete");
	return TRUE;

error:
	g_error_free(err);
	g_free(standard_error);
	return FALSE;
}

static void
check_mount(UDisksFilesystem *fs, const char *mount_path)
{
	GFile *mount = g_file_new_for_path(mount_path);
	GFile *test_suite = NULL;
	char *checksum = NULL;
	GVariant *opts;
	GVariantDict dict;
	gboolean unmounted = FALSE;

	/* opts for unmount */
	g_variant_dict_init(&dict, NULL);
	opts = g_variant_dict_end(&dict);

	if (!read_checksum(mount, &checksum))
		goto out;

	test_suite = copy_test_suite(mount);
	if (!test_suite)
		goto out;

	/* Won't be using the mount any more. */
	udisks_filesystem_call_unmount_sync(fs, opts, NULL, NULL);
	unmounted = TRUE;

	if (!verify_checksum(test_suite, checksum))
		goto out;

	if (!extract_test_suite(test_suite))
		goto out;

	/* Delete tarball which has now been extracted */
	g_file_delete(test_suite, NULL, NULL);

	try_exec_test_suite();

out:
	if (!unmounted)
		udisks_filesystem_call_unmount_sync(fs, opts, NULL, NULL);
	if (test_suite)
		g_object_unref(test_suite);
	g_object_unref(mount);
	g_free(checksum);
}


static void
mount_fs(UDisksFilesystem *fs)
{
	gchar *mount_path;
	GError *err = NULL;
	gboolean ret;
	GVariantDict dict;
	GVariant *opts;

	g_message("Mounting");

	g_variant_dict_init(&dict, NULL);
	g_variant_dict_insert(&dict, "options", "s", "ro");
	opts = g_variant_dict_end(&dict);

	ret = udisks_filesystem_call_mount_sync(fs, opts, &mount_path, NULL, &err);
	if (!ret) {
		g_warning("Failed to mount: %s", err->message);
		return;
	}

	g_message("Mounted at %s", mount_path);
	check_mount(fs, mount_path);
	g_free(mount_path);

	/* unmount happens in check_mount call above */
}

static void
check_udisks_object(UDisksObject *object)
{
	UDisksFilesystem *fs;
	UDisksBlock *block;
	UDisksObject *drive_proxy;
	UDisksDrive *drive;
	const char * const * mount_points;
	const char *drive_path;
	gboolean removable;

	g_debug("checking %s",
			g_dbus_object_get_object_path(G_DBUS_OBJECT(object)));
	fs = udisks_object_get_filesystem(object);
	if (!fs) {
		g_debug("not a filesystem");
		return;
	}

	mount_points = udisks_filesystem_get_mount_points(fs);
	if (g_strv_length((gchar **) mount_points) > 0) {
		g_debug("already mounted");
		goto out;
	}

	block = udisks_object_get_block(object);
	if (!block) {
		g_debug("no block device");
		goto out;
	}

	drive_path = udisks_block_get_drive(block);
	g_debug("got drive %s", drive_path);
	drive_proxy = get_object_by_path(drive_path);
	g_object_unref(block);
	if (!drive_proxy) {
		g_debug("failed to get proxy for %s", drive_path);
		goto out;
	}

	drive = udisks_object_get_drive(drive_proxy);
	g_object_unref(drive_proxy);
	if (!drive) {
		g_debug("failed to get drive object\n");
		goto out;
	}

	removable = udisks_drive_get_removable(drive);
	g_object_unref(drive);
	if (!removable) {
		g_debug("not removable, ignoring");
		goto out;
	}

	mount_fs(fs);

out:
	g_object_unref(fs);
}

static void
find_drives(void)
{
	GList *objects = g_dbus_object_manager_get_objects(manager);
	GList *item;

	for (item = objects; item; item = item->next) {
		UDisksObject *object = UDISKS_OBJECT(item->data);
		check_udisks_object(object);
	}

	g_list_free_full(objects, g_object_unref);
}

static void
udisks_object_added(GDBusObjectManager *manager, GDBusObject *object,
					gpointer user_data)
{
	check_home_dir();
	check_udisks_object(UDISKS_OBJECT(object));
}

int
main(void)
{
	GList *volumes;
	GList *drives;
	GMainLoop *loop = g_main_loop_new(NULL, FALSE);
	GError *err = NULL;

	client = udisks_client_new_sync(NULL, &err);
	if (client == NULL) {
		g_printerr("Error connecting to udisks: %s\n", err->message);
		g_error_free(err);
		goto out;
	}

	manager = udisks_client_get_object_manager(client);
	find_drives();
	try_exec_test_suite();

	g_signal_connect(manager, "object-added", G_CALLBACK(udisks_object_added),
					 NULL);

	g_message("Waiting for storage devices");
	g_debug("Start main loop");
	g_main_loop_run(loop);
	g_debug("Main loop exited");

out:
	if (client)
		g_object_unref(client);

	g_main_loop_unref(loop);
	return 0;
}
