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

const IVORY = 0xfffbf0; // analog layer: numerals, batons, hands
const CHAMPAGNE = 0xe8c97e; // digital heart accent
const AOD_GRAY = 0x999999;

// Hand geometry — MUST mirror tools/render-assets.py. Each hand PNG points to
// 12 o'clock with its tip at row 0 and the dial center at (posX, posY); only
// the outer segment is painted, so the visible bar floats while the firmware
// rotates the full (mostly transparent) image like a traditional hand.
// The hour hand's visible half starts at the same radius as the minute's so
// the empty inner ring reads as one clean circle around the digital digits.
const HAND_HOUR = { path: "hands/hour.png", posX: 7, posY: 155 };
const HAND_MINUTE = { path: "hands/minute.png", posX: 5, posY: 205 };

// Digital heart — two stacked rows (HH above, MM below), centered on the dial.
// Row boxes are symmetric around CY; exact px tuned in the simulator.
const DIGIT_SIZE = 64;
const DIGIT_BOX_W = 200;
const DIGIT_BOX_H = 76;
// Each row's center offset from CY — mirrored in tools/render-assets.py
// (DIGIT_ROW_DY). Boxes may overlap; they are transparent.
const DIGIT_ROW_DY = 32;

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

		// ── Floating hands — firmware-driven, no JS per-tick work ────────────
		createWidget(widget.TIME_POINTER, {
			hour_path: HAND_HOUR.path,
			hour_centerX: CX,
			hour_centerY: CY,
			hour_posX: HAND_HOUR.posX,
			hour_posY: HAND_HOUR.posY,
			minute_path: HAND_MINUTE.path,
			minute_centerX: CX,
			minute_centerY: CY,
			minute_posX: HAND_MINUTE.posX,
			minute_posY: HAND_MINUTE.posY,
			show_level: NORMAL,
		});

		// ── Digital heart — HH / MM in two rows ──────────────────────────────
		const hoursWidget = createWidget(widget.TEXT, {
			x: CX - DIGIT_BOX_W / 2,
			y: CY - DIGIT_ROW_DY - DIGIT_BOX_H / 2,
			w: DIGIT_BOX_W,
			h: DIGIT_BOX_H,
			color: CHAMPAGNE,
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
			color: CHAMPAGNE,
			text: pad(time.getMinutes()),
			text_size: DIGIT_SIZE,
			align_h: align.CENTER_H,
			align_v: align.CENTER_V,
			enable_scroll: false,
			font: FONT,
			show_level: NORMAL,
		});

		// ── AOD — digital heart only, dim gray, minimum lit pixels ───────────
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
