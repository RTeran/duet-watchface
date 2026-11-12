import { test } from "node:test";
import assert from "node:assert/strict";
import { createChangeLogger, readWeatherIcon, WEATHER_CHARS } from "../watchface/weather-icon.js";

const [SUNNY, CLOUDY, OVERCAST, RAIN, SNOW, STORM] = WEATHER_CHARS;

const DOCUMENTED_CONDITIONS = [
	[0, "Cloudy", CLOUDY],
	[1, "Showers", RAIN],
	[2, "Snow Showers", SNOW],
	[3, "Sunny", SUNNY],
	[4, "Overcast", OVERCAST],
	[5, "Light Rain", RAIN],
	[6, "Light Snow", SNOW],
	[7, "Moderate Rain", RAIN],
	[8, "Moderate Snow", SNOW],
	[9, "Heavy Snow", SNOW],
	[10, "Heavy Rain", RAIN],
	[11, "Sandstorm", OVERCAST],
	[12, "Rain and Snow", SNOW],
	[13, "Fog", OVERCAST],
	[14, "Hazy", OVERCAST],
	[15, "T-Storms", STORM],
	[16, "Snowstorm", SNOW],
	[17, "Floating dust", OVERCAST],
	[18, "Very Heavy Rainstorm", STORM],
	[19, "Rain and Hail", STORM],
	[20, "T-Storms and Hail", STORM],
	[21, "Heavy Rainstorm", STORM],
	[22, "Dust", OVERCAST],
	[23, "Heavy sand storm", OVERCAST],
	[24, "Rainstorm", STORM],
	[25, "Unknown", null],
	[26, "Cloudy Nighttime", CLOUDY],
	[27, "Showers Nighttime", RAIN],
	[28, "Sunny Nighttime", SUNNY],
];

function sensorWithIndex(index) {
	return { getForecast: () => ({ forecastData: { count: 1, data: [{ high: 0, low: 0, index }] } }) };
}

function readCollectingErrors(sensor) {
	const errors = [];
	const icon = readWeatherIcon(sensor, (e) => errors.push(e));
	return { icon, errors };
}

test("maps every documented condition index to its icon", () => {
	for (const [index, name, expected] of DOCUMENTED_CONDITIONS) {
		assert.equal(readWeatherIcon(sensorWithIndex(index)), expected, `${index} ${name}`);
	}
});

test("returns no icon for Unknown (25) without reporting an error", () => {
	assert.deepEqual(readCollectingErrors(sensorWithIndex(25)), { icon: null, errors: [] });
});

test("looks up string indices like numeric ones", () => {
	assert.equal(readWeatherIcon(sensorWithIndex("3")), SUNNY);
});

test("returns no icon and reports unmapped or missing indices", () => {
	for (const index of [29, 99, -1, undefined, null]) {
		const { icon, errors } = readCollectingErrors(sensorWithIndex(index));
		assert.equal(icon, null, `index ${index}`);
		assert.equal(errors.length, 1, `index ${index}`);
		assert.match(String(errors[0]), /unmapped index/);
	}
});

test("falls back to the legacy getForecastWeather method", () => {
	const legacy = {
		getForecastWeather: () => ({ forecastData: { count: 1, data: [{ index: 3 }] } }),
	};
	assert.equal(readWeatherIcon(legacy), SUNNY);
});

test("prefers getForecast and calls it bound to the sensor", () => {
	const sensor = {
		payload: { forecastData: { data: [{ index: 3 }] } },
		getForecast() {
			return this.payload;
		},
		getForecastWeather: () => {
			throw new Error("should not be called");
		},
	};
	assert.equal(readWeatherIcon(sensor), SUNNY);
});

test("ignores forecastData.count and trusts the data array", () => {
	const sensor = { getForecast: () => ({ forecastData: { data: [{ index: 3 }] } }) };
	assert.equal(readWeatherIcon(sensor), SUNNY);
});

test("returns no icon and reports a missing or empty forecast", () => {
	const payloads = [
		undefined,
		null,
		{},
		{ forecastData: undefined },
		{ forecastData: { count: 0, data: [] } },
		{ forecastData: { count: 0 } },
		{ forecastData: { data: [null] } },
	];
	for (const payload of payloads) {
		const { icon, errors } = readCollectingErrors({ getForecast: () => payload });
		assert.equal(icon, null, JSON.stringify(payload));
		assert.deepEqual(errors, ["no forecast data"], JSON.stringify(payload));
	}
});

test("returns no icon and reports when neither forecast method exists", () => {
	for (const sensor of [{}, null]) {
		assert.deepEqual(readCollectingErrors(sensor), { icon: null, errors: ["no forecast method"] });
	}
});

test("returns no icon and reports the error when the read throws", () => {
	const sensor = {
		getForecast: () => {
			throw new Error("boom");
		},
	};
	const { icon, errors } = readCollectingErrors(sensor);
	assert.equal(icon, null);
	assert.equal(errors.length, 1);
	assert.match(String(errors[0]), /boom/);
});

test("returns no icon when the read throws and no error handler is given", () => {
	const sensor = {
		getForecast: () => {
			throw new Error("boom");
		},
	};
	assert.equal(readWeatherIcon(sensor), null);
});

test("change logger logs a repeated failure once, and again after a reset", () => {
	const lines = [];
	const logger = createChangeLogger((line) => lines.push(line));
	logger.report("no forecast data");
	logger.report("no forecast data");
	logger.report("no forecast method");
	logger.reset();
	logger.report("no forecast method");
	assert.deepEqual(lines, ["no forecast data", "no forecast method", "no forecast method"]);
});

test("change logger includes the stack of an error", () => {
	const lines = [];
	const logger = createChangeLogger((line) => lines.push(line));
	const err = new Error("boom");
	logger.report(err);
	assert.equal(lines.length, 1);
	assert.match(lines[0], /^Error: boom\n.*at /s);
});
