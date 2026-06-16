import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "Streamline",
  description: "A small streaming platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex bg-bg text-text">
        <AuthProvider>
          <Sidebar />
          <main className="flex-1 min-h-screen md:ml-60">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
