import { IBM_Plex_Mono, Instrument_Serif } from "next/font/google";

export const display = Instrument_Serif({
  variable: "--font-display",
  weight: "400",
  subsets: ["latin"],
});

export const mono = IBM_Plex_Mono({
  variable: "--font-mono",
  weight: "400",
  subsets: ["latin"],
});
