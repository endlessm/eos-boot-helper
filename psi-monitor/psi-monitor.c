#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <assert.h>
#include <err.h>
#include <errno.h>
#include <limits.h>
#include <unistd.h>
#include <string.h>
#include <getopt.h>

/* Daemon parameters */
static unsigned int poll_interval = 5;
static unsigned int recovery_interval = 15;
static unsigned int mem_threshold = 40;

#define SYSRQ_TRIGGER_FILE  "/proc/sysrq-trigger"
/*
 * "/proc/pressure/memory" is memory pressure interface provided by kernel.
 * Please refer to PSI - Pressure Stall Information for more detail:
 * https://docs.kernel.org/accounting/psi.html
 */
#define PSI_MEMORY_FILE     "/proc/pressure/memory"
#define BUFSIZE             256

static bool opt_debug = false;
static const char *short_options = "m:p:r:dh";
static struct option long_options[] = {
    {"mem-threshold", 1, 0, 'm'},
    {"poll-interval", 1, 0, 'p'},
    {"recovery-interval", 1, 0, 'r'},
    {"debug", 0, 0, 'd'},
    {"help", 0, 0, 'h'},
    {0, 0, 0, 0}
};

static void usage(const char *progname) {
    printf("Usage: %s [OPTION]...\n"
           "Invoke out of memory killer on excessive memory pressure.\n"
           "\n"
           "  -m, --mem-threshold PCT\tmemory threshold percentage (default: %u)\n"
           "  -p, --poll-interval SEC\tpoll interval seconds (default: %u)\n"
           "  -r, --recovery-interval SEC\trecovery interval seconds (default: %u)\n"
           "  -d, --debug\t\t\tprint debugging messages\n"
           "  -h, --help\t\t\tdisplay this help and exit\n",
           progname, mem_threshold, poll_interval, recovery_interval);
}

static void set_mem_threshold(const char *arg) {
    long val;
    char *endptr = NULL;

    errno = 0;
    val = strtol(arg, &endptr, 10);
    if (errno != 0)
        err(1, "Invalid memory threshold value \"%s\"", arg);
    if (endptr == arg)
        errx(1, "No memory threshold value provided");
    if (val < 0)
        errx(1, "Memory threshold value cannot be negative");
    if (val > 100)
        errx(1, "Memory threshold value cannot exceed 100");
    mem_threshold = (unsigned int) val;
}

static void set_interval(unsigned int *var, const char *arg) {
    long val;
    char *endptr = NULL;

    assert(var != NULL);

    errno = 0;
    val = strtol(arg, &endptr, 10);
    if (errno != 0)
        err(1, "Invalid interval value \"%s\"", arg);
    if (endptr == arg)
        errx(1, "No interval value provided");
    if (val < 0)
        errx(1, "Interval value cannot be negative");
    if (val > UINT_MAX)
        errx(1, "Interval value cannot exceed %u", UINT_MAX);
    *var = (unsigned int) val;
}

static ssize_t fstr(const char *path, char *rbuf, const char *wbuf) {
    int fd;
    ssize_t n;

    /* one and only one operation per call */
    if ((!rbuf && !wbuf) || (rbuf && wbuf))
        return 0;

    fd = open(path, rbuf ? O_RDONLY : O_WRONLY);
    if (fd < 0)
        err(1, "%s", path);

    if (rbuf)
        n = read(fd, rbuf, BUFSIZE);
    else
        n = write(fd, wbuf, strlen(wbuf));
    if (n < 0)
        err(1, "%s", path);
    close(fd);

    if (rbuf)
        rbuf[n-1] = '\0';

    return n;
}

static void sysrq_trigger_oom() {
    fstr(SYSRQ_TRIGGER_FILE, NULL, "f");
    sleep(recovery_interval);
}

int main(int argc, char **argv) {
    while (true) {
        int c = getopt_long(argc, argv, short_options, long_options, NULL);
        if (c == -1)
            break;

        switch (c) {
        case 'm':
            set_mem_threshold(optarg);
            break;
        case 'p':
            set_interval(&poll_interval, optarg);
            break;
        case 'r':
            set_interval(&recovery_interval, optarg);
            break;
        case 'd':
            opt_debug = true;
            break;
        case 'h':
            usage(argv[0]);
            return 0;
        default:
            return 1;
        }
    }

    setvbuf(stdout, NULL, _IOLBF, 0);
    printf("poll_interval=%us, recovery_interval=%us, mem_threshold=%u%%\n",
           poll_interval, recovery_interval, mem_threshold);

    while (true) {
        int i;
        char buf[BUFSIZE];
        float full_avg10;

        fstr(PSI_MEMORY_FILE, buf, NULL);

        for (i = 0; buf[i] != '\n'; i++);
        i++; /* skip \n */
        i+=11; /* skip "full avg10=" */

        sscanf(buf+i, "%f", &full_avg10);
        if (opt_debug) printf("full_avg10=%f\n", full_avg10);

        if (full_avg10 > mem_threshold) {
            printf("Memory pressure %.1f%% above threshold limit %u%%, "
                   "killing task and pausing %u seconds for recovery\n",
                   full_avg10, mem_threshold, recovery_interval);
            sysrq_trigger_oom();
        } else {
            sleep(poll_interval);
        }
    }

    return 0;
}
