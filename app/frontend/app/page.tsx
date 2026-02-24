'use client'

import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '@/components/ui/select'
import {
	Tooltip,
	TooltipContent,
	TooltipProvider,
	TooltipTrigger,
} from '@/components/ui/tooltip'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import {
	Download,
	Copy,
	Code,
	FileCode,
	Sparkles,
	RefreshCw,
	Zap,
	Lightbulb,
	LayoutTemplate,
	Moon,
	Sun,
	Check,
} from 'lucide-react'

import {
	DIAGRAM_TEMPLATES,
	DIAGRAM_TYPES,
	DEFAULT_DIAGRAM_TYPE,
	MINDMAP_TEMPLATE,
} from '@/constants'
import { generateUMLAction, renderUMLAction } from '@/actions/uml.action'
import { generateMindmapAction, renderMindmapAction } from '@/actions/mindmap.action'
import UMLViewer from '@/components/UMLViewer'

type ChatMessage = {
	id: string
	role: 'user' | 'assistant' | 'system' | 'error'
	content: string
}

type DiagramMode = 'uml' | 'mindmap'

const createMessageId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
const MAX_HISTORY_MESSAGES = 10

const summarizeChatHistory = (history: ChatMessage[]) => {
	const relevant = history.slice(-MAX_HISTORY_MESSAGES)
	return relevant
		.map(msg => {
			const label =
				msg.role === 'user'
					? 'User'
					: msg.role === 'assistant'
						? 'Assistant'
						: msg.role === 'error'
							? 'Error'
							: 'System'
			return `${label}: ${msg.content}`
		})
		.join('\n')
}

const extractPlantUmlBlock = (code: string | null | undefined, mode: DiagramMode) => {
	if (!code) return null
	const pattern =
		mode === 'mindmap'
			? /@startmindmap[\s\S]*@endmindmap/i
			: /@startuml[\s\S]*@enduml/i
	const match = code.match(pattern)
	return match ? match[0] : null
}

const applyPromptyTemplate = ({
	template,
	diagramType,
	description,
	theme,
}: {
	template: string
	diagramType: string
	description: string
	theme?: string
}) => {
	const themeBlockRegex = /\{%\s*if\s+theme\s*%\}[\s\S]*?\{%\s*endif\s*%\}/g
	let resolved = template

	if (theme) {
		resolved = resolved
			.replace(/\{%\s*if\s+theme\s*%\}/g, '')
			.replace(/\{%\s*endif\s*%\}/g, '')
			.replace(/\{\{\s*theme\s*\}\}/g, theme)
	} else {
		resolved = resolved.replace(themeBlockRegex, '')
	}

	return resolved
		.replace(/\{\{\s*diagram_type\s*\}\}/g, diagramType)
		.replace(/\{\{\s*description\s*\}\}/g, description)
		.trim()
}

const buildPromptDescription = ({
	diagramType,
	currentCode,
	chatSummary,
	latestRequest,
	promptTemplate,
	mode,
}: {
	diagramType: string
	currentCode: string
	chatSummary: string
	latestRequest: string
	promptTemplate?: string | null
	mode: DiagramMode
}) => {
	const isMindmap = mode === 'mindmap'
	const outputFence = isMindmap
		? '@startmindmap and @endmindmap'
		: '@startuml and @enduml'
	const codeLabel = isMindmap
		? 'Existing PlantUML mindmap (reuse and refine rather than restart):'
		: 'Existing PlantUML (reuse and refine rather than restart):'
	const emptyLabel = isMindmap
		? 'No mindmap has been created yet. Create a fresh PlantUML mindmap.'
		: 'No diagram has been created yet. Create a fresh PlantUML diagram.'
	const descriptionSections = [
		`Latest user request:\n${latestRequest}`,
		currentCode ? `${codeLabel}\n${currentCode}` : emptyLabel,
		chatSummary ? `Recent conversation:\n${chatSummary}` : '',
		`Respond with PlantUML only between ${outputFence}.`,
	].filter(Boolean)

	const composedDescription = descriptionSections.join('\n\n')

	if (promptTemplate) {
		return applyPromptyTemplate({
			template: promptTemplate,
			diagramType,
			description: composedDescription,
		})
	}

	return [
		`You are an expert ${isMindmap ? 'mindmap' : 'UML'} assistant following the prompty template rules.`,
		`Diagram Type: ${diagramType}`,
		`Generate valid PlantUML enclosed between ${outputFence} with concise, professional notation. No extra prose or markdown fences.`,
		composedDescription,
	].join('\n\n')
}

export default function UMLGenerator() {
	const [chatInput, setChatInput] = useState('')
	const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])
	const [chatHistoryByType, setChatHistoryByType] = useState<
		Record<string, ChatMessage[]>
	>({})
	const [diagramType, setDiagramType] = useState(DEFAULT_DIAGRAM_TYPE)
	const [umlCode, setUmlCode] = useState(DIAGRAM_TEMPLATES[DEFAULT_DIAGRAM_TYPE] ?? '')
	const [umlCodeByType, setUmlCodeByType] = useState<Record<string, string>>({
		[DEFAULT_DIAGRAM_TYPE]: DIAGRAM_TEMPLATES[DEFAULT_DIAGRAM_TYPE] ?? '',
	})
	const [activeMode, setActiveMode] = useState<DiagramMode>('uml')
	const [mindmapCode, setMindmapCode] = useState(MINDMAP_TEMPLATE)
	const [mindmapImage, setMindmapImage] = useState('')
	const [mindmapHistory, setMindmapHistory] = useState<ChatMessage[]>([])
	const [mindmapErrorMsg, setMindmapErrorMsg] = useState<string | null>(null)
	const [mindmapPromptTemplate, setMindmapPromptTemplate] = useState<string | null>(
		null
	)
	const [isGenerating, setIsGenerating] = useState(false)
	const [isRefreshing, setIsRefreshing] = useState(false)
	const [isDarkMode, setIsDarkMode] = useState(false)
	const [activeTab, setActiveTab] = useState('split')
	const editorRef = useRef<HTMLDivElement>(null)
	const [image, setImage] = useState('')
	const [imageByType, setImageByType] = useState<Record<string, string>>({})
	const [isCopied, setIsCopied] = useState(false)
	const [errorMsg, setErrorMsg] = useState<string | null>(null)
	const [errorByType, setErrorByType] = useState<Record<string, string | null>>({})
	const [promptTemplate, setPromptTemplate] = useState<string | null>(null)

	// Toggle dark mode
	useEffect(() => {
		if (isDarkMode) {
			document.documentElement.classList.add('dark')
		} else {
			document.documentElement.classList.remove('dark')
		}
	}, [isDarkMode])

	useEffect(() => {
		const fetchPromptTemplate = async (
			endpoint: string,
			onSuccess: (template: string | null) => void,
			label: string
		) => {
			try {
				const response = await fetch(endpoint)
				if (!response.ok) {
					throw new Error(`Failed to load prompt template: ${response.status}`)
				}
				const data = await response.json()
				if (data.template) {
					onSuccess(data.template)
					return
				}
				onSuccess(null)
			} catch (error) {
				console.error(`Unable to load ${label} prompt template`, error)
				onSuccess(null)
			}
		}

		fetchPromptTemplate('/api/prompts/uml', setPromptTemplate, 'UML')
		fetchPromptTemplate('/api/prompts/mindmap', setMindmapPromptTemplate, 'mindmap')
	}, [])

	const handleSendMessage = async () => {
		const trimmedInput = chatInput.trim()
		if (!trimmedInput) return

		const userMessage: ChatMessage = {
			id: createMessageId(),
			role: 'user',
			content: trimmedInput,
		}

		setChatInput('')

		if (activeMode === 'uml') {
			const pendingHistory = [...chatHistory, userMessage]
			setChatHistory(pendingHistory)
			setChatHistoryByType(prev => ({ ...prev, [diagramType]: pendingHistory }))

			try {
				setIsGenerating(true)
				setErrorMsg(null)
				setImage('')

				const historyPrompt = summarizeChatHistory(pendingHistory)
				const composedDescription = buildPromptDescription({
					diagramType,
					currentCode: umlCode,
					chatSummary: historyPrompt,
					latestRequest: trimmedInput,
					promptTemplate,
					mode: 'uml',
				})

				const result = await generateUMLAction(composedDescription, diagramType)
				if (result.status === 'ok') {
					const normalizedCode =
						extractPlantUmlBlock(result.plantuml_code, 'uml') ??
						result.plantuml_code ??
						umlCode
					if (normalizedCode !== umlCode) {
						setUmlCode(normalizedCode)
						setUmlCodeByType(prev => ({ ...prev, [diagramType]: normalizedCode }))
					}
					if (result.image_base64) {
						const nextImage = `data:image/png;base64,${result.image_base64}`
						setImage(nextImage)
						setImageByType(prev => ({ ...prev, [diagramType]: nextImage }))
						setErrorByType(prev => ({ ...prev, [diagramType]: null }))
						setErrorMsg(null)
					} else {
						const failureMsg = 'Diagram rendered without a preview image.'
						setImage('')
						setImageByType(prev => ({ ...prev, [diagramType]: '' }))
						setErrorMsg(failureMsg)
						setErrorByType(prev => ({ ...prev, [diagramType]: failureMsg }))
					}
					setIsRefreshing(false)
					setChatHistory(prev => {
						const assistantMessage: ChatMessage = {
							id: createMessageId(),
							role: 'assistant',
							content: result.message || 'Diagram updated. Share your next change request!',
						}
						const nextHistory = [...prev, assistantMessage]
						setChatHistoryByType(current => ({
							...current,
							[diagramType]: nextHistory,
						}))
						return nextHistory
					})
				} else {
					const failureMsg = result.message || 'Failed to generate UML diagram'
					setErrorMsg(failureMsg)
					setErrorByType(prev => ({ ...prev, [diagramType]: failureMsg }))
					setIsRefreshing(false)
					setChatHistory(prev => {
						const errorMessage: ChatMessage = {
							id: createMessageId(),
							role: 'error',
							content: failureMsg,
						}
						const nextHistory = [...prev, errorMessage]
						setChatHistoryByType(current => ({
							...current,
							[diagramType]: nextHistory,
						}))
						return nextHistory
					})
				}
			} catch (error: unknown) {
				console.error(error)
				const message =
					error instanceof Error
						? error.message || 'Something went wrong/Out of credits'
						: 'Something went wrong/Out of credits'
				setErrorMsg(message)
				setErrorByType(prev => ({ ...prev, [diagramType]: message }))
				setIsRefreshing(false)
				setChatHistory(prev => {
					const errorMessage: ChatMessage = {
						id: createMessageId(),
						role: 'error',
						content: message,
					}
					const nextHistory = [...prev, errorMessage]
					setChatHistoryByType(current => ({
						...current,
						[diagramType]: nextHistory,
					}))
					return nextHistory
				})
			} finally {
				setIsGenerating(false)
			}
			return
		}

		const pendingHistory = [...mindmapHistory, userMessage]
		setMindmapHistory(pendingHistory)

		try {
			setIsGenerating(true)
			setMindmapErrorMsg(null)
			setMindmapImage('')

			const historyPrompt = summarizeChatHistory(pendingHistory)
			const composedDescription = buildPromptDescription({
				diagramType: 'Mindmap',
				currentCode: mindmapCode,
				chatSummary: historyPrompt,
				latestRequest: trimmedInput,
				promptTemplate: mindmapPromptTemplate,
				mode: 'mindmap',
			})

			const result = await generateMindmapAction(composedDescription, 'Mindmap')
			if (result.status === 'ok') {
				const normalizedCode =
					extractPlantUmlBlock(result.plantuml_code, 'mindmap') ??
					result.plantuml_code ??
					mindmapCode
				if (normalizedCode !== mindmapCode) {
					setMindmapCode(normalizedCode)
				}
				if (result.image_base64) {
					const nextImage = `data:image/png;base64,${result.image_base64}`
					setMindmapImage(nextImage)
					setMindmapErrorMsg(null)
				} else {
					const failureMsg = 'Mindmap rendered without a preview image.'
					setMindmapImage('')
					setMindmapErrorMsg(failureMsg)
				}
				setIsRefreshing(false)
				setMindmapHistory(prev => [
					...prev,
					{
						id: createMessageId(),
						role: 'assistant',
						content: result.message || 'Mindmap updated. Share your next change request!',
					},
				])
			} else {
				const failureMsg = result.message || 'Failed to generate mindmap'
				setMindmapErrorMsg(failureMsg)
				setIsRefreshing(false)
				setMindmapHistory(prev => [
					...prev,
					{
						id: createMessageId(),
						role: 'error',
						content: failureMsg,
					},
				])
			}
		} catch (error: unknown) {
			console.error(error)
			const message =
				error instanceof Error
					? error.message || 'Something went wrong/Out of credits'
					: 'Something went wrong/Out of credits'
			setMindmapErrorMsg(message)
			setIsRefreshing(false)
			setMindmapHistory(prev => [
				...prev,
				{
					id: createMessageId(),
					role: 'error',
					content: message,
				},
			])
		} finally {
			setIsGenerating(false)
		}
	}

	// Render helpers
	const renderUML = (
		currentCode: string,
		currentImage: string,
		currentError: string | null
	) => {
		if (currentError) {
			return (
				<div className="flex items-center justify-center h-full text-destructive">
					{currentError}
				</div>
			)
		}
		const emptyLabel = isUmlMode
			? currentCode
				? 'No UML preview yet'
				: 'No UML diagram available'
			: currentCode
				? 'No mindmap preview yet'
				: 'No mindmap available'
		const altText = isUmlMode ? 'UML Diagram Preview' : 'Mindmap Preview'
		return (
			<UMLViewer
				umlCode={currentCode}
				isGenerating={isBusy}
				imageUrl={currentImage || undefined}
				altText={altText}
				emptyLabel={emptyLabel}
			/>
		)
	}

	const renderChatHistory = (history: ChatMessage[], emptyMessage: string) => {
		if (history.length === 0) {
			return (
				<p className="text-sm text-muted-foreground">{emptyMessage}</p>
			)
		}

		return history.map(message => {
			const label =
				message.role === 'user'
					? 'You'
					: message.role === 'assistant'
						? 'Assistant'
						: message.role === 'system'
							? 'System'
							: 'Error'
			const accentClass =
				message.role === 'user'
					? 'text-primary'
					: message.role === 'assistant'
						? 'text-emerald-500'
						: message.role === 'error'
							? 'text-destructive'
							: 'text-muted-foreground'

			return (
				<div key={message.id} className="mb-3 last:mb-0">
					<p className={`text-xs font-semibold uppercase ${accentClass}`}>{label}</p>
					<p className="text-sm whitespace-pre-wrap">{message.content}</p>
				</div>
			)
		})
	}

	const handleTemplateChange = (type: string) => {
		setChatHistoryByType(prev => ({ ...prev, [diagramType]: chatHistory }))
		setUmlCodeByType(prev => ({ ...prev, [diagramType]: umlCode }))
		setImageByType(prev => ({ ...prev, [diagramType]: image }))
		setErrorByType(prev => ({ ...prev, [diagramType]: errorMsg }))

		setDiagramType(type)
		const nextHistory = chatHistoryByType[type] ?? []
		const nextCode = umlCodeByType[type] ?? DIAGRAM_TEMPLATES[type] ?? ''
		const nextImage = imageByType[type] ?? ''
		const nextError = errorByType[type] ?? null

		setChatHistory(nextHistory)
		setUmlCode(nextCode)
		setImage(nextImage)
		setErrorMsg(nextError)
		setIsRefreshing(false)
	}

	const handleCopy = () => {
		const textToCopy = activeMode === 'uml' ? umlCode : mindmapCode
		setIsCopied(true)
		navigator.clipboard.writeText(textToCopy)
		setTimeout(() => {
			setIsCopied(false)
		}, 2000)
	}

	const handleDownload = async () => {
		const currentImage = activeMode === 'uml' ? image : mindmapImage
		const filePrefix = activeMode === 'uml' ? 'uml' : 'mindmap'
		if (!currentImage) {
			return
		}
		try {
			let blob: Blob
			let extension = 'png'

			if (currentImage.startsWith('data:')) {
				const [meta, data] = currentImage.split(',', 2)
				const mimeMatch = meta.match(/data:([^;]+);base64/)
				const mimeType = mimeMatch ? mimeMatch[1] : 'image/png'
				const binary = atob(data)
				const bytes = new Uint8Array(binary.length)
				for (let i = 0; i < binary.length; i += 1) {
					bytes[i] = binary.charCodeAt(i)
				}
				blob = new Blob([bytes], { type: mimeType })
				if (mimeType.includes('svg')) {
					extension = 'svg'
				} else if (mimeType.includes('png')) {
					extension = 'png'
				}
			} else {
				const response = await fetch(currentImage)
				if (!response.ok) {
					throw new Error('Failed to fetch diagram content')
				}
				const contentType = response.headers.get('Content-Type') ?? ''
				if (contentType.includes('svg')) {
					extension = 'svg'
				} else if (contentType.includes('png')) {
					extension = 'png'
				}
				blob = await response.blob()
			}

			const url = URL.createObjectURL(blob)
			const link = document.createElement('a')
			link.href = url
			link.download = `${filePrefix}.${extension}`
			document.body.appendChild(link) // Append the link to the DOM (required for Firefox)
			link.click() // Trigger the download

			// Clean up by revoking the Blob URL and removing the link element
			URL.revokeObjectURL(url)
			document.body.removeChild(link)
		} catch (error) {
			console.error('Error downloading the SVG:', error)
		}
	}

	const handleManualUpdate = () => {
		const currentCode = activeMode === 'uml' ? umlCode : mindmapCode
		if (!currentCode.trim()) {
			return
		}
		setIsRefreshing(true)
		if (activeMode === 'uml') {
			setErrorMsg(null)
			setErrorByType(prev => ({ ...prev, [diagramType]: null }))
		} else {
			setMindmapErrorMsg(null)
		}
		const renderAction =
			activeMode === 'uml' ? renderUMLAction : renderMindmapAction
		renderAction(currentCode)
			.then(result => {
				if (result.status === 'ok') {
					if (result.image_base64) {
						const nextImage = `data:image/png;base64,${result.image_base64}`
						if (activeMode === 'uml') {
							setImage(nextImage)
							setImageByType(prev => ({ ...prev, [diagramType]: nextImage }))
							setErrorMsg(null)
							setErrorByType(prev => ({ ...prev, [diagramType]: null }))
						} else {
							setMindmapImage(nextImage)
							setMindmapErrorMsg(null)
						}
					} else {
						const failureMsg =
							activeMode === 'uml'
								? 'Diagram rendered without a preview image.'
								: 'Mindmap rendered without a preview image.'
						if (activeMode === 'uml') {
							setImage('')
							setImageByType(prev => ({ ...prev, [diagramType]: '' }))
							setErrorMsg(failureMsg)
							setErrorByType(prev => ({ ...prev, [diagramType]: failureMsg }))
						} else {
							setMindmapImage('')
							setMindmapErrorMsg(failureMsg)
						}
					}
				} else {
					const failureMsg =
						result.message ||
						(activeMode === 'uml'
							? 'Failed to render UML diagram'
							: 'Failed to render mindmap')
					if (activeMode === 'uml') {
						setErrorMsg(failureMsg)
						setErrorByType(prev => ({ ...prev, [diagramType]: failureMsg }))
					} else {
						setMindmapErrorMsg(failureMsg)
					}
				}
			})
			.catch(error => {
				const message =
					error instanceof Error
						? error.message || 'Failed to render diagram'
						: 'Failed to render diagram'
				if (activeMode === 'uml') {
					setErrorMsg(message)
					setErrorByType(prev => ({ ...prev, [diagramType]: message }))
				} else {
					setMindmapErrorMsg(message)
				}
			})
			.finally(() => {
				setIsRefreshing(false)
			})
	}

	const isBusy = isGenerating || isRefreshing
	const isUmlMode = activeMode === 'uml'
	const currentCode = isUmlMode ? umlCode : mindmapCode
	const currentImage = isUmlMode ? image : mindmapImage
	const currentError = isUmlMode ? errorMsg : mindmapErrorMsg
	const currentHistory = isUmlMode ? chatHistory : mindmapHistory
	const editorTitle = isUmlMode ? 'PlantUML Code' : 'Mindmap Code'
	const syntaxLabel = isUmlMode ? 'PlantUML' : 'PlantUML Mindmap'
	const assistantTitle = isUmlMode ? 'UML Chat Assistant' : 'Mindmap Assistant'
	const emptyChatMessage = isUmlMode
		? 'No messages yet. Describe a system or ask for a change to get started.'
		: 'No messages yet. Describe a topic or ask for a change to get started.'
	const tips = isUmlMode
		? [
				'Switch templates to explore available UML diagram types',
				'Select the diagram you need',
				'When revising, refer to existing elements',
				'Fine-tune the PlantUML code directly in the editor',
				'Refresh the page to wipe memory',
				'Save prompts elsewhere in early adoption',
			]
		: [
				'Describe the central topic first, then expand outward',
				'Use short, clear node labels',
				'Ask to group related branches together',
				'Refine by adding or removing sub-branches',
				'Fine-tune the mindmap code directly in the editor',
				'Refresh the page to wipe memory',
			]

	return (
		<div className={`min-h-screen bg-background text-foreground`}>
			<header className="border-b">
				<div className="container mx-auto px-4 py-3 flex items-center justify-between">
					<div className="flex items-center gap-2">
						<FileCode className="h-6 w-6 text-primary" />
						<h1 className="text-xl font-bold">UMLBot</h1>
						<Badge variant="accent" className="ml-2 uppercase tracking-wide">
							Alpha
						</Badge>
					</div>
					<div className="flex items-center gap-4">
						<TooltipProvider>
							<Tooltip>
								<TooltipTrigger asChild>
									<div className="flex items-center gap-2">
										<Switch
											checked={isDarkMode}
											onCheckedChange={setIsDarkMode}
											id="dark-mode"
										/>
										<Label htmlFor="dark-mode" className="cursor-pointer">
											{isDarkMode ? (
												<Moon className="h-4 w-4" />
											) : (
												<Sun className="h-4 w-4" />
											)}
										</Label>
									</div>
								</TooltipTrigger>
								<TooltipContent>
									<p>Toggle dark mode</p>
								</TooltipContent>
							</Tooltip>
						</TooltipProvider>
						{/* TODO: Add share and settings functionality */}
						{/* <Button variant="outline" size="sm">
							<Share2 className="h-4 w-4 mr-2" />
							Share
						</Button>

						<Button variant="outline" size="sm">
							<Settings className="h-4 w-4 mr-2" />
							Settings
						</Button> */}
					</div>
				</div>
			</header>

			<main className="container mx-auto px-4 py-6">
				<div className="mb-4 flex justify-between items-center">
					<Tabs
						value={activeMode}
						onValueChange={value => setActiveMode(value as DiagramMode)}
					>
						<TabsList>
							<TabsTrigger value="uml">UML Diagrams</TabsTrigger>
							<TabsTrigger value="mindmap">Mindmap</TabsTrigger>
						</TabsList>
					</Tabs>
				</div>
				<div className="mb-6">
					<Card>
						<CardContent className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between p-4">
							<div className="flex items-center gap-2">
								<Lightbulb className="h-5 w-5 text-primary" />
								<h2 className="text-base font-semibold">Tips</h2>
							</div>
							<ul className="text-sm text-muted-foreground grid gap-1 md:grid-cols-2 md:gap-x-4 md:gap-y-1">
								{tips.map(tip => (
									<li key={tip}>• {tip}</li>
								))}
							</ul>
						</CardContent>
					</Card>
				</div>

				<div className="grid grid-cols-1 lg:grid-cols-[1.3fr_2.7fr] gap-6">
					{/* Sidebar */}
					<div>
						<Card>
							<CardContent className="p-4">
								<div className="space-y-4">
									{isUmlMode ? (
										<div>
											<h3 className="text-lg font-medium mb-2 flex items-center gap-2">
												<LayoutTemplate className="h-4 w-4 text-primary" />
												Diagram Types
											</h3>
											<div className="space-y-2">
												<Select
													value={diagramType}
													onValueChange={handleTemplateChange}
												>
													<SelectTrigger>
														<SelectValue placeholder="Select template" />
													</SelectTrigger>
													<SelectContent>
														{DIAGRAM_TYPES.map(type => (
															<SelectItem key={type} value={type}>
																{type} Diagram
															</SelectItem>
														))}
													</SelectContent>
												</Select>
											</div>
										</div>
									) : (
										<div>
											<h3 className="text-lg font-medium mb-2 flex items-center gap-2">
												<LayoutTemplate className="h-4 w-4 text-primary" />
												Mindmap Mode
											</h3>
											<p className="text-sm text-muted-foreground">
												Describe a topic and the assistant will expand it into a structured mindmap.
											</p>
										</div>
									)}

									<Separator />

									<div>
										<h3 className="text-lg font-medium mb-2 flex items-center gap-2">
											<Sparkles className="h-4 w-4 text-primary" />
											{assistantTitle}
										</h3>
										<div className="space-y-3">
											<div className="border rounded-md bg-muted/40 p-3 h-56 overflow-y-auto">
												{renderChatHistory(currentHistory, emptyChatMessage)}
											</div>
											<Textarea
												placeholder={
													isUmlMode
														? 'Ask for a diagram or request a change (Shift+Enter for new line)...'
														: 'Describe a mindmap or request a change (Shift+Enter for new line)...'
												}
												value={chatInput}
												onChange={e => setChatInput(e.target.value)}
												onKeyDown={event => {
													if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
														event.preventDefault()
														handleSendMessage()
													}
												}}
												className="min-h-[100px]"
											/>
											<Button
												onClick={handleSendMessage}
												className="w-full"
												disabled={isGenerating || !chatInput.trim()}
											>
												{isGenerating ? (
													<>
														<RefreshCw className="mr-2 h-4 w-4 animate-spin" />
														Working...
													</>
												) : (
													<>
														<Zap className="mr-2 h-4 w-4" />
														Send Request
													</>
												)}
											</Button>
										</div>
									</div>

								</div>
							</CardContent>
						</Card>
					</div>

					{/* Main content */}
					<div>
						<Tabs
							value={activeTab}
							onValueChange={setActiveTab}
							className="w-full"
						>
							<div className="flex justify-between items-center mb-4">
								<TabsList>
									<TabsTrigger
										value="editor"
										className="flex items-center gap-2"
									>
										<Code className="h-4 w-4" />
										Editor
									</TabsTrigger>
									<TabsTrigger
										value="preview"
										className="flex items-center gap-2"
									>
										<FileCode className="h-4 w-4" />
										Preview
									</TabsTrigger>
									<TabsTrigger
										value="split"
										className="flex items-center gap-2"
									>
										<LayoutTemplate className="h-4 w-4" />
										Split View
									</TabsTrigger>
								</TabsList>

								<div className="flex items-center gap-2">
									<Button
										onClick={handleManualUpdate}
										variant="default"
										size="sm"
										disabled={!currentCode.trim() || isBusy}
									>
										{isRefreshing ? (
											<>
												<RefreshCw className="h-4 w-4 mr-2 animate-spin" />
												Updating...
											</>
										) : (
											<>
												<RefreshCw className="h-4 w-4 mr-2" />
												{isUmlMode ? 'Update Diagram' : 'Update Mindmap'}
											</>
										)}
									</Button>
									<Button onClick={handleCopy} variant="outline" size="sm">
										{isCopied ? (
											<Check className="h-4 w-4 mr-2" />
										) : (
											<Copy className="h-4 w-4 mr-2" />
										)}
										Copy
									</Button>
									<Button onClick={handleDownload} variant="outline" size="sm">
										<Download className="h-4 w-4 mr-2" />
										Export
									</Button>
								</div>
							</div>

							<TabsContent value="editor" className="mt-0">
								<Card>
									<CardContent className="p-0">
											<div className="border rounded-md">
												<div className="bg-muted/50 p-2 border-b flex items-center justify-between">
													<div className="text-sm font-medium">{editorTitle}</div>
													<div className="text-xs text-muted-foreground">
														Syntax: {syntaxLabel}
													</div>
												</div>
												<div
													ref={editorRef}
													className="p-4 font-mono text-sm h-[70vh] overflow-auto"
												>
													<Textarea
														value={currentCode}
														onChange={e =>
															isUmlMode
																? setUmlCode(e.target.value)
																: setMindmapCode(e.target.value)
														}
														className="font-mono h-full border-0 focus-visible:ring-0 resize-none"
												/>
											</div>
										</div>
									</CardContent>
								</Card>
							</TabsContent>

							<TabsContent value="preview" className="mt-0">
								<Card>
									<CardContent className="p-0">
											<div className="border rounded-md">
												<div className="bg-muted/50 p-2 border-b flex items-center justify-between">
													<div className="text-sm font-medium">
														{isUmlMode ? 'Diagram Preview' : 'Mindmap Preview'}
													</div>
													<div className="text-xs text-muted-foreground">
														{isBusy ? 'Generating...' : 'Ready'}
													</div>
												</div>
											<div className="h-[70vh] overflow-hidden">
												{renderUML(currentCode, currentImage, currentError)}
											</div>
										</div>
									</CardContent>
								</Card>
							</TabsContent>

							<TabsContent value="split" className="mt-0">
								<div className="grid grid-cols-1 md:grid-cols-2 gap-4">
									<Card>
										<CardContent className="p-0">
											<div className="border rounded-md">
												<div className="bg-muted/50 p-2 border-b flex items-center justify-between">
													<div className="text-sm font-medium">{editorTitle}</div>
													<div className="text-xs text-muted-foreground">
														Syntax: {syntaxLabel}
													</div>
												</div>
												<div className="p-4 font-mono text-sm h-[70vh] overflow-auto">
													<Textarea
														value={currentCode}
														onChange={e =>
															isUmlMode
																? setUmlCode(e.target.value)
																: setMindmapCode(e.target.value)
														}
														className="font-mono h-full border-0 focus-visible:ring-0 resize-none"
													/>
												</div>
											</div>
										</CardContent>
									</Card>

									<Card>
										<CardContent className="p-0">
												<div className="border rounded-md">
												<div className="bg-muted/50 p-2 border-b flex items-center justify-between">
													<div className="text-sm font-medium">
														{isUmlMode ? 'Diagram Preview' : 'Mindmap Preview'}
													</div>
													<div className="text-xs text-muted-foreground">
														{isBusy ? 'Generating...' : 'Ready'}
													</div>
												</div>
												<div className="h-[70vh] border overflow-hidden">
													{renderUML(currentCode, currentImage, currentError)}
												</div>
											</div>
										</CardContent>
									</Card>
								</div>
							</TabsContent>
						</Tabs>
					</div>
				</div>
			</main>
		</div>
	)
}
