// Streamware Voice Shell - Tauri Desktop Application
// High-performance Rust backend with system WebView

#![cfg_attr(
    all(not(debug_assertions), target_os = "windows"),
    windows_subsystem = "windows"
)]

mod commands;
mod server;

use tauri::Manager;

fn main() {
    env_logger::init();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Start Python server on app startup
            let port = 8765;
            let language = "en";
            
            log::info!("Starting Voice Shell backend server on port {}", port);
            
            match server::start_server(port, language) {
                Ok(_) => {
                    log::info!("Backend server started successfully");
                    
                    // Navigate to the server URL
                    if let Some(window) = app.get_webview_window("main") {
                        let url = format!("http://127.0.0.1:{}", port + 1);
                        log::info!("Loading UI from {}", url);
                        
                        // Wait a moment for server to be ready
                        std::thread::sleep(std::time::Duration::from_secs(2));
                        
                        let _ = window.eval(&format!(
                            "window.location.href = '{}'",
                            url
                        ));
                    }
                }
                Err(e) => {
                    log::error!("Failed to start backend server: {}", e);
                }
            }
            
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_server_status,
            commands::restart_server,
            commands::get_app_version,
            commands::get_language,
            commands::set_language,
            commands::show_notification,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
