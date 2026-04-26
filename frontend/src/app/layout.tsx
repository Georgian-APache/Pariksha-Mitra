import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Toaster } from "sonner";
import "./globals.css";
import { Header } from "@/components/Header";
import { ThemeProvider } from "@/components/ThemeProvider";
import { VoiceMic } from "@/components/VoiceMic";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ParikshaMitra - An AI that studies you",
  description:
    "Agentic AI study companion for JEE, NEET and other Indian competitive exams. Built on LangGraph, Gemini and a 4+1 cognitive architecture.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      {/*
        suppressHydrationWarning on <body> swallows the hydration mismatch
        triggered by browser extensions (Grammarly, LastPass, ColorZilla, ...)
        that inject attributes such as data-new-gr-c-s-check-loaded into the
        DOM after SSR but before React hydrates. The ThemeProvider also
        mutates <html data-theme=...> on mount, hence the same prop above.
        See https://nextjs.org/docs/messages/react-hydration-error
      */}
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        <Header />
        <main className="flex-1 px-4 sm:px-6 lg:px-10 py-6 max-w-7xl w-full mx-auto">
          {children}
        </main>
        <VoiceMic />
        <Toaster theme="dark" richColors position="top-right" />
        <ThemeProvider />
      </body>
    </html>
  );
}
