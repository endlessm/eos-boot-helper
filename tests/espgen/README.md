Test data directory for use with `test_esp_generator.py`. The data here is
created by running `eos-esp-generator` in gather mode. The easiest way to do
that is to install it as
`/etc/systemd/system-generators/eos-esp-generator-gather`.

Reboot so that it runs as an early boot generator. After booting, run it again
as a generator by calling `systemctl daemon-reload`. There will then be 2
tarballs at `/run/espgen-data-*.tar.gz`. Unpack the tarballs and add the data
files to this directory with a semi-descriptive prefix. The `mounts.json` and
`partitions.json` data files should be differentiated by adding `-init` or
`-reload` suffixes as appropriate. The `fstab.json` and `kcmdline.json` files
don't need to be differentiated as they won't change between the 2 executions
of the generator.

Finally, wire up the data in the `ESP_MOUNT_TEST_DATA` dictionary in
`test_esp_generator.py`. The key is the prefix added to the data files above.
