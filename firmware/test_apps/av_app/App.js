import { useEffect, useRef, useState } from 'react';
import { Button, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Buffer } from 'buffer';
import { Directory, File, Paths } from 'expo-file-system';
import TcpSocket from 'react-native-tcp-socket';
import { Recorder } from './recorder';
import JpegPreview from './modules/jpeg-preview';

// Board's WiFi network (av_wifi.ino). Join "XIAO-AV" in phone settings first.
const BOARD_HOST = '192.168.4.1';
const BOARD_PORT = 5000;

// Packets: 4-byte type + 8-byte timestamp (us) + 4-byte length + data, little-endian
const HEADER_SIZE = 16;
const TYPES = ['AUDI', 'FRAM', 'STRT', 'STOP', 'HELO'];
const MAX_PAYLOAD_BYTES = 1000000; // anything bigger is a corrupted length

// Calls onPacket for every complete packet in buf; returns the leftover bytes.
// Uses slice, not subarray: on Hermes subarray returns a plain Uint8Array, which
// has no Buffer methods (toString('base64') then gives "255,216,..." instead).
function parsePackets(buf, onPacket) {
  let pos = 0;
  while (buf.length - pos >= HEADER_SIZE) {
    const type = buf.toString('latin1', pos, pos + 4);
    const length = buf.readUInt32LE(pos + 12);
    if (!TYPES.includes(type) || length > MAX_PAYLOAD_BYTES) {
      pos++; // not a packet start - resync one byte later
      continue;
    }
    if (buf.length - pos < HEADER_SIZE + length) break; // wait for the rest
    const timestamp = buf.readUInt32LE(pos + 4) + buf.readUInt32LE(pos + 8) * 2 ** 32;
    onPacket(type, timestamp, buf.slice(pos + HEADER_SIZE, pos + HEADER_SIZE + length));
    pos += HEADER_SIZE + length;
  }
  return buf.slice(pos);
}

// Folder recordings are saved to, picked once through Android's folder picker
const settingsFile = new File(Paths.document, 'settings.json');

function loadSaveDir() {
  try {
    if (settingsFile.exists) {
      const { saveDirUri } = JSON.parse(settingsFile.textSync());
      if (saveDirUri) return new Directory(saveDirUri);
    }
  } catch {}
  return null;
}

// "content://.../tree/primary%3AMovies" -> "Movies"
function folderName(dir) {
  return decodeURIComponent(dir.uri).split('/tree/').pop().split(':').pop() || 'Internal storage';
}

// av_2026-10-24_14-05-09.mkv
function recordingName() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `av_${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}_${p(d.getHours())}-${p(d.getMinutes())}-${p(d.getSeconds())}.mkv`;
}

export default function App() {
  const [status, setStatus] = useState('Disconnected');
  const [connected, setConnected] = useState(false);
  const [recording, setRecording] = useState(false);
  const [stats, setStats] = useState('');
  const [saveInfo, setSaveInfo] = useState('');

  const socket = useRef(null);
  const pending = useRef(Buffer.alloc(0));
  const counts = useRef({ frames: 0, audio: 0, bytes: 0 });
  const saveDir = useRef(loadSaveDir());
  const [saveDirName, setSaveDirName] = useState(saveDir.current ? folderName(saveDir.current) : null);
  const recorder = useRef(null);
  const preview = useRef(null);

  // Stream stats once per second
  useEffect(() => {
    const timer = setInterval(() => {
      const c = counts.current;
      if (c.frames || c.audio) {
        setStats(`${c.frames} fps · ${c.audio} audio packets/s · ${(c.bytes / 1024).toFixed(0)} KB/s`);
      }
      counts.current = { frames: 0, audio: 0, bytes: 0 };
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  async function chooseSaveDir() {
    try {
      const dir = await Directory.pickDirectoryAsync();
      await settingsFile.write(JSON.stringify({ saveDirUri: dir.uri }));
      saveDir.current = dir;
      setSaveDirName(folderName(dir));
      return true;
    } catch {
      return false; // picker cancelled
    }
  }

  function startRecorder() {
    finishRecorder();
    recorder.current = new Recorder(saveDir.current, recordingName());
    setSaveInfo(`Recording to ${folderName(saveDir.current)}/${recorder.current.name}`);
  }

  function finishRecorder() {
    const r = recorder.current;
    if (!r) return;
    recorder.current = null;
    try {
      setSaveInfo(r.close()
        ? `Saved ${r.frames} frames + audio to ${folderName(r.directory)}/${r.name}`
        : 'No frames were received, so nothing was saved.');
    } catch (e) {
      setSaveInfo('Saving failed: ' + e.message);
    }
  }

  function handlePacket(type, timestamp, payload) {
    if (type === 'HELO') {
      setConnected(true);
      setStatus('Connected');
    } else if (type === 'STRT') {
      setRecording(true);
      setStatus('Recording');
      startRecorder();
    } else if (type === 'STOP') {
      setRecording(false);
      setStatus('Connected');
      finishRecorder();
    } else if (type === 'FRAM') {
      counts.current.frames++;
      // Plain Uint8Array view (no copy); the native view decodes and shows it
      preview.current?.showFrame(new Uint8Array(payload.buffer, payload.byteOffset, payload.length));
    } else if (type === 'AUDI') {
      counts.current.audio++; // 16-bit mono PCM at 16 kHz, not played yet
    }

    if ((type === 'FRAM' || type === 'AUDI') && recorder.current) {
      try {
        if (type === 'FRAM') recorder.current.addVideo(timestamp, payload);
        else recorder.current.addAudio(timestamp, payload);
      } catch (e) {
        recorder.current = null;
        setSaveInfo('Recording failed: ' + e.message);
      }
    }
  }

  async function connect() {
    if (!saveDir.current) {
      setStatus('Choose a folder for recordings');
      if (!(await chooseSaveDir())) {
        setStatus('Disconnected - a folder for recordings is needed');
        return;
      }
    }
    setStatus('Connecting...');
    pending.current = Buffer.alloc(0);
    // 'wifi' stops Android sending this over cellular, since the board's network has no internet
    const s = TcpSocket.createConnection(
      { host: BOARD_HOST, port: BOARD_PORT, interface: 'wifi', connectTimeout: 5000 },
      () => {
        s.setNoDelay(true);
        s.write('S');
      }
    );
    s.on('data', (data) => {
      counts.current.bytes += data.length;
      pending.current = parsePackets(Buffer.concat([pending.current, data]), handlePacket);
    });
    // A failed connect only sends 'error' (no 'close'), so both reset the connection.
    // The check stops a late event from an old socket clearing a newer one.
    const reset = () => {
      if (socket.current !== s) return;
      socket.current = null;
      setConnected(false);
      setRecording(false);
      finishRecorder(); // keep what was recorded if the connection drops
    };
    s.on('error', (err) => {
      reset();
      setStatus('Error: ' + err.message);
    });
    s.on('close', () => {
      reset();
      setStatus((prev) => (prev.startsWith('Error') ? prev : 'Disconnected'));
    });
    socket.current = s;
  }

  function disconnect() {
    if (!socket.current) return;
    socket.current.write('X');
    socket.current.end();
  }

  function send(command) {
    if (socket.current) socket.current.write(command);
  }

  return (
    <View style={styles.container}>
      <Text style={styles.status}>{status}</Text>
      <JpegPreview ref={preview} style={styles.video} />
      <Text style={styles.stats}>{stats}</Text>
      {saveInfo ? <Text style={styles.stats}>{saveInfo}</Text> : null}
      <View style={styles.buttons}>
        <Text style={styles.stats}>Save folder: {saveDirName ?? 'not chosen'}</Text>
        <Button title="Change" onPress={chooseSaveDir} disabled={recording} />
      </View>
      <View style={styles.buttons}>
        {connected ? (
          <Button title="Disconnect" onPress={disconnect} />
        ) : (
          <Button title="Connect" onPress={connect} disabled={socket.current !== null} />
        )}
        <Button
          title={recording ? 'Stop' : 'Start'}
          onPress={() => send(recording ? 'E' : 'R')}
          disabled={!connected}
        />
      </View>
      <StatusBar style="auto" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    gap: 12,
  },
  status: { fontSize: 18, fontWeight: 'bold' },
  video: { width: '100%', aspectRatio: 4 / 3, backgroundColor: '#000' },
  stats: { color: '#555' },
  buttons: { flexDirection: 'row', gap: 16 },
});
