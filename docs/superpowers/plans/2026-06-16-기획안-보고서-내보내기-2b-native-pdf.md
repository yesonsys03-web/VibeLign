# 기획안 → 보고서 무인 PDF (네이티브 웹뷰) Implementation Plan — 계획 2b/4

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`).
> **⚠ 이 계획은 1·2a 와 성격이 다르다.** Task 1 은 **결정적 구현이 아니라 스파이크(R&D)** 다 — 컴파일러/런타임과 반복하며 맞춰야 하는 `unsafe` 네이티브 Rust 이고, 검증에 **`cargo build` + 실제 GUI 앱 실행**이 필요하다. macOS 오프스크린 렌더링 이슈가 접근법 자체를 막을 수 있다(§Task 1 의 실패 분기 참조).

**Goal:** 생성된 보고서 HTML 을 **사용자 개입 없이(headless)** PDF 로 변환해 `.vibelign/reports/{slug}-{type}.pdf` 에 저장한다. macOS=WKWebView `createPDF`, Windows=WebView2 `PrintToPdf` 를, 오프스크린 웹뷰 + Tauri `with_webview` 로 호출한다.

**Architecture:** Rust 커맨드 `export_report_pdf(app, html_path_or_string, out_pdf_path)` 가 ① 오프스크린 `WebviewWindow` 를 만들어 보고서 HTML 을 로드, ② `PageLoadEvent::Finished` 대기, ③ `with_webview` 로 네이티브 핸들을 얻어 플랫폼별 print-to-PDF 호출, ④ 완료 핸들러에서 파일 저장 후 창 파기. 프론트는 `report.ts` 에 `generateReportPdf` 추가 + 모달에 "PDF로 저장". HTML 생성은 증분 1 CLI 재사용(먼저 `vib report --format html` 로 HTML 파일을 만든 뒤 그 경로를 PDF 커맨드에 넘김).

**Tech Stack:** Rust, Tauri 2.10.3 (`with_webview`, `PageLoadEvent`, `data-url` feature), 네이티브 interop: macOS `objc2`/`objc2-web-kit`/`objc2-app-kit`/`block2`, Windows `webview2-com`/`windows`. 프론트는 기존 invoke 패턴.

**상위 설계:** `docs/superpowers/specs/2026-06-15-기획안-보고서-내보내기-design.md` §13.1 (a 경로 확정), §7. 리서치 근거: 본 문서 말미 **부록 A**.

**실행 브랜치:** `feat/report-export-pdf` (base = `feat/report-export-gui`). HTML 연동(2a) 위에 PDF 를 얹는다.

**버전 핀(ABI 충돌 방지 — wry 0.54.4 와 일치):** `objc2 = "0.6"`, `objc2-web-kit = "0.3"`, `objc2-app-kit = "0.3"`, `block2 = "0.6"`, `webview2-com = "0.38"`, `windows = "0.61"`. 추가 후 `cargo tree -d` 로 중복 없음 확인.

---

## ⚠ Task 1: macOS 무인 PDF 스파이크 (HARD GATE)

목적: **"오프스크린 WKWebView 에서 createPDF 가 빈 PDF 가 아닌 실제 PDF 를 만든다"** 를 이 macOS 장비에서 증명한다. 이게 안 되면 접근법 (a) 가 막히고 계획 전체를 재검토해야 한다(실패 분기 참조). 결정적 코드가 아니라 **컴파일러와 반복**하는 스파이크다.

**Files (스파이크 — 나중에 정리/이동):**
- Modify: `vibelign-gui/src-tauri/Cargo.toml` (네이티브 deps + tauri `data-url` feature)
- Create: `vibelign-gui/src-tauri/src/commands/report_pdf.rs` (스파이크 커맨드)
- Modify: `vibelign-gui/src-tauri/src/commands/mod.rs` (모듈 등록)
- Modify: `vibelign-gui/src-tauri/src/lib.rs` (invoke handler 등록)

- [ ] **Step 1: deps 추가**

`Cargo.toml` 의 `tauri` 에 `data-url` feature 추가, 플랫폼별 deps 추가:
```toml
tauri = { version = "2", features = ["data-url"] }

[target.'cfg(target_os = "macos")'.dependencies]
objc2 = "0.6"
objc2-web-kit = { version = "0.3", features = ["WKWebView", "WKPDFConfiguration", "block2"] }
objc2-app-kit = { version = "0.3", features = ["NSWindow"] }
objc2-foundation = { version = "0.3", features = ["NSData", "NSError"] }
block2 = "0.6"

[target.'cfg(windows)'.dependencies]
webview2-com = "0.38"
windows = { version = "0.61", features = ["Win32_Foundation"] }
```
그리고 `cargo tree -d -p vibelign-gui 2>/dev/null | grep -E 'objc2|webview2-com|windows ' ` 로 중복 버전이 없는지 확인(있으면 버전 핀 조정).

- [ ] **Step 2: 스파이크 커맨드 작성 (리서치 부록 A 의 호출 shape 기반, 컴파일러와 반복)**

`report_pdf.rs` — 최소 스파이크. 고정 HTML 을 오프스크린 창에 로드하고, 로드 완료 후 createPDF 로 `out` 경로에 저장. **핵심 gotcha 반영**: `visible(false)` 가 아니라 **오프스크린 위치 + show** (안 그러면 빈 PDF).
```rust
// === ANCHOR: REPORT_PDF_START ===
use std::path::PathBuf;
use std::sync::mpsc;
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

#[tauri::command]
pub(crate) async fn export_report_pdf_spike(
    app: tauri::AppHandle,
    out: String,
) -> Result<String, String> {
    let out_path = PathBuf::from(&out);
    let html = "<html><head><meta charset='utf-8'></head><body style='font-family:serif'>\
                <h1>스파이크 보고서</h1><p>한글 PDF 렌더 확인</p></body></html>";

    // data: URL 로 HTML 로드 (data-url feature 필요)
    let data_url = format!("data:text/html,{}", urlencoding::encode(html));
    let label = "pdf-export-spike";
    if let Some(w) = app.get_webview_window(label) {
        let _ = w.close();
    }
    let win = WebviewWindowBuilder::new(&app, label, WebviewUrl::External(data_url.parse().unwrap()))
        .title("_pdf_spike")
        .inner_size(800.0, 1000.0)
        .visible(true)        // 보이게(렌더 파이프라인 진입) — 단 화면 밖으로
        .position(-10000.0, -10000.0)
        .build()
        .map_err(|e| e.to_string())?;

    // 로드 완료 대기 → createPDF (메인 스레드). 채널로 완료 신호.
    let (tx, rx) = mpsc::channel::<Result<(), String>>();
    let out_for_cb = out_path.clone();
    win.clone().on_page_load(move |w, payload| {
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
                let view: &WKWebView = &*webview.inner().cast();
                let tx3 = tx2.clone();
                let block = RcBlock::new(move |data: *mut NSData, err: *mut NSError| {
                    if !err.is_null() {
                        let _ = tx3.send(Err("createPDF error".into()));
                        return;
                    }
                    let bytes = (&*data).to_vec();
                    let _ = std::fs::write(&out2, bytes)
                        .map_err(|e| e.to_string())
                        .and_then(|_| Ok(()));
                    let _ = tx3.send(Ok(()));
                });
                view.createPDFWithConfiguration_completionHandler(None, &block);
            }
            #[cfg(not(target_os = "macos"))]
            {
                let _ = (webview, &out2);
                let _ = tx2.send(Err("spike: macOS 전용".into()));
            }
        });
    });

    // 완료 신호 대기(타임아웃)
    let res = rx.recv_timeout(std::time::Duration::from_secs(15))
        .map_err(|_| "PDF 생성 타임아웃".to_string())?;
    let _ = win.close();
    res.map(|_| out_path.to_string_lossy().into_owned())
}
// === ANCHOR: REPORT_PDF_END ===
```
> **주의:** 위 코드는 리서치 기반 **시작점**이다. `objc2-web-kit` 의 정확한 메서드 시그니처(`createPDFWithConfiguration_completionHandler` 인자 타입, `NSData::to_vec`/`bytes`), `with_webview` 콜백 시그니처, `block2::RcBlock` 사용법은 **컴파일 에러를 보며 맞춰라.** `urlencoding` 크레이트가 없으면 추가하거나 임시 파일+`WebviewUrl::App` 로 대체. 메인 스레드 요구·async 완료를 채널로 받는 구조는 유지.

- [ ] **Step 3: 등록**

`mod.rs` 에 `pub(crate) mod report_pdf;` 추가. `lib.rs` 의 `generate_handler![]` 에 `commands::report_pdf::export_report_pdf_spike` 추가.

- [ ] **Step 4: 빌드**

Run: `cd /Users/usabatch/coding/VibeLign/vibelign-gui/src-tauri && cargo build 2>&1 | tail -30`
Expected: 컴파일 성공. 실패 시 Step 2 의 시그니처를 에러에 맞춰 반복 수정(이게 스파이크의 본체다).

- [ ] **Step 5: 실행 + 트리거 + 검증 (실제 앱)**

앱을 dev 로 띄우고 스파이크 커맨드를 호출해 PDF 를 만든다:
```bash
cd /Users/usabatch/coding/VibeLign/vibelign-gui && npm run tauri dev
```
앱 콘솔(devtools) 또는 임시 트리거에서:
```js
await window.__TAURI__.core.invoke("export_report_pdf_spike", { out: "/tmp/spike.pdf" })
```
검증:
```bash
ls -la /tmp/spike.pdf && file /tmp/spike.pdf   # "PDF document" 여야
# 빈 PDF 아님 확인: 파일 크기 > 1KB 이고 페이지 텍스트가 있는지
```
**성공 기준:** `/tmp/spike.pdf` 가 생성되고, `file` 이 "PDF document", 크기 > 1KB, (가능하면) 텍스트 "스파이크 보고서" 포함.

- [ ] **Step 6: 결과 판정 + 분기**

- **성공** → Task 2 로(프로덕션화). 스파이크 커맨드는 Task 2 에서 정식 커맨드로 흡수.
- **실패(빈 PDF / 에러)** → STOP, 사용자에게 보고. 분기 옵션:
  - (a-fix) 오프스크린 트릭 변형(`makeKeyAndOrderFront` + `alphaValue=0`, 또는 로드 후 100~300ms 지연).
  - (대안) `wkhtmltopdf` 번들(`tauri-plugin-printer-wkhtml-bin`) — 무인 동작하나 +30MB·CSS 패리티 손실. design 비선호였으나 (a) 가 막히면 재논의.
  - 위 중 무엇도 막히면 §13.1 결정을 (b)/(c)로 되돌리는 것까지 사용자와 재논의.

- [ ] **Step 7: 커밋(스파이크 결과)**

성공 시: `git add -A && git commit -m "spike(report-pdf): macOS 오프스크린 WKWebView createPDF 실현성 검증"`

---

## Task 2: PDF export 커맨드 프로덕션화 (macOS + Windows)

**전제:** Task 1 성공. 스파이크를 정식 커맨드 `export_report_pdf(app, html_path, out_pdf)` 로 정리한다.

**Files:**
- Modify: `vibelign-gui/src-tauri/src/commands/report_pdf.rs`
- Test: `vibelign-gui/src-tauri/src/commands/report_pdf_tests.rs` (Create) — 순수 단위(경로 검증·data-url 빌더) 테스트. 네이티브 PDF 자체는 단위테스트 불가(런타임 필요).

- [ ] **Step 1: 입력을 HTML 파일 경로로 — data-url 대신 임시/실파일 로드**
  실제 보고서는 `.vibelign/reports/*.html`(2a 산출물). 그 파일을 `WebviewUrl::App` 또는 `file://` 로 로드(데이터-URL 길이 한계 회피). 경로는 프로젝트 루트 하위로 제한(2a `toProjectRelative`/storage 가드 정신 재사용).

- [ ] **Step 2: macOS 경로 = Task 1 코드 정리** (위 createPDF, 에러/타임아웃/창정리 견고화).

- [ ] **Step 3: Windows 경로 추가 (cfg(windows)) — 이 장비에서 검증 불가, 리서치 shape 기반**
```rust
#[cfg(windows)]
unsafe {
    use webview2_com::Microsoft::Web::WebView2::Win32::ICoreWebView2_7;
    use windows::core::{Interface, PCWSTR};
    let controller = webview.controller();
    let core = controller.CoreWebView2().map_err(|e| e.to_string())?;
    let wv7: ICoreWebView2_7 = core.cast().map_err(|e| e.to_string())?;
    let mut wide: Vec<u16> = out.encode_utf16().chain(Some(0)).collect();
    let handler = /* ICoreWebView2PrintToPdfCompletedHandler 구현 → 채널 send */;
    wv7.PrintToPdf(PCWSTR(wide.as_ptr()), None, &handler).map_err(|e| e.to_string())?;
}
```
> Windows 는 절대경로 필수, NavigationCompleted 후 호출, 동시 1건. **Windows 검증은 사용자 Windows 장비 QA 로 이월**(이 계획은 macOS 에서 빌드·동작, Windows 는 컴파일만 cfg 로 보장하되 런타임 미검증임을 명시).

- [ ] **Step 4: 단위 테스트(순수 부분만)** + `cargo test -p vibelign-gui report_pdf` 통과. 커밋.

---

## Task 3: 등록 + TS 래퍼 + 모달 PDF 옵션

**Files:**
- Modify: `vibelign-gui/src-tauri/src/lib.rs` (스파이크 핸들러 → 정식 `export_report_pdf` 로 교체)
- Modify: `vibelign-gui/src/lib/vib/report.ts` (`generateReportPdf`)
- Modify: `vibelign-gui/src/components/plan-doc/ExportReportModal.tsx` (포맷: HTML/PDF, "PDF로 저장")
- Test: 해당 `__tests__` vitest

- [ ] **Step 1 (TDD): `report.ts` 에 `generateReportPdf(cwd, planPath, type)`** — 먼저 `generatePlanningReport`(HTML) 로 HTML 파일 path 확보 → `invoke("export_report_pdf", { htmlPath, outPdf })` → `{ok, path}`. vitest 로 invoke/래퍼 모킹. 실패→구현→통과.
- [ ] **Step 2 (TDD): 모달에 포맷 선택(HTML/PDF) 라디오 + PDF 분기.** PDF 성공 시 미리보기 대신 "저장됨: …pdf" + 파일 열기. vitest(모킹). 실패→구현→통과.
- [ ] **Step 3: 커밋.**

---

## Task 4: 빌드·실행 통합 검증

- [ ] **Step 1:** `cd vibelign-gui/src-tauri && cargo build` 성공(0 에러).
- [ ] **Step 2:** `cd vibelign-gui && npx vitest run && npx tsc --noEmit` 그린.
- [ ] **Step 3 (실제 앱):** `npm run tauri dev` → PlanDocView 에서 기획안 선택 → 모달 → PDF → `.vibelign/reports/*.pdf` 생성 + 파일 열기. 육안: PDF 가 한글·레이아웃 정상.
- [ ] **Step 4:** Windows 런타임은 미검증임을 보고에 명시(사용자 QA 이월). 임시 스파이크 잔재 제거 확인.

---

## Self-Review (작성 시점)
- **§13.1 (a) 커버:** macOS createPDF + Windows PrintToPdf, with_webview, 오프스크린, 고정경로 `.vibelign/reports/*.pdf` ✓.
- **위험 격리:** 최대 위험(macOS 오프스크린 빈-PDF)을 Task 1 스파이크로 선검증하고 실패 분기를 명시 ✓.
- **정직성:** Task 1 은 결정적 코드가 아니라 스파이크(컴파일러 반복) 임을 명시; Windows 런타임 미검증 명시; 빌드/앱 실행 필요 명시.
- **이월:** 2a 의 `file://`+경로 Windows 백슬래시(Minor #2), `toProjectRelative` 드라이브 대소문자 — PDF 경로/파일열기에서 같이 정리.

---

## 부록 A — 리서치 요약 (구현 레퍼런스)
- **Tauri**: print-to-PDF 공식 API 없음 → `WebviewWindow::with_webview(|wv| …)`(2.9+, 메인스레드)로 네이티브 호출. 로드 동기화 = `PageLoadEvent::Finished`. HTML 로드 = `data:`URL(`data-url` feature) 또는 임시파일+`WebviewUrl::App`.
- **macOS**: `wv.inner()` → `WKWebView`. `createPDFWithConfiguration_completionHandler(None, &block)` (macOS 11+, `objc2-web-kit` 0.3, feature `WKPDFConfiguration`+`block2`). 완료=메인스레드 async. **⚠ `visible(false)` 면 렌더 안 됨 → 빈 PDF. 오프스크린 위치(-10000)+show 로 회피.** `loadHTMLString` 직후 즉시 호출 금지(Finished 대기).
- **Windows**: `controller().CoreWebView2()` → `cast::<ICoreWebView2_7>()` → `PrintToPdf(absPath, None, handler)` (`webview2-com` 0.38). NavigationCompleted 후, 절대경로, 동시 1건, WebView2 ≥1.0.1020.30.
- **버전 핀(wry 0.54.4)**: objc2 0.6.4 / objc2-web-kit 0.3.2 / objc2-app-kit 0.3.2 / block2 0.6.2 / webview2-com 0.38.2 / windows 0.61.3. `cargo tree -d` 로 중복 점검.
- **대안(차선)**: `wkhtmltopdf` 번들 — 무인·양OS 동작, +30MB·CSS 패리티 손실(design 비선호).
