import fs from "node:fs";
import path from "node:path";

const PAGES_DIR = path.join(process.cwd(), "content", "pages");

export function getPageMarkdown(name: string): string {
  return fs.readFileSync(path.join(PAGES_DIR, `${name}.md`), "utf8");
}
