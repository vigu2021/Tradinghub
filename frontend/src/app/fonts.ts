import { Archivo, IBM_Plex_Mono } from "next/font/google";

export const sans = Archivo({
  variable: "--font-sans",
  subsets: ["latin"],
});

export const mono = IBM_Plex_Mono({
  variable: "--font-mono",
  weight: ["400", "500"],
  subsets: ["latin"],
});
