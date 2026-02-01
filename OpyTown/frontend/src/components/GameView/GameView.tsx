import React, { useRef, useEffect, useState, useCallback } from "react"
import { PatternType, PATTERNS } from "@/utils/patternUtils"
import { GameLoop } from "./engine/GameLoop"
import { InputManager } from "./engine/InputManager"
import { Renderer } from "./engine/Renderer"
import { AssetManager } from "./engine/AssetManager"
import { TileMap } from "./engine/TileMap"
import { Player } from "./engine/Player"
import { Camera } from "./engine/Camera"
import { NPC } from "./engine/NPC"
import { InWorldUI } from "./ui/InWorldUI"

interface GameViewProps {
    selectedPattern: PatternType
    onPatternChange: (pattern: PatternType) => void
}

const GameView: React.FC<GameViewProps> = ({
    selectedPattern,
    onPatternChange,
}) => {
    const containerRef = useRef<HTMLDivElement>(null)
    const canvasRef = useRef<HTMLCanvasElement>(null)

    // Game State Refs (mutable, not causing re-renders)
    const loopRef = useRef<GameLoop | null>(null)
    const inputRef = useRef<InputManager | null>(null)
    const rendererRef = useRef<Renderer | null>(null)
    const assetsRef = useRef<AssetManager | null>(null)
    const mapRef = useRef<TileMap | null>(null)
    const playerRef = useRef<Player | null>(null)
    const cameraRef = useRef<Camera | null>(null)
    const npcsRef = useRef<NPC[]>([])

    // UI State
    const [nearbyNPC, setNearbyNPC] = useState<NPC | null>(null)
    const [isInteracting, setIsInteractingState] = useState(false)
    const [activeNPC, setActiveNPC] = useState<NPC | null>(null) // The NPC currently being chatted with

    // State Refs for Loop access
    const nearbyNPCRef = useRef<NPC | null>(null)
    const isInteractingRef = useRef(false)

    // Find Supervisor NPC (for T key broadcast)
    const getSupervisorNPC = useCallback((): NPC | null => {
        return npcsRef.current.find(npc => npc.def.id === "supervisor") || null
    }, [])

    const setInteracting = (interacting: boolean, npc?: NPC | null) => {
        isInteractingRef.current = interacting
        setIsInteractingState(interacting)

        // Update NPC chat state
        if (interacting && npc) {
            npc.startChat()
            setActiveNPC(npc)
        } else if (!interacting && activeNPC) {
            activeNPC.endChat()
            setActiveNPC(null)
        }
    }

    // T key handler for broadcast messaging
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // T key for broadcast (global chat to Supervisor)
            if (e.code === "KeyT" && !isInteractingRef.current) {
                const supervisor = getSupervisorNPC()
                if (supervisor) {
                    setInteracting(true, supervisor)
                }
            }
        }

        window.addEventListener("keydown", handleKeyDown)
        return () => window.removeEventListener("keydown", handleKeyDown)
    }, [getSupervisorNPC])

    useEffect(() => {
        if (!canvasRef.current || !containerRef.current) return

        // Initialize Engine
        inputRef.current = new InputManager()

        // World setup - uses CollisionMap data
        mapRef.current = new TileMap()

        // Player setup at spawn point (near farm area for easy access)
        playerRef.current = new Player(192, 320)

        // Camera setup with world dimensions from map
        cameraRef.current = new Camera(
            containerRef.current.clientWidth,
            containerRef.current.clientHeight,
            mapRef.current.worldWidth,
            mapRef.current.worldHeight
        )

        // NPC setup - Coffee buying workflow
        // Only Supervisor is needed (interactable)
        // Farm labels will be rendered as text on the background
        const npcSpawns = [
            { id: "supervisor", name: "Coffee Buyer", pattern: PATTERNS.PUBLISH_SUBSCRIBE, x: 378, y: 256, spriteKey: "npc_supervisor" },
        ]

        npcsRef.current = npcSpawns
            .filter(spawn => mapRef.current?.isWalkable(spawn.x, spawn.y))
            .map(spawn => new NPC(spawn))

        // Renderer setup
        const ctx = canvasRef.current.getContext("2d")
        if (ctx) {
            // Disable smoothing for pixel art look
            ctx.imageSmoothingEnabled = false
            rendererRef.current = new Renderer(
                ctx,
                containerRef.current.clientWidth,
                containerRef.current.clientHeight
            )
        }

        // Loop
        loopRef.current = new GameLoop((dt) => {
            if (!inputRef.current || !playerRef.current || !mapRef.current || !rendererRef.current || !cameraRef.current) return

            // Update Physics only if not interacting
            if (!isInteractingRef.current) {
                playerRef.current.update(dt, inputRef.current, mapRef.current)
            }
            cameraRef.current.follow(playerRef.current.x, playerRef.current.y)

            // Proximity Check
            let closest: NPC | null = null
            let minDist = 80 // Interaction radius

            for (const npc of npcsRef.current) {
                const dist = Math.sqrt(
                    Math.pow(playerRef.current.x - npc.def.x, 2) +
                    Math.pow(playerRef.current.y - npc.def.y, 2)
                )
                if (dist < minDist) {
                    closest = npc
                    minDist = dist
                }
            }

            // Update React state safely (check if changed)
            if (closest !== nearbyNPCRef.current) {
                nearbyNPCRef.current = closest
                setNearbyNPC(closest)
            }

            // Interaction Trigger (E key)
            if (closest && inputRef.current.isKeyDown("KeyE") && !isInteractingRef.current) {
                setInteracting(true, closest)
            }

            // Escape to cancel
            if (isInteractingRef.current && inputRef.current.isKeyDown("Escape")) {
                setInteracting(false)
            }

            // Render
            rendererRef.current.clear()
            rendererRef.current.render(
                mapRef.current,
                playerRef.current,
                npcsRef.current,
                cameraRef.current,
                assetsRef.current || undefined
            )
        })

        // Load assets
        assetsRef.current = new AssetManager()
        assetsRef.current.loadAll().catch(err => console.error("Failed to load assets", err))

        loopRef.current.start()

        const handleResize = () => {
            if (containerRef.current && canvasRef.current && rendererRef.current && cameraRef.current) {
                const w = containerRef.current.clientWidth
                const h = containerRef.current.clientHeight
                
                // Set canvas size attributes
                canvasRef.current.width = w
                canvasRef.current.height = h
                
                // Update renderer and camera
                rendererRef.current.setSize(w, h)
                cameraRef.current.resize(w, h)

                // Re-disable smoothing after resize might reset context
                const ctx = canvasRef.current.getContext("2d")
                if (ctx) ctx.imageSmoothingEnabled = false
            }
        }

        // Use ResizeObserver for better container size tracking
        const resizeObserver = new ResizeObserver(() => {
            handleResize()
        })

        if (containerRef.current) {
            resizeObserver.observe(containerRef.current)
        }

        // Also listen to window resize as fallback
        window.addEventListener("resize", handleResize)
        
        // Initial resize to fit
        handleResize()

        return () => {
            loopRef.current?.stop()
            inputRef.current?.destroy()
            resizeObserver.disconnect()
            window.removeEventListener("resize", handleResize)
        }
    }, []) // Empty dependency array ensures this effect runs only once

    const handleCloseUI = useCallback(() => {
        setInteracting(false)
    }, [])

    return (
        <div ref={containerRef} className="h-full w-full overflow-hidden bg-black relative" style={{ minHeight: 0 }}>
            <canvas
                ref={canvasRef}
                className="block w-full h-full"
                style={{ imageRendering: "pixelated", display: "block" }}
            />
            {/* UI Overlay Layer */}
            <div className="absolute top-4 left-4 text-white pointer-events-none opacity-70 font-mono text-sm bg-black/50 p-2 rounded">
                <p>WASD: Move</p>
                <p>E: Interact (near NPC)</p>
                <p>T: Talk to Buyer</p>
                <p>Esc: Close</p>
            </div>

            {/* Interaction Hint */}
            {nearbyNPC && !isInteracting && (
                <div
                    className="absolute text-white bg-black/80 px-3 py-2 rounded border border-green-500/50 transform -translate-x-1/2 pointer-events-none text-sm font-mono shadow-lg"
                    style={{
                        left: "50%",
                        bottom: "15%"
                    }}
                >
                    Press <span className="text-green-400 font-bold">E</span> to talk to {nearbyNPC.def.name}
                </div>
            )}

            {/* Interaction Panel */}
            {isInteracting && activeNPC && (
                <InWorldUI
                    npc={activeNPC}
                    onClose={handleCloseUI}
                />
            )}
        </div>
    )
}

export default GameView
