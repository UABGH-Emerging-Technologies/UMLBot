//Adopted from code by Hamidul Islam (https://umlai.vercel.app)
//https://github.com/hamidlabs/AI-uml-diagram-generator
//MIT license

import type React from 'react'
import '@/app/globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
	title: 'UMLBot | Create UML Diagrams Instantly',
	description:
		'Generate UML diagrams from natural language using AI. Fast, easy, and accurate UML diagram generation by Ryan Godwin.',
	keywords: [
		'UML diagrams',
		'UMLBot',
		'UML from natural language',
		'UML tool',
		'UMLBot',
		'Ryan Godwin',
		'AI diagram generator',
	],
	authors: [{ name: 'Ryan Godwin', url: 'https://ai-preview.anes.uab.edu'}],
	openGraph: {
		title: 'UMLBot',
		description:
			'Generate UML diagrams from natural language using AI. Fast and easy UML diagram generation.',
		url: 'https://ai-preview.anes.uab.edu',
		siteName: 'UMLBot',
		images: [
			{
				url: 'https://ai-preview.anes.uab.edu/cover.png', // Add an OpenGraph image for social sharing
				width: 1200,
				height: 630,
				alt: 'UMLBot',
			},
		],
		locale: 'en_US',
		type: 'website',
	},
	twitter: {
		card: 'summary_large_image',
		title: 'UMLBot',
		description:
			'Generate UML diagrams from natural language using AI. Fast, easy, and accurate UML diagram generation.',
		images: ['https://ai-preview.anes.uab.edu/cover.png'], // Add a Twitter image for social sharing
	},
	robots: {
		index: true,
		follow: true,
		nocache: false,
		googleBot: {
			index: true,
			follow: true,
			noimageindex: false,
			'max-video-preview': -1,
			'max-image-preview': 'large',
			'max-snippet': -1,
		},
	},
	metadataBase: new URL('https://ai-preview.anes.uab.edu/'), // Replace with your actual domain
	alternates: {
		canonical: '/', // Add canonical URL to avoid duplicate content issues
	},
}

export default function RootLayout({
	children,
}: {
	children: React.ReactNode
}) {
	return (
			<html lang="en" suppressHydrationWarning>
				<body className="font-sans">{children}</body>
			</html>
		)
	}
