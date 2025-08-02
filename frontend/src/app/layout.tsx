import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { AuthProvider } from '@/contexts/AuthContext';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: process.env.NEXT_PUBLIC_APP_NAME || 'Sprint Reports v2',
  description: 'Modern sprint management platform for agile teams',
  keywords: ['sprint', 'agile', 'project management', 'JIRA', 'planning'],
  authors: [{ name: 'Sprint Reports Team' }],
  robots: {
    index: false,
    follow: false,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body className={`${inter.className} h-full bg-gray-50 antialiased`}>
        <AuthProvider>
          <div id="root" className="h-full">
            {children}
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}