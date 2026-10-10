'use strict';
'require view';
'require fs';
'require poll';

return view.extend({
	load: function() {
		return fs.exec('/usr/bin/lotus-sensors', []).then(function(result) {
			if (result.code !== 0) throw new Error('Sensor read failed');
			return JSON.parse(result.stdout);
		});
	},
	rows: function(data) {
		var battery = data.battery || {};
		var rows = [E('tr', {}, [E('td', {}, _('Battery (five levels)')),
			E('td', {}, battery.capacity == null ? _('Waiting for a valid signal') : battery.capacity + '%')]),
			E('tr', {}, [E('td', {}, _('Charge indicator')), E('td', {},
				battery.status === 'charging' ? _('Charging') :
				battery.status === 'not-charging' ? _('Not charging') : _('Unavailable'))])];
		(data.temperatures || []).forEach(function(sensor) {
			rows.push(E('tr', {}, [E('td', {}, sensor.sensor === 'soc' ? _('SoC temperature') : _('Internal sensor channel 1')),
				E('td', {}, (sensor.millidegrees_celsius / 1000).toFixed(1) + ' °C')]));
		});
		if (!(data.temperatures || []).length)
			rows.push(E('tr', {}, [E('td', {}, _('SoC temperature')), E('td', {}, _('Unavailable'))]));
		var cpu = data.cpu || {};
		rows.push(E('tr', {}, [E('td', {}, _('CPU frequency / limit')),
			E('td', {}, cpu.frequency_khz == null || cpu.maximum_frequency_khz == null ? _('Unavailable') :
				(cpu.frequency_khz / 1000).toFixed(0) + ' / ' + (cpu.maximum_frequency_khz / 1000).toFixed(0) + ' MHz')]));
		var cooling = data.cooling || [];
		if (!cooling.length)
			rows.push(E('tr', {}, [E('td', {}, _('CPU thermal cooling')), E('td', {}, _('Not registered'))]));
		cooling.forEach(function(device) {
			rows.push(E('tr', {}, [E('td', {}, _('CPU thermal cooling')),
				E('td', {}, device.state == null || device.maximum_state == null ? _('Unavailable') :
					(device.state === 0 ? _('Inactive') : _('Throttling')) +
					' (' + device.state + '/' + device.maximum_state + ')')]));
		});
		return rows;
	},
	render: function(data) {
		var body = E('tbody', {}, this.rows(data));
		poll.add(L.bind(function() {
			return this.load().then(L.bind(function(next) {
				body.replaceChildren.apply(body, this.rows(next));
			}, this));
		}, this), 5);
		return E('div', {}, [E('h2', {}, _('CMCC HF-M10 sensors')),
			E('p', {}, _('Battery is reported in 25% steps. Temperature is internal to the SoC, not ambient or battery temperature.')),
			E('table', { 'class': 'table' }, [body])]);
	},
	handleSaveApply: null,
	handleSave: null,
	handleReset: null
});
