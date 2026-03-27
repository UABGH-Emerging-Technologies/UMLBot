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
	UI_MOCKUP_TEMPLATE,
	GANTT_TEMPLATE,
	ERD_TEMPLATE,
	JSON_TEMPLATE,
	C4_TEMPLATE,
} from '@/constants'
import { generateUMLAction, renderUMLAction } from '@/actions/uml.action'
import { generateMindmapAction, renderMindmapAction } from '@/actions/mindmap.action'
import { generateUIMockupAction, renderUIMockupAction } from '@/actions/ui_mockup.action'
import { generateGanttAction, renderGanttAction } from '@/actions/gantt.action'
import { generateERDAction, renderERDAction } from '@/actions/erd.action'
import { generateJSONAction, renderJSONAction } from '@/actions/json.action'
import { generateC4Action, renderC4Action } from '@/actions/c4.action'
import UMLViewer from '@/components/UMLViewer'

type ChatMessage = {
	id: string
	role: 'user' | 'assistant' | 'system' | 'error'
	content: string
}

type DiagramMode = 'uml' | 'mindmap' | 'ui-mockup' | 'gantt' | 'erd' | 'json' | 'c4'

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
			: mode === 'ui-mockup'
				? /@startsalt[\s\S]*@endsalt/i
				: mode === 'gantt'
					? /@startgantt[\s\S]*@endgantt/i
					: mode === 'json'
						? /@startjson[\s\S]*@endjson/i
						: mode === 'c4'
							? /@startuml[\s\S]*@enduml/i
							: /@startuml[\s\S]*@enduml/i
	const match = code.match(pattern)
	return match ? match[0] : null
}

const buildPromptDescription = ({
	diagramType,
	currentCode,
	chatSummary,
	latestRequest,
	mode,
}: {
	diagramType: string
	currentCode: string
	chatSummary: string
	latestRequest: string
	mode: DiagramMode
}) => {
	const isMindmap = mode === 'mindmap'
	const isUIMockup = mode === 'ui-mockup'
	const isGantt = mode === 'gantt'
	const isERD = mode === 'erd'
	const isJson = mode === 'json'
	const isC4 = mode === 'c4'
	const outputFence = isMindmap
		? '@startmindmap and @endmindmap'
		: isUIMockup
			? '@startsalt and @endsalt'
			: isGantt
				? '@startgantt and @endgantt'
				: isJson
					? '@startjson and @endjson'
					: isC4
						? '@startuml and @enduml with C4-PlantUML includes'
						: '@startuml and @enduml'
	const codeLabel = isMindmap
		? 'Existing PlantUML mindmap (reuse and refine rather than restart):'
		: isUIMockup
			? 'Existing PlantUML SALT mockup (reuse and refine rather than restart):'
			: isGantt
				? 'Existing PlantUML Gantt chart (reuse and refine rather than restart):'
				: isERD
					? 'Existing PlantUML ER diagram (reuse and refine rather than restart):'
					: isJson
						? 'Existing PlantUML JSON diagram (reuse and refine rather than restart):'
						: isC4
							? 'Existing PlantUML C4 diagram (reuse and refine rather than restart):'
							: 'Existing PlantUML (reuse and refine rather than restart):'
	const emptyLabel = isMindmap
		? 'No mindmap has been created yet. Create a fresh PlantUML mindmap.'
		: isUIMockup
			? 'No UI mockup has been created yet. Create a fresh PlantUML SALT mockup.'
			: isGantt
				? 'No Gantt chart has been created yet. Create a fresh PlantUML Gantt chart.'
				: isERD
					? 'No ER diagram has been created yet. Create a fresh PlantUML ER diagram.'
					: isJson
						? 'No JSON diagram has been created yet. Create a fresh PlantUML JSON diagram.'
						: isC4
							? 'No C4 diagram has been created yet. Create a fresh PlantUML C4 diagram.'
							: 'No diagram has been created yet. Create a fresh PlantUML diagram.'
	const descriptionSections = [
		`Latest user request:\n${latestRequest}`,
		currentCode ? `${codeLabel}\n${currentCode}` : emptyLabel,
		chatSummary ? `Recent conversation:\n${chatSummary}` : '',
		`Respond with PlantUML only between ${outputFence}.`,
	].filter(Boolean)

	const composedDescription = descriptionSections.join('\n\n')

	return [
		`You are an expert ${isMindmap ? 'mindmap' : isUIMockup ? 'UI mockup' : isGantt ? 'Gantt' : isERD ? 'ERD' : isJson ? 'JSON' : isC4 ? 'C4' : 'UML'} assistant following the prompty template rules.`,
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
	const [uiMockupCode, setUIMockupCode] = useState(UI_MOCKUP_TEMPLATE)
	const [uiMockupImage, setUIMockupImage] = useState('')
	const [uiMockupHistory, setUIMockupHistory] = useState<ChatMessage[]>([])
	const [uiMockupErrorMsg, setUIMockupErrorMsg] = useState<string | null>(null)
	const [ganttCode, setGanttCode] = useState(GANTT_TEMPLATE)
	const [ganttImage, setGanttImage] = useState('')
	const [ganttHistory, setGanttHistory] = useState<ChatMessage[]>([])
	const [ganttErrorMsg, setGanttErrorMsg] = useState<string | null>(null)
	const [erdCode, setErdCode] = useState(ERD_TEMPLATE)
	const [erdImage, setErdImage] = useState('')
	const [erdHistory, setErdHistory] = useState<ChatMessage[]>([])
	const [erdErrorMsg, setErdErrorMsg] = useState<string | null>(null)
	const [jsonCode, setJsonCode] = useState(JSON_TEMPLATE)
	const [jsonImage, setJsonImage] = useState('')
	const [jsonHistory, setJsonHistory] = useState<ChatMessage[]>([])
	const [jsonErrorMsg, setJsonErrorMsg] = useState<string | null>(null)
	const [c4Code, setC4Code] = useState(C4_TEMPLATE)
	const [c4Image, setC4Image] = useState('')
	const [c4History, setC4History] = useState<ChatMessage[]>([])
	const [c4ErrorMsg, setC4ErrorMsg] = useState<string | null>(null)
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

	// Toggle dark mode
	useEffect(() => {
		if (isDarkMode) {
			document.documentElement.classList.add('dark')
		} else {
			document.documentElement.classList.remove('dark')
		}
	}, [isDarkMode])


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

		if (activeMode === 'mindmap') {
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
							content:
								result.message || 'Mindmap updated. Share your next change request!',
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
			return
		}

		if (activeMode === 'ui-mockup') {
			const pendingHistory = [...uiMockupHistory, userMessage]
			setUIMockupHistory(pendingHistory)

			try {
				setIsGenerating(true)
				setUIMockupErrorMsg(null)
				setUIMockupImage('')

				const historyPrompt = summarizeChatHistory(pendingHistory)
				const composedDescription = buildPromptDescription({
					diagramType: 'salt',
					currentCode: uiMockupCode,
					chatSummary: historyPrompt,
					latestRequest: trimmedInput,
					mode: 'ui-mockup',
				})

				const result = await generateUIMockupAction(composedDescription, 'salt')
				if (result.status === 'ok') {
					const normalizedCode =
						extractPlantUmlBlock(result.plantuml_code, 'ui-mockup') ??
						result.plantuml_code ??
						uiMockupCode
					if (normalizedCode !== uiMockupCode) {
						setUIMockupCode(normalizedCode)
					}
					if (result.image_base64) {
						const nextImage = `data:image/png;base64,${result.image_base64}`
						setUIMockupImage(nextImage)
						setUIMockupErrorMsg(null)
					} else {
						const failureMsg = 'UI mockup rendered without a preview image.'
						setUIMockupImage('')
						setUIMockupErrorMsg(failureMsg)
					}
					setIsRefreshing(false)
					setUIMockupHistory(prev => [
						...prev,
						{
							id: createMessageId(),
							role: 'assistant',
							content:
								result.message || 'UI mockup updated. Share your next change request!',
						},
					])
				} else {
					const failureMsg = result.message || 'Failed to generate UI mockup'
					setUIMockupErrorMsg(failureMsg)
					setIsRefreshing(false)
					setUIMockupHistory(prev => [
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
				setUIMockupErrorMsg(message)
				setIsRefreshing(false)
				setUIMockupHistory(prev => [
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
			return
		}

		if (activeMode === 'gantt') {
			const pendingHistory = [...ganttHistory, userMessage]
			setGanttHistory(pendingHistory)

			try {
				setIsGenerating(true)
				setGanttErrorMsg(null)
				setGanttImage('')

				const historyPrompt = summarizeChatHistory(pendingHistory)
				const composedDescription = buildPromptDescription({
					diagramType: 'gantt',
					currentCode: ganttCode,
					chatSummary: historyPrompt,
					latestRequest: trimmedInput,
					mode: 'gantt',
				})

				const result = await generateGanttAction(composedDescription, 'gantt')
				if (result.status === 'ok') {
					const normalizedCode =
						extractPlantUmlBlock(result.plantuml_code, 'gantt') ??
						result.plantuml_code ??
						ganttCode
					if (normalizedCode !== ganttCode) {
						setGanttCode(normalizedCode)
					}
					if (result.image_base64) {
						const nextImage = `data:image/png;base64,${result.image_base64}`
						setGanttImage(nextImage)
						setGanttErrorMsg(null)
					} else {
						const failureMsg = 'Gantt chart rendered without a preview image.'
						setGanttImage('')
						setGanttErrorMsg(failureMsg)
					}
					setIsRefreshing(false)
					setGanttHistory(prev => [
						...prev,
						{
							id: createMessageId(),
							role: 'assistant',
							content:
								result.message || 'Gantt chart updated. Share your next change request!',
						},
					])
				} else {
					const failureMsg = result.message || 'Failed to generate Gantt chart'
					setGanttErrorMsg(failureMsg)
					setIsRefreshing(false)
					setGanttHistory(prev => [
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
				setGanttErrorMsg(message)
				setIsRefreshing(false)
				setGanttHistory(prev => [
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
			return
		}

		if (activeMode === 'erd') {
			const pendingHistory = [...erdHistory, userMessage]
			setErdHistory(pendingHistory)

			try {
				setIsGenerating(true)
				setErdErrorMsg(null)
				setErdImage('')

				const historyPrompt = summarizeChatHistory(pendingHistory)
				const composedDescription = buildPromptDescription({
					diagramType: 'ERD',
					currentCode: erdCode,
					chatSummary: historyPrompt,
					latestRequest: trimmedInput,
					mode: 'erd',
				})

				const result = await generateERDAction(composedDescription, 'ERD')
				if (result.status === 'ok') {
					const normalizedCode =
						extractPlantUmlBlock(result.plantuml_code, 'erd') ??
						result.plantuml_code ??
						erdCode
					if (normalizedCode !== erdCode) {
						setErdCode(normalizedCode)
					}
					if (result.image_base64) {
						const nextImage = `data:image/png;base64,${result.image_base64}`
						setErdImage(nextImage)
						setErdErrorMsg(null)
					} else {
						const failureMsg = 'ER diagram rendered without a preview image.'
						setErdImage('')
						setErdErrorMsg(failureMsg)
					}
					setIsRefreshing(false)
					setErdHistory(prev => [
						...prev,
						{
							id: createMessageId(),
							role: 'assistant',
							content:
								result.message || 'ER diagram updated. Share your next change request!',
						},
					])
				} else {
					const failureMsg = result.message || 'Failed to generate ER diagram'
					setErdErrorMsg(failureMsg)
					setIsRefreshing(false)
					setErdHistory(prev => [
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
				setErdErrorMsg(message)
				setIsRefreshing(false)
				setErdHistory(prev => [
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
			return
		}

		if (activeMode === 'json') {
			const pendingHistory = [...jsonHistory, userMessage]
			setJsonHistory(pendingHistory)

			try {
				setIsGenerating(true)
				setJsonErrorMsg(null)
				setJsonImage('')

				const historyPrompt = summarizeChatHistory(pendingHistory)
				const composedDescription = buildPromptDescription({
					diagramType: 'json',
					currentCode: jsonCode,
					chatSummary: historyPrompt,
					latestRequest: trimmedInput,
					mode: 'json',
				})

				const result = await generateJSONAction(composedDescription, 'json')
				if (result.status === 'ok') {
					const normalizedCode =
						extractPlantUmlBlock(result.plantuml_code, 'json') ??
						result.plantuml_code ??
						jsonCode
					if (normalizedCode !== jsonCode) {
						setJsonCode(normalizedCode)
					}
					if (result.image_base64) {
						const nextImage = `data:image/png;base64,${result.image_base64}`
						setJsonImage(nextImage)
						setJsonErrorMsg(null)
					} else {
						const failureMsg = 'JSON diagram rendered without a preview image.'
						setJsonImage('')
						setJsonErrorMsg(failureMsg)
					}
					setIsRefreshing(false)
					setJsonHistory(prev => [
						...prev,
						{
							id: createMessageId(),
							role: 'assistant',
							content:
								result.message || 'JSON diagram updated. Share your next change request!',
						},
					])
				} else {
					const failureMsg = result.message || 'Failed to generate JSON diagram'
					setJsonErrorMsg(failureMsg)
					setIsRefreshing(false)
					setJsonHistory(prev => [
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
				setJsonErrorMsg(message)
				setIsRefreshing(false)
				setJsonHistory(prev => [
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
			return
		}

		// C4 Diagram handler (default / fallback)
		const pendingC4History = [...c4History, userMessage]
		setC4History(pendingC4History)
		try {
			setIsGenerating(true)
			setC4ErrorMsg(null)
			setC4Image('')

			const historyPrompt = summarizeChatHistory(pendingC4History)
			const composedDescription = buildPromptDescription({
				diagramType: 'C4',
				currentCode: c4Code,
				chatSummary: historyPrompt,
				latestRequest: trimmedInput,
				mode: 'c4',
			})

			const result = await generateC4Action(composedDescription, 'C4')
			if (result.status === 'ok') {
				const normalizedCode =
					extractPlantUmlBlock(result.plantuml_code, 'c4') ??
					result.plantuml_code ??
					c4Code
				if (normalizedCode !== c4Code) {
					setC4Code(normalizedCode)
				}
				if (result.image_base64) {
					const nextImage = `data:image/png;base64,${result.image_base64}`
					setC4Image(nextImage)
					setC4ErrorMsg(null)
				} else {
					const failureMsg = 'C4 diagram rendered without a preview image.'
					setC4Image('')
					setC4ErrorMsg(failureMsg)
				}
				setIsRefreshing(false)
				setC4History(prev => [
					...prev,
					{
						id: createMessageId(),
						role: 'assistant',
						content:
							result.message || 'C4 diagram updated. Share your next change request!',
					},
				])
			} else {
				const failureMsg = result.message || 'Failed to generate C4 diagram'
				setC4ErrorMsg(failureMsg)
				setIsRefreshing(false)
				setC4History(prev => [
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
			setC4ErrorMsg(message)
			setIsRefreshing(false)
			setC4History(prev => [
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
			: isMindmapMode
				? currentCode
					? 'No mindmap preview yet'
					: 'No mindmap available'
				: isGanttMode
					? currentCode
						? 'No Gantt preview yet'
						: 'No Gantt chart available'
					: isERDMode
						? currentCode
							? 'No ERD preview yet'
							: 'No ERD available'
						: isJsonMode
							? currentCode
								? 'No JSON preview yet'
								: 'No JSON diagram available'
							: currentCode
								? 'No UI mockup preview yet'
								: 'No UI mockup available'
		const altText = isUmlMode
			? 'UML Diagram Preview'
			: isMindmapMode
				? 'Mindmap Preview'
				: isGanttMode
					? 'Gantt Preview'
					: isERDMode
						? 'ERD Preview'
						: isJsonMode
							? 'JSON Preview'
							: 'UI Mockup Preview'
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
		const textToCopy = isUmlMode
			? umlCode
			: isMindmapMode
				? mindmapCode
				: isGanttMode
					? ganttCode
					: isERDMode
						? erdCode
						: isJsonMode
							? jsonCode
							: isC4Mode
								? c4Code
								: uiMockupCode
		setIsCopied(true)
		navigator.clipboard.writeText(textToCopy)
		setTimeout(() => {
			setIsCopied(false)
		}, 2000)
	}

	const handleDownload = async () => {
		const currentImage = isUmlMode
			? image
			: isMindmapMode
				? mindmapImage
				: isGanttMode
					? ganttImage
					: isERDMode
						? erdImage
						: isJsonMode
							? jsonImage
							: isC4Mode
								? c4Image
								: uiMockupImage
		const filePrefix = isUmlMode
			? 'uml'
			: isMindmapMode
				? 'mindmap'
				: isGanttMode
					? 'gantt'
					: isERDMode
						? 'erd'
						: isJsonMode
							? 'json'
							: isC4Mode
								? 'c4-diagram'
								: 'ui-mockup'
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
		const isC4Mode = activeMode === 'c4'
		const currentCode = isUmlMode
			? umlCode
			: isMindmapMode
				? mindmapCode
				: isGanttMode
					? ganttCode
					: isERDMode
						? erdCode
						: isJsonMode
							? jsonCode
							: isC4Mode
								? c4Code
								: uiMockupCode
		if (!currentCode.trim()) {
			return
		}
		setIsRefreshing(true)
		if (isUmlMode) {
			setErrorMsg(null)
			setErrorByType(prev => ({ ...prev, [diagramType]: null }))
		} else if (isMindmapMode) {
			setMindmapErrorMsg(null)
		} else if (isGanttMode) {
			setGanttErrorMsg(null)
		} else if (isERDMode) {
			setErdErrorMsg(null)
		} else if (isJsonMode) {
			setJsonErrorMsg(null)
		} else if (isC4Mode) {
			setC4ErrorMsg(null)
		} else {
			setUIMockupErrorMsg(null)
		}
		const renderAction =
			isUmlMode
				? renderUMLAction
				: isMindmapMode
					? renderMindmapAction
					: isGanttMode
						? renderGanttAction
						: isERDMode
							? renderERDAction
							: isJsonMode
								? renderJSONAction
								: isC4Mode
									? renderC4Action
									: renderUIMockupAction
		renderAction(currentCode)
			.then(result => {
				if (result.status === 'ok') {
					if (result.image_base64) {
						const nextImage = `data:image/png;base64,${result.image_base64}`
						if (isUmlMode) {
							setImage(nextImage)
							setImageByType(prev => ({ ...prev, [diagramType]: nextImage }))
							setErrorMsg(null)
							setErrorByType(prev => ({ ...prev, [diagramType]: null }))
						} else if (isMindmapMode) {
							setMindmapImage(nextImage)
							setMindmapErrorMsg(null)
						} else if (isGanttMode) {
							setGanttImage(nextImage)
							setGanttErrorMsg(null)
						} else if (isERDMode) {
							setErdImage(nextImage)
							setErdErrorMsg(null)
						} else if (isJsonMode) {
							setJsonImage(nextImage)
							setJsonErrorMsg(null)
						} else if (isC4Mode) {
							setC4Image(nextImage)
							setC4ErrorMsg(null)
						} else {
							setUIMockupImage(nextImage)
							setUIMockupErrorMsg(null)
						}
					} else {
						const failureMsg =
							isUmlMode
								? 'Diagram rendered without a preview image.'
								: isMindmapMode
									? 'Mindmap rendered without a preview image.'
									: isGanttMode
										? 'Gantt chart rendered without a preview image.'
									: isERDMode
										? 'ER diagram rendered without a preview image.'
										: isJsonMode
											? 'JSON diagram rendered without a preview image.'
											: isC4Mode
												? 'C4 diagram rendered without a preview image.'
												: 'UI mockup rendered without a preview image.'
						if (isUmlMode) {
							setImage('')
							setImageByType(prev => ({ ...prev, [diagramType]: '' }))
							setErrorMsg(failureMsg)
							setErrorByType(prev => ({ ...prev, [diagramType]: failureMsg }))
						} else if (isMindmapMode) {
							setMindmapImage('')
							setMindmapErrorMsg(failureMsg)
						} else if (isGanttMode) {
							setGanttImage('')
							setGanttErrorMsg(failureMsg)
						} else if (isERDMode) {
							setErdImage('')
							setErdErrorMsg(failureMsg)
						} else if (isJsonMode) {
							setJsonImage('')
							setJsonErrorMsg(failureMsg)
						} else if (isC4Mode) {
							setC4Image('')
							setC4ErrorMsg(failureMsg)
						} else {
							setUIMockupImage('')
							setUIMockupErrorMsg(failureMsg)
						}
					}
				} else {
					const failureMsg =
						result.message ||
						(isUmlMode
							? 'Failed to render UML diagram'
							: isMindmapMode
								? 'Failed to render mindmap'
							: isGanttMode
								? 'Failed to render Gantt chart'
							: isERDMode
								? 'Failed to render ER diagram'
								: isJsonMode
									? 'Failed to render JSON diagram'
									: isC4Mode
										? 'Failed to render C4 diagram'
										: 'Failed to render UI mockup')
					if (isUmlMode) {
						setErrorMsg(failureMsg)
						setErrorByType(prev => ({ ...prev, [diagramType]: failureMsg }))
					} else if (isMindmapMode) {
						setMindmapErrorMsg(failureMsg)
					} else if (isGanttMode) {
						setGanttErrorMsg(failureMsg)
					} else if (isERDMode) {
						setErdErrorMsg(failureMsg)
					} else if (isJsonMode) {
						setJsonErrorMsg(failureMsg)
					} else if (isC4Mode) {
						setC4ErrorMsg(failureMsg)
					} else {
						setUIMockupErrorMsg(failureMsg)
					}
				}
			})
			.catch(error => {
				const message =
					error instanceof Error
						? error.message || 'Failed to render diagram'
						: 'Failed to render diagram'
				if (isUmlMode) {
					setErrorMsg(message)
					setErrorByType(prev => ({ ...prev, [diagramType]: message }))
				} else if (isMindmapMode) {
					setMindmapErrorMsg(message)
				} else if (isGanttMode) {
					setGanttErrorMsg(message)
				} else if (isERDMode) {
					setErdErrorMsg(message)
				} else if (isJsonMode) {
					setJsonErrorMsg(message)
				} else if (isC4Mode) {
					setC4ErrorMsg(message)
				} else {
					setUIMockupErrorMsg(message)
				}
			})
			.finally(() => {
				setIsRefreshing(false)
			})
	}

	const isBusy = isGenerating || isRefreshing
	const isUmlMode = activeMode === 'uml'
	const isMindmapMode = activeMode === 'mindmap'
	const isGanttMode = activeMode === 'gantt'
	const isERDMode = activeMode === 'erd'
	const isJsonMode = activeMode === 'json'
	const isC4Mode = activeMode === 'c4'
	const currentCode = isUmlMode
		? umlCode
		: isMindmapMode
			? mindmapCode
			: isGanttMode
				? ganttCode
				: isERDMode
					? erdCode
					: isJsonMode
						? jsonCode
						: isC4Mode
							? c4Code
							: uiMockupCode
	const currentImage = isUmlMode
		? image
		: isMindmapMode
			? mindmapImage
			: isGanttMode
				? ganttImage
				: isERDMode
					? erdImage
					: isJsonMode
						? jsonImage
						: isC4Mode
							? c4Image
							: uiMockupImage
	const currentError = isUmlMode
		? errorMsg
		: isMindmapMode
			? mindmapErrorMsg
			: isGanttMode
				? ganttErrorMsg
				: isERDMode
					? erdErrorMsg
					: isJsonMode
						? jsonErrorMsg
						: isC4Mode
							? c4ErrorMsg
							: uiMockupErrorMsg
	const currentHistory = isUmlMode
		? chatHistory
		: isMindmapMode
			? mindmapHistory
			: isGanttMode
				? ganttHistory
				: isERDMode
					? erdHistory
					: isJsonMode
						? jsonHistory
						: isC4Mode
							? c4History
							: uiMockupHistory
	const editorTitle = isUmlMode
		? 'PlantUML Code'
		: isMindmapMode
			? 'Mindmap Code'
			: isGanttMode
				? 'Gantt Code'
				: isERDMode
					? 'ERD Code'
					: isJsonMode
						? 'JSON Code'
						: isC4Mode
							? 'C4 Diagram Code'
							: 'SALT Mockup Code'
	const syntaxLabel = isUmlMode
		? 'PlantUML'
		: isMindmapMode
			? 'PlantUML Mindmap'
			: isGanttMode
				? 'PlantUML Gantt'
				: isERDMode
					? 'PlantUML ERD'
					: isJsonMode
						? 'PlantUML JSON'
						: isC4Mode
							? 'PlantUML C4'
							: 'PlantUML SALT'
	const assistantTitle = isUmlMode
		? 'UML Chat Assistant'
		: isMindmapMode
			? 'Mindmap Assistant'
			: isGanttMode
				? 'Gantt Assistant'
				: isERDMode
					? 'ERD Assistant'
					: isJsonMode
						? 'JSON Assistant'
						: isC4Mode
							? 'C4 Diagram Assistant'
							: 'UI Mockup Assistant'
	const emptyChatMessage = isUmlMode
		? 'No messages yet. Describe a system or ask for a change to get started.'
		: isMindmapMode
			? 'No messages yet. Describe a topic or ask for a change to get started.'
			: isGanttMode
				? 'No messages yet. Describe a schedule or ask for a change to get started.'
				: isERDMode
					? 'No messages yet. Describe a data model or ask for a change to get started.'
					: isJsonMode
						? 'No messages yet. Describe JSON or ask for a change to get started.'
						: isC4Mode
							? 'No messages yet. Describe your system architecture or ask for a change to get started.'
							: 'No messages yet. Describe a screen or ask for a change to get started.'
	const tips = isUmlMode
		? [
				'Switch templates to explore available UML diagram types',
				'Select the diagram you need',
				'When revising, refer to existing elements',
				'Fine-tune the PlantUML code directly in the editor',
				'Refresh the page to wipe memory',
				'Save prompts elsewhere in early adoption',
			]
		: isMindmapMode
			? [
					'Describe the central topic first, then expand outward',
					'Use short, clear node labels',
					'Ask to group related branches together',
					'Refine by adding or removing sub-branches',
					'Fine-tune the mindmap code directly in the editor',
					'Refresh the page to wipe memory',
				]
			: isGanttMode
				? [
						'List tasks with dates or durations',
						'Call out dependencies explicitly',
						'Include milestones for key events',
						'Keep task names short and clear',
						'Fine-tune the Gantt code directly in the editor',
						'Refresh the page to wipe memory',
					]
				: isERDMode
					? [
							'List entities and their attributes',
							'Mark primary keys and foreign keys',
							'Include cardinalities on relationships',
							'Keep attribute names short and clear',
							'Fine-tune the ERD code directly in the editor',
							'Refresh the page to wipe memory',
						]
					: isJsonMode
						? [
								'Paste valid JSON or describe the schema',
								'Keep keys concise and consistent',
								'Include nested objects and arrays as needed',
								'Validate the JSON structure if something looks off',
								'Fine-tune the JSON code directly in the editor',
								'Refresh the page to wipe memory',
							]
						: isC4Mode
							? [
									'Specify the C4 level: Context, Container, Component, or Code',
									'Describe systems, containers, and their relationships',
									'Include technology labels for containers and components',
									'Use boundaries to group related elements',
									'Fine-tune the C4 code directly in the editor',
									'Refresh the page to wipe memory',
								]
					: [
							'Describe the primary screen and its sections',
							'Call out forms, buttons, lists, and menus',
							'Group related UI elements into panels',
							'Refine labels and hierarchy for clarity',
						'Fine-tune the SALT code directly in the editor',
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
								<TabsTrigger value="ui-mockup">UI Mockups</TabsTrigger>
								<TabsTrigger value="gantt">Gantt</TabsTrigger>
								<TabsTrigger value="erd">ERD</TabsTrigger>
								<TabsTrigger value="json">JSON</TabsTrigger>
								<TabsTrigger value="c4">C4 Diagram</TabsTrigger>
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
									) : isMindmapMode ? (
										<div>
											<h3 className="text-lg font-medium mb-2 flex items-center gap-2">
												<LayoutTemplate className="h-4 w-4 text-primary" />
												Mindmap Mode
											</h3>
											<p className="text-sm text-muted-foreground">
												Describe a topic and the assistant will expand it into a structured mindmap.
											</p>
										</div>
									) : isGanttMode ? (
										<div>
											<h3 className="text-lg font-medium mb-2 flex items-center gap-2">
												<LayoutTemplate className="h-4 w-4 text-primary" />
												Gantt Mode
											</h3>
											<p className="text-sm text-muted-foreground">
												Describe tasks, durations, and dependencies to build a Gantt chart.
											</p>
										</div>
									) : isERDMode ? (
										<div>
											<h3 className="text-lg font-medium mb-2 flex items-center gap-2">
												<LayoutTemplate className="h-4 w-4 text-primary" />
												ERD Mode
											</h3>
											<p className="text-sm text-muted-foreground">
												Describe entities, attributes, and relationships to build an ER diagram.
											</p>
										</div>
									) : isJsonMode ? (
										<div>
											<h3 className="text-lg font-medium mb-2 flex items-center gap-2">
												<LayoutTemplate className="h-4 w-4 text-primary" />
												JSON Mode
											</h3>
											<p className="text-sm text-muted-foreground">
												Describe or paste JSON to visualize it as a PlantUML JSON diagram.
											</p>
										</div>
									) : isC4Mode ? (
										<div>
											<h3 className="text-lg font-medium mb-2 flex items-center gap-2">
												<LayoutTemplate className="h-4 w-4 text-primary" />
												C4 Diagram Mode
											</h3>
											<p className="text-sm text-muted-foreground">
												Describe your system architecture. Specify the C4 level (Context, Container, Component, or Code) in your description for best results.
											</p>
											<div className="mt-3 p-3 bg-muted/50 rounded-md">
												<p className="text-xs font-medium mb-1">C4 Levels:</p>
												<ul className="text-xs text-muted-foreground space-y-1">
													<li>&bull; <strong>Context</strong>: System in its environment</li>
													<li>&bull; <strong>Container</strong>: High-level tech building blocks</li>
													<li>&bull; <strong>Component</strong>: Components within containers</li>
													<li>&bull; <strong>Code</strong>: Implementation details</li>
												</ul>
											</div>
										</div>
									) : (
										<div>
											<h3 className="text-lg font-medium mb-2 flex items-center gap-2">
												<LayoutTemplate className="h-4 w-4 text-primary" />
												UI Mockup Mode
											</h3>
											<p className="text-sm text-muted-foreground">
												Describe the interface and the assistant will draft a SALT UI mockup.
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
														: isMindmapMode
															? 'Describe a mindmap or request a change (Shift+Enter for new line)...'
															: isGanttMode
																? 'Describe a Gantt chart or request a change (Shift+Enter for new line)...'
																: isERDMode
																	? 'Describe an ER diagram or request a change (Shift+Enter for new line)...'
																	: isJsonMode
																		? 'Describe JSON or request a change (Shift+Enter for new line)...'
																		: 'Describe a UI mockup or request a change (Shift+Enter for new line)...'
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
												{isUmlMode
													? 'Update Diagram'
													: isMindmapMode
														? 'Update Mindmap'
														: isGanttMode
															? 'Update Gantt'
															: isERDMode
																? 'Update ERD'
																: isJsonMode
																	? 'Update JSON'
																	: isC4Mode
																		? 'Update C4'
																		: 'Update Mockup'}
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
																: isMindmapMode
																	? setMindmapCode(e.target.value)
																	: isGanttMode
																		? setGanttCode(e.target.value)
																		: isERDMode
																			? setErdCode(e.target.value)
																			: isJsonMode
																				? setJsonCode(e.target.value)
																				: isC4Mode
																					? setC4Code(e.target.value)
																					: setUIMockupCode(e.target.value)
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
														{isUmlMode
															? 'Diagram Preview'
															: isMindmapMode
																? 'Mindmap Preview'
																: isGanttMode
																	? 'Gantt Preview'
																	: isERDMode
																		? 'ERD Preview'
																		: isJsonMode
																			? 'JSON Preview'
																			: 'UI Mockup Preview'}
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
																: isMindmapMode
																	? setMindmapCode(e.target.value)
																	: isGanttMode
																		? setGanttCode(e.target.value)
																		: isERDMode
																			? setErdCode(e.target.value)
																			: isJsonMode
																				? setJsonCode(e.target.value)
																				: isC4Mode
																					? setC4Code(e.target.value)
																					: setUIMockupCode(e.target.value)
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
														{isUmlMode
															? 'Diagram Preview'
															: isMindmapMode
																? 'Mindmap Preview'
																: isGanttMode
																	? 'Gantt Preview'
																	: isERDMode
																		? 'ERD Preview'
																		: isJsonMode
																			? 'JSON Preview'
																			: 'UI Mockup Preview'}
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
