import type { NextConfig } from 'next';

const config: NextConfig = {
  reactStrictMode: true,
  output: 'export',
  experimental: { cpus: 2 },
};
export default config;
