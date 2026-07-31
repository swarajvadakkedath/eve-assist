; Eve NSIS Uninstall Hooks
; Ensures bundled Python/runtime files are fully removed on uninstall.

!macro NSIS_HOOK_POSTUNINSTALL
  ; Force-remove bundled directories containing runtime artifacts.
  ; Use $LOCALAPPDATA (not ${LOCALAPPDATA}) for proper variable resolution.
  RMDir /r "$LOCALAPPDATA\Eve\python"
  RMDir /r "$LOCALAPPDATA\Eve\backend"
  RMDir /r "$LOCALAPPDATA\Eve\launcher"
  RMDir /r "$LOCALAPPDATA\Eve\tesseract"
  Delete "$LOCALAPPDATA\Eve\WebView2Loader.dll"
  Delete "$LOCALAPPDATA\Eve\*.exe"
  RMDir "$LOCALAPPDATA\Eve"
!macroend
