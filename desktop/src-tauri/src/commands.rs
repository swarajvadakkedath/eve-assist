use serde::Serialize;
use std::sync::Arc;
use tauri::{AppHandle, Manager, State};

use crate::launcher::LauncherProcess;

#[derive(Serialize)]
pub struct DesktopStatus {
    pub launcher_state: String,
    pub backend_healthy: bool,
    pub backend_url: String,
    pub uptime: f64,
}

#[tauri::command]
pub async fn get_status(
    launcher: State<'_, Arc<LauncherProcess>>,
) -> Result<DesktopStatus, String> {
    launcher.send_command("status")?;
    let line = launcher.read_line()?;
    let v: serde_json::Value =
        serde_json::from_str(&line).map_err(|e| format!("bad json: {e}"))?;
    let state = v.get("state").and_then(|s| s.as_str()).unwrap_or("unknown");
    let health = v
        .get("backend_healthy")
        .and_then(|h| h.as_bool())
        .unwrap_or(false);
    let url = v
        .get("backend_url")
        .and_then(|u| u.as_str())
        .unwrap_or("http://127.0.0.1:8456");
    let uptime = v.get("uptime").and_then(|u| u.as_f64()).unwrap_or(0.0);
    Ok(DesktopStatus {
        launcher_state: state.to_string(),
        backend_healthy: health,
        backend_url: url.to_string(),
        uptime,
    })
}

#[tauri::command]
pub async fn get_health(
    launcher: State<'_, Arc<LauncherProcess>>,
) -> Result<serde_json::Value, String> {
    launcher.send_command("health")?;
    let line = launcher.read_line()?;
    serde_json::from_str(&line).map_err(|e| format!("bad json: {e}"))
}

#[tauri::command]
pub async fn restart_backend(
    app: AppHandle,
    launcher: State<'_, Arc<LauncherProcess>>,
) -> Result<bool, String> {
    launcher.send_command("restart")?;
    let line = launcher.read_line()?;
    let val: serde_json::Value =
        serde_json::from_str(&line).map_err(|e| format!("bad json: {e}"))?;
    if val.get("ok").and_then(|o| o.as_bool()).unwrap_or(false) {
        if let Some(window) = app.get_webview_window("main") {
            let _ = window.show();
            let _ = window.set_focus();
        }
        return Ok(true);
    }
    Ok(false)
}

#[tauri::command]
pub async fn shutdown(
    app: AppHandle,
    launcher: State<'_, Arc<LauncherProcess>>,
) -> Result<(), String> {
    let _ = launcher.send_command("shutdown");
    std::thread::sleep(std::time::Duration::from_millis(500));
    app.exit(0);
    Ok(())
}

#[tauri::command]
pub async fn show_notification(
    app: AppHandle,
    title: String,
    body: String,
) -> Result<(), String> {
    use tauri_plugin_notification::NotificationExt;
    app.notification()
        .builder()
        .title(&title)
        .body(&body)
        .show()
        .map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn open_url(url: String) -> Result<(), String> {
    let escaped = url.replace('"', "%22");
    let _ = std::process::Command::new("cmd")
        .args(["/c", "start", &escaped])
        .spawn();
    Ok(())
}

#[tauri::command]
pub async fn get_app_config(
    launcher: State<'_, Arc<LauncherProcess>>,
) -> Result<serde_json::Value, String> {
    launcher.send_command("get_config")?;
    let line = launcher.read_line()?;
    serde_json::from_str(&line).map_err(|e| format!("bad json: {e}"))
}

#[tauri::command]
pub async fn set_app_config(
    launcher: State<'_, Arc<LauncherProcess>>,
    key: String,
    value: serde_json::Value,
) -> Result<bool, String> {
    let cmd = serde_json::json!({
        "type": "command",
        "command": "set_config",
        "key": key,
        "value": value,
    });
    launcher.send_raw(&cmd.to_string())?;
    let line = launcher.read_line()?;
    let val: serde_json::Value =
        serde_json::from_str(&line).map_err(|e| format!("bad json: {e}"))?;
    Ok(val.get("ok").and_then(|o| o.as_bool()).unwrap_or(false))
}
