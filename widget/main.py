import json
import math
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

from PySide6.QtCore import QLockFile, QPoint, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QActionGroup, QColor, QCursor, QFont, QFontMetrics, QPainter, QPen, QWindow
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMenu, QSlider, QWidget, QWidgetAction

import winapi

DATA_DIR = Path(os.environ["LOCALAPPDATA"]) / "AIUsageWidget"
USAGE_FILE = DATA_DIR / "usage.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
LOG_FILE = DATA_DIR / "widget.log"

STALE_MS = 15 * 60 * 1000
REFRESH_COOLDOWN_S = 30
RESTART_CODE = 3
PAD, RING_GAP, GROUP_GAP, LABEL_GAP, CAPTION_H = 10, 6, 14, 6, 11
RING_SCALE = {"small": 0.75, "medium": 0.87, "large": 1.0}
SIZE_NAMES = {"small": "작게", "medium": "보통", "large": "크게"}
DEFAULTS = {"transparency": 100, "size": "medium", "labels": True, "hidden": [], "x": 12}

# (data key, short label, full name, [(item key, caption)])
GROUPS = [
    ("claude", "Claude", "Claude", [("fiveHour", "5h"), ("sevenDay", "7d"), ("sevenDaySonnet", "Fable")]),
    ("chatgpt", "GPT", "ChatGPT", [("fiveHour", "5h"), ("sevenDay", "7d")]),
]
ITEM_COUNT = sum(len(items) for *_, items in GROUPS)

OK, WARN, BAD = QColor("#4ade80"), QColor("#facc15"), QColor("#ef4444")
THEMES = {
    False: {"panel": QColor("#2f2f2f"), "track": QColor(255, 255, 255, 40),
            "text": QColor("#f3f3f3"), "muted": QColor("#a0a0a6"),
            "tip_bg": "#2b2b2b", "tip_border": "#3d3d3d"},
    True: {"panel": QColor("#fbfbfb"), "track": QColor(0, 0, 0, 30),
           "text": QColor("#1a1a1c"), "muted": QColor("#5c5c62"),
           "tip_bg": "#f9f9f9", "tip_border": "#d0d0d0"},
}


def load_settings():
    try:
        saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    return {**DEFAULTS, **saved}


def save_settings(settings):
    SETTINGS_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def level_color(pct):
    return BAD if pct >= 90 else WARN if pct >= 70 else OK


def relative(target_ms):
    mins = max(0, int((target_ms - time.time() * 1000) // 60000))
    days, rest = divmod(mins, 1440)
    hours, mins = divmod(rest, 60)
    if days:
        return f"{days}d {hours}h 후"
    if hours:
        return f"{hours}h {mins}m 후"
    return f"{mins}m 후" if mins else "곧"


def font(px, bold=False):
    f = QFont("Segoe UI")
    f.setPixelSize(px)
    if bold:
        f.setWeight(QFont.DemiBold)
    return f


class UsageWidget(QWidget):
    """Lives inside the taskbar as a child window, so it shares the taskbar's z-order."""

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.settings = load_settings()
        self.usage, self.usage_mtime = None, None
        self.connected = False
        self.last_refresh = time.monotonic() - REFRESH_COOLDOWN_S
        self.light = winapi.light_theme()
        self.tray, self.tray_window = None, None
        self.labels, self.rings = [], []
        self.font_label, self.font_caption, self.font_pct = font(12, True), font(10), font(11, True)
        self.drag = None
        self.tip = QLabel(None, Qt.ToolTip)
        self.tip.setAttribute(Qt.WA_TranslucentBackground)
        self.tip_key = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)
        self.tick()

    # --- data ---------------------------------------------------------------
    def reload_usage(self):
        try:
            mtime = USAGE_FILE.stat().st_mtime_ns
        except OSError:
            return
        if mtime == self.usage_mtime:
            return
        try:
            self.usage = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
            self.usage_mtime = mtime
        except (OSError, ValueError):
            pass  # partially written file; retry next tick

    def group(self, gkey):
        return (self.usage or {}).get(gkey) or {}

    def caption(self, gkey, key, default):
        if key == "sevenDaySonnet":
            return self.group(gkey).get("sevenDaySonnetLabel") or default
        return default

    def stale(self):
        updated = (self.usage or {}).get("updatedAt")
        return not updated or time.time() * 1000 - updated > STALE_MS

    # --- placement ----------------------------------------------------------
    def tick(self):
        tray = winapi.taskbar()
        if not tray:
            return
        if self.tray is None:
            self.attach(tray)
        elif tray != self.tray:
            QApplication.exit(RESTART_CODE)  # Explorer restarted and took our child window with it
            return
        self.reload_usage()
        self.connected = winapi.host_connected()
        self.light = winapi.light_theme()
        self.place()
        self.update()

    def attach(self, tray):
        self.tray = tray
        self.tray_window = QWindow.fromWinId(tray)
        self.winId()
        self.windowHandle().setParent(self.tray_window)
        self.place()
        self.show()

    def place(self):
        dpr = QApplication.primaryScreen().devicePixelRatio()
        tray_w, tray_h = (v / dpr for v in winapi.client_size(self.tray))
        h = round(tray_h)
        w = self.layout(h)
        self.settings["x"] = x = max(0, min(self.settings["x"], round(tray_w) - w))
        rect = QRect(x, 0, w, h)
        if self.geometry() != rect:
            self.setGeometry(rect)

    def layout(self, h):
        show_labels = self.settings["labels"]
        caption_block = CAPTION_H + 1 if show_labels else 0
        d = round((h - 6 - caption_block) * RING_SCALE[self.settings["size"]])
        top = (h - d - caption_block) / 2
        self.font_pct.setPixelSize(max(9, round(d * 0.36)))
        fm_label, fm_caption = QFontMetrics(self.font_label), QFontMetrics(self.font_caption)
        self.labels, self.rings = [], []
        x = PAD
        for gkey, short, _, items in GROUPS:
            visible = [(k, c) for k, c in items if f"{gkey}.{k}" not in self.settings["hidden"]]
            if not visible:
                continue
            if self.rings:
                x += GROUP_GAP - RING_GAP
            if show_labels:
                lw = fm_label.horizontalAdvance(short)
                self.labels.append((short, QRectF(x, 0, lw, h)))
                x += lw + LABEL_GAP
            for key, default in visible:
                cap = self.caption(gkey, key, default)
                cw = max(d, fm_caption.horizontalAdvance(cap)) if show_labels else d
                ring = QRectF(x + (cw - d) / 2, top, d, d)
                self.rings.append((gkey, key, cap, ring, QRectF(x, top + d + 1, cw, CAPTION_H)))
                x += cw + RING_GAP
        return round(x - RING_GAP + PAD)

    def taskbar_top(self):
        return QApplication.primaryScreen().geometry().bottom() + 1 - self.height()

    # --- painting -----------------------------------------------------------
    def paintEvent(self, _):
        theme = THEMES[self.light]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        panel = QColor(theme["panel"])
        panel.setAlpha(max(1, round(255 * (100 - self.settings["transparency"]) / 100)))  # alpha 0 would pass clicks through
        p.setPen(Qt.NoPen)
        p.setBrush(panel)
        p.drawRoundedRect(QRectF(self.rect()), 6, 6)
        if self.stale() or not self.connected:
            p.setOpacity(0.45)
        p.setFont(self.font_label)
        p.setPen(theme["muted"])
        for text, rect in self.labels:
            p.drawText(rect, Qt.AlignVCenter | Qt.AlignLeft, text)
        for gkey, key, cap, ring, cap_rect in self.rings:
            self.paint_ring(p, theme, ring, self.group(gkey), key)
            if self.settings["labels"]:
                p.setFont(self.font_caption)
                p.setPen(theme["muted"])
                p.drawText(cap_rect, Qt.AlignCenter, cap)

    def paint_ring(self, p, theme, rect, data, key):
        pen_w = max(3.0, rect.width() * 0.13)
        arc = rect.adjusted(pen_w / 2, pen_w / 2, -pen_w / 2, -pen_w / 2)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(theme["track"], pen_w))
        p.drawEllipse(arc)
        v = data.get(key)
        if data.get("error"):
            text, color = "!", BAD
        elif v is None:
            text, color = "–", theme["muted"]
        else:
            text, color = str(round(v)), theme["text"]
            if v > 0:
                p.setPen(QPen(level_color(v), pen_w, Qt.SolidLine, Qt.RoundCap))
                p.drawArc(arc, 90 * 16, -round(v * 360 * 16 / 100))
        p.setFont(self.font_pct)
        p.setPen(color)
        p.drawText(rect, Qt.AlignCenter, text)

    # --- tooltip ------------------------------------------------------------
    # A custom popup placed fully above the taskbar: anything overlapping the
    # taskbar can end up underneath it once the Start menu has been opened.
    def show_tip(self, ring):
        if not ring:
            self.tip.hide()
            return
        theme = THEMES[self.light]
        self.tip.setStyleSheet(
            f"QLabel {{ background: {theme['tip_bg']}; color: {theme['text'].name()};"
            f" border: 1px solid {theme['tip_border']}; border-radius: 6px;"
            f" padding: 6px 9px; font: 12px 'Segoe UI'; }}")
        self.tip.setText(self.tooltip(*ring[:3]))
        self.tip.adjustSize()
        screen = QApplication.primaryScreen().geometry()
        x = QCursor.pos().x() - self.tip.width() // 2
        x = max(screen.left(), min(x, screen.right() + 1 - self.tip.width()))
        self.tip.move(x, self.taskbar_top() - self.tip.height() - 6)
        self.tip.show()

    def tooltip(self, gkey, key, cap):
        name = next(g[2] for g in GROUPS if g[0] == gkey)
        if not self.usage:
            return "데이터 없음 — Chrome 확장 연결 대기 중"
        data = self.group(gkey)
        if data.get("error"):
            return f"{name}: {data['error']}"
        v = data.get(key)
        lines = [f"{name} {cap} · {'–' if v is None else f'{round(v)}%'}"]
        reset = (data.get("resets") or {}).get(key)
        if reset:
            lines.append(f"리셋: {relative(reset)}")
        updated = self.usage.get("updatedAt")
        if updated:
            lines.append(f"갱신: {time.strftime('%H:%M', time.localtime(updated / 1000))}")
        if not self.connected:
            lines.append("Chrome 연결 안 됨 — 마지막으로 받은 값")
        elif self.stale():
            lines.append("15분 넘게 갱신되지 않음")
        return "\n".join(lines)

    # --- interaction --------------------------------------------------------
    def mouseMoveEvent(self, e):
        if self.drag:
            press_x, start_x = self.drag
            self.settings["x"] = start_x + round(e.globalPosition().x() - press_x)
            self.place()
            return
        ring = next((r for r in self.rings if r[3].contains(e.position())), None)
        key = ring[:2] if ring else None
        if key != self.tip_key:
            self.tip_key = key
            self.show_tip(ring)

    def leaveEvent(self, _):
        self.tip_key = None
        self.tip.hide()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.drag = (e.globalPosition().x(), self.settings["x"])
            self.tip_key = None
            self.tip.hide()

    def mouseReleaseEvent(self, e):
        if self.drag:
            self.drag = None
            save_settings(self.settings)

    def contextMenuEvent(self, e):
        self.tip_key = None
        self.tip.hide()
        menu = QMenu(self)
        wait = math.ceil(REFRESH_COOLDOWN_S - (time.monotonic() - self.last_refresh))
        if not self.connected:
            refresh = menu.addAction("새로고침 (Chrome 연결 안 됨)")
        elif wait > 0:
            refresh = menu.addAction(f"새로고침 ({wait}초 후 가능)")
        else:
            refresh = menu.addAction("새로고침", self.refresh)
        refresh.setEnabled(self.connected and wait <= 0)
        menu.addSeparator()
        menu.addAction(self.transparency_action(menu))
        menu.addSeparator()
        size_menu = menu.addMenu("원 크기")
        sizes = QActionGroup(size_menu)
        for key, name in SIZE_NAMES.items():
            a = size_menu.addAction(name)
            a.setCheckable(True)
            a.setChecked(self.settings["size"] == key)
            sizes.addAction(a)
            a.triggered.connect(lambda _=False, k=key: self.set_setting("size", k))
        items_menu = menu.addMenu("표시 항목")
        for gkey, _, name, items in GROUPS:
            for key, default in items:
                ident = f"{gkey}.{key}"
                a = items_menu.addAction(f"{name} {self.caption(gkey, key, default)}")
                a.setCheckable(True)
                a.setChecked(ident not in self.settings["hidden"])
                a.triggered.connect(lambda checked, i=ident: self.toggle_item(i, checked))
        labels = menu.addAction("라벨 표시")
        labels.setCheckable(True)
        labels.setChecked(self.settings["labels"])
        labels.triggered.connect(lambda checked: self.set_setting("labels", checked))
        menu.addAction("위치 초기화", lambda: self.set_setting("x", DEFAULTS["x"]))
        menu.addSeparator()
        # quit() first tries to close every QWindow, including the foreign taskbar
        # wrapper, which refuses and cancels the quit; exit() just stops the loop.
        menu.addAction("종료", lambda: QApplication.exit(0))
        menu.exec(QPoint(e.globalPos().x(), self.taskbar_top() - menu.sizeHint().height()))
        save_settings(self.settings)

    def transparency_action(self, menu):
        box = QWidget(menu)
        row = QHBoxLayout(box)
        row.setContentsMargins(12, 6, 12, 6)
        label = QLabel(box)
        label.setMinimumWidth(label.fontMetrics().horizontalAdvance("배경 투명도 100%") + 4)
        slider = QSlider(Qt.Horizontal, box)
        slider.setRange(0, 100)
        slider.setSingleStep(5)
        slider.setPageStep(10)
        slider.setFixedWidth(120)
        slider.setValue(self.settings["transparency"])

        def changed(v):
            label.setText(f"배경 투명도 {v}%")
            self.settings["transparency"] = v
            self.update()

        slider.valueChanged.connect(changed)
        changed(slider.value())
        row.addWidget(label)
        row.addWidget(slider)
        action = QWidgetAction(menu)
        action.setDefaultWidget(box)
        return action

    def refresh(self):
        if winapi.request_refresh():
            self.last_refresh = time.monotonic()

    def toggle_item(self, ident, checked):
        hidden = [h for h in self.settings["hidden"] if h != ident] + ([] if checked else [ident])
        if len(hidden) < ITEM_COUNT:  # keep at least one ring visible
            self.set_setting("hidden", hidden)

    def set_setting(self, key, value):
        self.settings[key] = value
        self.place()
        self.update()


def log_exception(exc_type, exc, tb):
    # pythonw has no console, so uncaught errors (e.g. in Qt event handlers) would vanish.
    with LOG_FILE.open("a", encoding="utf-8") as log:
        log.write(time.strftime("%Y-%m-%d %H:%M:%S\n") + "".join(traceback.format_exception(exc_type, exc, tb)) + "\n")
    sys.__excepthook__(exc_type, exc, tb)


def main():
    app = QApplication(sys.argv)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    sys.excepthook = log_exception
    lock = QLockFile(str(DATA_DIR / "widget.lock"))
    if not lock.tryLock(100):
        return  # another instance is already running
    _widget = UsageWidget()
    code = app.exec()
    lock.unlock()
    if code == RESTART_CODE:
        subprocess.Popen([sys.executable, *sys.argv])
    sys.exit(code)


if __name__ == "__main__":
    main()
