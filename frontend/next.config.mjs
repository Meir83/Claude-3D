/** @type {import('next').NextConfig} */
const nextConfig = {
  // Self-contained server bundle for the Docker image (.next/standalone)
  output: "standalone",
  async rewrites() {
    // Note: rewrites are resolved at build time, so BACKEND_URL must be set
    // when running `next build` (the Dockerfile takes it as a build arg).
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
  // Allow loading STL blobs and backend images
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "localhost" },
    ],
  },
};

export default nextConfig;
