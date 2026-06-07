import { getAllPosts, renderMarkdown } from "@/lib/posts";
import { site } from "@/lib/site";

function escapeXml(unsafe: string): string {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

export async function GET() {
  const posts = getAllPosts().slice(0, 10);
  const now = new Date().toUTCString();

  const items = await Promise.all(
    posts.map(async (post) => {
      const content = await renderMarkdown(post.body);
      const link = `${site.url}${post.url}`;
      const categories = post.categories
        .trim()
        .split(/\s+/)
        .filter(Boolean)
        .map((c) => c.replace(/,$/, ""))
        .map((c) => `<category>${escapeXml(c)}</category>`)
        .join("");
      return `      <item>
        <title>${escapeXml(post.title)}</title>
        <description>${escapeXml(content)}</description>
        <pubDate>${new Date(post.date).toUTCString()}</pubDate>
        <link>${link}</link>
        <guid isPermaLink="true">${link}</guid>
        ${categories}
      </item>`;
    }),
  );

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>${escapeXml(site.title)}</title>
    <description>${escapeXml(site.description)}</description>
    <link>${site.url}/</link>
    <atom:link href="${site.url}/feed.xml" rel="self" type="application/rss+xml"/>
    <pubDate>${now}</pubDate>
    <lastBuildDate>${now}</lastBuildDate>
    <generator>Next.js</generator>
${items.join("\n")}
  </channel>
</rss>
`;

  return new Response(xml, {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
    },
  });
}
