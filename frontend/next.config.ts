import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Disable experimental features that cause params/searchParams warnings
  experimental: {
    // Partial Prerendering causes params to be passed as Promises
    // We use client components with useParams() so we don't need PPR
    ppr: false,
  },
  
  // Suppress React DevTools console noise in development
  reactStrictMode: true,
  
  // Logging configuration
  logging: {
    fetches: {
      fullUrl: false,
    },
  },
};

export default nextConfig;

