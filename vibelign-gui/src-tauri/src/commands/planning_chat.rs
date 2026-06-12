// === ANCHOR: PLANNING_CHAT_START ===
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

use super::planning_chat_store::{
    latest_chat_session_file, planning_dir, read_json, write_json, StoredPlanningChatSession,
};
use super::planning_chat_synthesis::{read_saved_markdown, save_planning_markdown};
use super::planning_chat_types::{
    planning_chat_error, planning_chat_success, AppendPlanningChatTurnRequest,
    CreatePlanningChatSessionRequest, PlanningChatMessage, PlanningChatSessionResponse,
    PlanningSessionSummary, SavePlanningChatPlanRequest,
};
use super::planning_chat_cards::{extract_and_apply, read_cards};
use super::planning_persona::{is_persona_enabled, run_persona_response, PlanningChatLine};

#[tauri::command]
pub(crate) async fn create_planning_chat_session(
    request: CreatePlanningChatSessionRequest,
) -> PlanningChatSessionResponse {
    let project_dir = PathBuf::from(&request.project_dir);
    if !project_dir.is_absolute() {
        return planning_chat_error("projectDir must be absolute");
    }
    let prompt = request.prompt.trim().to_string();
    if prompt.is_empty() {
        return planning_chat_error("prompt is required");
    }

    tauri::async_runtime::spawn_blocking(move || {
        let now = timestamp_ms().to_string();
        let session_id = format!("chat_{}_{}", now, std::process::id());
        let session_dir = planning_dir(&project_dir).join(&session_id);
        if let Err(error) = std::fs::create_dir_all(&session_dir) {
            return planning_chat_error(error.to_string());
        }
        let session = StoredPlanningChatSession {
            schema_version: 1,
            session_id: session_id.clone(),
            idea: prompt.clone(),
            mode: "chat".to_string(),
            created_at: now.clone(),
            output_path: None,
            absolute_output_path: None,
            doc_stale: false,
            readiness: None,
        };
        let messages = vec![PlanningChatMessage {
            id: format!("msg_{}", timestamp_ms()),
            role: "user".to_string(),
            persona_id: None,
            content: prompt.clone(),
            status: "ok".to_string(),
            created_at: now,
            provider_used: None,
            fallback_reason: None,
        }];
        if let Err(error) = write_json(session_dir.join("session.json"), &session) {
            return planning_chat_error(error);
        }
        if let Err(error) = write_json(session_dir.join("messages.json"), &messages) {
            return planning_chat_error(error);
        }
        planning_chat_success(session, messages, None, Vec::new(), super::planning_chat_contract::read_contract(&session_dir))
    })
    .await
    .unwrap_or_else(|error| planning_chat_error(error.to_string()))
}

fn load_session_from_dir(
    project_dir: &std::path::Path,
    session_dir: &std::path::Path,
) -> PlanningChatSessionResponse {
    let session = match read_json::<StoredPlanningChatSession>(&session_dir.join("session.json")) {
        Ok(parsed) => parsed,
        Err(error) => return planning_chat_error(error),
    };
    let messages = match read_json::<Vec<PlanningChatMessage>>(&session_dir.join("messages.json")) {
        Ok(parsed) => parsed,
        Err(error) => return planning_chat_error(error),
    };
    let markdown = read_saved_markdown(project_dir, &session);
    let cards = super::planning_chat_cards::read_cards(session_dir);
    planning_chat_success(session, messages, markdown, cards, super::planning_chat_contract::read_contract(session_dir))
}

#[tauri::command]
pub(crate) async fn load_latest_planning_chat_session(
    project_dir: String,
) -> PlanningChatSessionResponse {
    let project_dir = PathBuf::from(project_dir);
    if !project_dir.is_absolute() {
        return planning_chat_error("projectDir must be absolute");
    }

    tauri::async_runtime::spawn_blocking(move || {
        let Some(session_path) = latest_chat_session_file(&project_dir) else {
            return planning_chat_error("planning chat session not found");
        };
        let session_dir = session_path
            .parent()
            .map(|path| path.to_path_buf())
            .unwrap_or_else(|| project_dir.clone());
        load_session_from_dir(&project_dir, &session_dir)
    })
    .await
    .unwrap_or_else(|error| planning_chat_error(error.to_string()))
}

#[tauri::command]
pub(crate) async fn load_planning_chat_session(
    project_dir: String,
    session_id: String,
) -> PlanningChatSessionResponse {
    let project_dir = PathBuf::from(project_dir);
    if !project_dir.is_absolute() {
        return planning_chat_error("projectDir must be absolute");
    }
    if session_id.trim().is_empty() {
        return planning_chat_error("sessionId is required");
    }
    tauri::async_runtime::spawn_blocking(move || {
        let session_dir = planning_dir(&project_dir).join(&session_id);
        if !session_dir.join("session.json").exists() {
            return planning_chat_error("planning chat session not found");
        }
        load_session_from_dir(&project_dir, &session_dir)
    })
    .await
    .unwrap_or_else(|error| planning_chat_error(error.to_string()))
}

#[tauri::command]
pub(crate) async fn append_planning_chat_turn(
    request: AppendPlanningChatTurnRequest,
) -> PlanningChatSessionResponse {
    let project_dir = PathBuf::from(&request.project_dir);
    if !project_dir.is_absolute() {
        return planning_chat_error("projectDir must be absolute");
    }
    let prompt = request.prompt.trim().to_string();
    if prompt.is_empty() {
        return planning_chat_error("prompt is required");
    }
    if request.session_id.trim().is_empty() {
        return planning_chat_error("sessionId is required");
    }

    tauri::async_runtime::spawn_blocking(move || {
        let session_dir = planning_dir(&project_dir).join(&request.session_id);
        let session_path = session_dir.join("session.json");
        let messages_path = session_dir.join("messages.json");
        let mut session = match read_json::<StoredPlanningChatSession>(&session_path) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        let mut messages = match read_json::<Vec<PlanningChatMessage>>(&messages_path) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        let now = timestamp_ms().to_string();
        if request.include_user_message.unwrap_or(true) {
            messages.push(PlanningChatMessage {
                id: format!("msg_{}", timestamp_ms()),
                role: "user".to_string(),
                persona_id: None,
                content: prompt.clone(),
                status: "ok".to_string(),
                created_at: now.clone(),
                provider_used: None,
                fallback_reason: None,
            });
        }
        for agent in request.agents {
            if !is_persona_enabled(&agent) {
                continue;
            }
            // 실패/대기 메시지는 페르소나 맥락에서 제외한다(에러 문구가 대화로 새는 것 방지).
            // 사용자 메시지는 status="ok" 이라 그대로 남는다.
            let lines = messages
                .iter()
                .filter(|message| message.status == "ok")
                .map(|message| PlanningChatLine {
                    role: &message.role,
                    persona_id: message.persona_id.as_deref(),
                    content: &message.content,
                })
                .collect::<Vec<_>>();
            let persona_run = run_persona_response(&project_dir, &agent, &lines);
            messages.push(PlanningChatMessage {
                id: format!("msg_{}_{}", agent, timestamp_ms()),
                role: "assistant".to_string(),
                persona_id: Some(agent),
                content: persona_run.content,
                status: persona_run.status,
                created_at: now.clone(),
                provider_used: persona_run.provider_used,
                fallback_reason: persona_run.fallback_reason,
            });
        }
        let now = timestamp_ms().to_string();
        // 카드 추출은 CLI를 한 번 더 기동한다. 프론트는 페르소나별로 호출하므로,
        // 턴의 마지막 페르소나 호출(extract_cards=true)에서만 1회 추출해 콜드스타트를 줄인다.
        // 그 외 호출은 기존 카드를 그대로 돌려준다(중간 깜빡임 방지).
        let cards = if request.extract_cards.unwrap_or(true) {
            let card_turn = messages_since_last_user(&messages);
            extract_and_apply(&project_dir, &session_dir, &messages, card_turn, &now)
        } else {
            read_cards(&session_dir)
        };
        if let Err(error) = write_json(messages_path, &messages) {
            return planning_chat_error(error);
        }
        // 저장된 기획안이 있는데 대화가 더 진행됐다 — 포인터(output_path)는 지우지 않고
        // stale 로만 표시한다. 지우면 기획안 탭에서 저장된 문서가 사라져 보인다(파일은 그대로인데).
        if mark_doc_stale(&mut session) {
            if let Err(error) = write_json(session_path, &session) {
                return planning_chat_error(error);
            }
        }
        planning_chat_success(session, messages, None, cards, super::planning_chat_contract::read_contract(&session_dir))
    })
    .await
    .unwrap_or_else(|error| planning_chat_error(error.to_string()))
}

#[tauri::command]
pub(crate) async fn save_planning_chat_as_markdown(
    request: SavePlanningChatPlanRequest,
) -> PlanningChatSessionResponse {
    let project_dir = PathBuf::from(&request.project_dir);
    if !project_dir.is_absolute() {
        return planning_chat_error("projectDir must be absolute");
    }
    if request.session_id.trim().is_empty() {
        return planning_chat_error("sessionId is required");
    }

    tauri::async_runtime::spawn_blocking(move || {
        let session_dir = planning_dir(&project_dir).join(&request.session_id);
        let session_path = session_dir.join("session.json");
        let messages_path = session_dir.join("messages.json");
        let mut session = match read_json::<StoredPlanningChatSession>(&session_path) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        let messages = match read_json::<Vec<PlanningChatMessage>>(&messages_path) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        // 즉시 저장(딜레이 제거) — 준비상태 판정·계약 추출의 CLI(LLM) 2회는 저장을 막던 주범이라
        // enrich_planning_chat_plan 이 백그라운드로 처리한다. 여기선 디스크에 캐시된 계약과 세션에
        // 저장돼 있던 readiness 로 즉시 파일을 쓴다(첫 저장이면 비어 있고, 직후 enrich 가 채운다).
        let contract = super::planning_chat_contract::read_contract(&session_dir);
        let cards = read_cards(&session_dir);
        let saved = match save_planning_markdown(
            &project_dir,
            &mut session,
            &messages,
            &cards,
            contract.as_ref(),
            request.target_path.as_deref(),
        ) {
            Ok(saved) => saved,
            Err(error) => return planning_chat_error(error),
        };
        if let Err(error) = write_json(session_path, &session) {
            return planning_chat_error(error);
        }
        // 저장이 실제로 끝난 뒤에만 입구 출처를 누적한다(실패 저장은 카운트 X). best-effort.
        if let Some(source) = request.source.as_deref() {
            super::planning_chat_store::record_save_source(&project_dir, source);
        }
        planning_chat_success(session, messages, Some(saved.markdown), cards, contract)
    })
    .await
    .unwrap_or_else(|error| planning_chat_error(error.to_string()))
}

/// enrich 캐시 — 마지막 '온전한' 분석(판정 Judged + 계약 추출 성공) 시점의 대화 해시.
/// 대화가 그대로면 다음 enrich 가 LLM 재호출을 건너뛴다.
#[derive(serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
struct EnrichCache {
    schema_version: u32,
    messages_hash: String,
}

/// LLM 분석 입력(status=ok 메시지의 화자·내용)을 해시한다. 실패/대기 메시지는
/// 판정·계약 프롬프트에 들어가지 않으므로 제외 — 무관한 변화로 캐시가 깨지지 않게.
fn enrich_input_hash(messages: &[PlanningChatMessage]) -> String {
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    for message in messages {
        if message.status != "ok" {
            continue;
        }
        hasher.update(message.role.as_bytes());
        hasher.update([0x1f]);
        hasher.update(message.persona_id.as_deref().unwrap_or("").as_bytes());
        hasher.update([0x1f]);
        hasher.update(message.content.as_bytes());
        hasher.update([0x1e]);
    }
    format!("{:x}", hasher.finalize())
}

/// 준비상태 판정·계약 추출 — 각각 CLI(LLM) 1회, 병렬 실행으로 ~1회분 지연.
/// enrich(저장 후 보강)와 prewarm(턴 종료 선행 분석)이 공유하는 무거운 분석부.
fn run_enrich_analysis(
    project_dir: &std::path::Path,
    messages: &[PlanningChatMessage],
    now: &str,
) -> (
    super::planning_chat_readiness::ReadinessReport,
    Option<super::planning_chat_contract::PlanningContract>,
) {
    let readiness_dir = project_dir.to_path_buf();
    let readiness_messages = messages.to_vec();
    let readiness_handle = std::thread::spawn(move || {
        super::planning_chat_readiness::judge_readiness(&readiness_dir, &readiness_messages)
    });
    let contract = super::planning_chat_contract::extract_contract(project_dir, messages, now);
    let readiness = readiness_handle
        .join()
        .unwrap_or_else(|_| super::planning_chat_readiness::ReadinessReport::unavailable());
    (readiness, contract)
}

/// 기획안 저장 후 백그라운드 보강 — 준비상태 판정·계약 추출(각 CLI 1회, 병렬)을 돌려 같은
/// 파일에 재저장한다. save 를 즉시화하면서 분리한 무거운 AI 분석부(저장 딜레이의 정체).
/// App 이 소유해 await 하므로 PlanningRoom 을 떠나도 완료된다 — 작업방 지시문이 쓰는 contract 보장.
#[tauri::command]
pub(crate) async fn enrich_planning_chat_plan(
    request: SavePlanningChatPlanRequest,
) -> PlanningChatSessionResponse {
    let project_dir = PathBuf::from(&request.project_dir);
    if !project_dir.is_absolute() {
        return planning_chat_error("projectDir must be absolute");
    }
    if request.session_id.trim().is_empty() {
        return planning_chat_error("sessionId is required");
    }

    tauri::async_runtime::spawn_blocking(move || {
        let session_dir = planning_dir(&project_dir).join(&request.session_id);
        let session_path = session_dir.join("session.json");
        let messages_path = session_dir.join("messages.json");
        let mut session = match read_json::<StoredPlanningChatSession>(&session_path) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        let messages = match read_json::<Vec<PlanningChatMessage>>(&messages_path) {
            Ok(parsed) => parsed,
            Err(error) => return planning_chat_error(error),
        };
        // 대화가 마지막 온전한 분석 이후 그대로면 LLM 2회를 건너뛴다 — 재저장이 즉시 끝난다.
        // 캐시는 분석이 온전히 성공했을 때만 기록되므로, 해시 일치 + 산출물 존재 = 디스크의
        // readiness·contract 가 이 대화의 유효한 분석 결과다(미완이었으면 여기서 재시도).
        let input_hash = enrich_input_hash(&messages);
        let cache_path = session_dir.join("enrich.json");
        let cache_hit = read_json::<EnrichCache>(&cache_path)
            .map(|cache| cache.schema_version == 1 && cache.messages_hash == input_hash)
            .unwrap_or(false);
        if cache_hit {
            let contract = super::planning_chat_contract::read_contract(&session_dir);
            let readiness_judged = session.readiness.as_ref().is_some_and(|report| {
                matches!(report.status, super::planning_chat_readiness::ReadinessStatus::Judged)
            });
            if readiness_judged && contract.is_some() {
                let markdown = read_saved_markdown(&project_dir, &session);
                let cards = read_cards(&session_dir);
                return planning_chat_success(session, messages, markdown, cards, contract);
            }
        }
        let now = timestamp_ms().to_string();
        let (readiness, contract) = run_enrich_analysis(&project_dir, &messages, &now);
        session.readiness = Some(readiness);
        if let Some(ref parsed) = contract {
            let _ = super::planning_chat_contract::write_contract(&session_dir, parsed);
        }
        // LLM 분석(수십 초) 동안 같은 세션에 새 대화가 붙었을 수 있다 — 최종 문서·응답은 최신
        // messages·cards 로 합성해 누락 없이(읽기 실패 시 분석 시점 스냅샷 유지, M3 enrich 리뷰 P2).
        let messages = read_json::<Vec<PlanningChatMessage>>(&messages_path).unwrap_or(messages);
        let cards = read_cards(&session_dir);
        // 즉시저장이 set 한 output_path 로 재저장(target 미지정 → 기존 경로 그대로).
        let saved = match save_planning_markdown(
            &project_dir,
            &mut session,
            &messages,
            &cards,
            contract.as_ref(),
            None,
        ) {
            Ok(saved) => saved,
            Err(error) => return planning_chat_error(error),
        };
        if let Err(error) = write_json(session_path, &session) {
            return planning_chat_error(error);
        }
        // 분석이 온전(판정 Judged + 계약 추출 성공)할 때만 입력 해시를 기록한다 — 다음
        // 재저장 스킵용. 미완이면 기록하지 않아 다음 enrich 가 재시도한다. best-effort.
        let analysis_complete = session.readiness.as_ref().is_some_and(|report| {
            matches!(report.status, super::planning_chat_readiness::ReadinessStatus::Judged)
        }) && contract.is_some();
        if analysis_complete {
            let _ = write_json(cache_path, &EnrichCache { schema_version: 1, messages_hash: input_hash });
        }
        planning_chat_success(session, messages, Some(saved.markdown), cards, contract)
    })
    .await
    .unwrap_or_else(|error| planning_chat_error(error.to_string()))
}

/// 턴 종료 직후 선행 분석(프리웜) — 판정·계약을 미리 돌려 enrich 캐시를 채운다.
/// 사용자가 페르소나 응답을 읽는 동안 분석이 끝나므로, 저장 시 enrich 가 캐시 히트로
/// 즉시 끝난다. enrich 와 달리 기획안 파일을 절대 저장하지 않는다(미저장 세션에
/// plans/*.md 가 생기면 안 됨). best-effort — 실패·미완이면 저장 흐름이 알아서 재분석한다.
#[tauri::command]
pub(crate) async fn prewarm_planning_enrich(
    project_dir: String,
    session_id: String,
) -> Result<(), String> {
    let project_dir = PathBuf::from(project_dir);
    if !project_dir.is_absolute() {
        return Err("projectDir must be absolute".to_string());
    }
    if session_id.trim().is_empty() {
        return Err("sessionId is required".to_string());
    }
    tauri::async_runtime::spawn_blocking(move || prewarm_planning_enrich_blocking(&project_dir, &session_id))
        .await
        .map_err(|error| error.to_string())?
}

/// prewarm 의 블로킹 본문 — 캐시 히트 경로(LLM 0회)를 테스트할 수 있게 분리.
fn prewarm_planning_enrich_blocking(
    project_dir: &std::path::Path,
    session_id: &str,
) -> Result<(), String> {
    let session_dir = planning_dir(project_dir).join(session_id);
    let session_path = session_dir.join("session.json");
    if !session_path.exists() {
        return Err("planning chat session not found".to_string());
    }
    let messages = read_json::<Vec<PlanningChatMessage>>(&session_dir.join("messages.json"))?;
    let input_hash = enrich_input_hash(&messages);
    let cache_path = session_dir.join("enrich.json");
    // 이미 이 대화의 온전한 분석이 캐시돼 있으면 할 일 없음(중복 LLM 호출 방지).
    let cache_hit = read_json::<EnrichCache>(&cache_path)
        .map(|cache| cache.schema_version == 1 && cache.messages_hash == input_hash)
        .unwrap_or(false);
    if cache_hit {
        return Ok(());
    }
    let now = timestamp_ms().to_string();
    let (readiness, contract) = run_enrich_analysis(project_dir, &messages, &now);
    // 분석이 온전(판정 Judged + 계약 성공)할 때만 산출물·캐시를 기록 — 미완이면
    // 아무것도 남기지 않아 다음 enrich/프리웜이 재시도한다.
    if !matches!(readiness.status, super::planning_chat_readiness::ReadinessStatus::Judged) {
        return Ok(());
    }
    let Some(ref parsed) = contract else {
        return Ok(());
    };
    super::planning_chat_contract::write_contract(&session_dir, parsed)?;
    // 분석(수십 초) 동안 session.json 이 바뀌었을 수 있다(저장이 output_path 설정 등) —
    // 최신본을 다시 읽어 readiness 만 갱신한다. 스냅샷으로 덮으면 저장 포인터가 날아간다.
    let mut session = read_json::<StoredPlanningChatSession>(&session_path)?;
    session.readiness = Some(readiness);
    write_json(session_path, &session)?;
    write_json(cache_path, &EnrichCache { schema_version: 1, messages_hash: input_hash })
}

/// 저장본이 있고 아직 stale 이 아니면 stale 로 표시. 변경이 있었는지 돌려준다(있을 때만 디스크 기록).
fn mark_doc_stale(session: &mut StoredPlanningChatSession) -> bool {
    if session.output_path.is_some() && !session.doc_stale {
        session.doc_stale = true;
        return true;
    }
    false
}

fn summary_title(idea: &str) -> String {
    idea.lines().next().unwrap_or("").trim().chars().take(60).collect()
}

fn list_sessions(project_dir: &std::path::Path) -> Vec<PlanningSessionSummary> {
    let dir = planning_dir(project_dir);
    let Ok(entries) = std::fs::read_dir(&dir) else {
        return Vec::new();
    };
    let mut rows: Vec<(std::time::SystemTime, PlanningSessionSummary)> = Vec::new();
    for entry in entries.flatten() {
        let session_dir = entry.path();
        let session_path = session_dir.join("session.json");
        let messages_path = session_dir.join("messages.json");
        if !session_path.exists() || !messages_path.exists() {
            continue;
        }
        let Ok(session) = read_json::<StoredPlanningChatSession>(&session_path) else {
            continue;
        };
        let messages = read_json::<Vec<PlanningChatMessage>>(&messages_path).unwrap_or_default();
        let cards = super::planning_chat_cards::read_cards(&session_dir);
        let modified = messages_path
            .metadata()
            .and_then(|meta| meta.modified())
            .unwrap_or(UNIX_EPOCH);
        rows.push((
            modified,
            PlanningSessionSummary {
                title: summary_title(&session.idea),
                saved: session.output_path.is_some(),
                doc_stale: session.doc_stale,
                output_path: session.output_path.clone(),
                created_at: session.created_at.clone(),
                message_count: messages.len(),
                card_count: cards.len(),
                session_id: session.session_id,
            },
        ));
    }
    rows.sort_by(|a, b| b.0.cmp(&a.0));
    rows.into_iter().map(|(_, summary)| summary).collect()
}

#[tauri::command]
pub(crate) async fn list_planning_chat_sessions(project_dir: String) -> Vec<PlanningSessionSummary> {
    let project_dir = PathBuf::from(project_dir);
    if !project_dir.is_absolute() {
        return Vec::new();
    }
    tauri::async_runtime::spawn_blocking(move || list_sessions(&project_dir))
        .await
        .unwrap_or_default()
}

/// 기획 세션 1개를 휴지통으로 보낸다(소프트 삭제). 세션 디렉터리 + 저장된 기획안 md
/// 를 .vibelign/planning/.trash/{id}/ 로 옮긴다. 30일 뒤 자동 정리되며, 그 전에는
/// restore_planning_chat_session 으로 복구하거나 empty_planning_trash 로 완전 삭제한다.
#[tauri::command]
pub(crate) async fn delete_planning_chat_session(
    project_dir: String,
    session_id: String,
) -> Result<(), String> {
    let project_dir = PathBuf::from(project_dir);
    if !project_dir.is_absolute() {
        return Err("projectDir must be absolute".to_string());
    }
    tauri::async_runtime::spawn_blocking(move || {
        super::planning_chat_trash::soft_delete(&project_dir, &session_id)
    })
    .await
    .map_err(|error| error.to_string())?
}

fn timestamp_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_or(0, |duration| duration.as_millis())
}

/// 마지막 사용자 메시지부터 끝까지(= 이번 턴 전체)를 돌려준다.
/// 카드 추출이 턴당 1회로 미뤄져도 그 턴의 모든 페르소나 응답을 보도록 보장한다.
fn messages_since_last_user(messages: &[PlanningChatMessage]) -> &[PlanningChatMessage] {
    let start = messages
        .iter()
        .rposition(|message| message.role == "user")
        .unwrap_or(0);
    &messages[start..]
}

#[cfg(test)]
mod tests {
    use super::*;

    fn msg(role: &str, persona: Option<&str>) -> PlanningChatMessage {
        PlanningChatMessage {
            id: "m".to_string(),
            role: role.to_string(),
            persona_id: persona.map(|p| p.to_string()),
            content: "x".to_string(),
            status: "ok".to_string(),
            created_at: "1".to_string(),
            provider_used: None,
            fallback_reason: None,
        }
    }

    #[test]
    fn enrich_input_hash_is_stable_and_ignores_non_ok_messages() {
        let base = vec![msg("user", None), msg("assistant", Some("chloe"))];
        let same = vec![msg("user", None), msg("assistant", Some("chloe"))];
        assert_eq!(enrich_input_hash(&base), enrich_input_hash(&same));

        // 실패/대기 메시지는 판정 프롬프트에 안 들어가므로 해시도 안 바뀌어야 한다.
        let mut failed = msg("assistant", Some("gio"));
        failed.status = "failed".to_string();
        let mut with_failed = vec![msg("user", None), msg("assistant", Some("chloe"))];
        with_failed.push(failed);
        assert_eq!(enrich_input_hash(&base), enrich_input_hash(&with_failed));

        // 내용·화자가 바뀌면 해시가 바뀐다.
        let mut changed = vec![msg("user", None), msg("assistant", Some("chloe"))];
        changed[0].content = "다른 내용".to_string();
        assert_ne!(enrich_input_hash(&base), enrich_input_hash(&changed));
        let other_persona = vec![msg("user", None), msg("assistant", Some("mina"))];
        assert_ne!(enrich_input_hash(&base), enrich_input_hash(&other_persona));

        // 메시지가 추가되면(새 턴) 해시가 바뀐다.
        let extended = vec![msg("user", None), msg("assistant", Some("chloe")), msg("user", None)];
        assert_ne!(enrich_input_hash(&base), enrich_input_hash(&extended));
    }

    #[test]
    fn prewarm_skips_without_writes_on_cache_hit() {
        let root = tempfile::tempdir().expect("root");
        write_session(root.path(), "chat_p", "프리웜", None, 2, 0);
        let session_dir = root.path().join(".vibelign/planning/chat_p");
        let messages: Vec<PlanningChatMessage> =
            read_json(&session_dir.join("messages.json")).expect("messages");
        write_json(
            session_dir.join("enrich.json"),
            &EnrichCache { schema_version: 1, messages_hash: enrich_input_hash(&messages) },
        )
        .expect("cache");
        let session_before =
            std::fs::read_to_string(session_dir.join("session.json")).expect("session");

        let result = prewarm_planning_enrich_blocking(root.path(), "chat_p");

        // 캐시 히트 = LLM 0회, 산출물 무변경(세션 그대로, 계약 파일 생성 안 함).
        assert!(result.is_ok());
        let session_after =
            std::fs::read_to_string(session_dir.join("session.json")).expect("session");
        assert_eq!(session_before, session_after);
        assert!(!session_dir.join("contract.json").exists());
    }

    #[test]
    fn prewarm_errors_on_missing_session() {
        let root = tempfile::tempdir().expect("root");
        let result = prewarm_planning_enrich_blocking(root.path(), "chat_none");
        assert_eq!(result.unwrap_err(), "planning chat session not found");
    }

    #[test]
    fn messages_since_last_user_returns_whole_turn() {
        // 마지막 사용자 메시지 + 그 뒤 모든 페르소나 응답이 카드 추출 대상이어야 한다.
        let messages = vec![
            msg("user", None),
            msg("assistant", Some("chloe")),
            msg("user", None),
            msg("assistant", Some("chloe")),
            msg("assistant", Some("gio")),
            msg("assistant", Some("mina")),
            msg("assistant", Some("deepseek")),
        ];
        let turn = messages_since_last_user(&messages);
        assert_eq!(turn.len(), 5); // 두 번째 user + 4개 페르소나
        assert_eq!(turn[0].role, "user");
        assert_eq!(turn[4].persona_id.as_deref(), Some("deepseek"));
    }

    #[test]
    fn messages_since_last_user_falls_back_to_start_without_user() {
        let messages = vec![msg("assistant", Some("chloe")), msg("assistant", Some("gio"))];
        let turn = messages_since_last_user(&messages);
        assert_eq!(turn.len(), 2);
    }

    fn write_session(root: &std::path::Path, id: &str, idea: &str, output: Option<&str>, msgs: usize, cards: usize) {
        let dir = root.join(".vibelign/planning").join(id);
        std::fs::create_dir_all(&dir).expect("mkdir");
        let output_json = match output {
            Some(p) => format!("\"{p}\""),
            None => "null".to_string(),
        };
        std::fs::write(
            dir.join("session.json"),
            format!(
                "{{\"schema_version\":1,\"session_id\":\"{id}\",\"idea\":\"{idea}\",\"mode\":\"chat\",\"created_at\":\"1\",\"output_path\":{output_json}}}"
            ),
        )
        .expect("session");
        let msg = "{\"id\":\"m\",\"role\":\"user\",\"personaId\":null,\"content\":\"hi\",\"status\":\"ok\",\"createdAt\":\"1\"}";
        let arr = vec![msg; msgs].join(",");
        std::fs::write(dir.join("messages.json"), format!("[{arr}]")).expect("messages");
        let card = "{\"id\":\"c\",\"title\":\"t\",\"summary\":\"\",\"reason\":\"\",\"state\":\"draft\",\"createdAt\":\"1\",\"updatedAt\":\"1\"}";
        let carr = vec![card; cards].join(",");
        std::fs::write(dir.join("cards.json"), format!("{{\"cards\":[{carr}]}}")).expect("cards");
    }

    #[test]
    fn list_sessions_returns_summaries_with_saved_flag_and_counts() {
        let root = tempfile::tempdir().expect("root");
        write_session(root.path(), "chat_1", "예약 앱", None, 2, 1);
        write_session(root.path(), "chat_2", "카드 흐름", Some("plans/a.md"), 4, 3);

        let summaries = list_sessions(root.path());

        assert_eq!(summaries.len(), 2);
        let saved = summaries.iter().find(|s| s.session_id == "chat_2").expect("chat_2");
        assert!(saved.saved);
        assert_eq!(saved.output_path.as_deref(), Some("plans/a.md"));
        assert_eq!(saved.title, "카드 흐름");
        assert_eq!(saved.message_count, 4);
        assert_eq!(saved.card_count, 3);
        let draft = summaries.iter().find(|s| s.session_id == "chat_1").expect("chat_1");
        assert!(!draft.saved);
        assert_eq!(draft.message_count, 2);
    }

    #[test]
    fn list_sessions_skips_dirs_without_messages() {
        let root = tempfile::tempdir().expect("root");
        let dir = root.path().join(".vibelign/planning/chat_x");
        std::fs::create_dir_all(&dir).expect("mkdir");
        std::fs::write(dir.join("session.json"), "{}").expect("session");
        assert!(list_sessions(root.path()).is_empty());
    }

    #[test]
    fn load_session_from_dir_reads_messages_and_cards() {
        let root = tempfile::tempdir().expect("root");
        write_session(root.path(), "chat_9", "복원 테스트", Some("plans/x.md"), 3, 2);
        let session_dir = root.path().join(".vibelign/planning/chat_9");

        let response = load_session_from_dir(root.path(), &session_dir);

        let json = serde_json::to_value(&response).expect("json");
        assert_eq!(json["ok"], true);
        assert_eq!(json["sessionId"], "chat_9");
        assert_eq!(json["messages"].as_array().expect("messages").len(), 3);
        assert_eq!(json["cards"].as_array().expect("cards").len(), 2);
        assert_eq!(json["outputPath"], "plans/x.md");
    }

    #[test]
    fn mark_doc_stale_marks_saved_session_once_and_keeps_path() {
        let mut session = StoredPlanningChatSession {
            schema_version: 1,
            session_id: "chat_1".to_string(),
            idea: "예약 앱".to_string(),
            mode: "chat".to_string(),
            created_at: "1".to_string(),
            output_path: Some("plans/a.md".to_string()),
            absolute_output_path: Some("/p/plans/a.md".to_string()),
            doc_stale: false,
            readiness: None,
        };

        assert!(mark_doc_stale(&mut session)); // 첫 턴 — 기록 필요
        assert!(session.doc_stale);
        assert_eq!(session.output_path.as_deref(), Some("plans/a.md")); // 포인터는 유지
        assert!(!mark_doc_stale(&mut session)); // 이미 stale — 재기록 불필요
    }

    #[test]
    fn mark_doc_stale_ignores_unsaved_session() {
        let mut session = StoredPlanningChatSession {
            schema_version: 1,
            session_id: "chat_2".to_string(),
            idea: "예약 앱".to_string(),
            mode: "chat".to_string(),
            created_at: "1".to_string(),
            output_path: None,
            absolute_output_path: None,
            doc_stale: false,
            readiness: None,
        };

        assert!(!mark_doc_stale(&mut session));
        assert!(!session.doc_stale);
    }

    #[test]
    fn list_sessions_exposes_doc_stale_flag() {
        let root = tempfile::tempdir().expect("root");
        let dir = root.path().join(".vibelign/planning/chat_s");
        std::fs::create_dir_all(&dir).expect("mkdir");
        std::fs::write(
            dir.join("session.json"),
            "{\"schema_version\":1,\"session_id\":\"chat_s\",\"idea\":\"알람앱\",\"mode\":\"chat\",\"created_at\":\"1\",\"output_path\":\"plans/알람앱.md\",\"absolute_output_path\":null,\"doc_stale\":true}",
        )
        .expect("session");
        std::fs::write(dir.join("messages.json"), "[]").expect("messages");

        let summaries = list_sessions(root.path());

        assert_eq!(summaries.len(), 1);
        assert!(summaries[0].saved);
        assert!(summaries[0].doc_stale);
        assert_eq!(summaries[0].output_path.as_deref(), Some("plans/알람앱.md"));
    }
}
// === ANCHOR: PLANNING_CHAT_END ===
