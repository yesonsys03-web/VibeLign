import { useEffect, useMemo, useState } from "react";

import CodeExplorerLayout from "../components/code-explorer/CodeExplorerLayout";
import CodeExplorerToolbar from "../components/code-explorer/CodeExplorerToolbar";
import CodeFileTree from "../components/code-explorer/CodeFileTree";
import CodeFileViewer from "../components/code-explorer/CodeFileViewer";
import { filterCodeFiles } from "../lib/code-explorer/filters";
import { listCodeFiles, readCodeFile, readCodeFileDiff, listChangedFiles, type CodeFileEntry, type CodeFileReadResult, type CodeFileDiffResult, type ChangeStatus, type ChangedEntry } from "../lib/vib";

interface CodeExplorerProps {
  projectDir: string;
}

export default function CodeExplorer({ projectDir }: CodeExplorerProps) {
  const [files, setFiles] = useState<CodeFileEntry[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<CodeFileReadResult | null>(null);
  const [query, setQuery] = useState("");
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingFile, setIsLoadingFile] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [selectedDiff, setSelectedDiff] = useState<CodeFileDiffResult | null>(null);
  const [diffMode, setDiffMode] = useState<boolean>(false);
  const [changes, setChanges] = useState<ReadonlyMap<string, ChangeStatus>>(new Map());

  const filteredFiles = useMemo(() => filterCodeFiles(files, query), [files, query]);

  async function refreshFiles() {
    setIsRefreshing(true);
    setListError(null);
    try {
      const [next, changed] = await Promise.all([
        listCodeFiles(projectDir),
        listChangedFiles(projectDir).catch(() => [] as ChangedEntry[]),
      ]);
      setFiles(next);
      setChanges(new Map(changed.map((entry) => [entry.path, entry.status])));
      setSelectedPath((current) => current && next.some((file) => file.path === current) ? current : next[0]?.path ?? null);
    } catch (error: unknown) {
      setListError(error instanceof Error ? error.message : "코드 파일 목록을 읽을 수 없어요");
    } finally {
      setIsLoadingList(false);
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    void refreshFiles();
  }, [projectDir]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedPath) {
      setSelectedFile(null);
      setSelectedDiff(null);
      setDiffMode(false);
      setFileError(null);
      return () => { cancelled = true; };
    }
    setIsLoadingFile(true);
    setSelectedFile(null);
    setSelectedDiff(null);
    setDiffMode(false); // diff 도착 전까지는 평면 뷰로 시작
    setFileError(null);

    // 코드 본문은 git 을 타지 않으므로(파일 read만) 먼저 띄운다 — 로딩 스피너를 이 호출에만
    // 연동해, 느린 diff(git 호출)가 코드 표시를 막지 않게 한다.
    readCodeFile(projectDir, selectedPath)
      .then((fileResult) => {
        if (cancelled) return;
        setSelectedFile(fileResult);
        setIsLoadingFile(false);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setFileError(error instanceof Error ? error.message : "코드 파일을 읽을 수 없어요");
        setIsLoadingFile(false);
      });

    // diff(baseline 비교)는 git 을 타서 느릴 수 있다 — 독립적으로 로드하고, 도착하면 배지/토글을
    // 채우고 자동 ON 규칙(baseline 있고 변경 있음 → diff 뷰로 전환)을 적용한다.
    readCodeFileDiff(projectDir, selectedPath)
      .then((diffResult) => {
        if (cancelled) return;
        setSelectedDiff(diffResult);
        const hasBaseline = diffResult.baseline_source !== "none";
        const hasChanges = (diffResult.added + diffResult.removed) > 0;
        setDiffMode(hasBaseline && hasChanges);
      })
      .catch(() => {
        if (!cancelled) setSelectedDiff(null); // diff 실패는 무시 — 평면 뷰 유지
      });

    return () => { cancelled = true; };
  }, [projectDir, selectedPath]);

  if (isLoadingList) {
    return <div style={{ padding: 16 }}>코드 파일 목록을 불러오는 중입니다…</div>;
  }

  if (listError) {
    return <div className="alert-error" style={{ margin: 16 }}>{listError}</div>;
  }

  return (
    <CodeExplorerLayout
      toolbar={<CodeExplorerToolbar query={query} fileCount={filteredFiles.length} isRefreshing={isRefreshing} onQueryChange={setQuery} onRefresh={() => void refreshFiles()} />}
      tree={<CodeFileTree files={filteredFiles} selectedPath={selectedPath} onSelect={setSelectedPath} autoExpandAll={query.trim().length > 0} changes={changes} />}
      viewer={<CodeFileViewer
        selectedPath={selectedPath}
        file={selectedFile}
        diff={selectedDiff}
        diffMode={diffMode}
        onToggleDiffMode={() => setDiffMode((v) => !v)}
        isLoading={isLoadingFile}
        error={fileError}
      />}
    />
  );
}
