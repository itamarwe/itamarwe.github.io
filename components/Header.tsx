import Link from "next/link";
import { site } from "@/lib/site";

const navPages = [{ title: "About", url: "/about/" }];

export default function Header() {
  return (
    <header className="site-header">
      <div className="wrapper">
        <Link className="site-title" href="/">
          {site.title}
        </Link>

        <nav className="site-nav">
          {navPages.map((p) => (
            <Link key={p.url} className="page-link" href={p.url}>
              {p.title}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
