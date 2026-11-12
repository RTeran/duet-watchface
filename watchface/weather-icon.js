// Weather condition glyphs from icons-outlined.ttf, one per bucket.
// Buckets: 0 sunny · 1 cloudy · 2 overcast · 3 rain · 4 snow · 5 storm.
export const WEATHER_CHARS = ["", "", "", "", "", ""];

// forecastData.data[0].index (0–28) → bucket, per the ZeppOS Weather docs; night
// variants fold into their daytime bucket. 25 ("Unknown") is deliberately absent:
// an unknown condition shows no icon rather than a misleading one.
const WEATHER_INDEX_TO_BUCKET = {
	0: 1, 1: 3, 2: 4, 3: 0, 4: 2, 5: 3, 6: 4, 7: 3, 8: 4, 9: 4,
	10: 3, 11: 2, 12: 4, 13: 2, 14: 2, 15: 5, 16: 4, 17: 2, 18: 5, 19: 5,
	20: 5, 21: 5, 22: 2, 23: 2, 24: 5, 26: 1, 27: 3, 28: 0,
};

export function readWeatherIcon(weather, onError) {
	try {
		// Active 2 firmware only has getForecast(); older ones only the legacy name.
		const read = weather && (weather.getForecast || weather.getForecastWeather);
		if (typeof read !== "function") return null;
		// forecastData.count is unreliable (seen empty with data present), so trust the array.
		const forecast = read.call(weather);
		const data = forecast && forecast.forecastData && forecast.forecastData.data;
		const first = Array.isArray(data) ? data[0] : null;
		const index = first ? first.index : undefined;
		if (typeof index !== "number") return null;
		const bucket = WEATHER_INDEX_TO_BUCKET[index];
		return bucket === undefined ? null : WEATHER_CHARS[bucket];
	} catch (e) {
		if (onError) onError(e);
		return null;
	}
}
