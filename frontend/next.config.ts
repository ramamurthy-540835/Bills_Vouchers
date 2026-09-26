import type { NextConfig } from 'next'
const nextConfig: NextConfig = { output: 'standalone', allowedDevOrigins: ['10.100.15.25', 'localhost'], async redirects(){return [{source:'/documents',destination:'/bills',statusCode:301}]} }
export default nextConfig
