import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

import { Sidebar } from "@/components/layout/sidebar";
import { ToastProvider } from "@/components/ui/toast";
import { QueryProvider } from "@/components/providers/query-provider";
import Script from "next/script";

const inter = Inter({ 
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "DrawDoc - Document Verification Agent",
  description: "AI-powered document verification and order processing system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased`}>
        {/* Suppress Next.js 16 params/searchParams dev warnings */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                const originalError = console.error;
                console.error = function(...args) {
                  const msg = args[0]?.toString() || '';
                  // Suppress specific Next.js 16 warnings about params/searchParams
                  if (
                    msg.includes('params are being enumerated') ||
                    msg.includes('The keys of') && msg.includes('searchParams') ||
                    msg.includes('React.use()') ||
                    msg.includes('sync-dynamic-apis')
                  ) {
                    return;
                  }
                  originalError.apply(console, args);
                };
              })();
            `
          }}
        />
        <QueryProvider>
          <ToastProvider>
            <div className="flex min-h-screen bg-background">
              <Sidebar />
              <main className="flex-1 overflow-auto">
                {children}
              </main>
            </div>
          </ToastProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
