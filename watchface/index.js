import {
	createWidget,
	deleteWidget,
	widget,
	align,
	prop,
	show_level,
	data_type,
} from "@zos/ui";
import {
	Time,
	Battery,
	Step,
	Calorie,
	HeartRate,
	Pai,
	Weather,
} from "@zos/sensor";

// Trial: Jost Light (OFL) on both layers — the same face the dial numerals are
// baked with, so analog and digital speak with one geometric voice. Swap back
// to "assets://fonts/Rubik-Bold.ttf" (still bundled) to revert the A/B.
const FONT = "assets://fonts/Jost-Light.ttf";
// Material Icons Outlined, subset to Duet's glyphs + converted CFF→glyf by
// tools/make-icon-font.py. Rendered live as TEXT widgets (tintable, scalable).
const ICONS_FONT = "assets://fonts/icons-outlined.ttf";

const CX = 233; // screen center x
const CY = 233; // screen center y

const IVORY = 0xfffbf0; // analog layer: numerals, batons, hour hand, complications
const AOD_GRAY = 0x999999;

// Editable accent themes — the color the user picks in edit mode paints the
// minute hand and the digital digits. `accent` is applied live to the TEXT
// widgets; `minute` is a pre-baked PNG per color (TIME_POINTER cannot tint an
// image at runtime). Keys and colors MUST match THEMES in tools/render-assets.py.
const THEMES = {
	champagne: { accent: 0xe8c97e, minute: "hands/minute.png" },
	rose: { accent: 0xe0a899, minute: "hands/minute-rose.png" },
	copper: { accent: 0xc98a5e, minute: "hands/minute-copper.png" },
	amethyst: { accent: 0xb69cd6, minute: "hands/minute-amethyst.png" },
	sapphire: { accent: 0x7fa6d9, minute: "hands/minute-sapphire.png" },
	turquoise: { accent: 0x6fc2c2, minute: "hands/minute-turquoise.png" },
	emerald: { accent: 0x6cbf9a, minute: "hands/minute-emerald.png" },
	ivory: { accent: 0xfffbf0, minute: "hands/minute-ivory.png" },
};
const DEFAULT_KEY = "champagne";

// WATCHFACE_EDIT_GROUP type ids — must live in the firmware's reserved range
// (0x186a0+). Assigned sequentially; Duet has no prior persisted selections, so
// no id migration is needed. Keep in the same order as `optional_types` below.
const EDIT_ROOT = "edit/";
const EDIT_COLOR_CHAMPAGNE = 0x186a0;
const EDIT_COLOR_ROSE = 0x186a1;
const EDIT_COLOR_COPPER = 0x186a2;
const EDIT_COLOR_AMETHYST = 0x186a3;
const EDIT_COLOR_SAPPHIRE = 0x186a4;
const EDIT_COLOR_TURQUOISE = 0x186a5;
const EDIT_COLOR_EMERALD = 0x186a6;
const EDIT_COLOR_IVORY = 0x186a7;

const COLOR_TYPE_TO_KEY = {
	[EDIT_COLOR_CHAMPAGNE]: "champagne",
	[EDIT_COLOR_ROSE]: "rose",
	[EDIT_COLOR_COPPER]: "copper",
	[EDIT_COLOR_AMETHYST]: "amethyst",
	[EDIT_COLOR_SAPPHIRE]: "sapphire",
	[EDIT_COLOR_TURQUOISE]: "turquoise",
	[EDIT_COLOR_EMERALD]: "emerald",
	[EDIT_COLOR_IVORY]: "ivory",
};

// ── Complications ────────────────────────────────────────────────────────────
// Three circular badges — LEFT, RIGHT and BOTTOM — each editable to one of a shared
// catalog of data, or hidden. Rendered in ivory only (the accent stays exclusive
// to the minute hand + digits). Hidden in AOD. The badge sits BELOW the hands —
// its widgets are created before the TIME_POINTER so the hands sweep in front.

// Zepp OS Time.getDay() is 1 (Mon) … 7 (Sun); index with getDay() - 1.
const DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];

// Weather condition glyphs from icons-outlined.ttf, one per bucket.
// Buckets: 0 sunny · 1 cloudy · 2 overcast · 3 rain · 4 snow · 5 storm.
const WEATHER_CHARS = ["\ue430", "\ue42d", "\ue2bd", "\uf1ad", "\ueb3b", "\uebdb"];
// getForecastWeather().forecastData.data[0].index (0–28) → bucket. Index meanings
// per the ZeppOS Weather docs; night variants fold into their daytime bucket.
const WEATHER_INDEX_TO_BUCKET = {
	0: 1, 1: 3, 2: 4, 3: 0, 4: 2, 5: 3, 6: 4, 7: 3, 8: 4, 9: 4,
	10: 3, 11: 2, 12: 4, 13: 2, 14: 2, 15: 5, 16: 4, 17: 2, 18: 5, 19: 5,
	20: 5, 21: 5, 22: 2, 23: 2, 24: 5, 25: 0, 26: 1, 27: 3, 28: 0,
};

// Badge geometry — both on the horizontal centerline, equidistant between the
// dial numerals (3 & 9) and the digital heart. Symmetric about CX.
const COMP_AXIS_Y = CY;
const COMP_LEFT_X = 120;
const COMP_RIGHT_X = 346;
const COMP_R = 31; // badge radius → the ring PNG is 62×62
const COMP_RING_R = 29.5; // ARC_PROGRESS radius — MUST equal COMP_RING_CENTER_R in render-assets.py
const COMP_RING_W = 3;
const COMP_BOX_W = 62;
const COMP_VALUE_SIZE = 26;
const COMP_SUB_SIZE = 13; // weekday / wordmark
const COMP_ICON_SIZE = 17;
const RING_CLOSED = "comp/ring-closed.png";
const RING_TRACK = "comp/ring-track.png";
// Bottom badge: midway between the minutes row and the baked "6".
const COMP_BOTTOM_X = CX;
const COMP_BOTTOM_Y = CY + 125;

// Weather shows the CURRENT temperature, which ZeppOS only exposes through a
// firmware-bound TEXT_IMG (WEATHER_CURRENT), never as a readable number. Its
// glyphs are baked by tools/render-assets.py to match the 26px value TEXT.
const TEMP_ROOT = "comp/temp/";
const TEMP_DIGITS = [];
for (let d = 0; d <= 9; d++) TEMP_DIGITS.push(TEMP_ROOT + d + ".png");

// Edit-mode chrome — all four tap zones (color center, left, right, bottom) share ONE
// size, so the select ring and the preview render 1:1 on every zone (assets in
// tools/render-assets.py are generated at EDIT_ZONE). tips = the option-name tag.
const EDIT_ZONE = 92;
const TIPS_W = 124;
const TIPS_GAP = 8; // vertical gap from the zone's bottom to the name tag

// Catalog order is the PERSISTED CONTRACT: an option's edit type id is
// COMP_LEFT/RIGHT/BOTTOM_BASE + its index here, so options may only be
// APPENDED, never reordered (a reorder would silently repoint saved selections).
const COMP_OPTIONS = [
	{ datum: "date", title: "Date" },
	{ datum: "battery", title: "Battery" },
	{ datum: "steps", title: "Steps" },
	{ datum: "calories", title: "Calories" },
	{ datum: "hr", title: "Heart Rate" },
	{ datum: "weather", title: "Weather" },
	{ datum: "pai", title: "PAI" },
	{ datum: "empty", title: "None" },
];
const COMP_LEFT_BASE = 0x186a8; // color ids occupy 0x186a0–0x186a7
const COMP_RIGHT_BASE = 0x186b0;
const COMP_BOTTOM_BASE = 0x186b8;

const TYPE_TO_DATUM = {};
for (let i = 0; i < COMP_OPTIONS.length; i++) {
	TYPE_TO_DATUM[COMP_LEFT_BASE + i] = COMP_OPTIONS[i].datum;
	TYPE_TO_DATUM[COMP_RIGHT_BASE + i] = COMP_OPTIONS[i].datum;
	TYPE_TO_DATUM[COMP_BOTTOM_BASE + i] = COMP_OPTIONS[i].datum;
}

// `kind` picks the ring: progress = gray track PNG + live ARC_PROGRESS fill;
// closed = ivory ring PNG. Icons identify the datum (weather's is dynamic; date
// shows the weekday and PAI a wordmark instead).
const DATUM_KIND = {
	date: "closed",
	battery: "progress",
	steps: "progress",
	calories: "progress",
	hr: "closed",
	weather: "closed",
	pai: "progress",
};
const DATUM_ICON = {
	battery: "\ue1a4",
	steps: "\ue536",
	calories: "\uef55",
	hr: "\ue87d",
};

const NORMAL = show_level.ONLY_NORMAL;
const AOD = show_level.ONAL_AOD;

let _delegate = null;
let _timeSensor = null;

WatchFace({
	build() {
		const time = new Time();
		const battery = new Battery();
		const step = new Step();
		const calorie = new Calorie();
		const weather = new Weather();
		// Optional sensors: absent on some targets — degrade to "--" instead of
		// aborting build().
		let heart = null;
		let pai = null;
		try {
			heart = new HeartRate();
		} catch (e) {}
		try {
			pai = new Pai();
		} catch (e) {}

		// ── Dial — numerals 12/3/6/9 + hour batons, baked into one PNG ───────
		createWidget(widget.IMG, {
			x: 0,
			y: 0,
			src: "background.png",
			show_level: NORMAL,
		});

		// ── Edit mode — masks + four tap zones (color, left, right, bottom) ──
		// Both masks are firmware-mandated (the edit-exit crashes without them).
		// WATCHFACE_EDIT_MASK sits BELOW the edit groups: its dark veil dims the
		// live dial so the (opaque) preview thumbnails + name tags stand out on
		// top. WATCHFACE_EDIT_FG_MASK sits ABOVE the edit UI, so it stays fully
		// transparent — any opacity there would veil the previews and their names.
		createWidget(widget.WATCHFACE_EDIT_MASK, {
			x: 0,
			y: 0,
			w: 466,
			h: 466,
			src: EDIT_ROOT + "mask100.png",
			show_level: show_level.ONLY_EDIT,
		});
		createWidget(widget.WATCHFACE_EDIT_FG_MASK, {
			x: 0,
			y: 0,
			w: 466,
			h: 466,
			src: EDIT_ROOT + "mask70.png",
			show_level: show_level.ONLY_EDIT,
		});

		// Centered edit zone over the digital heart: picks the accent color.
		const colorEditGroup = createWidget(widget.WATCHFACE_EDIT_GROUP, {
			edit_id: 1,
			x: CX - EDIT_ZONE / 2,
			y: COMP_AXIS_Y - EDIT_ZONE / 2,
			w: EDIT_ZONE,
			h: EDIT_ZONE,
			select_image: EDIT_ROOT + "select.png",
			un_select_image: EDIT_ROOT + "un_select.png",
			tips_BG: EDIT_ROOT + "tips.png",
			tips_x: (EDIT_ZONE - TIPS_W) / 2,
			tips_y: EDIT_ZONE + TIPS_GAP,
			tips_width: TIPS_W,
			default_type: EDIT_COLOR_CHAMPAGNE,
			optional_types: [
				{ type: EDIT_COLOR_CHAMPAGNE, preview: EDIT_ROOT + "preview-color-champagne.png", title_en: "Champagne" },
				{ type: EDIT_COLOR_ROSE, preview: EDIT_ROOT + "preview-color-rose.png", title_en: "Rose Gold" },
				{ type: EDIT_COLOR_COPPER, preview: EDIT_ROOT + "preview-color-copper.png", title_en: "Copper" },
				{ type: EDIT_COLOR_AMETHYST, preview: EDIT_ROOT + "preview-color-amethyst.png", title_en: "Amethyst" },
				{ type: EDIT_COLOR_SAPPHIRE, preview: EDIT_ROOT + "preview-color-sapphire.png", title_en: "Sapphire" },
				{ type: EDIT_COLOR_TURQUOISE, preview: EDIT_ROOT + "preview-color-turquoise.png", title_en: "Turquoise" },
				{ type: EDIT_COLOR_EMERALD, preview: EDIT_ROOT + "preview-color-emerald.png", title_en: "Emerald" },
				{ type: EDIT_COLOR_IVORY, preview: EDIT_ROOT + "preview-color-ivory.png", title_en: "Ivory" },
			],
			count: 8,
		});

		// Left, right + bottom complication zones. All offer the same catalog (shared
		// previews); only the defaults differ. Type ids are base + option index.
		const leftEditGroup = createWidget(widget.WATCHFACE_EDIT_GROUP, {
			edit_id: 2,
			x: COMP_LEFT_X - EDIT_ZONE / 2,
			y: COMP_AXIS_Y - EDIT_ZONE / 2,
			w: EDIT_ZONE,
			h: EDIT_ZONE,
			select_image: EDIT_ROOT + "select.png",
			un_select_image: EDIT_ROOT + "un_select.png",
			tips_BG: EDIT_ROOT + "tips.png",
			tips_x: (EDIT_ZONE - TIPS_W) / 2,
			tips_y: EDIT_ZONE + TIPS_GAP,
			tips_width: TIPS_W,
			default_type: COMP_LEFT_BASE + 0, // Date
			optional_types: COMP_OPTIONS.map((o, i) => ({
				type: COMP_LEFT_BASE + i,
				preview: EDIT_ROOT + "preview-comp-" + o.datum + ".png",
				title_en: o.title,
			})),
			count: COMP_OPTIONS.length,
		});
		const rightEditGroup = createWidget(widget.WATCHFACE_EDIT_GROUP, {
			edit_id: 3,
			x: COMP_RIGHT_X - EDIT_ZONE / 2,
			y: COMP_AXIS_Y - EDIT_ZONE / 2,
			w: EDIT_ZONE,
			h: EDIT_ZONE,
			select_image: EDIT_ROOT + "select.png",
			un_select_image: EDIT_ROOT + "un_select.png",
			tips_BG: EDIT_ROOT + "tips.png",
			tips_x: (EDIT_ZONE - TIPS_W) / 2,
			tips_y: EDIT_ZONE + TIPS_GAP,
			tips_width: TIPS_W,
			default_type: COMP_RIGHT_BASE + 1, // Battery
			optional_types: COMP_OPTIONS.map((o, i) => ({
				type: COMP_RIGHT_BASE + i,
				preview: EDIT_ROOT + "preview-comp-" + o.datum + ".png",
				title_en: o.title,
			})),
			count: COMP_OPTIONS.length,
		});
		const bottomEditGroup = createWidget(widget.WATCHFACE_EDIT_GROUP, {
			edit_id: 4,
			x: COMP_BOTTOM_X - EDIT_ZONE / 2,
			y: COMP_BOTTOM_Y - EDIT_ZONE / 2,
			w: EDIT_ZONE,
			h: EDIT_ZONE,
			select_image: EDIT_ROOT + "select.png",
			un_select_image: EDIT_ROOT + "un_select.png",
			tips_BG: EDIT_ROOT + "tips.png",
			tips_x: (EDIT_ZONE - TIPS_W) / 2,
			tips_y: EDIT_ZONE + TIPS_GAP,
			tips_width: TIPS_W,
			default_type: COMP_BOTTOM_BASE + 5, // Weather
			optional_types: COMP_OPTIONS.map((o, i) => ({
				type: COMP_BOTTOM_BASE + i,
				preview: EDIT_ROOT + "preview-comp-" + o.datum + ".png",
				title_en: o.title,
			})),
			count: COMP_OPTIONS.length,
		});

		// Read on-watch selections (firmware-persisted) before creating the
		// widgets that depend on them. Fall back to the defaults on first run.
		const colorType =
			colorEditGroup.getProperty(prop.CURRENT_TYPE) || EDIT_COLOR_CHAMPAGNE;
		const theme = THEMES[COLOR_TYPE_TO_KEY[colorType] || DEFAULT_KEY];

		const leftType =
			leftEditGroup.getProperty(prop.CURRENT_TYPE) || COMP_LEFT_BASE + 0;
		const rightType =
			rightEditGroup.getProperty(prop.CURRENT_TYPE) || COMP_RIGHT_BASE + 1;
		const bottomType =
			bottomEditGroup.getProperty(prop.CURRENT_TYPE) || COMP_BOTTOM_BASE + 5;
		const leftKey = TYPE_TO_DATUM[leftType] || "date";
		const rightKey = TYPE_TO_DATUM[rightType] || "battery";
		const bottomKey = TYPE_TO_DATUM[bottomType] || "weather";

		// ── Data readers ─────────────────────────────────────────────────────
		function readDatum(key) {
			try {
				switch (key) {
					case "date":
						return { value: String(time.getDate()), sub: DAYS[time.getDay() - 1] };
					case "battery": {
						const v = battery.getCurrent();
						return { value: String(v), level: v };
					}
					case "steps": {
						const c = step.getCurrent();
						const t = step.getTarget() || 0;
						return { value: fmtCount(c), level: t > 0 ? clampPct((c / t) * 100) : 0 };
					}
					case "calories": {
						const c = calorie.getCurrent();
						const t = calorie.getTarget() || 0;
						return { value: String(c), level: t > 0 ? clampPct((c / t) * 100) : 0 };
					}
					case "hr": {
						const v = heart && (heart.getLast() || heart.getCurrent());
						return { value: v ? String(v) : "--" };
					}
					case "weather": {
						const d0 = weather.getForecastWeather().forecastData.data[0];
						const b = WEATHER_INDEX_TO_BUCKET[d0.index];
						return { iconChar: WEATHER_CHARS[b === undefined ? 0 : b] };
					}
					case "pai": {
						const v = pai ? pai.getTotal() || 0 : 0;
						return { value: String(v), level: clampPct(v) };
					}
				}
			} catch (e) {
				return { value: "--" };
			}
			return { value: "" };
		}

		// ── Complication factory ─────────────────────────────────────────────
		// Creates a badge's widgets (all show_level NORMAL, i.e. hidden in AOD)
		// and returns a { refresh } handle. The progress fill is created ONCE and
		// updated in place — recreating it would push it above the later-created
		// hands, breaking the "badge sits under the hands" z-order.
		function makeComplication(centerX, centerY, key) {
			if (key === "empty") return { refresh() {} };

			const kind = DATUM_KIND[key];
			const isDate = key === "date";
			const isPai = key === "pai";

			createWidget(widget.IMG, {
				x: centerX - COMP_R,
				y: centerY - COMP_R,
				src: kind === "progress" ? RING_TRACK : RING_CLOSED,
				show_level: NORMAL,
			});

			// Weather's value is updated by the firmware, so it has no JS handle.
			let valueW = null;
			if (key === "weather") {
				createWidget(widget.TEXT_IMG, {
					x: centerX - COMP_BOX_W / 2,
					y: centerY - 22,
					w: COMP_BOX_W,
					h: 30,
					font_array: TEMP_DIGITS,
					unit_en: TEMP_ROOT + "deg.png",
					negative_image: TEMP_ROOT + "minus.png",
					type: data_type.WEATHER_CURRENT,
					h_space: 0,
					align_h: align.CENTER_H,
					show_level: NORMAL,
				});
			} else {
				valueW = createWidget(widget.TEXT, {
					x: centerX - COMP_BOX_W / 2,
					y: centerY - 22,
					w: COMP_BOX_W,
					h: 30,
					color: IVORY,
					text: "",
					text_size: COMP_VALUE_SIZE,
					align_h: align.CENTER_H,
					align_v: align.CENTER_V,
					enable_scroll: false,
					font: FONT,
					show_level: NORMAL,
				});
			}

			// Identifier line: weekday (date) · wordmark (pai) · icon glyph (rest).
			let subW = null;
			if (isDate || isPai) {
				subW = createWidget(widget.TEXT, {
					x: centerX - COMP_BOX_W / 2,
					y: centerY + 3,
					w: COMP_BOX_W,
					h: 20,
					color: IVORY,
					text: isPai ? "PAI" : "",
					text_size: COMP_SUB_SIZE,
					align_h: align.CENTER_H,
					align_v: align.CENTER_V,
					enable_scroll: false,
					font: FONT,
					show_level: NORMAL,
				});
			} else {
				subW = createWidget(widget.TEXT, {
					x: centerX - COMP_BOX_W / 2,
					y: centerY + 2,
					w: COMP_BOX_W,
					h: 22,
					color: IVORY,
					text: DATUM_ICON[key] || "",
					text_size: COMP_ICON_SIZE,
					align_h: align.CENTER_H,
					align_v: align.CENTER_V,
					enable_scroll: false,
					font: ICONS_FONT,
					show_level: NORMAL,
				});
			}

			let fillWidget = null;
			if (kind === "progress") {
				fillWidget = createWidget(widget.ARC_PROGRESS, { show_level: NORMAL });
			}
			function applyFill(level) {
				if (!fillWidget) return;
				const lv = level == null ? 0 : level;
				// start < end is required; keep a hair above 0 so a 0% badge still
				// shows a clean (empty) track rather than an invalid arc.
				const end = Math.max(0.5, Math.min(359.5, (360 * lv) / 100));
				fillWidget.setProperty(prop.MORE, {
					center_x: centerX,
					center_y: centerY,
					radius: COMP_RING_R,
					start_angle: 0,
					end_angle: end,
					line_width: COMP_RING_W,
					color: IVORY,
					level: 100,
				});
			}

			function refresh() {
				const d = readDatum(key);
				if (valueW) valueW.setProperty(prop.TEXT, d.value || "");
				if (isDate) subW.setProperty(prop.TEXT, d.sub || "");
				else if (key === "weather" && d.iconChar)
					subW.setProperty(prop.TEXT, d.iconChar);
				if (kind === "progress") applyFill(d.level);
			}
			refresh();
			return { refresh };
		}

		// Complications first — BELOW the hands (created next).
		const leftComp = makeComplication(COMP_LEFT_X, COMP_AXIS_Y, leftKey);
		const rightComp = makeComplication(COMP_RIGHT_X, COMP_AXIS_Y, rightKey);
		const bottomComp = makeComplication(COMP_BOTTOM_X, COMP_BOTTOM_Y, bottomKey);

		// ── Floating hands — firmware-driven, no JS per-tick work ────────────
		createWidget(widget.TIME_POINTER, {
			hour_path: "hands/hour.png",
			hour_centerX: CX,
			hour_centerY: CY,
			hour_posX: 7,
			hour_posY: 155,
			minute_path: theme.minute,
			minute_centerX: CX,
			minute_centerY: CY,
			minute_posX: 5,
			minute_posY: 205,
			show_level: NORMAL,
		});

		// ── Digital heart — HH / MM in two rows ──────────────────────────────
		const DIGIT_SIZE = 84;
		const DIGIT_BOX_W = 200;
		const DIGIT_BOX_H = 100;
		const DIGIT_ROW_DY = 42;
		const hoursWidget = createWidget(widget.TEXT, {
			x: CX - DIGIT_BOX_W / 2,
			y: CY - DIGIT_ROW_DY - DIGIT_BOX_H / 2,
			w: DIGIT_BOX_W,
			h: DIGIT_BOX_H,
			color: theme.accent,
			text: pad(time.getHours()),
			text_size: DIGIT_SIZE,
			align_h: align.CENTER_H,
			align_v: align.CENTER_V,
			enable_scroll: false,
			font: FONT,
			show_level: NORMAL,
		});

		const minutesWidget = createWidget(widget.TEXT, {
			x: CX - DIGIT_BOX_W / 2,
			y: CY + DIGIT_ROW_DY - DIGIT_BOX_H / 2,
			w: DIGIT_BOX_W,
			h: DIGIT_BOX_H,
			color: theme.accent,
			text: pad(time.getMinutes()),
			text_size: DIGIT_SIZE,
			align_h: align.CENTER_H,
			align_v: align.CENTER_V,
			enable_scroll: false,
			font: FONT,
			show_level: NORMAL,
		});

		// ── AOD — digital heart + hands dimmed to match the digits ───────────
		// Complications are intentionally NOT drawn in AOD (fewer lit pixels).
		// Separate TIME_POINTER pointing at gray hand PNGs: TIME_POINTER can't
		// tint at runtime, so the AOD hands are pre-baked in AOD_GRAY (0x999999).
		createWidget(widget.TIME_POINTER, {
			hour_path: "hands/hour-aod.png",
			hour_centerX: CX,
			hour_centerY: CY,
			hour_posX: 7,
			hour_posY: 155,
			minute_path: "hands/minute-aod.png",
			minute_centerX: CX,
			minute_centerY: CY,
			minute_posX: 5,
			minute_posY: 205,
			show_level: AOD,
		});

		const aodHoursWidget = createWidget(widget.TEXT, {
			x: CX - DIGIT_BOX_W / 2,
			y: CY - DIGIT_ROW_DY - DIGIT_BOX_H / 2,
			w: DIGIT_BOX_W,
			h: DIGIT_BOX_H,
			color: AOD_GRAY,
			text: pad(time.getHours()),
			text_size: DIGIT_SIZE,
			align_h: align.CENTER_H,
			align_v: align.CENTER_V,
			enable_scroll: false,
			font: FONT,
			show_level: AOD,
		});

		const aodMinutesWidget = createWidget(widget.TEXT, {
			x: CX - DIGIT_BOX_W / 2,
			y: CY + DIGIT_ROW_DY - DIGIT_BOX_H / 2,
			w: DIGIT_BOX_W,
			h: DIGIT_BOX_H,
			color: AOD_GRAY,
			text: pad(time.getMinutes()),
			text_size: DIGIT_SIZE,
			align_h: align.CENTER_H,
			align_v: align.CENTER_V,
			enable_scroll: false,
			font: FONT,
			show_level: AOD,
		});

		function refresh() {
			const h = pad(time.getHours());
			const m = pad(time.getMinutes());
			hoursWidget.setProperty(prop.TEXT, h);
			minutesWidget.setProperty(prop.TEXT, m);
			aodHoursWidget.setProperty(prop.TEXT, h);
			aodMinutesWidget.setProperty(prop.TEXT, m);
			leftComp.refresh();
			rightComp.refresh();
			bottomComp.refresh();
		}

		// App timers are suspended while the watchface is not in the foreground,
		// so refresh the moment it becomes visible again (wrist raise, etc).
		_delegate = createWidget(widget.WIDGET_DELEGATE, {
			resume_call() {
				refresh();
			},
		});

		_timeSensor = time;
		time.onPerMinute(refresh);
	},

	onDestroy() {
		if (_delegate) {
			deleteWidget(_delegate);
			_delegate = null;
		}
		_timeSensor = null;
	},
});

function pad(n) {
	return String(n).padStart(2, "0");
}

function clampPct(x) {
	return Math.max(0, Math.min(100, x));
}

function fmtCount(c) {
	return c >= 1000 ? (c / 1000).toFixed(1) + "k" : String(c);
}
