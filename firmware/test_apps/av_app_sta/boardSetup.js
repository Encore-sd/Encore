import { PermissionsAndroid, Platform } from 'react-native';
import { BleManager } from 'react-native-ble-plx';
import { Buffer } from 'buffer';

// Bluetooth WiFi setup for av_wifi_sta.ino: list the WiFi networks the board can see,
// send it the one to join, and read back where it is on the network.

const SETUP_SERVICE_UUID = '7a1e0001-3c4f-4a4b-9d2e-5f6a7b8c9d00';
const CREDS_UUID = '7a1e0002-3c4f-4a4b-9d2e-5f6a7b8c9d00';
const STATUS_UUID = '7a1e0003-3c4f-4a4b-9d2e-5f6a7b8c9d00';
const SCAN_UUID = '7a1e0004-3c4f-4a4b-9d2e-5f6a7b8c9d00';
const FIND_TIMEOUT_MS = 8000;
const SCAN_TIMEOUT_MS = 20000; // the board's scan takes ~10 s while it runs its own network
const JOIN_TIMEOUT_MS = 25000; // the board tries for 15 s before falling back

const ble = new BleManager();

// "connected 192.168.1.50 HomeWifi" -> { state: 'connected', host: '192.168.1.50', detail: 'HomeWifi' }
// States: connected, connecting, ap (board is on its own network)
export function parseStatus(status) {
  const [state, host, ...rest] = status.split(' ');
  return { state, host: state === 'connecting' ? null : host, detail: rest.join(' '), text: status };
}

async function requestPermissions() {
  if (Platform.OS !== 'android' || Platform.Version < 31) return;
  const results = await PermissionsAndroid.requestMultiple([
    PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
    PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
  ]);
  if (Object.values(results).some((r) => r !== PermissionsAndroid.RESULTS.GRANTED)) {
    throw new Error('Bluetooth permission is needed to set up the board');
  }
}

function findBoard() {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      ble.stopDeviceScan();
      reject(new Error("Board not found over Bluetooth - it only offers setup while it isn't on a WiFi network (hold its B button for 3 s to make it forget its WiFi)"));
    }, FIND_TIMEOUT_MS);
    ble.startDeviceScan([SETUP_SERVICE_UUID], null, (error, device) => {
      if (error) {
        clearTimeout(timer);
        ble.stopDeviceScan();
        reject(new Error('Bluetooth scan failed: ' + error.message + ' (is Bluetooth on?)'));
      } else if (device) {
        clearTimeout(timer);
        ble.stopDeviceScan();
        resolve(device);
      }
    });
  });
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function read(device, uuid) {
  const characteristic = await device.readCharacteristicForService(SETUP_SERVICE_UUID, uuid);
  return Buffer.from(characteristic.value ?? '', 'base64').toString('utf8');
}

function write(device, uuid, text) {
  return device.writeCharacteristicWithResponseForService(
    SETUP_SERVICE_UUID, uuid, Buffer.from(text, 'utf8').toString('base64'));
}

async function readStatus(device) {
  return parseStatus(await read(device, STATUS_UUID));
}

// Asks the board to scan; returns [{ ssid, rssi, secured }], strongest first
async function scanNetworks(device) {
  await write(device, SCAN_UUID, 'scan');
  const started = Date.now();
  while (Date.now() - started < SCAN_TIMEOUT_MS) {
    await sleep(700);
    const list = await read(device, SCAN_UUID);
    if (list === 'scanning') continue;
    return list.split('\n').filter(Boolean).map((line) => {
      const [rssi, secured, ...name] = line.split('\t');
      return { ssid: name.join('\t'), rssi: Number(rssi), secured: secured === '1' };
    });
  }
  throw new Error('The board did not finish scanning in time');
}

// Sends WiFi details (empty ssid = forget, use the board's own network) and waits for
// the board to join or give up. onProgress gets status text along the way.
async function joinNetwork(device, ssid, password, onProgress) {
  await write(device, CREDS_UUID, `${ssid}\n${password}`);
  const started = Date.now();
  let sawConnecting = !ssid;
  while (Date.now() - started < JOIN_TIMEOUT_MS) {
    await sleep(1000);
    const status = await readStatus(device);
    onProgress?.(status.text);
    if (status.state === 'connecting') sawConnecting = true;
    // The status only reflects the new details once the board has started on them
    else if (sawConnecting || Date.now() - started > 3000) return status;
  }
  throw new Error('The board did not answer in time');
}

// Opens a Bluetooth connection to the board for setup; close() it when done
export async function openSetupSession() {
  await requestPermissions();
  const device = await (await findBoard()).connect({ requestMTU: 517 });
  await device.discoverAllServicesAndCharacteristics();
  return {
    status: () => readStatus(device),
    scan: () => scanNetworks(device),
    join: (ssid, password, onProgress) => joinNetwork(device, ssid, password, onProgress),
    close: () => device.cancelConnection().catch(() => {}),
  };
}

// Where the board is now, e.g. { state: 'connected', host: '192.168.1.50', ... }
export async function getBoardStatus() {
  const session = await openSetupSession();
  try {
    return await session.status();
  } finally {
    await session.close();
  }
}
