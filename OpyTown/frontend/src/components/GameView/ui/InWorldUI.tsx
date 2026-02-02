import React, { useState, useEffect, useRef } from "react"
import { NPC } from "../engine/NPC"
import { useAgentAPI } from "@/hooks/useAgentAPI"
import {
    useStreamingStatus,
    useStreamingEvents,
    useStreamingError,
    useStreamingActions,
} from "@/stores/auctionStreamingStore"
import {
    useStartGroupStreaming,
    useGroupStreamingActions,
    useGroupIsStreaming,
    useGroupFinalResponse,
    useGroupError
} from "@/stores/groupStreamingStore"
import { PATTERNS, getPatternDisplayName } from "@/utils/patternUtils"

interface InWorldUIProps {
    npc: NPC
    onClose: () => void
}

interface SuggestedPrompt {
    prompt: string
    description?: string
}

const DEFAULT_EXCHANGE_APP_API_URL = "http://127.0.0.1:8000"
const EXCHANGE_APP_API_URL =
    import.meta.env.VITE_EXCHANGE_APP_API_URL || DEFAULT_EXCHANGE_APP_API_URL

export const InWorldUI: React.FC<InWorldUIProps> = ({ npc, onClose }) => {
    const [input, setInput] = useState("")
    const [messages, setMessages] = useState<{ role: "user" | "agent", content: string }[]>([])
    const [suggestedPrompts, setSuggestedPrompts] = useState<SuggestedPrompt[]>([])
    const [isLoadingPrompts, setIsLoadingPrompts] = useState(true)
    const [showPrompts, setShowPrompts] = useState(true)
    const [pendingAgentResponse, setPendingAgentResponse] = useState(false)

    // Hooks
    const { sendMessage, loading: agentLoading } = useAgentAPI()

    // Streaming Hooks (Group Comm)
    const startStreaming = useStartGroupStreaming()
    const { reset: resetGroup } = useGroupStreamingActions()
    const isGroupStreaming = useGroupIsStreaming()
    const groupFinal = useGroupFinalResponse()
    const groupError = useGroupError()

    // Auction Streaming Hooks (Publish/Subscribe Streaming)
    const { connect, reset: resetAuction } = useStreamingActions()
    const auctionStatus = useStreamingStatus()
    const auctionEvents = useStreamingEvents()
    const auctionError = useStreamingError()

    const scrollRef = useRef<HTMLDivElement>(null)
    const processedEventsRef = useRef<Set<string>>(new Set())

    // Fetch suggested prompts
    useEffect(() => {
        const controller = new AbortController()

        const fetchPrompts = async () => {
            try {
                setIsLoadingPrompts(true)
                const isStreamingPattern = npc.def.pattern === PATTERNS.PUBLISH_SUBSCRIBE_STREAMING
                const url = isStreamingPattern
                    ? `${EXCHANGE_APP_API_URL}/suggested-prompts?pattern=streaming`
                    : `${EXCHANGE_APP_API_URL}/suggested-prompts`

                const res = await fetch(url, {
                    cache: "no-cache",
                    signal: controller.signal,
                })

                if (!res.ok) throw new Error(`HTTP ${res.status}`)

                const data = await res.json()

                // Flatten all prompts from categories
                const allPrompts: SuggestedPrompt[] = []
                Object.values(data).forEach((category: any) => {
                    if (Array.isArray(category)) {
                        allPrompts.push(...category)
                    }
                })

                setSuggestedPrompts(allPrompts.slice(0, 5)) // Take first 5
                setIsLoadingPrompts(false)
            } catch (err: any) {
                if (err.name !== "AbortError") {
                    console.warn("Failed to load prompts", err)
                    setIsLoadingPrompts(false)
                }
            }
        }

        fetchPrompts()

        return () => controller.abort()
    }, [npc.def.pattern])

    // Reset stores on open
    useEffect(() => {
        if (npc.def.pattern === PATTERNS.GROUP_COMMUNICATION) {
            resetGroup()
        } else if (npc.def.pattern === PATTERNS.PUBLISH_SUBSCRIBE_STREAMING) {
            resetAuction()
        }
        // Clear processed events on new conversation
        processedEventsRef.current.clear()
    }, [npc, resetGroup, resetAuction])

    // Watch for Group Streaming updates
    useEffect(() => {
        if (npc.def.pattern === PATTERNS.GROUP_COMMUNICATION) {
            if (groupFinal && pendingAgentResponse) {
                setMessages(prev => [...prev, { role: "agent", content: groupFinal }])
                setPendingAgentResponse(false)
            } else if (groupError && pendingAgentResponse) {
                setMessages(prev => [...prev, { role: "agent", content: `Error: ${groupError}` }])
                setPendingAgentResponse(false)
            }
        }
    }, [groupFinal, groupError, npc.def.pattern, pendingAgentResponse])

    // Watch for Auction Streaming events
    useEffect(() => {
        if (npc.def.pattern === PATTERNS.PUBLISH_SUBSCRIBE_STREAMING) {
            // Process new events
            for (const event of auctionEvents) {
                const eventKey = event.response
                if (eventKey && !processedEventsRef.current.has(eventKey)) {
                    processedEventsRef.current.add(eventKey)
                    setMessages(prev => [...prev, { role: "agent", content: event.response }])
                }
            }

            if (auctionError && pendingAgentResponse) {
                setMessages(prev => [...prev, { role: "agent", content: `Error: ${auctionError}` }])
                setPendingAgentResponse(false)
            }

            if (auctionStatus === "completed") {
                setPendingAgentResponse(false)
            }
        }
    }, [auctionEvents, auctionError, auctionStatus, npc.def.pattern, pendingAgentResponse])

    const handleSend = async (query?: string) => {
        const userMsg = query || input
        if (!userMsg.trim()) return

        setInput("")
        setShowPrompts(false) // Hide prompts after first message
        setMessages(prev => [...prev, { role: "user", content: userMsg }])
        setPendingAgentResponse(true)

        try {
            if (npc.def.pattern === PATTERNS.GROUP_COMMUNICATION) {
                // Group Communication Streaming
                resetGroup()
                await startStreaming(userMsg)
            } else if (npc.def.pattern === PATTERNS.PUBLISH_SUBSCRIBE_STREAMING) {
                // Auction Streaming
                processedEventsRef.current.clear()
                resetAuction()
                await connect(userMsg)
            } else {
                // Standard Request/Response (PUBLISH_SUBSCRIBE, SLIM_A2A)
                // This is what the old UI does for coffee buying prompts
                const res = await sendMessage(userMsg, npc.def.pattern)
                setMessages(prev => [...prev, { role: "agent", content: res.response }])
                setPendingAgentResponse(false)
            }
        } catch (e: any) {
            console.error("Agent API error:", e)
            setMessages(prev => [...prev, { role: "agent", content: `Error: ${e.message}` }])
            setPendingAgentResponse(false)
        }
    }

    // Auto-scroll
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight
        }
    }, [messages])

    const isLoading = pendingAgentResponse || agentLoading ||
        (npc.def.pattern === PATTERNS.GROUP_COMMUNICATION && isGroupStreaming) ||
        (npc.def.pattern === PATTERNS.PUBLISH_SUBSCRIBE_STREAMING && auctionStatus === "streaming")

    return (
        <div className="absolute inset-0 flex items-center justify-center bg-black/40 backdrop-blur-sm z-50 p-4 animate-fade-in">
            <div className="bg-gray-900/80 backdrop-blur-xl w-full max-w-2xl rounded-2xl border border-white/10 shadow-2xl flex flex-col h-[80vh] overflow-hidden ring-1 ring-white/5">
                {/* Header */}
                <div className="flex justify-between items-center px-6 py-4 border-b border-white/5 bg-white/5">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-700 flex items-center justify-center text-white font-bold text-lg shadow-lg">
                            {npc.def.name.charAt(0)}
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-white leading-tight">{npc.def.name}</h2>
                            <span className="text-xs font-medium text-green-400 uppercase tracking-wider">{getPatternDisplayName(npc.def.pattern)}</span>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-white hover:bg-white/10 rounded-full p-2 transition-all duration-200"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                {/* Suggested Prompts Header - appearing when relevant */}
                {showPrompts && messages.length === 0 && (
                    <div className="px-6 py-3 bg-gray-800/30 border-b border-white/5">
                        <div className="flex items-center justify-between mb-2">
                            <p className="text-xs font-bold text-gray-400 uppercase tracking-wider">Suggested Topics</p>
                        </div>
                        {isLoadingPrompts ? (
                            <div className="flex gap-2">
                                <div className="h-8 w-24 bg-white/5 rounded animate-pulse"></div>
                                <div className="h-8 w-32 bg-white/5 rounded animate-pulse"></div>
                                <div className="h-8 w-20 bg-white/5 rounded animate-pulse"></div>
                            </div>
                        ) : suggestedPrompts.length > 0 ? (
                            <div className="flex flex-wrap gap-2">
                                {suggestedPrompts.map((prompt, i) => (
                                    <button
                                        key={i}
                                        onClick={() => handleSend(prompt.prompt)}
                                        className="text-xs font-medium bg-white/5 hover:bg-green-500/20 hover:text-green-300 hover:border-green-500/30 text-gray-300 px-3 py-1.5 rounded-full border border-white/10 transition-all duration-200 truncate max-w-[250px]"
                                        title={prompt.prompt}
                                    >
                                        {prompt.prompt}
                                    </button>
                                ))}
                            </div>
                        ) : (
                            <div className="text-gray-500 text-xs italic">No suggestions available</div>
                        )}
                    </div>
                )}

                {/* Chat Area */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent" ref={scrollRef}>
                    {messages.length === 0 && (
                        <div className="h-full flex flex-col items-center justify-center text-gray-500 space-y-4 opacity-60">
                            <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center">
                                <span className="text-3xl">💬</span>
                            </div>
                            <p className="text-sm font-medium">Start a conversation with {npc.def.name}...</p>
                        </div>
                    )}
                    {messages.map((msg, i) => (
                        <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-slide-up`}>
                            <div className={`max-w-[80%] rounded-2xl px-5 py-3 text-sm leading-relaxed shadow-md ${msg.role === "user"
                                ? "bg-gradient-to-br from-green-600 to-emerald-700 text-white rounded-br-none"
                                : "bg-gray-800 text-gray-100 border border-white/5 rounded-bl-none"
                                }`}>
                                {msg.content}
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="flex justify-start">
                            <div className="bg-gray-800 border border-white/5 rounded-2xl rounded-bl-none px-4 py-3 flex items-center gap-1.5 shadow-md">
                                <span className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                                <span className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                                <span className="w-2 h-2 bg-green-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                            </div>
                        </div>
                    )}
                </div>

                {/* Input Area */}
                <div className="p-4 bg-gray-900/90 border-t border-white/10 backdrop-blur">
                    <div className="flex gap-3 relative">
                        <input
                            type="text"
                            className="flex-1 bg-black/40 border border-white/10 rounded-xl pl-4 pr-12 py-3 text-white focus:outline-none focus:ring-2 focus:ring-green-500/50 focus:border-green-500/50 text-sm placeholder-gray-500 transition-all shadow-inner"
                            placeholder={`Message ${npc.def.name}...`}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && !isLoading && handleSend()}
                            disabled={isLoading}
                            autoFocus
                        />
                        <button
                            className={`absolute right-2 top-1.5 bottom-1.5 px-4 rounded-lg text-sm font-bold transition-all duration-200 flex items-center justify-center ${isLoading || !input.trim()
                                ? "text-gray-600 cursor-not-allowed bg-transparent"
                                : "bg-green-600 hover:bg-green-500 text-white shadow-lg shadow-green-900/20"
                                }`}
                            onClick={() => handleSend()}
                            disabled={isLoading || !input.trim()}
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 transform rotate-90" viewBox="0 0 20 20" fill="currentColor">
                                <path d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z" />
                            </svg>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
