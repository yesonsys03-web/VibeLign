// pdf.js 인앱 미리보기에 필요한 런타임 에셋을 public/ 으로 복사한다.
//   - cmaps:          CID 폰트 인코딩 매핑(.bcmap)
//   - standard_fonts: 비임베드 표준폰트(Helvetica 등) 대체 폰트
// 이게 없으면 pdf.js 가 폰트 로딩에 실패해 텍스트를 못 그린다(벡터만 렌더).
// public/ 은 Vite 가 dev·build 양쪽에서 루트(`/pdfjs/...`)로 서빙한다.
// 복사본은 node_modules 에서 재생성 가능하므로 .gitignore 처리한다(레포 미커밋).
import { cpSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const src = resolve(root, "node_modules/pdfjs-dist");
const dest = resolve(root, "public/pdfjs");

for (const sub of ["cmaps", "standard_fonts"]) {
  const from = resolve(src, sub);
  const to = resolve(dest, sub);
  mkdirSync(to, { recursive: true });
  cpSync(from, to, { recursive: true });
}

console.log(`[copy-pdfjs-assets] cmaps + standard_fonts -> public/pdfjs/`);
