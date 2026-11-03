import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Button, FlatList, Keyboard, Modal, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { openSetupSession } from './boardSetup';

// Pop-up that lists the WiFi networks the board can see (scanned by the board over
// Bluetooth) and has it join the one the user picks.
// onResult gets the board's final status: { state: 'connected' | 'ap', host, detail }.

const BARS = '▂▄▆█';

function signalBars(rssi) {
  const bars = rssi >= -55 ? 4 : rssi >= -67 ? 3 : rssi >= -78 ? 2 : 1;
  return (
    <Text style={styles.bars}>
      {BARS.slice(0, bars)}
      <Text style={styles.barsOff}>{BARS.slice(bars)}</Text>
    </Text>
  );
}

// Password field that masks with '*'. Android's own masking (secureTextEntry) draws '•',
// which some phone fonts don't have, so the password showed as blank spaces.
// While hidden, the cursor stays at the end: typing/pasting adds to the end and backspace
// removes from the end, so every edit maps exactly onto the real password. To fix a
// character in the middle, show the password (then it's a normal text field).
function PasswordInput({ value, onChangeText, visible, style, ...props }) {
  function onChange(text) {
    if (visible) onChangeText(text);
    else if (text.length > value.length) onChangeText(value + text.slice(value.length));
    else onChangeText(value.slice(0, text.length));
  }

  return (
    <TextInput
      {...props}
      style={style}
      value={visible ? value : '*'.repeat(value.length)}
      onChangeText={onChange}
      selection={visible ? undefined : { start: value.length, end: value.length }}
      keyboardType="visible-password" // no suggestions, and the keyboard doesn't learn the password
      autoCapitalize="none"
      autoCorrect={false}
      autoComplete="off"
      importantForAutofill="no"
    />
  );
}

export default function WifiSetupModal({ visible, onClose, onResult }) {
  // finding -> scanning -> list -> password -> joining; error from any of them
  const [phase, setPhase] = useState('finding');
  const [message, setMessage] = useState('');
  const [networks, setNetworks] = useState([]);
  const [selected, setSelected] = useState(null); // { ssid, secured, other }
  const [ssid, setSsid] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [keyboardHeight, setKeyboardHeight] = useState(0);
  const session = useRef(null);

  // Pop-ups don't move out of the keyboard's way on Android, so lift the card above it
  useEffect(() => {
    const shown = Keyboard.addListener('keyboardDidShow', (e) => setKeyboardHeight(e.endCoordinates.height));
    const hidden = Keyboard.addListener('keyboardDidHide', () => setKeyboardHeight(0));
    return () => {
      shown.remove();
      hidden.remove();
    };
  }, []);

  async function scan() {
    setPhase('scanning');
    try {
      setNetworks(await session.current.scan());
      setPhase('list');
    } catch (e) {
      setMessage(e.message);
      setPhase('error');
    }
  }

  async function start() {
    setPhase('finding');
    setMessage('');
    try {
      session.current = await openSetupSession();
      await scan();
    } catch (e) {
      setMessage(e.message);
      setPhase('error');
    }
  }

  function close() {
    session.current?.close();
    session.current = null;
    onClose();
  }

  // Connect to the board when the pop-up opens, disconnect when it closes
  useEffect(() => {
    if (!visible) return;
    start();
    return () => {
      session.current?.close();
      session.current = null;
    };
  }, [visible]);

  function choose(network) {
    setSelected(network);
    setSsid(network.ssid);
    setPassword('');
    setShowPassword(false);
    if (network.secured || network.other) setPhase('password');
    else join(network.ssid, '');
  }

  async function join(name, pass) {
    setPhase('joining');
    setMessage(name ? `Asking the board to join "${name}"...` : "Switching the board to its own network...");
    try {
      const result = await session.current.join(name, pass, () => {});
      if (result.state === 'connected' || !name) {
        onResult(result);
        close();
      } else {
        setMessage(`The board couldn't join "${name}": ${result.detail.replace(/^could not join [^:]*: /, '')}`);
        setPhase('password');
      }
    } catch (e) {
      setMessage(e.message);
      setPhase('error');
    }
  }

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={close}>
      <View style={[styles.backdrop, { paddingBottom: keyboardHeight }]}>
        <View style={styles.card}>
          <Text style={styles.title}>Choose a WiFi network for the board</Text>

          {(phase === 'finding' || phase === 'scanning' || phase === 'joining') && (
            <View style={styles.busy}>
              <ActivityIndicator size="large" />
              <Text style={styles.note}>
                {phase === 'finding' && 'Looking for the board over Bluetooth...'}
                {phase === 'scanning' && 'The board is scanning for networks (about 10 seconds)...'}
                {phase === 'joining' && message}
              </Text>
            </View>
          )}

          {phase === 'list' && (
            <>
              <Text style={styles.note}>Networks the board can see (2.4 GHz):</Text>
              <FlatList
                style={styles.list}
                data={networks}
                keyExtractor={(n) => n.ssid}
                ListEmptyComponent={<Text style={styles.note}>No networks found - try Refresh.</Text>}
                renderItem={({ item }) => (
                  <Pressable style={({ pressed }) => [styles.row, pressed && styles.rowPressed]} onPress={() => choose(item)}>
                    <Text style={styles.ssid} numberOfLines={1}>{item.ssid}</Text>
                    <Text style={styles.lock}>{item.secured ? '🔒' : ''}</Text>
                    {signalBars(item.rssi)}
                  </Pressable>
                )}
                ListFooterComponent={
                  <Pressable style={({ pressed }) => [styles.row, pressed && styles.rowPressed]}
                    onPress={() => choose({ ssid: '', secured: true, other: true })}>
                    <Text style={styles.other}>Other network...</Text>
                  </Pressable>
                }
              />
              <View style={styles.buttons}>
                <Button title="Refresh" onPress={scan} />
                <Button title="Use board's own network" onPress={() => join('', '')} />
              </View>
            </>
          )}

          {phase === 'password' && selected && (
            <>
              {selected.other ? (
                <TextInput style={styles.input} placeholder="Network name" value={ssid}
                  onChangeText={setSsid} autoCapitalize="none" autoCorrect={false} />
              ) : (
                <Text style={styles.selected}>{selected.ssid}</Text>
              )}
              <PasswordInput style={styles.input} placeholder="Password" value={password}
                onChangeText={setPassword} visible={showPassword} autoFocus={!selected.other} />
              <Pressable onPress={() => setShowPassword(!showPassword)}>
                <Text style={styles.link}>{showPassword ? 'Hide password' : 'Show password'}</Text>
              </Pressable>
              {message ? <Text style={styles.error}>{message}</Text> : null}
              <View style={styles.buttons}>
                <Button title="Back" onPress={() => { setMessage(''); setPhase('list'); }} />
                <Button title="Join" onPress={() => join(ssid, password)} disabled={!ssid} />
              </View>
            </>
          )}

          {phase === 'error' && (
            <>
              <Text style={styles.error}>{message}</Text>
              <View style={styles.buttons}>
                <Button title="Try again" onPress={() => { session.current?.close(); start(); }} />
              </View>
            </>
          )}

          <View style={styles.cancel}>
            <Button title="Close" onPress={close} disabled={phase === 'joining'} />
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'flex-end' },
  card: { backgroundColor: '#fff', borderTopLeftRadius: 12, borderTopRightRadius: 12, padding: 16, gap: 10, maxHeight: '85%' },
  title: { fontSize: 18, fontWeight: 'bold' },
  busy: { alignItems: 'center', gap: 12, paddingVertical: 24 },
  note: { color: '#555' },
  list: { flexGrow: 0 },
  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#eee', gap: 8 },
  rowPressed: { backgroundColor: '#f0f4ff' },
  ssid: { flex: 1, fontSize: 16 },
  lock: { width: 22, textAlign: 'center' },
  bars: { fontSize: 14, color: '#222', letterSpacing: 1 },
  barsOff: { color: '#ccc' },
  other: { flex: 1, fontSize: 16, color: '#2a6edb' },
  selected: { fontSize: 16, fontWeight: 'bold' },
  input: { borderWidth: 1, borderColor: '#ccc', borderRadius: 4, paddingHorizontal: 8, paddingVertical: 8 },
  link: { color: '#2a6edb' },
  error: { color: '#c0392b' },
  buttons: { flexDirection: 'row', justifyContent: 'space-between', gap: 8 },
  cancel: { marginTop: 4 },
});
