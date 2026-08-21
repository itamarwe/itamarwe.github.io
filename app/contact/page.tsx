import type { Metadata } from "next";
import { getPageMarkdown } from "@/lib/pages";
import { renderMarkdown } from "@/lib/posts";

const TITLE = "Contact";
const DESCRIPTION =
  "How to reach Itamar Weiss for AI and data consulting inquiries, questions about blog posts, or speaking invitations.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/contact/" },
  openGraph: {
    title: TITLE,
    description: DESCRIPTION,
    url: "/contact/",
    type: "website",
  },
};

export default async function ContactPage() {
  const html = await renderMarkdown(getPageMarkdown("contact"));
  return (
    <article className="post">
      <header className="post-header">
        <h1 className="post-title">{TITLE}</h1>
      </header>
      <div className="post-content" dangerouslySetInnerHTML={{ __html: html }} />
    </article>
  );
}
