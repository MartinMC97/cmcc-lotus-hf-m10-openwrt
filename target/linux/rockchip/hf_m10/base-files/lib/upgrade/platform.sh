# SPDX-License-Identifier: GPL-2.0-only
# Stock SFTL/Android Boot is not OpenWrt's generic MTD or SD upgrade format.
REQUIRE_IMAGE_METADATA=1

platform_check_image() {
    echo 'CMCC HF-M10: sysupgrade is not implemented. Use the verified paired installer.' >&2
    return 1
}

platform_copy_config() {
    echo 'CMCC HF-M10: no generic upgrade partition writes are permitted.' >&2
    return 1
}

# Keep the write stage disabled even if a caller forces past image checking.
platform_do_upgrade() {
    echo 'CMCC HF-M10: refusing generic sysupgrade; Boot/Rootfs must be paired.' >&2
    return 1
}
