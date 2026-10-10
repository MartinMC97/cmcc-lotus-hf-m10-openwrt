// SPDX-License-Identifier: GPL-2.0-only
#ifndef REBOOT_MODE
#error Build must select a fixed reboot mode
#endif
.text
.global _start
.type _start, %function
_start:
 mov x8, #81
 svc #0
 movz w0, #0xdead
 movk w0, #0xfee1, lsl #16
 movz w1, #0x1969
 movk w1, #0x2812, lsl #16
 movz w2, #0xc3d4
 movk w2, #0xa1b2, lsl #16
 adr x3, mode
 mov x8, #142
 svc #0
 mov x0, #1
 mov x8, #93
 svc #0
mode:
 .asciz REBOOT_MODE
.size _start, . - _start
