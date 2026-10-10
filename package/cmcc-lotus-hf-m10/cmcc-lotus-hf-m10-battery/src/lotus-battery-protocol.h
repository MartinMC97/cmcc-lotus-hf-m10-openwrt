/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef LOTUS_BATTERY_PROTOCOL_H
#define LOTUS_BATTERY_PROTOCOL_H
/* Recovered from stock Image IRQ handler, not an ADC/voltage estimator. */
struct lotus_battery_decoder {
	unsigned long long last_us;
	unsigned int count;
	int seen, gate;
};

/* Return 1 only at a stock publication boundary; invalid counts give -1. */
static inline int lotus_battery_edge(struct lotus_battery_decoder *d,
				    unsigned long long now, int *capacity)
{
	static const int levels[] = {0, 25, 50, 75, 100};
	unsigned long long gap = now - d->last_us;
	d->last_us = now;
	if (!d->seen) { d->seen = 1; return 0; }
	if (gap > 1000000ULL) {
		if (!d->gate) {
			d->gate = 1;
			d->count = 1;
			return 0;
		}
		d->gate = 0;
		*capacity = d->count <= 4 ? levels[d->count] : -1;
		d->count = 1;
		return 1;
	}
	/* Saturate malformed/noisy input rather than indexing beyond the table. */
	if (d->count < 5) d->count++;
	return 0;
}
#endif
