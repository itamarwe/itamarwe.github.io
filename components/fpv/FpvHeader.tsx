import Link from "next/link";

// Slim section sub-header shown under the global site header on every /fpv
// page, giving the dataset its own identity + navigation without replacing the
// site chrome.
const DATASET_REPO = "https://github.com/itamarwe/fpv-drone-strikes-lebanon-dataset";
const WRITEUP = "/blog/fpv-drone-strikes-open-dataset/";

export function FpvHeader() {
  return (
    <div className="fpv-subheader">
      <div className="fpv-wrap fpv-subheader-inner">
        <Link className="fpv-section-title" href="/fpv/">
          FPV Drone-Strike Dataset
        </Link>
        <nav className="fpv-section-nav">
          <Link href="/fpv/">Gallery</Link>
          <Link href={WRITEUP}>Writeup</Link>
          <a href={DATASET_REPO} target="_blank" rel="noreferrer">
            GitHub
          </a>
        </nav>
      </div>
    </div>
  );
}
