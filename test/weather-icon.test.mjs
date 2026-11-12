import { test } from "node:test";
import assert from "node:assert/strict";
import { readWeatherIcon, WEATHER_CHARS } from "../watchface/weather-icon.js";

const SUNNY = WEATHER_CHARS[0];
const CLOUDY = WEATHER_CHARS[1];
const RAIN = WEATHER_CHARS[3];

function sensorWithIndex(index) {
	return { getForecast: () => ({ forecastData: { count: 1, data: [{ high: 0, low: 0, index }] } }) };
}

test("maps a known condition index to its icon", () => {
	assert.equal(readWeatherIcon(sensorWithIndex(0)), CLOUDY);
	assert.equal(readWeatherIcon(sensorWithIndex(3)), SUNNY);
	assert.equal(readWeatherIcon(sensorWithIndex(1)), RAIN);
});

test("folds night variants into their daytime icon", () => {
	assert.equal(readWeatherIcon(sensorWithIndex(26)), CLOUDY);
	assert.equal(readWeatherIcon(sensorWithIndex(28)), SUNNY);
});

test("returns no icon for the Unknown condition (25)", () => {
	assert.equal(readWeatherIcon(sensorWithIndex(25)), null);
});

test("returns no icon for unmapped or missing indices", () => {
	for (const index of [29, 99, -1, undefined, null, "3"]) {
		assert.equal(readWeatherIcon(sensorWithIndex(index)), null, `index ${index}`);
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

test("returns no icon when the forecast is missing or empty", () => {
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
		assert.equal(readWeatherIcon({ getForecast: () => payload }), null, JSON.stringify(payload));
	}
});

test("returns no icon when neither forecast method exists", () => {
	assert.equal(readWeatherIcon({}), null);
	assert.equal(readWeatherIcon(null), null);
});

test("returns no icon and reports the error when the read throws", () => {
	const errors = [];
	const sensor = {
		getForecast: () => {
			throw new Error("boom");
		},
	};
	assert.equal(readWeatherIcon(sensor, (e) => errors.push(e)), null);
	assert.equal(errors.length, 1);
	assert.match(String(errors[0]), /boom/);
});
