import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "404 — Page not found",
  robots: { index: false },
};

/**
 * Global 404. Served with a real 404 status; the body gives both people and
 * agents somewhere to go next instead of a bare app shell.
 */
export default function NotFound() {
  return (
    <article className="post">
      <header className="post-header">
        <h1 className="post-title">404 — Page not found</h1>
      </header>
      <div className="post-content">
        <p>
          This page does not exist. It may have moved — old Jekyll-era URLs
          redirect automatically, so a dead link here usually means a typo or
          removed content.
        </p>
        <p>Where to look instead:</p>
        <ul>
          <li>
            <Link href="/">Homepage</Link> — latest writing and the full post
            index (posts live at <code>/blog/&lt;slug&gt;/</code>)
          </li>
          <li>
            <Link href="/about/">About</Link>, <Link href="/contact/">Contact</Link>,{" "}
            <Link href="/privacy/">Privacy</Link>
          </li>
          <li>
            <a href="/llms.txt">llms.txt</a> — machine-readable index of this
            site for AI agents
          </li>
          <li>
            <a href="/sitemap.xml">sitemap.xml</a> — every canonical URL
          </li>
          <li>
            <a href="/feed.xml">RSS feed</a>
          </li>
        </ul>
        <p>
          Agents: every page here also serves markdown via{" "}
          <code>Accept: text/markdown</code> content negotiation.
        </p>
      </div>
    </article>
  );
}
