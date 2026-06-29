import type { Metadata } from "next";
import { getPageMarkdown } from "@/lib/pages";
import { renderMarkdown } from "@/lib/posts";
import ProfileDots from "@/components/ProfileDots";

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
      {/* Floated before the header so both the title and the body text wrap
          around the portrait. Rendered client-side as dot-art: the portrait is
          sampled into a grid and drawn as white dots sized by brightness. */}
      <ProfileDots alt="Itamar Weiss" className="profile-photo" />
      <header className="post-header">
        <h1 className="post-title">{TITLE}</h1>
      </header>
      <div className="post-content" dangerouslySetInnerHTML={{ __html: html }} />
    </article>
  );
}
