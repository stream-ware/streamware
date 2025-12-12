// Tauri IPC Commands
// These functions are callable from JavaScript via invoke()

use tauri::command;

use crate::server;

/// Get the current server status
#[command]
pub async fn get_server_status() -> Result<ServerStatus, String> {
    let is_running = server::is_server_running();
    let port = server::get_server_port();
    
    Ok(ServerStatus {
        running: is_running,
        port,
        url: format!("http://127.0.0.1:{}", port + 1),
    })
}

/// Restart the backend server
#[command]
pub async fn restart_server(port: u16, language: String) -> Result<String, String> {
    server::stop_server();
    
    // Wait for clean shutdown
    std::thread::sleep(std::time::Duration::from_millis(500));
    
    match server::start_server(port, &language) {
        Ok(_) => Ok("Server restarted successfully".to_string()),
        Err(e) => Err(format!("Failed to restart server: {}", e)),
    }
}

/// Get application version
#[command]
pub fn get_app_version() -> String {
    env!("CARGO_PKG_VERSION").to_string()
}

/// Get current language setting
#[command]
pub fn get_language() -> String {
    server::get_language()
}

/// Set language
#[command]
pub async fn set_language(language: String) -> Result<String, String> {
    server::set_language(&language);
    Ok(format!("Language set to: {}", language))
}

/// Show a system notification
#[command]
pub fn show_notification(title: String, body: String) -> Result<(), String> {
    notify_rust::Notification::new()
        .summary(&title)
        .body(&body)
        .icon("dialog-information")
        .show()
        .map_err(|e| e.to_string())?;
    
    Ok(())
}

// Response types
#[derive(serde::Serialize)]
pub struct ServerStatus {
    running: bool,
    port: u16,
    url: String,
}
