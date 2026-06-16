// === ANCHOR: REPORT_PDF_START ===
//! 보고서 무인 PDF 내보내기 (계획 2b / Task 2).
//!
//! 증분 1 의 `vib report --format html` 이 만든 `.vibelign/reports/*.html` 을
//! 오프스크린 웹뷰에 로드해 사용자 개입 없이(headless) PDF 로 변환한다.
//! macOS=WKWebView `createPDF`, Windows=WebView2 `PrintToPdf`.
//!
//! 핵심 gotcha(macOS): `.visible(false)` 면 WKWebView 렌더 파이프라인이 멈춰 빈 PDF 가
//! 된다. 그래서 `.visible(true)` 로 띄우되 화면 밖(-10000,-10000)으로 보낸다.

use std::path::{Component, Path, PathBuf};
use std::sync::mpsc;
use std::time::Duration;

use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

/// 경로 컴포넌트에 `..`(ParentDir) 이 포함되어 있는지 검사한다.
fn has_parent_dir(path: &Path) -> bool {
    path.components()
        .any(|c| matches!(c, Component::ParentDir))
}

/// out_pdf 를 containment 검증한다.
/// - `.pdf` 확장자
/// - `..` 컴포넌트 없음 (사이드-이펙트 없이 먼저 검사)
/// - 부모 디렉터리 생성 후 정규화 경로가 `canon_root` 하위
/// 성공 시 정규화된 out_pdf PathBuf 반환.
pub(crate) fn validate_out_pdf(
    canon_root: &Path,
    out_pdf: &str,
) -> Result<PathBuf, String> {
    let path = PathBuf::from(out_pdf);

    // 1) 확장자 검사
    let ext_ok = path
        .extension()
        .and_then(|e| e.to_str())
        .map(|e| e.eq_ignore_ascii_case("pdf"))
        .unwrap_or(false);
    if !ext_ok {
        return Err(format!("출력 경로가 .pdf 가 아닙니다: {out_pdf}"));
    }

    // 2) `..` / 탈출 컴포넌트 검사 (FS 사이드이펙트 없이)
    if has_parent_dir(&path) {
        return Err(format!("출력 경로에 상위 디렉터리 참조(..)가 포함되어 있습니다: {out_pdf}"));
    }

    // 3) 부모 디렉터리 생성 (검증 통과 후에만)
    if let Some(parent) = path.parent() {
        if !parent.as_os_str().is_empty() {
            std::fs::create_dir_all(parent)
                .map_err(|e| format!("출력 디렉터리 생성 실패({}): {e}", parent.display()))?;
        }
    }

    // 4) 컨테인먼트: 정규화 경로가 canon_root 하위여야 한다.
    //    부모가 존재하게 된 뒤에 canonicalize 해야 성공한다.
    let parent = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let canon_parent = std::fs::canonicalize(parent)
        .map_err(|e| format!("출력 디렉터리 정규화 실패: {e}"))?;
    if !canon_parent.starts_with(canon_root) {
        return Err("출력 경로가 프로젝트 밖을 가리킵니다".into());
    }

    Ok(path)
}

/// html_path 를 containment 검증한다.
/// - `..` 컴포넌트 없음
/// - 파일이 존재해야 함
/// - 정규화 경로가 `canon_root` 하위
/// 성공 시 정규화된 PathBuf 반환.
pub(crate) fn validate_html_path(
    canon_root: &Path,
    html_path: &str,
) -> Result<PathBuf, String> {
    let path = PathBuf::from(html_path);

    // 1) `..` 검사
    if has_parent_dir(&path) {
        return Err(format!("HTML 경로에 상위 디렉터리 참조(..)가 포함되어 있습니다: {html_path}"));
    }

    // 2) 존재 확인 + 정규화
    let canon_file = std::fs::canonicalize(&path)
        .map_err(|_| format!("HTML 파일을 찾을 수 없습니다: {html_path}"))?;

    // 3) 컨테인먼트
    if !canon_file.starts_with(canon_root) {
        return Err("기획안 경로가 프로젝트 밖을 가리킵니다".into());
    }

    Ok(canon_file)
}

/// 절대 파일 경로를 퍼센트-인코딩된 `file:///…` URL 로 변환한다.
/// 한글·공백·`#` 등 특수문자를 올바르게 인코딩한다.
pub(crate) fn file_url_for(path: &Path) -> Result<String, String> {
    url::Url::from_file_path(path)
        .map(|u| u.to_string())
        .map_err(|()| format!("file:// URL 변환 실패: {}", path.display()))
}

/// 보고서 HTML 파일을 오프스크린 웹뷰에 로드하고, 로드 완료 후 네이티브 print-to-PDF 로
/// `out_pdf` 에 저장한다.
///
/// `root`: 프로젝트 루트 절대 경로. `html_path`·`out_pdf` 모두 이 경로 하위여야 한다.
///
/// 반환: 성공 시 out_pdf 경로 문자열, 실패 시 에러 메시지.
#[tauri::command]
pub(crate) async fn export_report_pdf(
    app: tauri::AppHandle,
    root: String,
    html_path: String,
    out_pdf: String,
) -> Result<String, String> {
    // 프로젝트 루트 정규화 (모든 containment 검사의 기준).
    let canon_root = std::fs::canonicalize(&root)
        .map_err(|e| format!("프로젝트 루트 정규화 실패({root}): {e}"))?;

    let html_file = validate_html_path(&canon_root, &html_path)?;
    let out_path = validate_out_pdf(&canon_root, &out_pdf)?;

    // 실제 HTML 파일을 퍼센트-인코딩된 file:// URL 로 로드한다.
    // url::Url::from_file_path 가 한글·공백·# 등을 올바르게 인코딩한다.
    let file_url_str = file_url_for(&html_file)?;
    let parsed = file_url_str
        .parse()
        .map_err(|e| format!("file:// URL 파싱 실패: {e}"))?;

    let label = "pdf-export";
    if let Some(w) = app.get_webview_window(label) {
        let _ = w.close();
    }

    // 로드 완료 → 네이티브 print-to-PDF(메인 스레드). 채널로 완료 신호를 받는다.
    // on_page_load 는 빌더 메서드라 build() 전에 등록한다. Fn 콜백이므로 tx/out 은
    // move 캡처 후 매 호출 clone.
    let (tx, rx) = mpsc::channel::<Result<(), String>>();
    let out_for_cb = out_path.clone();

    let win = WebviewWindowBuilder::new(&app, label, WebviewUrl::External(parsed))
        .title("_pdf_export")
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
                #[cfg(windows)]
                unsafe {
                    use webview2_com::Microsoft::Web::WebView2::Win32::{
                        ICoreWebView2_7, ICoreWebView2PrintToPdfCompletedHandler,
                    };
                    use webview2_com::PrintToPdfCompletedHandler;
                    use windows::core::{Interface, PCWSTR};

                    let tx3 = tx2.clone();
                    let out_str = out2.to_string_lossy().into_owned();

                    // controller() → CoreWebView2() → ICoreWebView2_7(PrintToPdf 보유).
                    let result = (|| -> Result<(), String> {
                        let controller = webview.controller();
                        let core = controller
                            .CoreWebView2()
                            .map_err(|e| format!("CoreWebView2 획득 실패: {e}"))?;
                        let wv7: ICoreWebView2_7 = core
                            .cast()
                            .map_err(|e| format!("ICoreWebView2_7 캐스트 실패: {e}"))?;

                        // 절대경로 와이드 문자열(널 종단).
                        let wide: Vec<u16> =
                            out_str.encode_utf16().chain(std::iter::once(0)).collect();

                        // PrintToPdf 완료 핸들러: 성공 여부를 채널로 전달한다.
                        // CompletedClosure<HRESULT, BOOL> 의 인자는 변환된 형태로 들어온다:
                        //   error_code: windows::core::Result<()> (HRESULT::ok())
                        //   is_success: bool (BOOL::as_bool())
                        let tx4 = tx3.clone();
                        let handler: ICoreWebView2PrintToPdfCompletedHandler =
                            PrintToPdfCompletedHandler::create(Box::new(
                                move |error_code: windows::core::Result<()>, is_success: bool| {
                                    match error_code {
                                        Err(e) => {
                                            let _ = tx4
                                                .send(Err(format!("PrintToPdf 콜백 오류: {e}")));
                                        }
                                        Ok(()) if is_success => {
                                            let _ = tx4.send(Ok(()));
                                        }
                                        Ok(()) => {
                                            let _ = tx4.send(Err(
                                                "PrintToPdf 실패(is_success=false)".into(),
                                            ));
                                        }
                                    }
                                    Ok(())
                                },
                            ));

                        wv7.PrintToPdf(PCWSTR(wide.as_ptr()), None, &handler)
                            .map_err(|e| format!("PrintToPdf 호출 실패: {e}"))?;
                        Ok(())
                    })();

                    if let Err(e) = result {
                        let _ = tx2.send(Err(e));
                    }
                }
                #[cfg(not(any(target_os = "macos", windows)))]
                {
                    let _ = (webview, &out2);
                    let _ = tx2.send(Err("PDF 내보내기는 macOS/Windows 에서만 지원됩니다".into()));
                }
            });
        })
        .build()
        .map_err(|e| e.to_string())?;

    // 완료 신호 대기(타임아웃 ~30s).
    let res = rx
        .recv_timeout(Duration::from_secs(30))
        .map_err(|_| "PDF 생성 타임아웃".to_string());

    let _ = win.close();

    res?.map(|_| out_path.to_string_lossy().into_owned())
}
// === ANCHOR: REPORT_PDF_END ===
