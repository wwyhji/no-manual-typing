#!/usr/bin/env python3
"""Keyboard text injector — type specified text into the focused text box.

Simulates keyboard input into whatever text field currently has focus:
- Pure-ASCII text is typed key-by-key via pyautogui (real keystrokes).
- Chinese (BMP) text is injected character-by-character via SendInput
  KEYEVENTF_UNICODE, producing WM_CHAR events — no clipboard, no IME
  dependency, so it also works in paste-blocked inputs.
- Text containing non-BMP chars (emoji) falls back to clipboard paste.

Usage:
    python type_text.py "hello world" --delay 3
    python type_text.py "你好，世界" --delay 3
    echo "从管道读入" | python type_text.py --delay 3
    python type_text.py "大段中文" --paste   # 强制剪贴板粘贴

Safety: pyautogui.FAILSAFE is on — move the cursor to a screen corner
during the countdown to abort before any input is sent.
"""

from __future__ import annotations

import argparse
import sys
import time

import pyautogui
import pyperclip

# Windows console may default to GBK; use UTF-8 so Chinese prompts render
# and piped-in UTF-8 text decodes correctly.
if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    try:
        sys.stdin.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

pyautogui.FAILSAFE = True   # corner flick aborts
pyautogui.PAUSE = 0.05


# ── Windows SendInput Unicode injection ──────────────────────────────────
# Injects BMP code points as WM_CHAR, bypassing IME and clipboard, so
# Chinese can be "typed" character-by-character even into paste-blocked
# fields. Non-Windows platforms fall back to clipboard paste.

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    _INPUT_KEYBOARD = 1
    _KEYEVENTF_KEYUP = 0x0002
    _KEYEVENTF_UNICODE = 0x0004

    class _KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_void_p),
        ]

    class _MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_void_p),
        ]

    class _HARDWAREINPUT(ctypes.Structure):
        _fields_ = [
            ("uMsg", wintypes.DWORD),
            ("wParamL", wintypes.WORD),
            ("wParamH", wintypes.WORD),
        ]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [
            ("ki", _KEYBDINPUT),
            ("mi", _MOUSEINPUT),
            ("hi", _HARDWAREINPUT),
        ]

    class _INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [
            ("type", wintypes.DWORD),
            ("u", _INPUTUNION),
        ]

    def _send_unicode_char(code: int) -> None:
        """Inject one BMP code point as a key down + key up pair."""
        for flags in (_KEYEVENTF_UNICODE, _KEYEVENTF_UNICODE | _KEYEVENTF_KEYUP):
            inp = _INPUT()
            inp.type = _INPUT_KEYBOARD
            inp.ki.wVk = 0
            inp.ki.wScan = code
            inp.ki.dwFlags = flags
            inp.ki.dwExtraInfo = None
            ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
else:
    def _send_unicode_char(code: int) -> None:
        raise RuntimeError("Unicode injection requires Windows")


def _is_ascii(text: str) -> bool:
    return all(ord(c) < 128 for c in text)


def _is_bmp(text: str) -> bool:
    return all(ord(c) < 0x10000 for c in text)


def _paste(text: str) -> None:
    """Paste text via clipboard + Ctrl+V (reliable fallback)."""
    pyperclip.copy(text)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")


def _type_unicode(text: str, interval: float) -> None:
    """Type text character-by-character via Unicode WM_CHAR injection."""
    for ch in text:
        _send_unicode_char(ord(ch))
        if interval:
            time.sleep(interval)


def _press_key(key: str) -> None:
    """Press a single key, or a hotkey combo like 'ctrl+s'."""
    parts = [k.strip() for k in key.split("+")]
    if len(parts) > 1:
        pyautogui.hotkey(*parts)
    else:
        pyautogui.press(parts[0])


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="在聚焦的文本框内模拟键盘输入指定文字",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("text", nargs="?", help="要输入的文字；省略时从 stdin 读取")
    p.add_argument("--delay", type=float, default=3.0,
                   help="聚焦倒计时秒数，给你时间点进目标文本框（默认 3，设为 0 立即输入）")
    p.add_argument("--paste", action="store_true",
                   help="强制剪贴板粘贴（默认：英文逐键，中文逐字注入）")
    p.add_argument("--interval", type=float, default=0.02,
                   help="逐键/逐字间隔秒数（默认 0.02）")
    p.add_argument("--enter", action="store_true", help="输入后按回车")
    p.add_argument("--tab", action="store_true", help="输入后按 Tab")
    p.add_argument("--key", action="append", default=[],
                   help="输入后额外按的键/组合键，可重复，如 --key enter --key 'ctrl+s'")
    args = p.parse_args(argv)

    text = args.text
    if text is None:
        if sys.stdin.isatty():
            p.error("未提供文字：作为参数传入，或通过管道/stdin 输入")
        text = sys.stdin.read().rstrip("\n")
    if not text:
        p.error("文字为空")

    # Countdown so the user can click into the target text box.
    if args.delay > 0:
        print(f"聚焦目标文本框，{args.delay:.1f}s 后开始输入"
              f"（倒计时内把鼠标移到屏幕角落可中止）", flush=True)
        whole = int(args.delay)
        for i in range(whole, 0, -1):
            print(f"  {i}...", flush=True)
            time.sleep(1)
        time.sleep(args.delay - whole)

    # Choose injection mode.
    if args.paste:
        mode = "paste"
    elif _is_ascii(text):
        mode = "ascii"
    elif _is_bmp(text) and sys.platform == "win32":
        mode = "unicode"
    else:
        mode = "paste"

    try:
        if mode == "ascii":
            pyautogui.write(text, interval=args.interval)
        elif mode == "unicode":
            _type_unicode(text, args.interval)
        else:
            _paste(text)

        if args.enter:
            pyautogui.press("enter")
        if args.tab:
            pyautogui.press("tab")
        for k in args.key:
            _press_key(k)
    except pyautogui.FailSafeException:
        print("已中止：检测到鼠标位于屏幕角落", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1

    mode_names = {"ascii": "逐键", "unicode": "逐字注入", "paste": "粘贴"}
    print(f"完成：已用「{mode_names[mode]}」方式输入 {len(text)} 字符", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
