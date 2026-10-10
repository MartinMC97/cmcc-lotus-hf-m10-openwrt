// SPDX-License-Identifier: MIT
/* Short, RAM-only software-PWM diagnostic for a verified Lotus Mini GPIO LED. */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define PERIOD_US 10000L
#define STEPS_PER_CYCLE 300
#define CYCLES 3

static volatile sig_atomic_t interrupted;

static void stop_on_signal(int signum)
{
    (void)signum;
    interrupted = 1;
}

static int set_led(int fd, int on)
{
    const char *value = on ? "1\n" : "0\n";
    return pwrite(fd, value, 2, 0) == 2 ? 0 : -1;
}

static void delay_us(long us)
{
    struct timespec remaining = { .tv_sec = us / 1000000L,
                                  .tv_nsec = (us % 1000000L) * 1000L };
    while (!interrupted && nanosleep(&remaining, &remaining) < 0 && errno == EINTR)
        ;
}

int main(int argc, char **argv)
{
    char path[128];
    struct sigaction action = { .sa_handler = stop_on_signal };
    const char *color;
    int fd, step, rc = 0;

    if (argc != 2 || (strcmp(argv[1], "redled") &&
                      strcmp(argv[1], "greenled") &&
                      strcmp(argv[1], "blueled"))) {
        fprintf(stderr, "usage: %s redled|greenled|blueled\n", argv[0]);
        return 2;
    }
    color = argv[1];
    if (snprintf(path, sizeof(path), "/sys/class/leds/%s/brightness", color) >=
        (int)sizeof(path))
        return 2;
    fd = open(path, O_WRONLY | O_CLOEXEC);
    if (fd < 0) {
        perror(path);
        return 1;
    }
    sigemptyset(&action.sa_mask);
    sigaction(SIGINT, &action, NULL);
    sigaction(SIGTERM, &action, NULL);
    if (set_led(fd, 0) < 0) {
        perror("LED initial off");
        close(fd);
        return 1;
    }

    printf("color=%s pwm_hz=100 cycles=%d seconds_nominal=9\n", color, CYCLES);
    fflush(stdout);
    for (step = 0; step < CYCLES * STEPS_PER_CYCLE && !interrupted; step++) {
        double phase = (step % STEPS_PER_CYCLE) / (double)STEPS_PER_CYCLE;
        double ramp = phase < 0.5 ? phase * 2.0 : (1.0 - phase) * 2.0;
        double smooth = ramp * ramp * (3.0 - 2.0 * ramp);
        long on_us = (long)(smooth * PERIOD_US);
        if (on_us > 0) {
            if (set_led(fd, 1) < 0) { rc = 1; break; }
            delay_us(on_us);
        }
        if (set_led(fd, 0) < 0) { rc = 1; break; }
        delay_us(PERIOD_US - on_us);
    }
    if (set_led(fd, 0) < 0)
        rc = 1;
    close(fd);
    if (rc) perror("LED write");
    puts(interrupted ? "interrupted; led=off" : "complete; led=off");
    return rc;
}
