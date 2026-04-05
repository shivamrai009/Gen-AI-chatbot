import { Inter } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "../components/ThemeProvider";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata = {
  title: "GitLab AI — Knowledge Intelligence Layer",
  description:
    "Instantly surface answers from GitLab's Handbook and Direction pages. Grounded in sources. Verified by AI.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" data-theme="dark">
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
(function() {
  try {
    var stored = localStorage.getItem('theme');
    if (stored === 'light' || stored === 'dark') {
      document.documentElement.setAttribute('data-theme', stored);
    } else {
      var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    }
  } catch(e) {}
})();
`,
          }}
        />
      </head>
      <body className={inter.variable}>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
