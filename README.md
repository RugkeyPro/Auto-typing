# MacAutoTyper

MacAutoTyper is a user-controlled macOS background text entry helper. The setup window is used to prepare text and speed settings; the app then keeps running from the macOS menu bar/tray. After the user places the cursor in Word, a chat box, a browser address bar, or another text field, `Ctrl+1` starts simulated character-by-character input and `Ctrl+2` pauses it.

## Features

- Edit text directly in the app.
- Import `.txt` and `.md` files.
- Adjust typing delay from 20 to 800 ms per character.
- Use `Ctrl+1` to start or resume and `Ctrl+2` to pause.
- Preserve the current character position when paused.
- Suppress physical keyboard input while auto typing is running, while still allowing `Ctrl+2` to pause.
- Minimize the setup window without losing normal Dock/window recovery.
- Use a mock typing backend on Windows so development and tests do not control the local system.

## Local Development on Windows 11

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
python -m mac_auto_typer
```

On Windows, the app opens normally but system-wide typing and keyboard suppression are mocked. This is intentional; macOS event posting and user-keyboard blocking are only enabled on macOS.

## macOS Permissions

The macOS build needs Accessibility permission to post keyboard events and Input Monitoring permission for global hotkeys and the temporary keyboard blocker.

Open:

`System Settings -> Privacy & Security -> Accessibility`

and:

`System Settings -> Privacy & Security -> Input Monitoring`

Allow `MacAutoTyper`. If the app is unsigned, macOS may also require manually approving the first launch in Privacy & Security.

## Build macOS App

PyInstaller is not a cross-compiler. Build the macOS `.app` on macOS, either locally on a Mac or through the included GitHub Actions workflow.

Manual macOS build:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
python -m PyInstaller build/macos/MacAutoTyper.spec --clean --noconfirm
hdiutil create -volname "MacAutoTyper" -srcfolder "dist/MacAutoTyper.app" -ov -format UDZO "dist_dmg/MacAutoTyper.dmg"
```

GitHub Actions:

1. Push the repository to GitHub.
2. Open Actions.
3. Run `Build macOS App`.
4. Download `MacAutoTyper-arm64-dmg` for Apple Silicon Macs or `MacAutoTyper-x64-dmg` for Intel Macs.
5. Open the artifact folder, then open the `.dmg` inside it.
6. In the mounted DMG window, drag `MacAutoTyper.app` to `Applications`.
7. Open `Applications`, right-click `MacAutoTyper.app`, and choose `Open`.

Do not open the raw `.app` folder from a GitHub artifact zip. GitHub artifact zips can lose macOS executable permissions for app bundles. Use the `.dmg` artifact, or use the `.app.tar.gz` artifact if you specifically need the raw app bundle with permissions preserved.

If opening still appears to do nothing, run these commands on the Mac and send the output:

```bash
open /Applications/MacAutoTyper.app
cat ~/Library/Logs/MacAutoTyper/MacAutoTyper.log
/Applications/MacAutoTyper.app/Contents/MacOS/MacAutoTyper
```

The GitHub Actions warning about Node.js 20 is not related to the app runtime. It only warns that GitHub's reusable workflow actions will move to Node.js 24 in the future.

## Closing the App

Close the setup window with the red close button or use `Cmd+Q`. The app exits and releases keyboard blocking. If an older build is stuck in the background, run:

```bash
pkill -f MacAutoTyper
```

On macOS, `Ctrl+1` and `Ctrl+2` are handled by the same Quartz event tap used for keyboard blocking. If they do not work after changing permissions, quit and reopen the app so macOS applies the new Input Monitoring permission.

## Without a Local Mac

You can still build and run non-interactive macOS checks through GitHub Actions:

1. Push this folder to a GitHub repository.
2. Open the repository's `Actions` tab.
3. Run `Build macOS App`.
4. Confirm the workflow passes `Run tests`, `Run macOS dependency smoke check`, and `Verify app bundle`.
5. Download the generated `MacAutoTyper-*-dmg` artifact and open the `.dmg` inside it.

This verifies the macOS dependency set, Quartz imports, backend selection, controller behavior, PyInstaller packaging, and app bundle structure. It does not verify real cursor typing, Accessibility permission prompts, or keyboard suppression inside Word/chat/browser fields. Those require an interactive macOS desktop session.

Practical options for final manual validation:

- Use a temporary cloud Mac or rented Mac desktop where you can log in, open System Settings, grant permissions, and test TextEdit/browser/chat input fields.
- Ask a tester with a Mac to run the `.dmg` and follow the checklist below.
- If you later get Apple Developer signing credentials, add signing/notarization before broader distribution.

## Acceptance Checklist

- In TextEdit, type Chinese, English, punctuation, and newlines.
- While auto typing is running, press normal letter/number keys and confirm they are not inserted into the target field.
- Press `Ctrl+2` while typing and confirm the app pauses.
- After `Ctrl+2`, confirm normal manual typing works again.
- Press `Ctrl+1` again and confirm typing resumes from the next unsent character.
- Repeat pause/resume several times on a long text and confirm there are no duplicated or skipped characters.
- Confirm speed changes affect the next character cycle.
