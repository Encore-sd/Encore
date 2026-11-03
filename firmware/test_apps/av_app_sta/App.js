import { useEffect, useRef, useState } from 'react';
import { Alert, Button, StyleSheet, Text, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Buffer } from 'buffer';
import { Directory, File, Paths } from 'expo-file-system';
import TcpSocket from 'react-native-tcp-socket';
import { Recorder } from './recorder';
import JpegPreview from './modules/jpeg-preview';
import { getBoardStatus } from './boardSetup';
import WifiSetupModal from './WifiSetupModal';

// av_wifi_sta.ino joins your WiFi (set up over Bluetooth, see boardSetup.js) and is
// found there as BOARD_HOSTNAME; if it can't, it makes its own "XIAO-AV" network at
// OWN_NETWORK_HOST like av_wifi.ino
const BOARD_HOSTNAME = 'xiao-av.local';
const OWN_NETWORK_HOST = '192.168.4.1';
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

// Saved settings: saveDirUri (folder recordings go to, picked once through Android's
// folder picker), boardHost (the board's address on your WiFi) and boardWifi (the WiFi
// the board is set up on; null while it's in setup mode on its own network)
const settingsFile = new File(Paths.document, 'settings.json');

function loadSettings() {
  try {
    if (settingsFile.exists) return JSON.parse(settingsFile.textSync());
  } catch {}
  return {};
}

async function saveSettings(changes) {
  await settingsFile.write(JSON.stringify({ ...loadSettings(), ...changes }));
}

function loadSaveDir() {
  const { saveDirUri } = loadSettings();
  return saveDirUri ? new Directory(saveDirUri) : null;
}

// Opens a TCP connection; resolves once connected, rejects if it can't connect
function openSocket(host, ownNetwork) {
  return new Promise((resolve, reject) => {
    const s = TcpSocket.createConnection(
      {
        host,
        port: BOARD_PORT,
        connectTimeout: 4000,
        // 'wifi' stops Android sending this over cellular, since the board's own network has no internet
        ...(ownNetwork && { interface: 'wifi' }),
      },
      () => resolve(s)
    );
    s.once('error', reject);
  });
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
  const [searching, setSearching] = useState(false);
  const [showSetup, setShowSetup] = useState(false);
  const [setupInfo, setSetupInfo] = useState('');

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
      await saveSettings({ saveDirUri: dir.uri });
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

  // Finds and connects to the board: its saved address on your WiFi, its name there,
  // where it says it is over Bluetooth (setup mode only), then its own network.
  // Returns the socket, or null.
  async function findBoard() {
    const { boardHost } = loadSettings();
    for (const host of [boardHost, BOARD_HOSTNAME]) {
      if (!host) continue;
      setStatus(`Connecting to ${host}...`);
      try {
        const s = await openSocket(host, false);
        // Remember the address it was found at (its IP can change between power-ups)
        // Board is on your WiFi, so it's set up (boardWifi is the network name, if known)
        await saveSettings({
          boardHost: s.remoteAddress || host,
          boardWifi: loadSettings().boardWifi || 'your WiFi',
        });
        return s;
      } catch {}
    }

    setStatus('Asking the board where it is (Bluetooth)...');
    let board = null;
    try {
      board = await getBoardStatus();
    } catch {} // Bluetooth is only on while the board isn't on a WiFi network
    if (board?.state === 'ap') await saveSettings({ boardWifi: null }); // e.g. reset with the B button

    if (board?.state === 'connected') {
      await saveSettings({ boardHost: board.host, boardWifi: board.detail });
      setStatus(`Connecting to ${board.host}...`);
      try {
        return await openSocket(board.host, false);
      } catch {}
    }

    setStatus(`Trying the board's own network (${OWN_NETWORK_HOST})...`);
    try {
      const s = await openSocket(OWN_NETWORK_HOST, true);
      await saveSettings({ boardWifi: null }); // on its own network = in setup mode
      return s;
    } catch {}

    setStatus(board?.state === 'ap'
      ? 'Board is on its own network "XIAO-AV" - join it, or set up WiFi'
      : 'Board not found - check it is on, or power-cycle it and try again');
    return null;
  }

  // Result of the WiFi setup pop-up: once the board is on the network, connect straight away
  async function onSetupResult(result) {
    if (result.state === 'connected') {
      await saveSettings({ boardHost: result.host, boardWifi: result.detail });
      setSetupInfo(`Board joined "${result.detail}" at ${result.host}.`);
      await connect();
    } else {
      await saveSettings({ boardHost: null, boardWifi: null });
      setSetupInfo('Board is on its own network "XIAO-AV".');
    }
  }

  // Once the board is on a WiFi network its Bluetooth setup is off, so say so straight
  // away instead of searching for it; "I've reset it" covers resetting with the B button
  function setUpWifiPressed() {
    setSetupInfo('');
    const { boardWifi } = loadSettings();
    if (!boardWifi) {
      setShowSetup(true);
      return;
    }
    Alert.alert(
      'Board is already on WiFi',
      `It's set up on "${boardWifi}". To give it a different network, reset it first: ` +
        'connect and press Forget WiFi, or hold its B button for 3 seconds (the LED flashes 4 times slowly).',
      [
        { text: 'Cancel', style: 'cancel' },
        { text: "I've reset it", onPress: () => setShowSetup(true) },
      ]
    );
  }

  async function connect() {
    if (!saveDir.current) {
      setStatus('Choose a folder for recordings');
      if (!(await chooseSaveDir())) {
        setStatus('Disconnected - a folder for recordings is needed');
        return;
      }
    }
    setSearching(true);
    const s = await findBoard();
    setSearching(false);
    if (!s) return;

    pending.current = Buffer.alloc(0);
    s.setNoDelay(true);
    s.write('S');
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

  // The board clears its saved WiFi and restarts on its own network, ready for setup
  async function forgetWifi() {
    send('F');
    await saveSettings({ boardHost: null, boardWifi: null });
    setSetupInfo('Board forgot its WiFi and is restarting on its own network "XIAO-AV" (about 10 s). Use Set up WiFi to give it a new one.');
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
          <Button title="Connect" onPress={connect} disabled={socket.current !== null || searching} />
        )}
        <Button
          title={recording ? 'Stop' : 'Start'}
          onPress={() => send(recording ? 'E' : 'R')}
          disabled={!connected}
        />
        {connected ? (
          <Button title="Forget WiFi" onPress={forgetWifi} disabled={recording} />
        ) : (
          <Button title="Set up WiFi" onPress={setUpWifiPressed} disabled={searching} />
        )}
      </View>
      {setupInfo ? <Text style={styles.stats}>{setupInfo}</Text> : null}
      <WifiSetupModal visible={showSetup} onClose={() => setShowSetup(false)} onResult={onSetupResult} />
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
