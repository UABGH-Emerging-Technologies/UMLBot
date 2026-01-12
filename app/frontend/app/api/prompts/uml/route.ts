import { NextResponse } from 'next/server'
import { readFile } from 'fs/promises'
import path from 'path'

const PROMPTY_FILENAME = 'uml_diagram.prompty'

const getPromptyPath = () =>
	path.resolve(process.cwd(), '..', '..', 'assets', PROMPTY_FILENAME)

const extractTemplate = (content: string) => {
	const match = content.match(/prompt:\s*\n\s*template:\s*\|\s*\n([\s\S]*)/)
	if (!match) return null
	const templateLines = match[1].split('\n')
	const normalizedLines = templateLines.map(line => line.replace(/^[ \t]{4}/, ''))
	const template = normalizedLines.join('\n').trim()
	return template.length > 0 ? template : null
}

export async function GET() {
	try {
		const fileContent = await readFile(getPromptyPath(), 'utf-8')
		const template = extractTemplate(fileContent)
		if (!template) {
			return NextResponse.json(
				{ error: 'Prompt template not found' },
				{ status: 500 }
			)
		}
		return NextResponse.json({ template })
	} catch (error) {
		console.error('Failed to load UML prompt template', error)
		return NextResponse.json(
			{ error: 'Failed to load prompt template' },
			{ status: 500 }
		)
	}
}
