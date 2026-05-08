// === ANCHOR: MAIN_START ===
mod backup;
mod constants;
mod db;
mod ipc;
mod project_scan;
mod security;

use ipc::protocol::{handle, EngineRequest, EngineResponse};
use std::io::{self, Read};
use std::path::PathBuf;

fn main() {
    if let Some(root) = daemon_root_arg(std::env::args().skip(1).collect()) {
        if let Err(error) = ipc::daemon::run_daemon(root) {
            eprintln!("{error}");
            std::process::exit(1);
        }
        return;
    }

    let mut input = String::new();
    if let Err(error) = io::stdin().read_to_string(&mut input) {
        print_response(EngineResponse::Error {
            code: "STDIN_READ_FAILED".to_string(),
            message: error.to_string(),
        });
        return;
    }
    let request = match serde_json::from_str::<EngineRequest>(&input) {
        Ok(request) => request,
        Err(error) => {
            print_response(EngineResponse::Error {
                code: "INVALID_JSON".to_string(),
                message: error.to_string(),
            });
            return;
        }
    };
    print_response(handle(request));
}

fn daemon_root_arg(args: Vec<String>) -> Option<PathBuf> {
    if args.first().map(String::as_str) != Some("--daemon") {
        return None;
    }
    let mut index = 1;
    while index < args.len() {
        if args[index] == "--root" {
            return args.get(index + 1).map(PathBuf::from);
        }
        index += 1;
    }
    None
}

fn print_response(response: EngineResponse) {
    match serde_json::to_string(&response) {
        Ok(json) => println!("{json}"),
        Err(error) => println!(
            "{{\"status\":\"error\",\"code\":\"SERIALIZE_FAILED\",\"message\":{}}}",
            serde_json::to_string(&error.to_string()).unwrap_or_else(|_| "\"unknown\"".to_string())
        ),
    }
}
// === ANCHOR: MAIN_END ===
