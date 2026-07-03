import {
	createWidget,
	deleteWidget,
	widget,
	align,
	prop,
	show_level,
} from "@zos/ui";
import { Time } from "@zos/sensor";

// Trial: Jost Light (OFL) on both layers — the same face the dial numerals are
// baked with, so analog and digital speak with one geometric voice. Swap back
// to "assets://fonts/Rubik-Bold.ttf" (still bundled) to revert the A/B.
const FONT = "assets://fonts/Jost-Light.ttf";

const CX = 233; // screen center x
const CY = 233; // screen center y

const IVORY = 0xfffbf0; // analog layer: numerals, batons, hour hand
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

// Hand geometry — MUST mirror tools/render-assets.py. Each hand PNG points to
// 12 o'clock with its tip at row 0 and the dial center at (posX, posY); only
// the outer segment is painted, so the visible bar floats while the firmware
// rotates the full (mostly transparent) image like a traditional hand.
// The hour hand's visible half starts at the same radius as the minute's so
// the empty inner ring reads as one clean circle around the digital digits.
const HAND_HOUR = { path: "hands/hour.png", posX: 7, posY: 155 };
const HAND_MINUTE_POS = { posX: 5, posY: 205 }; // path is theme-driven

// Digital heart — two stacked rows (HH above, MM below), centered on the dial.
// Row boxes are symmetric around CY; exact px tuned in the simulator.
const DIGIT_SIZE = 84;
const DIGIT_BOX_W = 200;
const DIGIT_BOX_H = 100;
// Each row's center offset from CY — mirrored in tools/render-assets.py
// (DIGIT_ROW_DY). Boxes may overlap; they are transparent.
const DIGIT_ROW_DY = 42;

const NORMAL = show_level.ONLY_NORMAL;
const AOD = show_level.ONAL_AOD;

let _delegate = null;
let _timeSensor = null;

WatchFace({
	build() {
		const time = new Time();

		// ── Dial — numerals 12/3/6/9 + hour batons, baked into one PNG ───────
		createWidget(widget.IMG, {
			x: 0,
			y: 0,
			src: "background.png",
			show_level: NORMAL,
		});

		// ── Edit mode — pick the accent color (minute hand + digits) ─────────
		// Masks are firmware-mandated (the edit-exit crashes without them) but
		// kept fully transparent so the dial stays crisp instead of dimming.
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

		// Single centered edit zone over the digital heart: the affordance ring
		// sits around the very element whose color it changes.
		const colorEditGroup = createWidget(widget.WATCHFACE_EDIT_GROUP, {
			edit_id: 1,
			x: 133,
			y: 133,
			w: 200,
			h: 200,
			select_image: EDIT_ROOT + "select.png",
			un_select_image: EDIT_ROOT + "un_select.png",
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

		// Read the on-watch selection (firmware-persisted) before creating the
		// widgets that depend on it. Falls back to the default on first run.
		const colorType =
			colorEditGroup.getProperty(prop.CURRENT_TYPE) || EDIT_COLOR_CHAMPAGNE;
		const theme = THEMES[COLOR_TYPE_TO_KEY[colorType] || DEFAULT_KEY];

		// ── Floating hands — firmware-driven, no JS per-tick work ────────────
		createWidget(widget.TIME_POINTER, {
			hour_path: HAND_HOUR.path,
			hour_centerX: CX,
			hour_centerY: CY,
			hour_posX: HAND_HOUR.posX,
			hour_posY: HAND_HOUR.posY,
			minute_path: theme.minute,
			minute_centerX: CX,
			minute_centerY: CY,
			minute_posX: HAND_MINUTE_POS.posX,
			minute_posY: HAND_MINUTE_POS.posY,
			show_level: NORMAL,
		});

		// ── Digital heart — HH / MM in two rows ──────────────────────────────
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

		// ── AOD — digital heart + white hands, minimum lit pixels ────────────
		// Separate TIME_POINTER so the minute hand stays white in AOD instead
		// of inheriting the theme accent (the ivory PNG doubles as white).
		createWidget(widget.TIME_POINTER, {
			hour_path: HAND_HOUR.path,
			hour_centerX: CX,
			hour_centerY: CY,
			hour_posX: HAND_HOUR.posX,
			hour_posY: HAND_HOUR.posY,
			minute_path: "hands/minute-ivory.png",
			minute_centerX: CX,
			minute_centerY: CY,
			minute_posX: HAND_MINUTE_POS.posX,
			minute_posY: HAND_MINUTE_POS.posY,
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
