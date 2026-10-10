// SPDX-License-Identifier: GPL-2.0-only
/* Input-only port of the stock GPIO indicator. No power/charger outputs. */
#include <linux/gpio/consumer.h>
#include <linux/interrupt.h>
#include <linux/ktime.h>
#include <linux/module.h>
#include <linux/of.h>
#include <linux/platform_device.h>
#include <linux/power_supply.h>
#include <linux/spinlock.h>
#include "lotus-battery-protocol.h"

struct lotus_battery {
	struct gpio_desc *indicator, *charge;
	struct power_supply *psy;
	struct lotus_battery_decoder decoder;
	spinlock_t lock;
	int capacity;
	u64 updated_us;
};

static enum power_supply_property lotus_props[] = {
	POWER_SUPPLY_PROP_CAPACITY, POWER_SUPPLY_PROP_STATUS,
};

static int lotus_get_property(struct power_supply *psy,
			     enum power_supply_property prop,
			     union power_supply_propval *val)
{
	struct lotus_battery *b = power_supply_get_drvdata(psy);
	unsigned long flags;
	int capacity, charging;
	u64 updated;

	if (prop == POWER_SUPPLY_PROP_STATUS) {
		charging = gpiod_get_value_cansleep(b->charge);
		if (charging < 0) return charging;
		/* The pin doesn't distinguish unplugged, full or charging disabled. */
		val->intval = charging ? POWER_SUPPLY_STATUS_CHARGING :
			POWER_SUPPLY_STATUS_NOT_CHARGING;
		return 0;
	}
	if (prop != POWER_SUPPLY_PROP_CAPACITY) return -EINVAL;
	spin_lock_irqsave(&b->lock, flags);
	capacity = b->capacity;
	updated = b->updated_us;
	spin_unlock_irqrestore(&b->lock, flags);
	/* Do not invent a 100% default or retain a stalled signal indefinitely. */
	if (capacity < 0 || ktime_to_us(ktime_get()) - updated > 60000000ULL)
		return -ENODATA;
	val->intval = capacity;
	return 0;
}

static irqreturn_t lotus_indicator_irq(int irq, void *data)
{
	struct lotus_battery *b = data;
	unsigned long flags;
	u64 now = ktime_to_us(ktime_get());
	int capacity, publish;

	spin_lock_irqsave(&b->lock, flags);
	publish = lotus_battery_edge(&b->decoder, now, &capacity);
	if (publish) {
		b->capacity = capacity;
		b->updated_us = now;
	}
	spin_unlock_irqrestore(&b->lock, flags);
	if (publish) power_supply_changed(b->psy);
	return IRQ_HANDLED;
}

static irqreturn_t lotus_charge_irq(int irq, void *data)
{
	struct lotus_battery *b = data;
	power_supply_changed(b->psy);
	return IRQ_HANDLED;
}

static const struct power_supply_desc lotus_desc = {
	.name = "lotus-battery",
	.type = POWER_SUPPLY_TYPE_BATTERY,
	.properties = lotus_props,
	.num_properties = ARRAY_SIZE(lotus_props),
	.get_property = lotus_get_property,
};

static int lotus_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct power_supply_config config = {};
	struct lotus_battery *b;
	int irq, ret;

	b = devm_kzalloc(dev, sizeof(*b), GFP_KERNEL);
	if (!b) return -ENOMEM;
	spin_lock_init(&b->lock);
	b->capacity = -1;
	b->indicator = devm_gpiod_get(dev, "indicator", GPIOD_IN);
	if (IS_ERR(b->indicator)) return dev_err_probe(dev, PTR_ERR(b->indicator), "indicator input\n");
	b->charge = devm_gpiod_get(dev, "charge", GPIOD_IN);
	if (IS_ERR(b->charge)) return dev_err_probe(dev, PTR_ERR(b->charge), "charge input\n");
	config.drv_data = b;
	config.of_node = dev->of_node;
	b->psy = devm_power_supply_register(dev, &lotus_desc, &config);
	if (IS_ERR(b->psy)) return dev_err_probe(dev, PTR_ERR(b->psy), "power supply\n");
	irq = gpiod_to_irq(b->indicator);
	if (irq < 0) return dev_err_probe(dev, irq, "indicator IRQ\n");
	/* Stock request_irq flags=1: physical rising edge despite active-low DT. */
	ret = devm_request_irq(dev, irq, lotus_indicator_irq, IRQF_TRIGGER_RISING,
			       "lotus-battery-indicator", b);
	if (ret) return dev_err_probe(dev, ret, "indicator IRQ registration\n");
	irq = gpiod_to_irq(b->charge);
	if (irq < 0) return dev_err_probe(dev, irq, "charge IRQ\n");
	ret = devm_request_irq(dev, irq, lotus_charge_irq,
			       IRQF_TRIGGER_RISING | IRQF_TRIGGER_FALLING,
			       "lotus-battery-charge", b);
	if (ret) return dev_err_probe(dev, ret, "charge IRQ registration\n");
	dev_info(dev, "read-only five-level GPIO indicator; awaiting pulse frames\n");
	return 0;
}

static const struct of_device_id lotus_match[] = {
	{ .compatible = "lotus,mini-battery-indicator" }, {}
};
MODULE_DEVICE_TABLE(of, lotus_match);
static struct platform_driver lotus_driver = {
	.probe = lotus_probe,
	.driver = { .name = "lotus-mini-battery", .of_match_table = lotus_match },
};
module_platform_driver(lotus_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Lotus Mini read-only stock five-level battery indicator");
