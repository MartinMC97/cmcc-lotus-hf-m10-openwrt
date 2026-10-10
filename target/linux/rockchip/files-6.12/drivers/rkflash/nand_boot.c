// SPDX-License-Identifier: GPL-2.0

/* Copyright (c) 2018 Rockchip Electronics Co., Ltd. */

#include <linux/kernel.h>
#include <linux/errno.h>
#include <linux/mutex.h>
#include <linux/slab.h>

#include "flash.h"
#include "rkflash_api.h"
#include "rk_sftl.h"

/* Keep the allocator API and GFP bits in C for each target kernel. */
void *lotus_mini_ftl_malloc(unsigned int size)
{
	return kmalloc(size, GFP_KERNEL | GFP_DMA);
}

#ifdef CONFIG_LOTUS_MINI_SFTL_RAM_ONLY
int lotus_mini_sftl_skip_maintenance(unsigned int stage)
{
	static unsigned long seen;

	if (stage < BITS_PER_LONG && !test_and_set_bit(stage, &seen))
		pr_info("Lotus Mini NAND: RAM-only skipped maintenance stage=%u\n", stage);
	return 0;
}
#endif

static int sftl_flash_init(void __iomem *reg_addr)
{
	int ret;

	if (IS_ENABLED(CONFIG_LOTUS_MINI_NAND_READ_ONLY_GUARD))
		pr_info("Lotus Mini NAND: controller-init-enter\n");
	ret = nandc_flash_init(reg_addr);
	if (IS_ENABLED(CONFIG_LOTUS_MINI_NAND_READ_ONLY_GUARD))
		pr_info("Lotus Mini NAND: controller-init-exit ret=%d\n", ret);
	if (IS_ENABLED(CONFIG_LOTUS_MINI_NAND_ID_ONLY)) {
		pr_info("Lotus Mini NAND: ID-only stop; SFTL not entered\n");
		return ret ? ret : -EAGAIN;
	}
	if (ret == 0) {
		if (IS_ENABLED(CONFIG_LOTUS_MINI_NAND_READ_ONLY_GUARD))
			pr_info("Lotus Mini NAND: sftl-init-enter\n");
		ret = sftl_init();
		if (IS_ENABLED(CONFIG_LOTUS_MINI_NAND_READ_ONLY_GUARD))
			pr_info("Lotus Mini NAND: sftl-init-exit ret=%d\n", ret);
	}

	return ret;
}

static unsigned int sftl_flash_get_capacity(void)
{
	return sftl_get_density();
}

static int sftl_flash_read(u32 sec, u32 n_sec, void *p_data)
{
	return sftl_read(sec, n_sec, p_data);
}

static int sftl_flash_write(u32 sec, u32 n_sec, void *p_data)
{
	return sftl_write(sec, n_sec, p_data);
}

static int sftl_flash_vendor_read(u32 sec, u32 n_sec, void *p_data)
{
	return sftl_vendor_read(sec, n_sec, p_data);
}

static int sftl_flash_vendor_write(u32 sec, u32 n_sec, void *p_data)
{
	return sftl_vendor_write(sec, n_sec, p_data);
}

static int sftl_flash_gc(void)
{
	return sftl_gc();
}

static int sftl_flash_discard(u32 sec, u32 n_sec)
{
	return sftl_discard(sec, n_sec);
}

static void sftl_flash_deinit(void)
{
	u8 chip_sel = 0;

	sftl_deinit();
	nandc_flash_reset(chip_sel);
}

static int sftl_flash_resume(void __iomem *reg_addr)
{
	return nandc_flash_init(reg_addr);
}

const struct flash_boot_ops nandc_nand_ops = {
	sftl_flash_init,
	sftl_flash_read,
	sftl_flash_write,
	sftl_flash_get_capacity,
	sftl_flash_deinit,
	sftl_flash_resume,
	sftl_flash_vendor_read,
	sftl_flash_vendor_write,
	sftl_flash_gc,
	sftl_flash_discard,
};
