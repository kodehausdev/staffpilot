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
  allowedDevOrigins: [getLocalIP()],
};

module.exports = nextConfig;
