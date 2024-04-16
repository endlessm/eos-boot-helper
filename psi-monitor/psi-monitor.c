#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <err.h>
#include <unistd.h>
#include <string.h>
#include <getopt.h>

/* Daemon parameters */
#define POLL_INTERVAL       5
#define RECOVERY_INTERVAL  15
#define MEM_THRESHOLD      10

#define SYSRQ_TRIGGER_FILE  "/proc/sysrq-trigger"
#define PSI_MEMORY_FILE     "/proc/pressure/memory"
#define BUFSIZE             256

static bool opt_debug = false;
static const char *short_options = "dh";
static struct option long_options[] = {
    {"debug", 0, 0, 'd'},
    {"help", 0, 0, 'h'},
    {0, 0, 0, 0}
};

static void usage(const char *progname) {
    printf("Usage: %s [OPTION]...\n"
           "Invoke out of memory killer on excessive memory pressure.\n"
           "\n"
           "  -d, --debug\tprint debugging messages\n"
           "  -h, --help\tdisplay this help and exit\n",
           progname);
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
    sleep(RECOVERY_INTERVAL);
}

int main(int argc, char **argv) {
    while (true) {
        int c = getopt_long(argc, argv, short_options, long_options, NULL);
        if (c == -1)
            break;

        switch (c) {
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
    printf("poll_interval=%ds, recovery_interval=%ds, stall_threshold=%d%%\n",
           POLL_INTERVAL, RECOVERY_INTERVAL, MEM_THRESHOLD);

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

        if (full_avg10 > MEM_THRESHOLD) {
            printf("Memory pressure %.1f%% above threshold limit %d%%, "
                   "killing task and pausing %d seconds for recovery\n",
                   full_avg10, MEM_THRESHOLD, RECOVERY_INTERVAL);
            sysrq_trigger_oom();
        } else {
            sleep(POLL_INTERVAL);
        }
    }

    return 0;
}
