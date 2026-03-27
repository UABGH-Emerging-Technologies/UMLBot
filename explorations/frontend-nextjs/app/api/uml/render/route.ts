import { NextResponse } from 'next/server'

const resolveBackendBase = () => {
	return (
		process.env.GRADIO_API_BASE ??
		process.env.UMLBOT_API_BASE ??
		process.env.NEXT_PUBLIC_GRADIO_API_BASE ??
		'http://backend:7860'
	).replace(/\/$/, '')
}

export async function POST(request: Request) {
	try {
		const payload = await request.json()
		const backendBase = resolveBackendBase()
		const response = await fetch(`${backendBase}/api/render`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify(payload),
		})

		const contentType = response.headers.get('Content-Type') ?? ''
		const body = contentType.includes('application/json')
			? await response.json()
			: await response.text()

		return NextResponse.json(body, { status: response.status })
	} catch (error) {
		console.error('Failed to proxy UML render request', error)
		return NextResponse.json(
			{ status: 'error', message: 'Failed to reach backend service' },
			{ status: 502 }
		)
	}
}
