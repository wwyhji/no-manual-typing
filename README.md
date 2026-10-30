# 叫我手打？没门

> `no-manual-typing` — 模拟键盘输入，在聚焦的文本框内逐字/逐键打入指定文字。

一个单文件命令行工具：把要输入的文字（中文 / 英文 / 符号），模拟成真实键盘输入，
打到**当前光标聚焦的文本框**里。无需复制粘贴，也无需切换输入法。

Apache-2.0。

## 核心能力

| 能力 | 说明 |
|------|------|
| **中文逐字注入** | `SendInput` + `KEYEVENTF_UNICODE` 逐字发 `WM_CHAR`，绕过输入法与剪贴板，防粘贴拦截的输入框照样能打 |
| **英文逐键** | `pyautogui.write` 逐键模拟真实按键 |
| **剪贴板粘贴** | `--paste` 显式兜底（含 emoji 等非 BMP 字符时自动回退） |
| **倒计时聚焦** | `--delay N` 给你时间点进目标框 |
| **按键收尾** | `--enter` / `--tab` / `--key` 输入后追加回车、Tab 或组合键 |

## 安装

```bash
pip install -r requirements.txt        # 或 pip install pyautogui pyperclip
```

依赖：Python 3.9+、`pyautogui`、`pyperclip`。中文逐字注入需 Windows。

## 快速上手

```bash
# 纯英文 → 逐键模拟
python type_text.py "hello world" --delay 3

# 含中文 → 逐字 Unicode 注入
python type_text.py "你好，世界" --delay 3

# 从管道读入（支持多行长文本）
echo "从管道读入" | python type_text.py --delay 3

# 输入后按回车提交
python type_text.py "搜索关键词" --delay 5 --enter

# 强制剪贴板粘贴（含 emoji 时自动回退到粘贴）
python type_text.py "内容 😀" --paste
```

## 参数

| 参数 | 作用 |
|------|------|
| `--delay N` | 倒计时秒数（默认 3），给你时间点进目标框；`0` 立即输入 |
| `--paste` | 强制剪贴板粘贴（默认：英文逐键，中文逐字注入） |
| `--interval N` | 逐键/逐字间隔秒数（默认 0.02） |
| `--enter` / `--tab` | 输入后按回车 / Tab |
| `--key KEY` | 输入后额外按键，可重复，如 `--key ctrl+s` |

## 工作原理

| 模式 | 触发条件 | 机制 |
|------|----------|------|
| 逐键 `ascii` | 纯 ASCII | `pyautogui.write` 真实按键 |
| 逐字 `unicode` | 含中文（BMP 内） | `SendInput` `KEYEVENTF_UNICODE` 发 `WM_CHAR` |
| 粘贴 `paste` | `--paste` 或含非 BMP（emoji） | 剪贴板 + `Ctrl+V` |

## 安全

- `pyautogui.FAILSAFE` 默认开启：倒计时内把鼠标甩到**屏幕角落**立即中止，不发出任何输入。
- 工具只向当前聚焦窗口注入键盘事件，不读取、不上传任何内容。

## License

Apache License 2.0，见 [LICENSE](LICENSE)。版权 wwyhji。
