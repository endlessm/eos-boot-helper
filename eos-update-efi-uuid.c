/*
 * Copyright 2024 Endless OS Foundation LLC
 * SPDX-License-Identifier: GPL-2.0-or-later
 */

#include <efivar.h>
#include <efiboot.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stdint.h>
#include <ctype.h>
#include <err.h>
#include <errno.h>
#include <unistd.h>
#include <getopt.h>

#define LOAD_OPTION_ACTIVE              0x00000001

static bool opt_verbose = false;
static bool opt_dry_run = false;
static const char *short_options = "vnh";
static struct option long_options[] = {
  {"verbose", 0, 0, 'v'},
  {"dry-run", 0, 0, 'n'},
  {"help", 0, 0, 'h'},
  {0, 0, 0, 0}
};

/* This and the cleanup_free macro are ripped off from g_autofree. */
static void
_cleanup_free (void *pp)
{
  void *p = *(void **)pp;
  free (p);
}

#define cleanup_free __attribute__ ((cleanup (_cleanup_free)))

/* Check if an EFI variable is a BootXXXX load option. */
static bool
is_load_option (const efi_guid_t *guid, const char *name)
{
  if (guid == NULL || name == NULL)
    {
      warnx ("%s: guid or name is NULL", __func__);
      return false;
    }

  /* Check that this is a global EFI variable. */
  if (memcmp (guid, &efi_guid_global, sizeof (efi_guid_t)) != 0)
    return false;

  /* Check that the name matches BootXXXX. */
  if (strlen (name) != 8 ||
      strncmp (name, "Boot", 4) != 0 ||
      isxdigit (name[4]) == 0 ||
      isxdigit (name[5]) == 0 ||
      isxdigit (name[6]) == 0 ||
      isxdigit (name[7]) == 0)
    return false;

  return true;
}

/* Read an EFI variable and parse it into an efi_load_option when appropriate.
 * Returns false if the variable is not a load option.
 */
static bool
read_load_option (const efi_guid_t  *guid,
                  const char        *name,
                  efi_load_option  **out_opt,
                  size_t            *out_opt_size,
                  uint32_t          *out_attributes)
{
  if (guid == NULL || name == NULL)
    {
      errno = EINVAL;
      warnx ("%s: guid or name is NULL", __func__);
      return false;
    }

  cleanup_free uint8_t *data = NULL;
  size_t data_size = 0;
  uint32_t attributes = 0;
  if (efi_get_variable (*guid, name, &data, &data_size, &attributes) < 0)
    {
      warn ("efi_get_variable");
      return false;
    }

  efi_load_option *opt = (efi_load_option *)data;
  if (!efi_loadopt_is_valid (opt, data_size))
    {
      errno = EINVAL;
      warn ("efi_loadopt_is_valid");
      return false;
    }

  if (out_opt)
    {
      *out_opt = opt;
      data = NULL;
    }
  if (out_opt_size)
    *out_opt_size = data_size;
  if (out_attributes)
    *out_attributes = attributes;

  return true;
}

/* A very minimal hexdump. */
static void
hexdump (const uint8_t *data, size_t size)
{
  const uint8_t *cur;
  size_t offset;

  for (cur = data, offset = 0; offset < size; cur++, offset++)
    {
      const char *prefix;

      if (offset % 16 == 0)
        prefix = offset == 0 ? "" : "\n";
      else if (offset % 8 == 0)
        prefix = "  ";
      else
        prefix = " ";

      printf ("%s%.2x", prefix, *cur);
    }

  putchar ('\n');
}

/* Check if an EFI load option matches a partition UUID. */
static bool
load_option_matches_partition (efi_load_option *opt,
                               size_t           opt_size,
                               efi_guid_t      *part_uuid)
{
  if (opt == NULL || part_uuid == NULL)
    {
      errno = EINVAL;
      warnx ("%s: opt or part_uuid is NULL", __func__);
      return false;
    }

  efidp dp = efi_loadopt_path (opt, opt_size);
  if (dp == NULL)
    {
      errno = EINVAL;
      warn ("efi_loadopt_path");
      return false;
    }

  /* Only Hard Drive Media Device Paths are supported. */
  if (efidp_type (dp) != EFIDP_MEDIA_TYPE ||
      efidp_subtype (dp) != EFIDP_MEDIA_HD)
    return false;

  /* Only GPT formatted hard drives with UUID signatures are supported. */
  efidp_hd *hd = (efidp_hd *)dp;
  if (hd->format != EFIDP_HD_FORMAT_GPT ||
      hd->signature_type != EFIDP_HD_SIGNATURE_GUID)
    return false;

  if (memcmp (hd->signature, part_uuid, sizeof (efi_guid_t)) != 0)
    return false;

  return true;
}

/* Dump a load option to stdout. A single line summary similar to efibootmgr is
 * provided followed by a hexdump of the load option.
 */
static bool
dump_load_option (const char      *name,
                  efi_load_option *opt,
                  size_t           opt_size)
{
  if (name == NULL || opt == NULL)
    {
      errno = EINVAL;
      warnx ("%s: name or opt is NULL", __func__);
      return false;
    }

  const unsigned char *desc = efi_loadopt_desc (opt, opt_size);

  efidp dp = efi_loadopt_path (opt, opt_size);
  if (dp == NULL)
    {
      errno = EINVAL;
      warn ("efi_loadopt_path");
      return false;
    }

  uint16_t dp_len = efi_loadopt_pathlen (opt, opt_size);
  if (dp <= 0)
    {
      errno = EINVAL;
      warn ("efi_loadopt_pathlen");
      return false;
    }

  ssize_t len = efidp_format_device_path (NULL, 0, dp, dp_len);
  if (len < 0)
    {
      errno = EINVAL;
      warn ("efi_format_device_path");
      return false;
    }

  size_t path_len = len + 1;
  cleanup_free unsigned char *path = calloc (path_len, sizeof (char));
  if (path == NULL)
    return false;

  len = efidp_format_device_path (path, path_len, dp, dp_len);
  if (len < 0)
    {
      errno = EINVAL;
      warn ("efi_format_device_path");
      return false;
    }

  printf ("%s: %s%s %s\n",
          name,
          (efi_loadopt_attrs(opt) & LOAD_OPTION_ACTIVE) ? "* " : "",
          desc,
          path);

  hexdump ((const uint8_t *)opt, opt_size);

  return true;
}

static bool
update_load_option_partition (efi_load_option *opt,
                              size_t           opt_size,
                              efi_guid_t      *part_uuid)
{
  if (opt == NULL || part_uuid == NULL)
    {
      errno = EINVAL;
      warnx ("%s: opt or part_uuid is NULL", __func__);
      return false;
    }

  efidp dp = efi_loadopt_path (opt, opt_size);
  if (dp == NULL)
    {
      errno = EINVAL;
      warn ("efi_loadopt_path");
      return false;
    }

  /* Make sure this is a Hard Drive Media Device Path before updating. */
  if (efidp_type (dp) != EFIDP_MEDIA_TYPE ||
      efidp_subtype (dp) != EFIDP_MEDIA_HD)
    {
      errno = EINVAL;
      warnx ("Only Hard Drive Media Device Paths can be updated");
      return false;
    }

  /* Make sure this is a GPT formatted drive with a UUID signature. */
  efidp_hd *hd = (efidp_hd *)dp;
  if (hd->format != EFIDP_HD_FORMAT_GPT ||
      hd->signature_type != EFIDP_HD_SIGNATURE_GUID)
    {
      errno = EINVAL;
      warnx ("Only GPT formatted hard drives with UUID signatures can be updated");
      return false;
    }

  /* Finally, update the signature UUID. */
  memmove (hd->signature, part_uuid, sizeof (efi_guid_t));

  return true;
}

static void
usage (const char *progname)
{
  printf ("Usage: %s [OPTION]... CUR_UUID NEW_UUID\n"
          "\n"
          "Update all BootXXXX options using partition CUR_UUID to NEW_UUID.\n"
          "\n"
          "  -v, --verbose\tprint verbose messages\n"
          "  -n, --dry-run\tonly show what would be done\n"
          "  -h, --help\tdisplay this help and exit\n",
          progname);
}

int
main (int argc, char *argv[])
{
  while (true)
    {
      int opt = getopt_long (argc, argv, short_options, long_options, NULL);
      if (opt == -1)
        break;

      switch (opt)
        {
          case 'v':
            opt_verbose = true;
            break;
          case 'n':
            opt_dry_run = true;
            break;
          case 'h':
            usage (argv[0]);
            return 0;
          default:
            return 1;
        }
    }

  argc -= optind;
  argv += optind;
  if (argc < 2)
    errx (EXIT_FAILURE, "No partition UUIDs supplied");

  const char *cur_part_uuid_str = argv[0];
  efi_guid_t cur_part_uuid = { 0 };
  if (efi_str_to_guid (cur_part_uuid_str, &cur_part_uuid) < 0)
    errx (EXIT_FAILURE, "Invalid partition UUID \"%s\"", cur_part_uuid_str);

  const char *new_part_uuid_str = argv[1];
  efi_guid_t new_part_uuid = { 0 };
  if (efi_str_to_guid (new_part_uuid_str, &new_part_uuid) < 0)
    errx (EXIT_FAILURE, "Invalid partition UUID \"%s\"", new_part_uuid_str);

  /* Iterate all EFI variables looking for load options to update. */
  while (true)
    {
      efi_guid_t *guid = NULL;
      char *name = NULL;
      int ret = efi_get_next_variable_name (&guid, &name);
      if (ret < 0)
        err (EXIT_FAILURE, "Getting next EFI variable");
      else if (ret == 0)
        break;

      if (guid == NULL || name == NULL)
        errx (EXIT_FAILURE, "efi_get_next_variable_name returned NULL guid or name");

      if (!is_load_option (guid, name))
        {
          if (opt_verbose)
            printf ("Variable %s is not a load option\n", name);
          continue;
        }

      cleanup_free efi_load_option *opt = NULL;
      size_t opt_size = 0;
      uint32_t attributes = 0;
      if (!read_load_option (guid, name, &opt, &opt_size, &attributes))
        err (EXIT_FAILURE, "Reading load option %s", name);

      errno = 0;
      if (!load_option_matches_partition (opt, opt_size, &cur_part_uuid))
        {
          if (errno != 0)
            err (EXIT_FAILURE, "Matching load option %s partition", name);
          if (opt_verbose)
            printf ("Load option %s does not match partition %s\n",
                    name, cur_part_uuid_str);
          continue;
        }

      if (opt_verbose && !dump_load_option (name, opt, opt_size))
        err (EXIT_FAILURE, "Dump load option %s", name);

      if (!update_load_option_partition (opt, opt_size, &new_part_uuid))
        err (EXIT_FAILURE, "Updating load option %s partition", name);

      if (opt_verbose && !dump_load_option (name, opt, opt_size))
        err (EXIT_FAILURE, "Dump load option %s", name);

      printf ("Updating %s HD UUID from %s to %s\n",
              name, cur_part_uuid_str, new_part_uuid_str);
      if (!opt_dry_run)
        if (efi_set_variable (*guid, name, (uint8_t *)opt, opt_size, attributes, 0644) < 0)
          err (EXIT_FAILURE, "Setting load option %s", name);
    }

  return 0;
}
