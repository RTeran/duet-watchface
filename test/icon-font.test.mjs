import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { WEATHER_CHARS } from "../watchface/weather-icon.js";

const FONTS = [
	"assets/466x466-amazfit-active-2-round/fonts/icons-outlined.ttf",
	"assets/466x466-amazfit-gtr-4/fonts/icons-outlined.ttf",
];

function readCmapFormat4(path) {
	const buf = readFileSync(new URL("../" + path, import.meta.url));
	const numTables = buf.readUInt16BE(4);
	let cmap = -1;
	for (let i = 0; i < numTables; i++) {
		const rec = 12 + 16 * i;
		if (buf.toString("latin1", rec, rec + 4) === "cmap") cmap = buf.readUInt32BE(rec + 8);
	}
	assert.notEqual(cmap, -1, `${path} has no cmap table`);
	const codepoints = new Set();
	const subtables = buf.readUInt16BE(cmap + 2);
	for (let i = 0; i < subtables; i++) {
		const sub = cmap + buf.readUInt32BE(cmap + 4 + 8 * i + 4);
		if (buf.readUInt16BE(sub) !== 4) continue;
		const segX2 = buf.readUInt16BE(sub + 6);
		for (let s = 0; s < segX2; s += 2) {
			const end = buf.readUInt16BE(sub + 14 + s);
			const start = buf.readUInt16BE(sub + 16 + segX2 + s);
			if (start === 0xffff) continue;
			for (let cp = start; cp <= end; cp++) codepoints.add(cp);
		}
	}
	return codepoints;
}

test("every weather glyph is in the bundled icon fonts", () => {
	for (const path of FONTS) {
		const cmap = readCmapFormat4(path);
		for (const ch of WEATHER_CHARS) {
			assert.ok(cmap.has(ch.codePointAt(0)), `${path} lacks U+${ch.codePointAt(0).toString(16)}`);
		}
	}
});

// U+F1AD drew blank in the icon font on the Active 2 and in the simulator, while
// the same outline mapped to U+E001 drew fine. Only F1AD is verified; the whole
// U+F000+ block is kept out as a precaution.
test("weather glyphs avoid the U+F000+ block that draws blank on device", () => {
	for (const ch of WEATHER_CHARS) {
		assert.ok(ch.codePointAt(0) < 0xf000, `U+${ch.codePointAt(0).toString(16)}`);
	}
});
