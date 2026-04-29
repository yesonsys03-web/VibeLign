mod backup;
mod constants;
mod db;
mod ipc;
mod security;

use ipc::protocol::{handle, EngineRequest, EngineResponse};
use std::io::{self, Read};

fn main() {
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

fn print_response(response: EngineResponse) {
    match serde_json::to_string(&response) {
        Ok(json) => println!("{json}"),
        Err(error) => println!(
            "{{\"status\":\"error\",\"code\":\"SERIALIZE_FAILED\",\"message\":{}}}",
            serde_json::to_string(&error.to_string()).unwrap_or_else(|_| "\"unknown\"".to_string())
        ),
    }
}
