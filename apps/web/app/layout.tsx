import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {title:"ScratchLab // Financial Crime Control Center",description:"Synthetic AML control testing platform"};
export default function RootLayout({children}:{children:React.ReactNode}) {return <html lang="en"><body>{children}</body></html>}
