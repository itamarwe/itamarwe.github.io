"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import type { VideoRecord } from "@/lib/fpv/types";
import { THUMB_BASE } from "@/lib/fpv/config";
import { sceneHref, videoHref } from "@/lib/fpv/paths";

const PlayIcon = () => (
  <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden>
    <path d="M8 5.14v13.72L19 12 8 5.14z" />
  </svg>
);

const GlobeIcon = () => (
  <svg
    viewBox="0 0 24 24"
    width="14"
    height="14"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    aria-hidden
  >
    <circle cx="12" cy="12" r="9" />
    <ellipse cx="12" cy="12" rx="4" ry="9" />
    <path d="M3.5 9h17M3.5 15h17" />
  </svg>
);

const ArrowIcon = ({ dir }: { dir: "asc" | "desc" }) => (
  <svg
    viewBox="0 0 24 24"
    width="13"
    height="13"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    aria-hidden
  >
    {dir === "desc" ? <path d="M12 4v16m0 0l-6-6m6 6l6-6" /> : <path d="M12 20V4m0 0l-6 6m6-6l6 6" />}
  </svg>
);

function Thumb({ video }: { video: VideoRecord }) {
  const [broken, setBroken] = useState(false);
  const useLocal = Boolean(video.thumbWidths?.length) && !broken;
  const src = useLocal
    ? `${THUMB_BASE}/${video.slug}/${video.thumbWidths![video.thumbWidths!.length - 1]}.webp`
    : video.thumbnailUrl;
  const srcSet = useLocal
    ? video.thumbWidths!.map((w) => `${THUMB_BASE}/${video.slug}/${w}.webp ${w}w`).join(", ")
    : undefined;
  return (
    <Link
      className="thumb"
      href={videoHref(video.slug)}
      style={video.blur ? { backgroundImage: `url(${video.blur})` } : undefined}
    >
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          srcSet={srcSet}
          sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 280px"
          alt={video.description}
          loading="lazy"
          decoding="async"
          onError={() => setBroken(true)}
        />
      ) : null}
      {video.scenePath ? <span className="badge-3d">3D scene</span> : null}
    </Link>
  );
}

type SceneFilter = "all" | "with";
type SortDir = "desc" | "asc";
type GalleryState = {
  query: string;
  sort: SortDir;
  sceneFilter: SceneFilter;
};

function galleryStateFromParams(params: Pick<URLSearchParams, "get">): GalleryState {
  return {
    query: params.get("q") ?? "",
    sort: params.get("sort") === "asc" ? "asc" : "desc",
    sceneFilter: params.get("scene") === "with" ? "with" : "all",
  };
}

function writeGalleryState(params: URLSearchParams, state: GalleryState) {
  if (state.query) params.set("q", state.query);
  else params.delete("q");

  if (state.sort === "asc") params.set("sort", "asc");
  else params.delete("sort");

  if (state.sceneFilter === "with") params.set("scene", "with");
  else params.delete("scene");
}

type GalleryContentsProps = {
  videos: VideoRecord[];
  query: string;
  sort: SortDir;
  sceneFilter: SceneFilter;
  onQueryChange?: (query: string) => void;
  onSortChange?: () => void;
  onSceneFilterChange?: () => void;
};

function GalleryContents({
  videos,
  query,
  sort,
  sceneFilter,
  onQueryChange,
  onSortChange,
  onSceneFilterChange,
}: GalleryContentsProps) {
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = videos.filter((v) => {
      if (sceneFilter === "with" && !v.scenePath) return false;
      if (!q) return true;
      return `${v.description} ${v.town} ${v.date} ${v.videoFile}`.toLowerCase().includes(q);
    });
    list.sort((a, b) => {
      const cmp = a.date < b.date ? -1 : a.date > b.date ? 1 : 0;
      return sort === "desc" ? -cmp : cmp;
    });
    return list;
  }, [videos, query, sort, sceneFilter]);

  return (
    <div>
      <div className="gallery-toolbar">
        <input
          type="search"
          name="site-search-query"
          value={query}
          onChange={(e) => onQueryChange?.(e.target.value)}
          readOnly={!onQueryChange}
          placeholder="Search by description, town, date…"
          aria-label="Search videos"
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
        />
        <button
          type="button"
          className="toolbar-btn"
          onClick={onSortChange}
          aria-label={`Sort by date, ${sort === "desc" ? "newest" : "oldest"} first`}
          title={sort === "desc" ? "Newest first" : "Oldest first"}
        >
          Date <ArrowIcon dir={sort} />
        </button>
        <button
          type="button"
          className={`toolbar-btn${sceneFilter === "with" ? " active" : ""}`}
          onClick={onSceneFilterChange}
          aria-pressed={sceneFilter === "with"}
          title="Only videos with a reconstructed 3D scene"
        >
          <GlobeIcon /> 3D scenes
        </button>
        <span className="gallery-count">
          {filtered.length === videos.length
            ? `${videos.length} videos`
            : `${filtered.length} of ${videos.length}`}
        </span>
      </div>
      <div className="video-grid">
        {filtered.map((v) => (
          <div className="video-card" key={v.videoFile}>
            <Thumb video={v} />
            <Link className="title" href={videoHref(v.slug)}>
              {v.description || v.videoFile}
            </Link>
            <span className="meta">
              {v.date}
              {v.town ? ` · ${v.town}` : ""}
            </span>
            <div className="card-actions">
              <Link className="card-btn" href={videoHref(v.slug)}>
                <PlayIcon /> Video
              </Link>
              {v.scenePath ? (
                <Link className="card-btn primary" href={sceneHref(v.slug)}>
                  <GlobeIcon /> 3D scene
                </Link>
              ) : (
                <span className="card-btn disabled" title="No reconstructed scene yet">
                  <GlobeIcon /> No scene
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
      {filtered.length === 0 ? <p className="not-found">No videos match your filters.</p> : null}
    </div>
  );
}

export function Gallery({ videos }: { videos: VideoRecord[] }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [state, setState] = useState<GalleryState>(() => galleryStateFromParams(searchParams));
  const stateRef = useRef(state);

  useEffect(() => {
    const syncFromUrl = () => {
      const nextState = galleryStateFromParams(new URLSearchParams(window.location.search));
      stateRef.current = nextState;
      setState(nextState);
    };

    window.addEventListener("popstate", syncFromUrl);
    return () => window.removeEventListener("popstate", syncFromUrl);
  }, []);

  const updateState = useCallback(
    (getNextState: (current: GalleryState) => GalleryState) => {
      const nextState = getNextState(stateRef.current);
      stateRef.current = nextState;
      setState(nextState);

      const params = new URLSearchParams(window.location.search);
      writeGalleryState(params, nextState);
      const queryString = params.toString();
      const nextUrl = queryString ? `${pathname}?${queryString}` : pathname;
      window.history.replaceState(null, "", nextUrl);
    },
    [pathname],
  );

  return (
    <GalleryContents
      videos={videos}
      query={state.query}
      sort={state.sort}
      sceneFilter={state.sceneFilter}
      onQueryChange={(query) => updateState((current) => ({ ...current, query }))}
      onSortChange={() =>
        updateState((current) => ({
          ...current,
          sort: current.sort === "desc" ? "asc" : "desc",
        }))
      }
      onSceneFilterChange={() =>
        updateState((current) => ({
          ...current,
          sceneFilter: current.sceneFilter === "all" ? "with" : "all",
        }))
      }
    />
  );
}

export function GalleryFallback({ videos }: { videos: VideoRecord[] }) {
  return <GalleryContents videos={videos} query="" sort="desc" sceneFilter="all" />;
}
