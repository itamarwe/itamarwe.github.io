import type { Metadata } from "next";
import Image from "next/image";
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
      {/* Floated before the header so both the title and the body text wrap
          around the portrait. Served through Vercel's image optimizer
          (next/image) for AVIF/WebP + a responsive srcset. */}
      <Image
        src="/img/profile.jpg"
        alt="Itamar Weiss"
        width={1254}
        height={1254}
        sizes="(max-width: 600px) 220px, 300px"
        priority
        className="profile-photo"
      />
      <header className="post-header">
        <h1 className="post-title">{TITLE}</h1>
      </header>
      <div className="post-content" dangerouslySetInnerHTML={{ __html: html }} />
    </article>
  );
}
