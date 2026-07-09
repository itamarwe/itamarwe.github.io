// Brute-force check of the interaction counts shown in the interactive.
function counts(F, T, R) {
  const N = T + R;
  // global layer: every token (all frames) attends to every token
  let global = 0;
  for (let q = 0; q < F * N; q++) for (let k = 0; k < F * N; k++) global++;
  // register layer: only registers (F*R of them) attend among themselves
  let reg = 0;
  for (let q = 0; q < F * R; q++) for (let k = 0; k < F * R; k++) reg++;
  // frame layer: within each frame, all N tokens attend to each other
  let frame = 0;
  for (let f = 0; f < F; f++) for (let q = 0; q < N; q++) for (let k = 0; k < N; k++) frame++;
  return { global, reg, frame };
}
for (const [F, T, R] of [[2, 48, 2], [4, 48, 8], [8, 48, 16], [3, 5, 4]]) {
  const b = counts(F, T, R);
  const f = { global: (F * (T + R)) ** 2, reg: (F * R) ** 2, frame: F * (T + R) ** 2 };
  const ok = b.global === f.global && b.reg === f.reg && b.frame === f.frame;
  console.log(`F=${F} T=${T} R=${R}:`, JSON.stringify(f), ok ? "OK" : `MISMATCH ${JSON.stringify(b)}`);
}
