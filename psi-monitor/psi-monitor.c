#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <err.h>
#include <unistd.h>
#include <string.h>

#define DEBUG false

/* Daemon parameters */
#define POLL_INTERVAL       5
#define RECOVERY_INTERVAL  15
#define MEM_THRESHOLD      10

#define SYSRQ_FILE          "/proc/sys/kernel/sysrq"
#define SYSRQ_TRIGGER_FILE  "/proc/sysrq-trigger"
#define PSI_MEMORY_FILE     "/proc/pressure/memory"
#define SYSRQ_MASK          0x40
#define BUFSIZE             256

static void sysrq_trigger_oom() {
    int fd;
    ssize_t n;

    printf("Above threshold limit, killing task and pausing for recovery\n");

    fd = open(SYSRQ_TRIGGER_FILE, O_WRONLY);
    if (fd < 0)
        err(1, "%s", SYSRQ_TRIGGER_FILE);
    n = write(fd, "f", strlen("f"));
    if (n < 0)
        err(1, "%s", SYSRQ_TRIGGER_FILE);
    close(fd);
    sleep(RECOVERY_INTERVAL);
}

static void sysrq_enable_oom() {
    int fd, sysrq;
    ssize_t n;
    char buf[BUFSIZE];

    fd = open(SYSRQ_FILE, O_RDONLY);
    if (fd < 0)
        err(1, "%s", SYSRQ_FILE);
    n = read(fd, buf, BUFSIZE);
    if (n < 0)
        err(1, "%s", SYSRQ_FILE);
    close(fd);
    buf[n-1] = '\0';

    sysrq = atoi(buf);
    sysrq |= SYSRQ_MASK;
    snprintf(buf, BUFSIZE, "%d", sysrq);
    fd = open(SYSRQ_FILE, O_WRONLY);
    if (fd < 0)
        err(1, "%s", SYSRQ_FILE);
    n = write(fd, buf, strlen(buf));
    if (n < 0)
        err(1, "%s", SYSRQ_FILE);
    close(fd);
}

int main(int argc, char **argv) {
    printf("poll_interval=%ds, recovery_interval=%ds, stall_threshold=%d%%\n",
           POLL_INTERVAL, RECOVERY_INTERVAL, MEM_THRESHOLD);

    sysrq_enable_oom();

    while (true) {
        int fd, i;
        ssize_t n;
        char buf[BUFSIZE];
        float full_avg10;

        fd = open(PSI_MEMORY_FILE, O_RDONLY);
        if (fd < 0)
            err(1, "%s", PSI_MEMORY_FILE);
        n = read(fd, buf, BUFSIZE);
        if (n < 0)
            err(1, "%s", PSI_MEMORY_FILE);
        close(fd);
        buf[n-1] = '\0';

        for (i = 0; buf[i] != '\n'; i++);
        i++; /* skip \n */
        i+=11; /* skip "full avg10=" */
        sscanf(buf+i, "%f", &full_avg10);
        if (DEBUG) printf("full_avg10=%f\n", full_avg10);

        if (full_avg10 > MEM_THRESHOLD)
            sysrq_trigger_oom();
        else
            sleep(POLL_INTERVAL);
    }

    return 0;
}
