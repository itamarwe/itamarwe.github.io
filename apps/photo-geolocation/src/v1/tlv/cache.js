/**
 * Persistent per-cell building cache (IndexedDB).
 *
 * Buildings are stored already converted to the local ground-metres frame, so
 * the cache is namespaced by the origin it was computed against — changing
 * DEFAULT_ORIGIN transparently starts a fresh database. Falls back to a no-op
 * (always-miss) if IndexedDB is unavailable, so callers always get a usable
 * result and simply re-fetch.
 *
 * Each cell value is the array of buildings whose centroid falls in that cell
 * (possibly empty — an empty array is a valid "fetched, nothing here" marker,
 * which is exactly what lets us avoid re-querying empty patches).
 */

const STORE = 'cells'
const dbPromises = new Map()

function dbName(origin) {
  return `tlv-buildings@${origin.lat.toFixed(4)},${origin.lon.toFixed(4)}`
}

function openDb(name) {
  if (typeof indexedDB === 'undefined') return Promise.resolve(null)
  if (!dbPromises.has(name)) {
    dbPromises.set(name, new Promise((resolve) => {
      let req
      try { req = indexedDB.open(name, 1) } catch { return resolve(null) }
      req.onupgradeneeded = () => {
        const db = req.result
        if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE)
      }
      req.onsuccess = () => resolve(req.result)
      req.onerror = () => resolve(null)
      req.onblocked = () => resolve(null)
    }))
  }
  return dbPromises.get(name)
}

/** Read multiple cells. Returns { [key]: buildings[] } for cells present. */
export async function getCells(origin, keys) {
  const out = {}
  if (keys.length === 0) return out
  const db = await openDb(dbName(origin))
  if (!db) return out
  return new Promise((resolve) => {
    let tx
    try { tx = db.transaction(STORE, 'readonly') } catch { return resolve(out) }
    const store = tx.objectStore(STORE)
    let pending = keys.length
    const done = () => { if (--pending === 0) resolve(out) }
    for (const key of keys) {
      const r = store.get(key)
      r.onsuccess = () => { if (r.result !== undefined) out[key] = r.result; done() }
      r.onerror = done
    }
  })
}

/** Write multiple cells. `entries` is { [key]: buildings[] }. Fire-and-forget. */
export async function putCells(origin, entries) {
  const keys = Object.keys(entries)
  if (keys.length === 0) return
  const db = await openDb(dbName(origin))
  if (!db) return
  return new Promise((resolve) => {
    let tx
    try { tx = db.transaction(STORE, 'readwrite') } catch { return resolve() }
    const store = tx.objectStore(STORE)
    for (const key of keys) store.put(entries[key], key)
    tx.oncomplete = () => resolve()
    tx.onerror = () => resolve()
    tx.onabort = () => resolve()
  })
}
