import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { AuthProvider } from "@/lib/auth";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: { default: "EmotionSense", template: "%s · EmotionSense" },
  description: "Facial-expression recognition with a CNN trained on FER-2013: predicted expression, confidence, "
    + "top-3 alternatives and Grad-CAM model attention. Not a diagnostic tool.",
};

export const viewport: Viewport = { themeColor: "#f5f7fb" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={inter.variable}>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
