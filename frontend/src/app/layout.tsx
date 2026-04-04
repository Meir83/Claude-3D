import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Claude 3D — AI-Powered CAD Generator",
  description: "Generate parametric 3D-printable models from natural language using Claude AI and CadQuery.",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full antialiased">{children}</body>
    </html>
  );
}
