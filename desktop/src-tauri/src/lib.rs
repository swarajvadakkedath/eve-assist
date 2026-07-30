mod commands;
mod launcher;

use launcher::LauncherProcess;
use std::sync::Arc;
use std::time::Instant;
use tauri::{
    menu::{MenuBuilder, MenuItemBuilder},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Emitter, Manager, WindowEvent,
};
use tauri_plugin_shell::ShellExt;

fn startup_log(msg: &str) {
    eprintln!("[eve] {msg}");
    if std::fs::create_dir_all(startup_log_dir()).is_ok() {
        if let Ok(mut f) = std::fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(format!("{}\\startup.log", startup_log_dir()))
        {
            use std::io::Write;
            let _ = writeln!(f, "[{}] {}", chrono_now(), msg);
        }
    }
}

fn chrono_now() -> String {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = now.as_secs();
    let millis = now.as_millis() % 1000;
    format!("{}.{:03}", secs, millis)
}

fn startup_log_dir() -> String {
    let home = std::env::var("USERPROFILE")
        .or_else(|_| std::env::var("HOME"))
        .unwrap_or_else(|_| ".".to_string());
    format!("{}\\.eve\\logs", home)
}

fn startup_info() -> String {
    #[cfg(debug_assertions)]
    {
        let cargo_dir = std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let root = cargo_dir
            .parent()
            .and_then(|p| p.parent())
            .map(|p| p.to_path_buf())
            .unwrap_or_default();
        format!("project root: {}", root.display())
    }
    #[cfg(not(debug_assertions))]
    {
        format!(
            "install dir: {}",
            std::env::current_exe()
                .ok()
                .and_then(|p| p.parent().map(|p| p.to_path_buf()))
                .unwrap_or_default()
                .display()
        )
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let started = Instant::now();
    startup_log("[1/8] Starting Eve Desktop");

    if let Err(e) = try_run() {
        startup_log(&format!("[FATAL] {e}"));

        let msg = format!(
            "Eve Desktop failed to start.\n\n{0}\n\n\
             Check %USERPROFILE%\\.eve\\logs\\startup.log for details.",
            e
        );

        show_error_dialog("Eve Desktop — Startup Error", &msg);
        std::process::exit(1);
    }

    startup_log(&format!(
        "[8/8] Shutdown complete (uptime {:.1}s)",
        started.elapsed().as_secs_f64()
    ));
}

fn try_run() -> Result<(), String> {
    startup_log("[2/8] Resolving environment");
    startup_log(&startup_info());

    tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .setup(|app| {
            startup_log("[3/8] Starting embedded Python launcher");

            let lp = Arc::new(LauncherProcess::new());
            lp.spawn(app.handle())
                .map_err(|e| format!("launcher spawn failed: {e}"))?;
            startup_log("[3/8] Python launcher process spawned");

            app.manage(lp.clone());

            startup_log("[5/8] Creating tray icon and menu");
            setup_tray(app)?;
            startup_log("[5/8] Tray created");

            startup_log("[6/8] Showing main window");
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }

            // --- BACKGROUND: wait for backend health ---
            // NEVER block the main thread. The window and event loop start now.
            // The backend is checked on a background thread.
            startup_log("[4/8] Waiting for backend health (background thread)");
            let app_handle = app.handle().clone();
            let lp_watcher = lp.clone();
            std::thread::Builder::new()
                .name("eve-backend-watcher".into())
                .spawn(move || {
                    let start = Instant::now();
                    let _ = app_handle.emit("eve:backend-status", serde_json::json!({
                        "state": "starting",
                    }));

                    match lp_watcher.wait_for_ready(60) {
                        Ok(true) => {
                            let elapsed = start.elapsed().as_secs_f64();
                            startup_log(&format!("[4/8] Backend ready in {elapsed:.1}s"));
                            let _ = app_handle.emit("eve:backend-ready", serde_json::json!({
                                "uptime": elapsed,
                            }));
                            let _ = app_handle.emit("eve:startup-complete", serde_json::json!({
                                "uptime": elapsed,
                                "ready": true,
                            }));
                        }
                        Ok(false) => {
                            startup_log("[4/8] WARNING: Backend not ready within 60s (timeout)");
                            let _ = app_handle.emit("eve:backend-status", serde_json::json!({
                                "state": "timeout",
                            }));
                        }
                        Err(e) => {
                            startup_log(&format!("[4/8] ERROR: Backend failed: {e}"));
                            let _ = app_handle.emit("eve:backend-status", serde_json::json!({
                                "state": "error",
                                "error": e,
                            }));
                        }
                    }
                })
                .map_err(|e| format!("failed to spawn background thread: {e}"))?;

            startup_log("[7/8] Window visible, event loop starting");
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                let _ = window.hide();
                api.prevent_close();
            }
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_status,
            commands::get_health,
            commands::restart_backend,
            commands::shutdown,
            commands::show_notification,
            commands::open_url,
            commands::get_app_config,
            commands::set_app_config,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Eve Desktop");

    Ok(())
}

fn setup_tray(app: &tauri::App) -> Result<(), Box<dyn std::error::Error>> {
    let open = MenuItemBuilder::with_id("open", "Open Eve").build(app)?;
    let devtools = MenuItemBuilder::with_id("devtools", "Developer Tools").build(app)?;
    let health = MenuItemBuilder::with_id("health", "Health Dashboard").build(app)?;
    let restart = MenuItemBuilder::with_id("restart", "Restart Backend").build(app)?;
    let settings = MenuItemBuilder::with_id("settings", "Settings").build(app)?;
    let logs = MenuItemBuilder::with_id("logs", "Logs").build(app)?;
    let exit = MenuItemBuilder::with_id("exit", "Exit").build(app)?;

    let menu = MenuBuilder::new(app)
        .item(&open)
        .separator()
        .item(&devtools)
        .item(&health)
        .separator()
        .item(&restart)
        .item(&settings)
        .item(&logs)
        .separator()
        .item(&exit)
        .build()?;

    TrayIconBuilder::new()
        .tooltip("Eve OS")
        .menu(&menu)
        .on_menu_event(|app, event| match event.id().as_ref() {
            "open" => show_main_window(app),
            "devtools" => open_url_cmd(app, "http://127.0.0.1:8456/docs"),
            "health" => open_url_cmd(app, "http://127.0.0.1:8456/api/v1/system/health"),
            "restart" => {
                let _ = app
                    .get_webview_window("main")
                    .map(|w| w.emit("eve:restart-backend", ()));
            }
            "settings" => show_main_window(app),
            "logs" => open_logs(app),
            "exit" => {
                startup_log("exit requested via tray");
                let lp = app.state::<Arc<LauncherProcess>>();
                let _ = lp.send_command("shutdown");
                std::thread::sleep(std::time::Duration::from_millis(500));
                app.exit(0);
            }
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                if let Some(window) = tray.app_handle().get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
        })
        .build(app)?;

    Ok(())
}

fn show_main_window(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.set_focus();
    }
}

fn open_url_cmd(app: &tauri::AppHandle, url: &str) {
    #[allow(deprecated)]
    let _ = app.shell().open(url, None);
}

fn open_logs(_app: &tauri::AppHandle) {
    let logs_dir = dirs_data_dir();
    let _ = std::process::Command::new("explorer")
        .arg(&logs_dir)
        .spawn();
}

fn show_error_dialog(title: &str, message: &str) {
    #[cfg(windows)]
    unsafe {
        use std::ffi::OsStr;
        use std::os::windows::ffi::OsStrExt;
        extern "system" {
            fn MessageBoxW(
                hWnd: *mut std::ffi::c_void,
                lpText: *const u16,
                lpCaption: *const u16,
                uType: u32,
            ) -> i32;
        }
        let wide_title: Vec<u16> = OsStr::new(title).encode_wide().chain(std::iter::once(0)).collect();
        let wide_msg: Vec<u16> = OsStr::new(message).encode_wide().chain(std::iter::once(0)).collect();
        MessageBoxW(std::ptr::null_mut(), wide_msg.as_ptr(), wide_title.as_ptr(), 0x00000010);
    }
    #[cfg(not(windows))]
    eprintln!("[eve] FATAL: {title}: {message}");
}

fn dirs_data_dir() -> String {
    let home = std::env::var("USERPROFILE")
        .or_else(|_| std::env::var("HOME"))
        .unwrap_or_else(|_| ".".to_string());
    format!("{}\\.eve\\logs", home)
}
