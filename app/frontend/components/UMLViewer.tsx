'use client'

import Image from 'next/image'
import { RefreshCw, RotateCw, ZoomIn, ZoomOut } from 'lucide-react'
import { TransformComponent, TransformWrapper } from 'react-zoom-pan-pinch'

type UMLViewerProps = {
	umlCode: string
	isGenerating: boolean
	imageUrl?: string
}

const UMLViewer = ({ umlCode, isGenerating, imageUrl }: UMLViewerProps) => {
	const previewSrc = imageUrl

	try {
		return (
			<div className="flex flex-col items-center justify-center h-full max-h-full bg-muted/30 rounded-md p-4 cursor-grab w-full">
				{isGenerating ? (
					<div className="flex flex-col items-center gap-2">
						<RefreshCw className="animate-spin h-8 w-8" />
						<p>Generating diagram...</p>
					</div>
				) : (
					<TransformWrapper
						smooth
						initialScale={0.8}
						minScale={0.2}
						maxScale={4}
						centerOnInit
					>
						{({ zoomIn, zoomOut, resetTransform, centerView }) => (
							<>
								{/* Controls */}
								<div className="flex gap-2 mb-2 self-end">
									<button
										onClick={() => zoomIn()}
										className="p-2 bg-secondary text-secondary-foreground rounded-md"
									>
										<ZoomIn />
									</button>
									<button
										onClick={() => zoomOut()}
										className="p-2 bg-secondary text-secondary-foreground rounded-md"
									>
										<ZoomOut />
									</button>
									<button
										onClick={() => {
											resetTransform()
											centerView(0.8)
										}}
										className="p-2 bg-secondary text-secondary-foreground rounded-md"
									>
										<RotateCw />
									</button>
								</div>

								{/* Image with Zoom & Pan */}
								<TransformComponent wrapperClass="w-full h-full">
									<div className="w-full h-full max-h-[60vh] overflow-hidden flex items-center justify-center">
										{previewSrc ? (
											<Image
												src={previewSrc}
												alt="UML Diagram Preview"
												width={1600}
												height={1200}
												className="w-full h-full object-contain"
												sizes="100vw"
												priority
												unoptimized
											/>
										) : (
											<p>{umlCode ? 'No preview yet' : 'No diagram available'}</p>
										)}
									</div>
								</TransformComponent>
							</>
						)}
					</TransformWrapper>
				)}
			</div>
		)
	} catch (error) {
		console.error('Error rendering UML:', error)
		return (
			<div className="flex items-center justify-center h-full bg-muted/30 rounded-md p-4">
				<div className="text-center text-muted-foreground">
					<p>Error generating diagram</p>
				</div>
			</div>
		)
	}
}

export default UMLViewer
