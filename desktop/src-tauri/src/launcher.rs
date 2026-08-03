use std::io::{BufRead, BufReader, Read, Write};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::Manager;

const MAX_LINE_BYTES: usize = 8192;

#[cfg(target_os = "windows")]
mod winapi {
    use std::ffi::c_void;

    pub const JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: u32 = 0x2000;
    pub const JOB_OBJECT_EXTENDED_LIMIT_INFORMATION: u32 = 9;

    #[repr(C)]
    pub struct IoCounters {
        pub read_operation_count: u64,
        pub write_operation_count: u64,
        pub other_operation_count: u64,
        pub read_transfer_count: u64,
        pub write_transfer_count: u64,
        pub other_transfer_count: u64,
    }

    #[repr(C)]
    pub struct BasicLimitInformation {
        pub per_process_user_time_limit: i32,
        pub per_job_user_time_limit: i32,
        pub limit_flags: u32,
        pub minimum_working_set_size: usize,
        pub maximum_working_set_size: usize,
        pub active_process_limit: u32,
        pub affiliate_process_limit: u32,
        pub priority_class: u32,
        pub scheduling_class: u32,
    }

    #[repr(C)]
    pub struct JobObjectExtendedLimitInformation {
        pub basic_limit_information: BasicLimitInformation,
        pub process_memory_limit: usize,
        pub job_memory_limit: usize,
        pub peak_process_memory_used: usize,
        pub peak_job_memory_used: usize,
        pub io_counters: IoCounters,
    }

    extern "system" {
        pub fn CreateJobObjectW(lp_job_attributes: *const c_void, lp_name: *const c_void) -> *mut c_void;
        pub fn SetInformationJobObject(
            h_job: *mut c_void,
            job_object_information_class: u32,
            lp_job_object_information: *const c_void,
            cb_job_object_information_length: u32,
        ) -> i32;
        pub fn AssignProcessToJobObject(h_job: *mut c_void, h_process: *mut c_void) -> i32;
        pub fn CloseHandle(h_object: *mut c_void) -> i32;
    }

    pub struct JobGuard {
        handle: *mut c_void,
    }

    unsafe impl Send for JobGuard {}
    unsafe impl Sync for JobGuard {}

    impl JobGuard {
        pub fn new() -> Option<Self> {
            unsafe {
                let handle = CreateJobObjectW(std::ptr::null(), std::ptr::null());
                if handle.is_null() {
                    return None;
                }
                let mut info = JobObjectExtendedLimitInformation {
                    basic_limit_information: BasicLimitInformation {
                        per_process_user_time_limit: 0,
                        per_job_user_time_limit: 0,
                        limit_flags: JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
                        minimum_working_set_size: 0,
                        maximum_working_set_size: 0,
                        active_process_limit: 0,
                        affiliate_process_limit: 0,
                        priority_class: 0,
                        scheduling_class: 0,
                    },
                    process_memory_limit: 0,
                    job_memory_limit: 0,
                    peak_process_memory_used: 0,
                    peak_job_memory_used: 0,
                    io_counters: IoCounters {
                        read_operation_count: 0,
                        write_operation_count: 0,
                        other_operation_count: 0,
                        read_transfer_count: 0,
                        write_transfer_count: 0,
                        other_transfer_count: 0,
                    },
                };
                let ok = SetInformationJobObject(
                    handle,
                    JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                    &mut info as *mut _ as *const c_void,
                    std::mem::size_of::<JobObjectExtendedLimitInformation>() as u32,
                );
                if ok == 0 {
                    CloseHandle(handle);
                    return None;
                }
                Some(JobGuard { handle })
            }
        }

        pub fn assign(&self, child: &std::process::Child) -> bool {
            unsafe {
                use std::os::windows::io::AsRawHandle;
                let h_process = child.as_raw_handle() as *mut c_void;
                AssignProcessToJobObject(self.handle, h_process) != 0
            }
        }
    }

    impl Drop for JobGuard {
        fn drop(&mut self) {
            unsafe {
                if !self.handle.is_null() {
                    CloseHandle(self.handle);
                }
            }
        }
    }
}

pub struct LauncherProcess {
    child: Mutex<Option<Child>>,
    stdin: Mutex<Option<std::process::ChildStdin>>,
    stdout: Mutex<Option<BufReader<std::process::ChildStdout>>>,
    #[cfg(target_os = "windows")]
    job: Mutex<Option<winapi::JobGuard>>,
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
            #[cfg(target_os = "windows")]
            job: Mutex::new(None),
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

        #[cfg(target_os = "windows")]
        {
            if let Some(job) = winapi::JobGuard::new() {
                if job.assign(&child) {
                    eprintln!("[eve] launcher process assigned to job object");
                } else {
                    eprintln!("[eve] WARNING: failed to assign launcher to job object");
                }
                *self.job.lock().unwrap() = Some(job);
            }
        }

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
            let mut buf = Vec::with_capacity(256);
            let n = reader
                .read_until(b'\n', &mut buf)
                .map_err(|e| format!("read stdout: {e}"))?;
            if n == 0 {
                return Ok(String::new());
            }
            if std::str::from_utf8(&buf).is_err() {
                eprintln!("[eve] WARNING: launcher stdout contained non-UTF8 bytes, decoded lossy");
            }
            let line = String::from_utf8_lossy(&buf).to_string();
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
