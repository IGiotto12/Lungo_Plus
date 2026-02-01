import { PatternType } from "@/utils/patternUtils"

export interface NPCDefinition {
    id: string
    name: string
    pattern: PatternType // Agent pattern to trigger
    x: number // World coordinates
    y: number
    spriteKey?: string
}

export class NPC {
    def: NPCDefinition
    // Display size: 112×112 (2x scale of 56×56 source image to match player size)
    // Player model: 100×70 pixels display size
    width: number = 112   // Display width (2x scaled from 56px source)
    height: number = 112  // Display height (2x scaled from 56px source)

    // Chat state
    isChatting: boolean = false

    constructor(def: NPCDefinition) {
        this.def = def
    }

    startChat() {
        this.isChatting = true
    }

    endChat() {
        this.isChatting = false
    }
}
