# macOS 自动录入工具开发计划

## Summary

- 当前目录 `C:\Users\Lenovo\Desktop\work_mac` 用于创建一个新的 macOS 自动录入工具项目。
- 技术路线：Python + PySide6 配置窗口 + 后台驻留；macOS 实际录入使用 PyObjC Quartz 按键事件；Windows 11 仅做界面、状态机和单元测试。
- 构建路线：Windows 开发，GitHub Actions macOS runner 打包 `.app` 和未签名 `.dmg`。PyInstaller 不能从 Windows 交叉打包 macOS，所以必须在 macOS runner 或真实 Mac 上打包。

## Key Changes

- 新建 Python 项目结构：`src/mac_auto_typer/`、`tests/`、`.github/workflows/build-macos.yml`、`pyproject.toml`、`README.md`。
- GUI 功能：多行文本编辑、导入 `.txt/.md`、清空/重置进度、速度滑块、当前字符位置/总字数、运行状态显示。
- 后台功能：关闭窗口后隐藏到托盘/菜单栏，程序继续驻留；托盘菜单支持显示窗口、开始/继续、暂停、退出。
- 全局快捷键：`Ctrl+1` 开始/继续，`Ctrl+2` 暂停；快捷键在软件窗口失焦时仍生效。
- 运行期间键盘锁定：自动录入开始后阻止用户物理键盘输入，避免人工输入夹入目标文本；`Ctrl+2` 作为保留暂停键，暂停后立即释放键盘。
- 录入状态机：`idle/running/paused/completed/error`；每成功发送一个字符后再递增索引，暂停后从原字符位置继续。
- macOS 后端：通过 PyObjC 的 `Quartz` 调用 CoreGraphics 键盘事件，使用 `CGEventKeyboardSetUnicodeString` 发送 Unicode 字符。
- macOS 输入锁：通过 Quartz session event tap 拦截用户键盘事件，允许本程序发出的 Quartz 事件通过。
- Windows 后端：默认使用 mock typer，不真实控制系统输入；用于本机开发调试、测试暂停/续打/速度逻辑。
- 权限处理：首次运行检测并提示用户授予 macOS Accessibility/Input Monitoring 权限；不尝试静默提权。
- 分发：未签名 `.dmg`，内部使用；README 明确首次打开可能需要用户手动信任。

## Build Plan

- 使用 Python 3.12，依赖按平台区分：`PySide6`、`pynput`、`pyobjc-framework-Quartz` 仅 macOS、`pyobjc-framework-ApplicationServices` 仅 macOS、`pyinstaller`、`pytest`。
- GitHub Actions 使用 macOS matrix 构建 Apple Silicon 与 Intel 版本；runner 选择固定 macOS 标签，避免 `latest` 漂移。
- 构建步骤：安装依赖，运行测试，执行 PyInstaller `--windowed` app bundle 构建，用 `hdiutil` 生成 `.dmg`，上传 artifacts。
- 不做签名和公证；后续若需要正式商用分发，再加入 Apple Developer 证书、codesign、notarization。

## Test Plan

- 单元测试：文本导入编码、字符索引、暂停/继续、完成状态、速度延迟计算、重复快捷键输入。
- 单元测试新增：输入锁启动/释放、输入锁失败时阻止自动录入。
- Windows 本地验证：GUI 可打开，导入文本可显示，mock typer 可记录输出字符序列，暂停续打索引正确。
- macOS 手工验收：TextEdit、浏览器输入框、聊天输入框各测试一次；输入中文、英文、标点、换行；运行中普通键盘输入不会进入目标框；按 `Ctrl+2` 暂停后可手动输入，再按 `Ctrl+1` 续打。
- 验收标准：1000 字中文文本多次暂停/继续后无重复、无漏字；窗口不在前台时快捷键有效；运行期间用户键盘输入被阻止；速度调节在下一字符周期生效。

## Assumptions

- 第一版只支持手动编辑和导入 `.txt/.md`，不支持 DOCX/Excel。
- 第一版按“键盘逐字模拟”实现，不使用剪贴板逐字粘贴。
- 目标是用户主动控制的文本录入辅助工具，不做隐藏运行、刷屏、自动提交或绕过平台限制的功能。
