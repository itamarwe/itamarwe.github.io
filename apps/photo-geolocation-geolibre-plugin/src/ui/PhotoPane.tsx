import { useRef, useState } from 'react';
import { useStore } from '../store';

/**
 * The photo half of the anchor UX (ported from the original tool's PhotoView,
 * minus the synthetic-scene rendering): upload an image, then click the same
 * physical point you'll click on the map. The click is recorded in the photo's
 * natural pixel coordinates, which is what the PnP solver's principal-point
 * assumption (cx = width/2) expects.
 */
export default function PhotoPane() {
  const photoUrl = useStore((s) => s.photoUrl);
  const image = useStore((s) => s.image);
  const anchors = useStore((s) => s.anchors);
  const activeAnchorId = useStore((s) => s.activeAnchorId);
  const setPhoto = useStore((s) => s.setPhoto);
  const clearPhoto = useStore((s) => s.clearPhoto);
  const setAnchorPhotoPixel = useStore((s) => s.setAnchorPhotoPixel);
  const imgRef = useRef<HTMLImageElement>(null);
  const [dragOver, setDragOver] = useState(false);

  function loadFile(file: File) {
    const url = URL.createObjectURL(file);
    const probe = new Image();
    probe.onload = () => setPhoto(url, probe.naturalWidth, probe.naturalHeight, file.name);
    probe.src = url;
  }

  function onClickImage(e: React.MouseEvent<HTMLImageElement>) {
    if (activeAnchorId == null) return;
    const el = imgRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    // displayed px → natural px
    const sx = image.width / rect.width;
    const sy = image.height / rect.height;
    setAnchorPhotoPixel(activeAnchorId, {
      x: (e.clientX - rect.left) * sx,
      y: (e.clientY - rect.top) * sy,
    });
  }

  if (!photoUrl) {
    return (
      <div
        className={`gp-drop ${dragOver ? 'gp-drop--over' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f) loadFile(f);
        }}
      >
        <p>Drop a photo here, or</p>
        <label className="gp-btn">
          Choose image
          <input
            type="file"
            accept="image/*"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) loadFile(f);
            }}
          />
        </label>
      </div>
    );
  }

  return (
    <div className="gp-photo">
      <div className="gp-photo__wrap">
        <img
          ref={imgRef}
          src={photoUrl}
          alt="uploaded"
          className="gp-photo__img"
          onClick={onClickImage}
          style={{ cursor: activeAnchorId != null ? 'crosshair' : 'default' }}
        />
        {/* anchor pixel markers, positioned in natural-pixel space via % */}
        {anchors.map((a) =>
          a.photoPixel ? (
            <span
              key={a.id}
              className="gp-dot"
              style={{
                left: `${(a.photoPixel.x / image.width) * 100}%`,
                top: `${(a.photoPixel.y / image.height) * 100}%`,
                background: a.color,
                outline: a.id === activeAnchorId ? '2px solid #fff' : 'none',
              }}
            />
          ) : null,
        )}
      </div>
      <button className="gp-btn gp-btn--ghost" onClick={() => clearPhoto()}>
        Remove photo
      </button>
    </div>
  );
}
