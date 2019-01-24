#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <linux/fb.h>
#include <linux/kd.h>

#define FBDEV "/dev/fb0"
#define TTYDEV "/dev/tty0"

int main(int argc, char **argv) {
    int ret = 0, fb_fd = -1, tty_fd = -1, tty_mode;
    uint8_t *fbp = MAP_FAILED;
    size_t screensize, bytes_per_pixel;
    struct fb_var_screeninfo vinfo;

    tty_fd = open(TTYDEV, O_RDWR);
    if (tty_fd == -1) {
        perror("Failed to open " TTYDEV);
        ret = errno;
        goto exit;
    }

    if (ioctl(tty_fd, KDGETMODE, &tty_mode) == -1) {
        perror("KDGETMODE failed on " TTYDEV);
        ret = errno;
        goto exit;
    }

    if (tty_mode == KD_TEXT) {
        printf("VT is in text mode, exiting");
        goto exit;
    }

    fb_fd = open(FBDEV, O_RDWR);
    if (fb_fd == -1) {
        perror("Failed to open " FBDEV);
        ret = errno;
        goto exit;
    }

    if (ioctl(fb_fd, FBIOGET_VSCREENINFO, &vinfo) == -1) {
        perror("FBIOGET_VSCREENINFO failed on " FBDEV);
        ret = errno;
        goto exit;
    }

    bytes_per_pixel = vinfo.bits_per_pixel / 8;
    screensize = vinfo.xres * vinfo.yres * bytes_per_pixel;

    fbp = mmap(NULL, screensize, PROT_WRITE, MAP_SHARED, fb_fd, (off_t) 0);
    if (fbp == MAP_FAILED) {
        perror("Failed to mmap " FBDEV);
        ret = errno;
        goto exit;
    }

    memset(fbp, 0, screensize);
    printf("Cleared %s", FBDEV);

exit:
    if (fbp != MAP_FAILED)
        munmap(fbp, screensize);

    if (fb_fd != -1)
        close(fb_fd);

    if (tty_fd != -1)
        close(tty_fd);

    return ret;
}
