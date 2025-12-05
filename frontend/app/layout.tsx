"use client";

import type { ReactNode } from "react";
import "./globals.css";
import { Inter } from "next/font/google";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"] });

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.className} min-h-screen bg-background text-foreground`}
      >
        <div className="min-h-screen flex flex-col">
          <header className="border-b border-border bg-slate-950/70 backdrop-blur">
            <div className="max-w-6xl mx-auto flex items-center justify-between px-4 py-3">
              <Link
                href="/"
                className="flex items-center gap-2 text-primary-foreground"
              >
                <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center text-xs font-semibold tracking-tight text-slate-950 shadow-lg shadow-primary/40">
                  Court
                </div>
                <div className="flex flex-col leading-tight">
                  <span className="text-sm font-semibold">
                    Hearing Transcriber
                  </span>
                  <span className="text-xs text-muted-foreground">
                    NyayaSetu
                  </span>
                </div>
              </Link>
              <nav className="flex items-center gap-3 text-sm">
                <Link
                  href="/"
                  className="px-3 py-1.5 rounded-md hover:bg-slate-900/70 transition-colors"
                >
                  Upload
                </Link>
                <Link
                  href="/transcripts"
                  className="px-3 py-1.5 rounded-md hover:bg-slate-900/70 transition-colors"
                >
                  Transcripts
                </Link>
              </nav>
            </div>
          </header>
          <main className="flex-1">
            <div className="max-w-6xl mx-auto px-4 py-6">{children}</div>
          </main>
          <footer className="border-t border-border py-3 text-xs text-center text-muted-foreground bg-slate-950/70">
            Court hearing transcription dashboard &middot; Palette{" "}
            <span className="inline-flex items-center gap-1">
              <span className="h-3 w-3 rounded-full bg-[#C1785A]" />
              <span className="h-3 w-3 rounded-full bg-[#305669]" />
              <span className="h-3 w-3 rounded-full bg-[#8ABEB9]" />
            </span>
          </footer>
        </div>
      </body>
    </html>
  );
}


