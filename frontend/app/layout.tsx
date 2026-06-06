import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Atris",
  description: "Atris is an AI prediction analyst for Formula 1 race intelligence.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}
