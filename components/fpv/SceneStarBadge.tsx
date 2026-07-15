type SceneStarBadgeProps = {
  compact?: boolean;
};

export function SceneStarBadge({ compact = false }: SceneStarBadgeProps) {
  return (
    <span
      className={`scene-star-badge${compact ? " compact" : ""}`}
      title="Starred 3D scene"
      aria-label="Starred 3D scene"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m12 3.8 2.55 5.16 5.7.83-4.13 4.03.98 5.68L12 16.82 6.9 19.5l.98-5.68-4.13-4.03 5.7-.83L12 3.8Z" />
      </svg>
      {compact ? null : "Starred 3D scene"}
    </span>
  );
}
