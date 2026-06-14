import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Doto } from "next/font/google";
import "katex/dist/katex.min.css";
import "@/styles/globals.scss";

// Doto — dot-matrix display font used for the site title in the header.
const doto = Doto({
  subsets: ["latin"],
  weight: ["500", "700"],
  variable: "--font-doto",
});
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

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#000000",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable} ${doto.variable}`}
    >
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
