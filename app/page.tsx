import type { Metadata } from "next";
import Link from "next/link";
import { getAllPosts, getExcerpt, formatDate, DEFAULT_OG_IMAGE } from "@/lib/posts";
import { homeJsonLd } from "@/lib/structured-data";

const HOME_TITLE = "Itamar Weiss — Hands-on AI & Data Consultant";
const HOME_DESCRIPTION =
  "Helping teams ship AI agents, data platforms, and production AI features. Hands-on building with modern AI and data engineering stacks.";

export const metadata: Metadata = {
  title: HOME_TITLE,
  description: HOME_DESCRIPTION,
  alternates: { canonical: "/" },
  openGraph: {
    title: HOME_TITLE,
    description: HOME_DESCRIPTION,
    url: "/",
    type: "website",
    images: [DEFAULT_OG_IMAGE],
  },
};

export default function Home() {
  const posts = getAllPosts();

  return (
    <div className="home">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(homeJsonLd()) }}
      />
      <header className="home-intro">
        <h1 className="post-title">Itamar Weiss — Hands-on AI &amp; Data Consultant</h1>
        <p>
          I help teams design and ship AI agents, data platforms, and production
          AI features. I write about AI systems, software engineering, data
          infrastructure, and the practical work of turning technical ideas into
          reliable products. Read about my background and selected work on the{" "}
          <Link href="/about/">About page</Link>, or{" "}
          <Link href="/contact/">get in touch</Link> about a project.
        </p>
      </header>

      <h2 className="page-heading">Latest Writing</h2>

      <ul className="post-list">
        {posts.map((post) => (
          <li key={post.slug}>
            <span className="post-meta">{formatDate(post.date)}</span>
            <h2>
              <Link className="post-link" href={post.url}>
                {post.title}
              </Link>
            </h2>
            <p className="post-excerpt">{getExcerpt(post.body)}</p>
          </li>
        ))}
      </ul>

      <p className="rss-subscribe">
        subscribe <a href="/feed.xml">via RSS</a>
      </p>
    </div>
  );
}
