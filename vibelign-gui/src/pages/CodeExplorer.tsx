import { useEffect, useMemo, useState } from "react";

import CodeExplorerLayout from "../components/code-explorer/CodeExplorerLayout";
import CodeExplorerToolbar from "../components/code-explorer/CodeExplorerToolbar";
import CodeFileTree from "../components/code-explorer/CodeFileTree";
import CodeFileViewer from "../components/code-explorer/CodeFileViewer";
import { filterCodeFiles } from "../lib/code-explorer/filters";
import { listCodeFiles, readCodeFile, readCodeFileDiff, type CodeFileEntry, type CodeFileReadResult, type CodeFileDiffResult } from "../lib/vib";

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

  const filteredFiles = useMemo(() => filterCodeFiles(files, query), [files, query]);

  async function refreshFiles() {
    setIsRefreshing(true);
    setListError(null);
    try {
      const next = await listCodeFiles(projectDir);
      setFiles(next);
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
    setFileError(null);
    Promise.all([
      readCodeFile(projectDir, selectedPath),
      readCodeFileDiff(projectDir, selectedPath).catch(() => null),
    ])
      .then(([fileResult, diffResult]) => {
        if (cancelled) return;
        setSelectedFile(fileResult);
        setSelectedDiff(diffResult);
        // 자동 ON 규칙: baseline 있고 변경 있음 → diffMode = true
        const hasBaseline = diffResult !== null && diffResult.baseline_source !== "none";
        const hasChanges = diffResult !== null && (diffResult.added + diffResult.removed) > 0;
        setDiffMode(hasBaseline && hasChanges);
      })
      .catch((error: unknown) => {
        if (!cancelled) setFileError(error instanceof Error ? error.message : "코드 파일을 읽을 수 없어요");
      })
      .finally(() => {
        if (!cancelled) setIsLoadingFile(false);
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
      tree={<CodeFileTree files={filteredFiles} selectedPath={selectedPath} onSelect={setSelectedPath} autoExpandAll={query.trim().length > 0} />}
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
