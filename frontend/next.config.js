const os = require('os');

/** @type {import('next').NextConfig} */
const getLocalIP = () => {
  const interfaces = os.networkInterfaces();
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      // Look for an IPv4 address that is not a local loopback
      if (iface.family === 'IPv4' && !iface.internal) {
        return iface.address;
      }
    }
  }
  return 'localhost';
};

const nextConfig = {
  allowedDevOrigins: [
    'localhost',
    '127.0.0.1',
    '40de-102-91-102-212.ngrok-free.app',  // no wildcard, no https://
    '*.ngrok-free.app',                      // wildcard for any ngrok URL
    '*.ngrok.io',
  ],
  turbopack: {
    root: __dirname,
  },
}

module.exports = nextConfig
