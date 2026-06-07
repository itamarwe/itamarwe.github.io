import type { Metadata } from "next";
import { getPageMarkdown } from "@/lib/pages";
import { renderMarkdown } from "@/lib/posts";

const TITLE = "About";
const DESCRIPTION =
  "Expert consulting in AI agents, LLMs, RAG, and data engineering. Helping teams ship production AI systems on modern data stacks.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/about/" },
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    url: "/about/",
    type: "website",
  },
};

export default async function AboutPage() {
  const html = await renderMarkdown(getPageMarkdown("about"));
  return (
    <article className="post">
      <header className="post-header">
        <h1 className="post-title">{TITLE}</h1>
      </header>
      <div className="post-content" dangerouslySetInnerHTML={{ __html: html }} />
    </article>
  );
}
