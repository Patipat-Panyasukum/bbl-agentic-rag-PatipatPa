import type { Metadata } from "next";
import "./globals.css";
import { IBM_Plex_Sans_Thai } from "next/font/google";
import React from "react";
import { NuqsAdapter } from "nuqs/adapters/next/app";
import { EmployeeSessionProvider } from "@/providers/EmployeeSession";

const bodyFont = IBM_Plex_Sans_Thai({
  subsets: ["latin", "thai"],
  weight: ["400", "500", "600"],
  preload: true,
  display: "swap",
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "BenefitWise AI — Employee Benefits Demo",
  description:
    "A grounded, employee-aware benefits assistant built with LangGraph.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={bodyFont.variable}>
        <NuqsAdapter>
          <EmployeeSessionProvider>{children}</EmployeeSessionProvider>
        </NuqsAdapter>
      </body>
    </html>
  );
}
