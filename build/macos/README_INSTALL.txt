MacAutoTyper install and first launch

1. Open this DMG.
2. Drag MacAutoTyper.app to Applications.
3. Open Applications.
4. Right-click MacAutoTyper.app and choose Open.
5. If macOS blocks the app, open System Settings -> Privacy & Security and allow it.
6. Grant Accessibility and Input Monitoring permissions when testing auto typing.

If double-clicking does nothing, run these commands in Terminal and send the output:

open /Applications/MacAutoTyper.app
cat ~/Library/Logs/MacAutoTyper/MacAutoTyper.log
/Applications/MacAutoTyper.app/Contents/MacOS/MacAutoTyper
