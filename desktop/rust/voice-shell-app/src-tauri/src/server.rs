// Python Server Management
// Handles starting, stopping, and monitoring the Python backend

use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::io::{BufRead, BufReader};
use std::thread;

lazy_static::lazy_static! {
    static ref SERVER_PROCESS: Arc<Mutex<Option<Child>>> = Arc::new(Mutex::new(None));
    static ref SERVER_PORT: Arc<Mutex<u16>> = Arc::new(Mutex::new(8765));
    static ref SERVER_LANGUAGE: Arc<Mutex<String>> = Arc::new(Mutex::new("en".to_string()));
}

/// Start the Python Voice Shell server
pub fn start_server(port: u16, language: &str) -> Result<(), String> {
    // Check if already running
    if is_server_running() {
        return Err("Server is already running".to_string());
    }
    
    // Store configuration
    *SERVER_PORT.lock().unwrap() = port;
    *SERVER_LANGUAGE.lock().unwrap() = language.to_string();
    
    // Find Python executable
    let python = find_python().ok_or("Python not found")?;
    
    log::info!("Starting Python server with: {} -m streamware.voice_shell_server", python);
    
    // Start the Python process
    let child = Command::new(&python)
        .args([
            "-m", "streamware.voice_shell_server",
            "--port", &port.to_string(),
            "--lang", language,
        ])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to spawn Python process: {}", e))?;
    
    let pid = child.id();
    log::info!("Python server started with PID: {}", pid);
    
    // Store the process handle
    *SERVER_PROCESS.lock().unwrap() = Some(child);
    
    // Start log forwarding thread
    start_log_forwarder();
    
    // Wait for server to be ready (check HTTP port)
    let http_port = port + 1;
    let max_attempts = 30;  // 30 seconds timeout
    for attempt in 1..=max_attempts {
        if check_server_ready(http_port) {
            log::info!("Server ready on port {} after {} seconds", http_port, attempt);
            return Ok(());
        }
        std::thread::sleep(std::time::Duration::from_secs(1));
        log::debug!("Waiting for server... attempt {}/{}", attempt, max_attempts);
    }
    
    log::warn!("Server may not be fully ready after {} seconds", max_attempts);
    Ok(())
}

/// Check if the HTTP server is responding
fn check_server_ready(port: u16) -> bool {
    use std::net::TcpStream;
    use std::time::Duration;
    
    let addr = format!("127.0.0.1:{}", port);
    TcpStream::connect_timeout(
        &addr.parse().unwrap(),
        Duration::from_millis(500)
    ).is_ok()
}

/// Stop the Python server
pub fn stop_server() {
    if let Some(mut child) = SERVER_PROCESS.lock().unwrap().take() {
        log::info!("Stopping Python server...");
        
        // Try graceful shutdown first
        #[cfg(unix)]
        {
            unsafe {
                libc::kill(child.id() as i32, libc::SIGTERM);
            }
        }
        
        #[cfg(windows)]
        {
            let _ = child.kill();
        }
        
        // Wait for process to exit
        match child.wait() {
            Ok(status) => log::info!("Python server exited with: {}", status),
            Err(e) => log::error!("Error waiting for Python server: {}", e),
        }
    }
}

/// Check if server is running
pub fn is_server_running() -> bool {
    if let Some(ref mut child) = *SERVER_PROCESS.lock().unwrap() {
        // Try to get exit status without blocking
        match child.try_wait() {
            Ok(Some(_)) => false, // Process has exited
            Ok(None) => true,     // Process is still running
            Err(_) => false,      // Error checking status
        }
    } else {
        false
    }
}

/// Get current server port
pub fn get_server_port() -> u16 {
    *SERVER_PORT.lock().unwrap()
}

/// Get current language
pub fn get_language() -> String {
    SERVER_LANGUAGE.lock().unwrap().clone()
}

/// Set language
pub fn set_language(language: &str) {
    *SERVER_LANGUAGE.lock().unwrap() = language.to_string();
}

/// Find Python executable
fn find_python() -> Option<String> {
    // Try common Python paths
    let candidates = [
        "python3",
        "python",
        "/usr/bin/python3",
        "/usr/local/bin/python3",
    ];
    
    for candidate in candidates {
        if Command::new(candidate)
            .arg("--version")
            .output()
            .is_ok()
        {
            return Some(candidate.to_string());
        }
    }
    
    // Try to find in virtual environment
    if let Ok(venv) = std::env::var("VIRTUAL_ENV") {
        let venv_python = format!("{}/bin/python", venv);
        if std::path::Path::new(&venv_python).exists() {
            return Some(venv_python);
        }
    }
    
    None
}

/// Forward Python process logs
fn start_log_forwarder() {
    if let Some(ref mut child) = *SERVER_PROCESS.lock().unwrap() {
        // Forward stdout
        if let Some(stdout) = child.stdout.take() {
            thread::spawn(move || {
                let reader = BufReader::new(stdout);
                for line in reader.lines().filter_map(|l| l.ok()) {
                    log::info!("[Python] {}", line);
                }
            });
        }
        
        // Forward stderr
        if let Some(stderr) = child.stderr.take() {
            thread::spawn(move || {
                let reader = BufReader::new(stderr);
                for line in reader.lines().filter_map(|l| l.ok()) {
                    log::warn!("[Python] {}", line);
                }
            });
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_find_python() {
        assert!(find_python().is_some());
    }
}
