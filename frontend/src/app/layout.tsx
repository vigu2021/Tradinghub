import type { Metadata } from "next";

import "./globals.css";
import { display, mono } from "./fonts";
import { GlobalProviders } from "./providers";

export const metadata: Metadata = {
  title: "Tradinghub",
  description: "A trading journal for reviewing your own decisions.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${display.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <GlobalProviders>{children}</GlobalProviders>
      </body>
    </html>
  );
}
