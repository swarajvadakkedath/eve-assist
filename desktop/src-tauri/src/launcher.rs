use std::io::{BufRead, BufReader, Read, Write};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::Manager;

pub struct LauncherProcess {
    child: Mutex<Option<Child>>,
    stdin: Mutex<Option<std::process::ChildStdin>>,
    stdout: Mutex<Option<BufReader<std::process::ChildStdout>>>,
}

fn bundled_python(resource_dir: &std::path::Path) -> Option<(String, String)> {
    let python_path = resource_dir.join("python").join("python.exe");
    if python_path.is_file() {
        eprintln!("[eve] using bundled Python: {}", python_path.display());
        Some((python_path.to_string_lossy().to_string(), "-m".to_string()))
    } else {
        eprintln!("[eve] bundled Python not found at: {}", python_path.display());
        None
    }
}

fn system_python() -> Option<(String, String)> {
    let candidates = [("python", "-m"), ("python3", "-m"), ("py", "-m")];
    for (exe, flag) in &candidates {
        if Command::new(exe)
            .arg("--version")
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .is_ok()
        {
            return Some((exe.to_string(), flag.to_string()));
        }
    }
    None
}

fn resource_dirs(handle: &tauri::AppHandle) -> (PathBuf, PathBuf) {
    #[cfg(debug_assertions)]
    {
        let cargo_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let root = cargo_dir
            .parent()
            .and_then(|p| p.parent())
            .unwrap_or(&cargo_dir)
            .to_path_buf();
        return (root.clone(), root);
    }
    #[cfg(not(debug_assertions))]
    {
        if let Ok(res_dir) = handle.path().resource_dir() {
            let install_dir = std::env::current_exe()
                .ok()
                .and_then(|p| p.parent().map(|p| p.to_path_buf()))
                .unwrap_or_else(|| res_dir.clone());
            (res_dir, install_dir)
        } else {
            let fallback = PathBuf::from(".");
            (fallback.clone(), fallback)
        }
    }
}

fn find_launcher_base(resource_dir: &std::path::Path, install_dir: &std::path::Path) -> PathBuf {
    let candidates = [
        resource_dir.join("launcher"),
        install_dir.join("launcher"),
        install_dir.join("resources").join("launcher"),
    ];
    for c in &candidates {
        if c.join("tauri_integration.py").is_file() {
            eprintln!("[eve] launcher found at: {}", c.display());
            return c.parent().unwrap_or(install_dir).to_path_buf();
        }
    }
    eprintln!("[eve] WARNING: launcher module not found, using install dir");
    install_dir.to_path_buf()
}

fn build_pythonpath(resource_dir: &std::path::Path, launcher_base: &std::path::Path) -> String {
    let mut paths: Vec<String> = Vec::new();

    let launcher_parent = resource_dir.join("launcher");
    if launcher_parent.is_dir() {
        if let Some(parent) = launcher_parent.parent() {
            paths.push(parent.to_string_lossy().to_string());
        }
    }

    let backend_aios = resource_dir.join("backend").join("aios");
    if backend_aios.is_dir() {
        if let Some(parent) = backend_aios.parent() {
            paths.push(parent.to_string_lossy().to_string());
        }
    }

    let site_packages = resource_dir.join("python").join("Lib").join("site-packages");
    if site_packages.is_dir() {
        paths.push(site_packages.to_string_lossy().to_string());
    }

    let dlls_dir = resource_dir.join("python").join("DLLs");
    if dlls_dir.is_dir() {
        paths.push(dlls_dir.to_string_lossy().to_string());
    }

    paths.push(launcher_base.to_string_lossy().to_string());

    let existing = std::env::var("PYTHONPATH").unwrap_or_default();
    if !existing.is_empty() {
        paths.push(existing);
    }

    paths.join(";")
}

impl LauncherProcess {
    pub fn new() -> Self {
        LauncherProcess {
            child: Mutex::new(None),
            stdin: Mutex::new(None),
            stdout: Mutex::new(None),
        }
    }

    pub fn spawn(&self, handle: &tauri::AppHandle) -> Result<(), String> {
        let (resource_dir, install_dir) = resource_dirs(handle);
        let launcher_base = find_launcher_base(&resource_dir, &install_dir);

        let python_exe;
        let python_flag;
        #[cfg(not(debug_assertions))]
        {
            if let Some(bundled) = bundled_python(&resource_dir) {
                python_exe = bundled.0;
                python_flag = bundled.1;
            } else {
                let system = system_python().ok_or_else(|| {
                    format!(
                        "Python not found. Eve requires Python 3.12+.\n\
                         Bundled Python not found and no system Python available.\n\
                         Install Python from https://python.org or reinstall Eve."
                    )
                })?;
                python_exe = system.0;
                python_flag = system.1;
            }
        }
        #[cfg(debug_assertions)]
        {
            let system = system_python().ok_or_else(|| {
                format!(
                    "Python not found. Eve requires Python 3.12+.\n\
                     Install Python from https://python.org and ensure it's on PATH.\n\
                     Tried: python, python3, py"
                )
            })?;
            python_exe = system.0;
            python_flag = system.1;
        }

        let mut cmd = Command::new(&python_exe);
        cmd.arg(&python_flag).arg("launcher.tauri_integration");
        cmd.current_dir(&launcher_base);
        cmd.stdin(Stdio::piped());
        cmd.stdout(Stdio::piped());
        cmd.stderr(Stdio::piped());

        let pythonpath = build_pythonpath(&resource_dir, &launcher_base);
        if !pythonpath.is_empty() {
            cmd.env("PYTHONPATH", &pythonpath);
        }

        let mut child = cmd.spawn().map_err(|e| {
            format!(
                "Failed to start Python ({}) from {}: {}\n\
                 Ensure `{} -m launcher.tauri_integration` works from:\n{}",
                python_exe,
                launcher_base.display(),
                e,
                python_exe,
                launcher_base.display()
            )
        })?;

        let child_stdin = child.stdin.take().ok_or("failed to capture stdin")?;
        let child_stdout = child.stdout.take().ok_or("failed to capture stdout")?;

        *self.child.lock().unwrap() = Some(child);
        *self.stdin.lock().unwrap() = Some(child_stdin);
        *self.stdout.lock().unwrap() = Some(BufReader::new(child_stdout));

        Ok(())
    }

    pub fn stderr_output(&self) -> Result<String, String> {
        let mut guard = self.child.lock().map_err(|e| e.to_string())?;
        if let Some(ref mut child) = *guard {
            if let Some(ref mut stderr) = child.stderr {
                let mut buf = String::new();
                stderr
                    .read_to_string(&mut buf)
                    .map_err(|e| format!("read stderr: {e}"))?;
                return Ok(buf);
            }
        }
        Ok(String::new())
    }

    pub fn send_command(&self, cmd: &str) -> Result<(), String> {
        let payload = serde_json::json!({
            "type": "command",
            "command": cmd,
        });
        self.send_raw(&payload.to_string())
    }

    pub fn send_raw(&self, json: &str) -> Result<(), String> {
        let mut stdin = self.stdin.lock().map_err(|e| e.to_string())?;
        if let Some(stdin) = stdin.as_mut() {
            writeln!(stdin, "{json}").map_err(|e| format!("write stdin: {e}"))?;
            stdin.flush().map_err(|e| format!("flush stdin: {e}"))?;
            Ok(())
        } else {
            Err("stdin not available".to_string())
        }
    }

    pub fn read_line(&self) -> Result<String, String> {
        let mut stdout = self.stdout.lock().map_err(|e| e.to_string())?;
        if let Some(reader) = stdout.as_mut() {
            let mut line = String::new();
            reader
                .read_line(&mut line)
                .map_err(|e| format!("read stdout: {e}"))?;
            Ok(line.trim().to_string())
        } else {
            Err("stdout not available".to_string())
        }
    }

    pub fn wait_for_ready(&self, timeout_secs: u64) -> Result<bool, String> {
        let start = std::time::Instant::now();
        loop {
            if start.elapsed().as_secs() > timeout_secs {
                let stderr = self.stderr_output()?;
                if !stderr.is_empty() {
                    return Err(format!(
                        "timeout waiting for launcher ready (>{timeout_secs}s).\n\
                         Python stderr:\n{stderr}"
                    ));
                }
                return Ok(false);
            }
            let line = self.read_line()?;
            if line.is_empty() {
                std::thread::sleep(std::time::Duration::from_millis(100));
                continue;
            }
            if let Ok(v) = serde_json::from_str::<serde_json::Value>(&line) {
                if v.get("type").and_then(|t| t.as_str()) == Some("status") {
                    let state = v.get("state").and_then(|s| s.as_str()).unwrap_or("");
                    match state {
                        "ready" => return Ok(true),
                        "error" => {
                            let error = v
                                .get("error")
                                .and_then(|e| e.as_str())
                                .unwrap_or("unknown");
                            let stderr = self.stderr_output().unwrap_or_default();
                            let details = if stderr.is_empty() {
                                error.to_string()
                            } else {
                                format!("{error}\nstderr:\n{stderr}")
                            };
                            return Err(details);
                        }
                        _ => {}
                    }
                }
            }
        }
    }

    pub fn kill(&self) {
        if let Ok(mut guard) = self.child.lock() {
            if let Some(ref mut child) = *guard {
                let _ = child.kill();
                let _ = child.wait();
            }
            *guard = None;
        }
    }
}

impl Drop for LauncherProcess {
    fn drop(&mut self) {
        self.kill();
    }
}
