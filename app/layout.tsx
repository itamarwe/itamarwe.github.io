import type { Metadata } from "next";
import "@/styles/globals.scss";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import Analytics from "@/components/Analytics";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  metadataBase: new URL(site.url),
  title: site.title,
  description: site.description,
  authors: [{ name: site.author }],
  icons: { shortcut: "/favicon.ico" },
  alternates: {
    types: {
      "application/rss+xml": "/feed.xml",
    },
  },
  openGraph: {
    type: "website",
    siteName: site.title,
    images: ["/img/profile.jpg"],
  },
  twitter: {
    card: "summary",
    site: `@${site.twitterUsername}`,
    creator: `@${site.twitterUsername}`,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Header />
        <div className="page-content">
          <div className="wrapper">{children}</div>
        </div>
        <Footer />
        <Analytics />
      </body>
    </html>
  );
}
