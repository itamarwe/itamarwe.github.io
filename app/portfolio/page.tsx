import type { Metadata } from "next";
import { getPageMarkdown } from "@/lib/pages";
import { renderMarkdown } from "@/lib/posts";
import { site } from "@/lib/site";

const TITLE = "Portfolio";
const DESCRIPTION = site.description;

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/portfolio/" },
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    url: "/portfolio/",
    type: "website",
  },
};

export default async function PortfolioPage() {
  const html = await renderMarkdown(getPageMarkdown("portfolio"));
  return (
    <article className="post">
      <header className="post-header">
        <h1 className="post-title">{TITLE}</h1>
      </header>
      <div className="post-content" dangerouslySetInnerHTML={{ __html: html }} />
    </article>
  );
}
