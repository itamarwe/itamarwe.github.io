import type { Metadata } from "next";
import { getPageMarkdown } from "@/lib/pages";
import { renderMarkdown } from "@/lib/posts";

const TITLE = "Privacy";
const DESCRIPTION =
  "What data itamarweiss.com does and does not collect: no accounts, no forms, no ads — just hosting logs, optional analytics, and email you initiate.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/privacy/" },
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    url: "/privacy/",
    type: "website",
  },
};

export default async function PrivacyPage() {
  const html = await renderMarkdown(getPageMarkdown("privacy"));
  return (
    <article className="post">
      <header className="post-header">
        <h1 className="post-title">{TITLE}</h1>
      </header>
      <div className="post-content" dangerouslySetInnerHTML={{ __html: html }} />
    </article>
  );
}
