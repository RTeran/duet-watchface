// Weather condition glyphs from icons-outlined.ttf, one per bucket.
// Buckets: 0 sunny · 1 cloudy · 2 overcast · 3 rain · 4 snow · 5 storm.
export const WEATHER_CHARS = ["\ue430", "\ue42d", "\ue2bd", "\ue1ad", "\ueb3b", "\uebdb"];

const UNKNOWN_INDEX = 25;

// forecastData.data[0].index (0–28) → bucket, per the ZeppOS Weather docs; night
// variants fold into their daytime bucket. 25 ("Unknown") is deliberately absent:
// an unknown condition shows no icon rather than a misleading one.
export const WEATHER_INDEX_TO_BUCKET = {
	0: 1, 1: 3, 2: 4, 3: 0, 4: 2, 5: 3, 6: 4, 7: 3, 8: 4, 9: 4,
	10: 3, 11: 2, 12: 4, 13: 2, 14: 2, 15: 5, 16: 4, 17: 2, 18: 5, 19: 5,
	20: 5, 21: 5, 22: 2, 23: 2, 24: 5, 26: 1, 27: 3, 28: 0,
};

export function readWeatherIcon(weather, onError) {
	const fail = (reason) => {
		if (onError) onError(reason);
		return null;
	};
	try {
		// Active 2 firmware only has getForecast(); older ones only the legacy name.
		const read = weather && (weather.getForecast || weather.getForecastWeather);
		if (typeof read !== "function") return fail("no forecast method");
		const forecast = read.call(weather);
		// forecastData.count is unreliable (seen empty with data present), so trust the array.
		const data = forecast && forecast.forecastData && forecast.forecastData.data;
		const first = Array.isArray(data) ? data[0] : null;
		if (!first) return fail("no forecast data");
		const bucket = WEATHER_INDEX_TO_BUCKET[first.index];
		if (bucket !== undefined) return WEATHER_CHARS[bucket];
		if (first.index == UNKNOWN_INDEX) return null;
		return fail("unmapped index " + first.index);
	} catch (e) {
		return fail(e);
	}
}

// refresh() runs every minute; this keeps a persistent failure from logging each time.
export function createChangeLogger(log) {
	let last = null;
	return {
		report(e) {
			const msg = e && e.stack ? String(e) + "\n" + e.stack : String(e);
			if (msg === last) return;
			last = msg;
			log(msg);
		},
		reset() {
			last = null;
		},
	};
}
