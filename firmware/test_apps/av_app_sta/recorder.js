import { Buffer } from 'buffer';
import { FileMode } from 'expo-file-system';

// Same file as av_receiver.py: the board's JPEG frames (copied as-is) + 16-bit PCM audio
// in one MKV, timed by the board's clock. Plays in VLC.
// Written front to back only, because folders picked through Android's picker can't seek.

const SAMPLE_RATE = 16000;
const CLUSTER_MS = 1000; // blocks are buffered and written about once a second
const VIDEO_TRACK = 1;
const AUDIO_TRACK = 2;

// --- Minimal Matroska (EBML) encoding ---

function idBytes(id) {
  const out = [];
  for (; id > 0; id = Math.floor(id / 256)) out.unshift(id % 256);
  return Buffer.from(out);
}

function sizeBytes(n) {
  let len = 1;
  while (n >= 2 ** (7 * len) - 1) len++;
  const out = Buffer.alloc(len);
  for (let i = len - 1, v = n; i >= 0; i--, v = Math.floor(v / 256)) out[i] = v % 256;
  out[0] |= 0x80 >> (len - 1);
  return out;
}

function el(id, ...children) {
  const payload = Buffer.concat(children);
  return Buffer.concat([idBytes(id), sizeBytes(payload.length), payload]);
}

function uint(id, n) {
  const out = [];
  do {
    out.unshift(n % 256);
    n = Math.floor(n / 256);
  } while (n > 0);
  return el(id, Buffer.from(out));
}

const str = (id, s) => el(id, Buffer.from(s, 'latin1'));

function float(id, x) {
  const b = Buffer.alloc(8);
  b.writeDoubleBE(x);
  return el(id, b);
}

function simpleBlock(track, relativeMs, data) {
  const header = Buffer.alloc(4);
  header[0] = 0x80 | track;
  header.writeInt16BE(relativeMs, 1);
  header[3] = 0x80; // keyframe (every JPEG / PCM block stands alone)
  return el(0xa3, header, data);
}

function fileHeader(width, height) {
  const ebml = el(0x1a45dfa3,
    uint(0x4286, 1), uint(0x42f7, 1), uint(0x42f2, 4), uint(0x42f3, 8),
    str(0x4282, 'matroska'), uint(0x4287, 4), uint(0x4285, 2));
  // Segment of unknown size, so it never needs patching afterwards
  const segment = Buffer.concat([idBytes(0x18538067), Buffer.from([0x01, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff])]);
  const info = el(0x1549a966, uint(0x2ad7b1, 1000000), str(0x4d80, 'av_app'), str(0x5741, 'av_app'));
  const tracks = el(0x1654ae6b,
    el(0xae, uint(0xd7, VIDEO_TRACK), uint(0x73c5, VIDEO_TRACK), uint(0x83, 1), uint(0x9c, 0),
      str(0x86, 'V_MJPEG'), el(0xe0, uint(0xb0, width), uint(0xba, height))),
    el(0xae, uint(0xd7, AUDIO_TRACK), uint(0x73c5, AUDIO_TRACK), uint(0x83, 2), uint(0x9c, 0),
      str(0x86, 'A_PCM/INT/LIT'), el(0xe1, float(0xb5, SAMPLE_RATE), uint(0x9f, 1), uint(0x6264, 16))));
  return Buffer.concat([ebml, segment, info, tracks]);
}

// Width/height from the JPEG's start-of-frame marker; null if it isn't a usable JPEG
function jpegSize(jpg) {
  if (jpg.length < 4 || jpg[0] !== 0xff || jpg[1] !== 0xd8) return null;
  let pos = 2;
  while (pos + 9 < jpg.length) {
    if (jpg[pos] !== 0xff) return null;
    const marker = jpg[pos + 1];
    const isSof = marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker);
    if (isSof) return { height: jpg.readUInt16BE(pos + 5), width: jpg.readUInt16BE(pos + 7) };
    pos += 2 + jpg.readUInt16BE(pos + 2);
  }
  return null;
}

// Writes one recording. The file is only created once the first frame arrives.
export class Recorder {
  constructor(directory, name) {
    this.directory = directory;
    this.name = name;
    this.handle = null;
    this.t0 = null;          // board time (us) that becomes 0 in the file
    this.pendingAudio = [];  // audio that arrives before the first frame
    this.lastVideoMs = -1;
    this.frames = 0;
    this.cluster = [];
    this.clusterMs = 0;
  }

  addVideo(timestamp, jpg) {
    const size = jpegSize(jpg);
    if (!size) return; // skip corrupted frames
    if (this.t0 === null) this.t0 = timestamp;
    if (!this.handle) {
      this.file = this.directory.createFile(this.name, 'video/x-matroska');
      this.handle = this.file.open(FileMode.WriteOnly);
      this.write(fileHeader(size.width, size.height));
      const pending = this.pendingAudio;
      this.pendingAudio = [];
      for (const [ts, pcm] of pending) this.addAudio(ts, pcm);
    }
    const ms = Math.floor((timestamp - this.t0) / 1000);
    if (ms <= this.lastVideoMs) return;
    this.addBlock(VIDEO_TRACK, ms, jpg);
    this.lastVideoMs = ms;
    this.frames++;
  }

  addAudio(timestamp, pcm) {
    if (this.t0 === null) this.t0 = timestamp;
    if (!this.handle) {
      this.pendingAudio.push([timestamp, pcm]);
      return;
    }
    // Timestamps come from the board's sample count, so dropped audio leaves a gap and sync is kept
    const ms = Math.round((timestamp - this.t0) / 1000);
    if (ms >= 0) this.addBlock(AUDIO_TRACK, ms, pcm);
  }

  addBlock(track, ms, data) {
    if (this.cluster.length && (ms - this.clusterMs >= CLUSTER_MS || ms - this.clusterMs < -30000)) {
      this.flushCluster();
    }
    if (!this.cluster.length) this.clusterMs = ms;
    this.cluster.push(simpleBlock(track, ms - this.clusterMs, data));
  }

  flushCluster() {
    if (!this.cluster.length) return;
    this.write(el(0x1f43b675, uint(0xe7, this.clusterMs), ...this.cluster));
    this.cluster = [];
  }

  write(buf) {
    this.handle.writeBytesSync(new Uint8Array(buf.buffer, buf.byteOffset, buf.length));
  }

  // Returns false if no frames arrived, so nothing was saved
  close() {
    if (!this.handle) return false;
    this.flushCluster();
    this.handle.close();
    return true;
  }
}
