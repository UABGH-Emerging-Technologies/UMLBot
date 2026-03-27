/**
 * Calls the backend API to generate mindmaps.
 * Returns: { plantuml_code: string, image_base64: string, image_url: string, status: string, message: string }
 */
const API_BASE_URL = '/api/mindmap'

export async function generateMindmapAction(
	description: string,
	diagramType: string,
	theme?: string,
	code?: string
): Promise<{
	plantuml_code: string | null,
	image_base64: string | null,
	image_url: string | null,
	status: string,
	message: string
}> {
	try {
		const response = await fetch(`${API_BASE_URL}/generate`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({
				description,
				diagram_type: diagramType,
				theme,
				code,
			}),
		})
		if (!response.ok) {
			const errorText = await response.text()
			throw new Error(`API error: ${response.status} - ${errorText}`)
		}
		const data = await response.json()
		if (data.status !== 'ok') {
			throw new Error(data.message || 'Unknown error from backend')
		}
		return data
	} catch (error: any) {
		console.error('Mindmap generation error:', error)
		return {
			plantuml_code: null,
			image_base64: null,
			image_url: null,
			status: 'error',
			message: error.message || 'Failed to generate mindmap',
		}
	}
}

export async function renderMindmapAction(
	plantumlCode: string
): Promise<{
	image_base64: string | null,
	image_url: string | null,
	status: string,
	message: string
}> {
	try {
		const response = await fetch(`${API_BASE_URL}/render`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({
				plantuml_code: plantumlCode,
			}),
		})
		if (!response.ok) {
			const errorText = await response.text()
			throw new Error(`API error: ${response.status} - ${errorText}`)
		}
		const data = await response.json()
		if (data.status !== 'ok') {
			throw new Error(data.message || 'Unknown error from backend')
		}
		return data
	} catch (error: any) {
		console.error('Mindmap render error:', error)
		return {
			image_base64: null,
			image_url: null,
			status: 'error',
			message: error.message || 'Failed to render mindmap',
		}
	}
}
