# Frontend Development

The Encore frontend is a React Native application that uses Expo.

## Frontend Port

The frontend container runs on the port specified by `FRONTEND_PORT` in the root `.env` file.

The default Expo/Metro port is:

`8081`

## Expo Account Setup

Expo Go development uses an Expo tunnel so that a physical mobile device can connect to the frontend running inside Docker.

Each developer must create a Personal Access Token from their Expo account and add it to the root `.env` file:

`EXPO_TOKEN=<your personal Expo access token>`

Do not commit or share this token.

Docker Compose passes `EXPO_TOKEN` into the frontend container so Expo can authenticate and create the signed tunnel. Node, npm, and Expo CLI do not need to be installed on the host machine for Expo authentication.

## Starting the Application

From the project root, run:

`docker compose up -d --build`

Then view the Expo QR code and tunnel URL with:

`docker compose logs --tail=100 frontend`

Scan the QR code using Expo Go on the mobile device.

If Expo reports that it could not create a signed tunnel URL, verify that `docker compose exec frontend npx expo whoami` returns your Expo username.

## Backend API Configuration

The mobile frontend communicates with the remote backend using the `EXPO_PUBLIC_API_URL` environment variable.

Create a `.env` file inside the `frontend` directory and add:

`EXPO_PUBLIC_API_URL=<remote backend URL>`

During local development, this URL must be reachable from the physical device running Expo Go. `localhost` cannot be used because it would refer to the mobile device itself rather than the development computer.

Once the remote backend is deployed, `EXPO_PUBLIC_API_URL` can be updated to use the shared hosted backend URL.

### Local Backend Connection for Physical Devices

When testing the application on a physical mobile device, the device must be able to reach the remote backend running on the development computer.

First, find the Windows IPv4 address by running the following command in Windows Command Prompt:  
`ipconfig`

Look for the `IPv4 Address` of the network adapter currently being used.

Next, find the WSL IPv4 address by running the following command in the VS Code Ubuntu/WSL terminal:

`hostname -I`

The Windows IPv4 address is used by the mobile application to contact the development computer. The WSL IPv4 address is used to forward that connection to the backend running through Docker.

## For Linux:

Or if you're on Linux run this command to show all ipv4 address on you computer:  
`ip -4 -br addr show`  
The one you're looking for should start with 192.--- or 10.---

If you have your firewall on, make sure to allow traffic in on the posrt your backend is running on

### Configure the Frontend API URL

Create a `.env` file inside the `frontend` directory if one does not already exist.

Set `EXPO_PUBLIC_API_URL` to the Windows IPv4 address and remote backend port:

`EXPO_PUBLIC_API_URL=http://<YOUR_IPV4>:5001`

For example:

`EXPO_PUBLIC_API_URL=http://192.168.1.100:5001`

Do not use `localhost` when testing on a physical mobile device. On the phone, `localhost` refers to the phone itself rather than the development computer.

If the Windows IPv4 address changes, update `frontend/.env` with the new address and restart the frontend container so Expo reloads the environment variable.

### Configure Windows Port Forwarding

The physical mobile device connects to the Windows IPv4 address, while the backend is running through Docker inside WSL. Windows must forward port `5001` to the WSL IPv4 address.

Open Windows Command Prompt or PowerShell as Administrator and run:

`netsh interface portproxy add v4tov4 listenaddress=<WINDOWS_IPV4> listenport=5001 connectaddress=<WSL_IPV4> connectport=5001`

Verify the forwarding rule with:

`netsh interface portproxy show all`

The output should show the Windows IPv4 address on port `5001` forwarding to the WSL IPv4 address on port `5001`.

If the Windows or WSL IPv4 address changes, remove the old forwarding rule and create a new one using the current addresses.

View the existing forwarding rule:

`netsh interface portproxy show all`

Remove the old rule using the Windows IPv4 address shown in the existing rule:

`netsh interface portproxy delete v4tov4 listenaddress=<OLD_WINDOWS_IPV4> listenport=5001`

Then create the new rule using the current Windows and WSL IPv4 addresses:

`netsh interface portproxy add v4tov4 listenaddress=<WINDOWS_IPV4> listenport=5001 connectaddress=<WSL_IPV4> connectport=5001`

### Configure Windows Firewall

Windows Firewall must allow the physical mobile device to connect to the remote backend on TCP port `5001`.

The firewall rule can be configured to allow inbound TCP traffic on port `5001`. For additional security during local development, the rule can be restricted to the development computer's current Windows IPv4 address and the mobile device's IPv4 address.

If an existing firewall rule is restricted to an old Windows or mobile device IPv4 address, update the rule when those addresses change.

To create a firewall rule that allows a specific mobile device to access the backend, first find the mobile device's IPv4 address from its Wi-Fi/network settings.

Then open Windows Command Prompt or PowerShell as Administrator and run:

`netsh advfirewall firewall add rule name="Encore Backend Mobile" dir=in action=allow protocol=TCP localport=5001 localip=<WINDOWS_IPV4> remoteip=<MOBILE_IPV4> profile=public`

Verify the rule with:

`netsh advfirewall firewall show rule name="Encore Backend Mobile" verbose`

If the Windows or mobile device IPv4 address changes, update the existing rule:

`netsh advfirewall firewall set rule name="Encore Backend Mobile" new localip=<WINDOWS_IPV4> remoteip=<MOBILE_IPV4>`

### Test the Backend Connection

Before testing Sign In or Create Account in Expo Go, open the following URL in the mobile device's browser:

`http://<YOUR_IPV4>:5001`

A successful response from the Encore remote backend confirms that the mobile device can reach the backend.

If the page does not load, verify:

- the `backend-remote` Docker container is running;
- `frontend/.env` contains the current Windows IPv4 address;
- the Windows port forwarding rule contains the current Windows and WSL IPv4 addresses; and
- Windows Firewall allows the mobile device to connect to TCP port `5001`.

Once the remote backend is deployed to a shared public URL, this Windows/WSL port forwarding setup will no longer be necessary. `EXPO_PUBLIC_API_URL` can instead point to the deployed backend.

