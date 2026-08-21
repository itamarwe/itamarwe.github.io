import { site } from "./site.ts";

/**
 * JSON-LD for the homepage: a Person (this is a personal site) plus the
 * WebSite that belongs to them, in one @graph so agents resolve both from a
 * single script tag.
 */
export function homeJsonLd(): Record<string, unknown> {
  const personId = `${site.url}/#person`;
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Person",
        "@id": personId,
        name: site.author,
        url: `${site.url}/`,
        email: `mailto:${site.email}`,
        jobTitle: "AI & Data Consultant",
        description:
          "Hands-on AI and data consultant helping teams ship AI agents, " +
          "data platforms, and production AI features.",
        image: `${site.url}/img/profile.jpg`,
        sameAs: [
          `https://github.com/${site.githubUsername}`,
          `https://x.com/${site.twitterUsername}`,
          `https://twitter.com/${site.twitterUsername}`,
        ],
        knowsAbout: [
          "AI agents",
          "Large language models",
          "Retrieval-augmented generation",
          "Data engineering",
          "Apache Iceberg",
          "Apache Kafka",
          "Apache Flink",
          "Apache Spark",
        ],
      },
      {
        "@type": "WebSite",
        "@id": `${site.url}/#website`,
        name: site.title,
        url: `${site.url}/`,
        description: site.description,
        author: { "@id": personId },
        publisher: { "@id": personId },
        inLanguage: "en",
      },
    ],
  };
}
