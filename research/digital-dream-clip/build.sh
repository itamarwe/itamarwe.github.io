#!/bin/bash
set -e
cd "$(dirname "$0")"
PY=./venv/bin/python
NF=$($PY -c "import numpy as np; print(int(np.load('features.npz')['nframes']))")
NW=4
CHUNK=$(( (NF + NW - 1) / NW ))
echo "frames=$NF workers=$NW chunk=$CHUNK"
rm -f seg_*.mp4 list.txt
pids=()
for k in $(seq 0 $((NW-1))); do
  s=$(( k*CHUNK )); e=$(( (k+1)*CHUNK )); [ $e -gt $NF ] && e=$NF
  [ $s -ge $NF ] && continue
  $PY worker.py $s $e seg_$k.mp4 &
  pids+=($!)
done
for p in "${pids[@]}"; do wait $p; done
echo "=== concat segments + mux audio ==="
for k in $(seq 0 $((NW-1))); do [ -f seg_$k.mp4 ] && echo "file 'seg_$k.mp4'" >> list.txt; done
cat list.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i list.txt -i song.mp3 \
  -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest \
  -movflags +faststart digital_dream.mp4
echo "=== done ==="
ffprobe -v error -show_entries format=duration,size -show_entries stream=codec_type,codec_name,width,height,r_frame_rate -of default=noprint_wrappers=1 digital_dream.mp4
ls -la digital_dream.mp4
