// === ANCHOR: REPORT_PDF_START ===
//! 보고서 무인 PDF 스파이크 (계획 2b / Task 1).
//!
//! 목적: 오프스크린 WKWebView 가 `createPDF` 로 *빈 PDF 가 아닌* 실제 PDF 를
//! 만들 수 있음을 이 macOS 장비에서 증명한다. 결정적 코드가 아니라 컴파일러/런타임과
//! 반복하는 R&D 스파이크다(부록 A 참조).
//!
//! 핵심 gotcha: `.visible(false)` 면 WKWebView 렌더 파이프라인이 멈춰 빈 PDF 가 된다.
//! 그래서 `.visible(true)` 로 띄우되 화면 밖(-10000,-10000)으로 보낸다.

use std::path::PathBuf;
use std::sync::mpsc;
use std::time::Duration;

use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

/// 고정 테스트 HTML 을 오프스크린 창에 로드하고, 로드 완료 후 createPDF 로 `out` 에 저장한다.
///
/// 반환: 성공 시 out 경로 문자열, 실패 시 에러 메시지.
#[tauri::command]
pub(crate) async fn export_report_pdf_spike(
    app: tauri::AppHandle,
    out: String,
) -> Result<String, String> {
    let out_path = PathBuf::from(&out);

    // 고정 HTML (한글 포함) 을 임시 파일로 쓴 뒤 file:// 로 로드한다.
    // data:URL 대신 임시파일을 쓰는 이유: urlencoding 크레이트 의존 회피 +
    // data:URL 길이 한계를 피한다(부록 A 의 대체 경로).
    let html = "<!doctype html><html><head><meta charset='utf-8'></head>\
                <body style='font-family:serif'>\
                <h1>스파이크 보고서</h1><p>한글 PDF 렌더 확인</p></body></html>";
    let mut tmp_html = std::env::temp_dir();
    tmp_html.push(format!("vibelign_pdf_spike_{}.html", std::process::id()));
    std::fs::write(&tmp_html, html).map_err(|e| format!("임시 HTML 쓰기 실패: {e}"))?;

    let file_url = format!("file://{}", tmp_html.to_string_lossy());
    let parsed = file_url
        .parse()
        .map_err(|e| format!("file:// URL 파싱 실패: {e}"))?;

    let label = "pdf-export-spike";
    if let Some(w) = app.get_webview_window(label) {
        let _ = w.close();
    }

    // 로드 완료 → createPDF(메인 스레드). 채널로 완료 신호를 받는다.
    // on_page_load 는 빌더 메서드라 build() 전에 등록해야 한다(WebviewWindow 가
    // 핸들러 첫 인자로 전달된다). Fn 콜백이므로 tx/out 은 move 캡처 후 매 호출 clone.
    let (tx, rx) = mpsc::channel::<Result<(), String>>();
    let out_for_cb = out_path.clone();

    let win = WebviewWindowBuilder::new(&app, label, WebviewUrl::External(parsed))
        .title("_pdf_spike")
        .inner_size(800.0, 1000.0)
        // 보이게(렌더 파이프라인 진입) — 단 화면 밖으로. visible(false) 면 빈 PDF.
        .visible(true)
        .position(-10000.0, -10000.0)
        .on_page_load(move |w, payload| {
            if payload.event() != tauri::webview::PageLoadEvent::Finished {
                return;
            }
            let out2 = out_for_cb.clone();
            let tx2 = tx.clone();
            let _ = w.with_webview(move |webview| {
            #[cfg(target_os = "macos")]
            unsafe {
                use block2::RcBlock;
                use objc2_foundation::{NSData, NSError};
                use objc2_web_kit::WKWebView;

                // wv.inner() 은 *mut c_void (WKWebView 포인터). objc2 참조로 캐스팅.
                let view: &WKWebView = &*(webview.inner() as *const WKWebView);

                let tx3 = tx2.clone();
                let out3 = out2.clone();
                let block = RcBlock::new(
                    move |data: *mut NSData, err: *mut NSError| {
                        if !err.is_null() {
                            let msg = (*err).localizedDescription();
                            let _ = tx3.send(Err(format!("createPDF error: {msg}")));
                            return;
                        }
                        if data.is_null() {
                            let _ = tx3.send(Err("createPDF: NSData 가 null".into()));
                            return;
                        }
                        // 즉시 바이트를 복사한다(NSData 를 보존하지 않음).
                        let data_ref: &NSData = &*data;
                        let bytes = data_ref.to_vec();
                        match std::fs::write(&out3, &bytes) {
                            Ok(_) => {
                                let _ = tx3.send(Ok(()));
                            }
                            Err(e) => {
                                let _ = tx3.send(Err(format!("PDF 쓰기 실패: {e}")));
                            }
                        }
                    },
                );

                // configuration=None → 기본 PDF 설정. completionHandler 는 메인스레드 async.
                view.createPDFWithConfiguration_completionHandler(None, &block);
            }
                #[cfg(not(target_os = "macos"))]
                {
                    let _ = (webview, &out2);
                    let _ = tx2.send(Err("spike: macOS 전용".into()));
                }
            });
        })
        .build()
        .map_err(|e| e.to_string())?;

    // 완료 신호 대기(타임아웃 ~15s).
    let res = rx
        .recv_timeout(Duration::from_secs(15))
        .map_err(|_| "PDF 생성 타임아웃".to_string());

    let _ = win.close();
    let _ = std::fs::remove_file(&tmp_html);

    res?.map(|_| out_path.to_string_lossy().into_owned())
}
// === ANCHOR: REPORT_PDF_END ===
