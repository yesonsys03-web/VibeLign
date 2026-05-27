import { useEffect, useMemo, useState } from "react";

import CodeExplorerLayout from "../components/code-explorer/CodeExplorerLayout";
import CodeExplorerToolbar from "../components/code-explorer/CodeExplorerToolbar";
import CodeFileTree from "../components/code-explorer/CodeFileTree";
import CodeFileViewer from "../components/code-explorer/CodeFileViewer";
import { filterCodeFiles } from "../lib/code-explorer/filters";
import { listCodeFiles, readCodeFile, type CodeFileEntry, type CodeFileReadResult } from "../lib/vib";

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
      setFileError(null);
      return () => { cancelled = true; };
    }
    setIsLoadingFile(true);
    setSelectedFile(null);
    setFileError(null);
    readCodeFile(projectDir, selectedPath)
      .then((result) => {
        if (!cancelled) setSelectedFile(result);
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
      viewer={<CodeFileViewer selectedPath={selectedPath} file={selectedFile} isLoading={isLoadingFile} error={fileError} />}
    />
  );
}
