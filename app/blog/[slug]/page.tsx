import type { Metadata } from "next";
import { notFound } from "next/navigation";
import {
  getAllPosts,
  getPostBySlug,
  renderMarkdown,
  getExcerpt,
  formatDate,
  DEFAULT_OG_IMAGE,
} from "@/lib/posts";
import KatexAutofit from "@/components/KatexAutofit";
import TwitterWidgets from "@/components/TwitterWidgets";

export function generateStaticParams() {
  return getAllPosts().map((post) => ({ slug: post.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = getPostBySlug(slug);
  if (!post) return {};
  const description = getExcerpt(post.body);
  const hasCustomImage = post.image !== DEFAULT_OG_IMAGE;
  return {
    title: post.title,
    description,
    alternates: { canonical: post.url },
    openGraph: {
      title: post.title,
      description,
      url: post.url,
      type: "article",
      images: [post.image],
    },
    twitter: {
      card: hasCustomImage ? "summary_large_image" : "summary",
      images: [post.image],
    },
  };
}

export default async function PostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = getPostBySlug(slug);
  if (!post) notFound();

  const html = await renderMarkdown(post.body);

  return (
    <>
      <article className="post" itemScope itemType="http://schema.org/BlogPosting">
        <header className="post-header">
          <h1 className="post-title" itemProp="name headline">
            {post.title}
          </h1>
          <p className="post-meta">
            <time dateTime={post.date} itemProp="datePublished">
              {formatDate(post.date)}
            </time>
          </p>
        </header>

        <div
          className="post-content"
          itemProp="articleBody"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </article>

      <KatexAutofit />
      <TwitterWidgets />
    </>
  );
}
