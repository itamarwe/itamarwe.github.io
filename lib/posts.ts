import fs from "node:fs";
import path from "node:path";
import matter from "gray-matter";
import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkGfm from "remark-gfm";
import remarkRehype from "remark-rehype";
import rehypeRaw from "rehype-raw";
import rehypeHighlight from "rehype-highlight";
import rehypeStringify from "rehype-stringify";

const POSTS_DIR = path.join(process.cwd(), "content", "posts");

/** Default social-share image when a post sets no `image` in its frontmatter. */
export const DEFAULT_OG_IMAGE = "/img/profile.jpg";

export interface Post {
  /** Filename-derived slug, e.g. "how-does-a-drone-fly" (case preserved). */
  slug: string;
  title: string;
  /** ISO date string (UTC) of the post. */
  date: string;
  /** Raw `categories` frontmatter value, as written. */
  categories: string;
  /** Whether Disqus comments are enabled. */
  comments: boolean;
  /** Social-share (OpenGraph/Twitter) image path. Optional `image` in
   *  frontmatter; falls back to {@link DEFAULT_OG_IMAGE}. */
  image: string;
  /** Raw markdown body (frontmatter stripped). */
  body: string;
  /** Clean canonical path, e.g. "/blog/how-does-a-drone-fly/". */
  url: string;
  /** The exact legacy Jekyll URL this post used to live at. */
  legacyUrl: string;
}

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** Format a date the way the Jekyll templates did: e.g. "Nov 5, 2017". */
export function formatDate(iso: string): string {
  const d = new Date(iso);
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()}`;
}

function toIsoDate(value: unknown): string {
  if (value instanceof Date) return value.toISOString();
  // gray-matter usually yields a Date; fall back to parsing a string.
  return new Date(String(value)).toISOString();
}

/**
 * Reproduce Jekyll's `:categories` permalink segment exactly. Jekyll splits the
 * raw `categories` string on whitespace, so `categories: a, b` (a comma-joined
 * string) becomes the path segments `a,/b`. We preserve that faithfully so the
 * legacy URLs we redirect from match what was actually published.
 */
function legacyCategoryPath(categories: string): string {
  return categories.trim().split(/\s+/).filter(Boolean).join("/");
}

function buildPost(filename: string): Post {
  const fullPath = path.join(POSTS_DIR, filename);
  const raw = fs.readFileSync(fullPath, "utf8");
  const { data, content } = matter(raw);

  const slug = filename.replace(/^\d{4}-\d{2}-\d{2}-/, "").replace(/\.(md|markdown)$/, "");
  const iso = toIsoDate(data.date);
  const d = new Date(iso);
  const categories = String(data.categories ?? "");

  const legacyDatePath = `${d.getUTCFullYear()}/${pad(d.getUTCMonth() + 1)}/${pad(d.getUTCDate())}`;
  const legacyUrl = `/${legacyCategoryPath(categories)}/${legacyDatePath}/${slug}.html`;

  return {
    slug,
    title: String(data.title ?? slug),
    date: iso,
    categories,
    comments: data.comments === true,
    image: typeof data.image === "string" && data.image.trim()
      ? data.image.trim()
      : DEFAULT_OG_IMAGE,
    body: content,
    url: `/blog/${slug}/`,
    legacyUrl,
  };
}

let cachedPosts: Post[] | null = null;

/** All posts, newest first (matches Jekyll's `site.posts` ordering). */
export function getAllPosts(): Post[] {
  if (cachedPosts) return cachedPosts;
  const files = fs
    .readdirSync(POSTS_DIR)
    .filter((f) => /\.(md|markdown)$/.test(f));
  cachedPosts = files
    .map(buildPost)
    .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  return cachedPosts;
}

export function getPostBySlug(slug: string): Post | undefined {
  return getAllPosts().find((p) => p.slug === slug);
}

/** Render a markdown string to HTML (raw HTML, GFM, and code highlighting). */
export async function renderMarkdown(markdown: string): Promise<string> {
  const file = await unified()
    .use(remarkParse)
    .use(remarkGfm)
    .use(remarkRehype, { allowDangerousHtml: true })
    .use(rehypeRaw)
    .use(rehypeHighlight, { detect: true })
    .use(rehypeStringify)
    .process(markdown);
  return String(file);
}

/** Plain-text excerpt (first paragraph) for meta descriptions. */
export function getExcerpt(markdown: string, limit = 160): string {
  const blocks = markdown.split(/\n{2,}/);
  let paragraph = "";
  for (const block of blocks) {
    const t = block.trim();
    if (!t) continue;
    // Skip headings, images, html, lists, blockquotes, code fences, tables.
    if (/^(#|!\[|<|>|\||```|[-*]\s|\d+\.\s)/.test(t)) continue;
    paragraph = t;
    break;
  }
  const text = paragraph
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/[*_`>#]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  if (text.length <= limit) return text;
  return text.slice(0, limit - 3).trimEnd() + "...";
}
