import { useEffect, useId, useRef, useState, type CSSProperties } from "react"
import { motion } from "framer-motion"
import { addPropertyControls, ControlType, RenderTarget } from "framer"

/**
 * DIFF BEAM — one prompt, everything that follows.
 * Adapted from the Magic UI AnimatedBeam port (hub & spoke).
 * Replaces the AI-tool logo hub in "How it works" card 2: the centre is the new
 * version created by a prompt; beams flow out to the six things it rebuilds
 * (CAD, BOM, cost, DFM, certifications, factories), and each chip lights up when its beam arrives.
 * Text chips only: no third-party logos. Defaults follow mvp/docs/BRAND.md after W26
 * (borderless chips on paper-2, lit = accent-soft + accent-ink, centre radius 12).
 * Place it on a white or paper (#F7F6F3) card: on a paper-2 card the chips blend in.
 *
 * @framerSupportedLayoutWidth any-prefer-fixed
 * @framerSupportedLayoutHeight any-prefer-fixed
 * @framerIntrinsicWidth 384
 * @framerIntrinsicHeight 410
 */

interface NodeItem {
    label?: string
    image?: string
}

interface Props {
    padding: number
    gap: number
    nodeHeight: number
    centerSize: number
    centerLabel: string
    centerCaption: string
    centerImage?: string
    leftNodes: NodeItem[]
    rightNodes: NodeItem[]
    labelFont: CSSProperties
    centerFont: CSSProperties
    captionFont: CSSProperties
    nodeBackground: string
    nodeBorderColor: string
    nodeTextColor: string
    nodeBorderWidth: number
    nodeRadius: number
    centerBackground: string
    centerTextColor: string
    captionColor: string
    highlight: boolean
    highlightBackground: string
    highlightBorder: string
    highlightText: string
    pathColor: string
    pathWidth: number
    pathOpacity: number
    gradientStartColor: string
    gradientStopColor: string
    curvature: number
    endYOffset: number
    duration: number
    delay: number
    stagger: number
    repeatDelay: number
    speedVariation: number
    easing: string
    outward: boolean
    style?: CSSProperties
}

interface Beam {
    d: string
    reverse: boolean
    delay: number
    duration: number
    // Fraction of the sweep at which the beam reaches its chip (outward flow only).
    arrival: number
    side: "l" | "r"
    index: number
}

const SANS = '"Inter Tight", Inter, system-ui, sans-serif'
const MONO = '"Geist Mono", ui-monospace, SFMono-Regular, Menlo, monospace'

// What one refine prompt rebuilds (PRD §8.2, the diff chips).
const defaultLeft: NodeItem[] = [{ label: "CAD" }, { label: "BOM" }, { label: "Cost" }]
const defaultRight: NodeItem[] = [{ label: "DFM" }, { label: "Certs" }, { label: "Factories" }]

export default function DiffBeam(props: Props) {
    const {
        padding = 24,
        gap = 20,
        nodeHeight = 32,
        centerSize = 72,
        centerLabel = "v2",
        centerCaption = "“Add SpO2 and skin-temperature sensing”",
        centerImage,
        leftNodes = defaultLeft,
        rightNodes = defaultRight,
        labelFont,
        centerFont,
        captionFont,
        nodeBackground = "rgba(239, 237, 232, 0.8)",
        nodeBorderColor = "rgba(0, 0, 0, 0)",
        nodeTextColor = "#5F5E5A",
        nodeBorderWidth = 0,
        nodeRadius = 999,
        centerBackground = "#111111",
        centerTextColor = "#FFFFFF",
        captionColor = "#5F5E5A",
        highlight = true,
        highlightBackground = "#FFF1EA",
        highlightBorder = "rgba(0, 0, 0, 0)",
        highlightText = "#C43C00",
        pathColor = "#111111",
        pathWidth = 1.5,
        pathOpacity = 0.12,
        gradientStartColor = "#FF4F00",
        gradientStopColor = "#FF6A26",
        curvature = 60,
        endYOffset = 0,
        duration = 3,
        delay = 0,
        stagger = 0.25,
        repeatDelay = 1.5,
        speedVariation = 0,
        easing = "linear",
        outward = true,
        style,
    } = props

    // useId() returns ":r0:"-style ids; colons break url(#id) references, so strip them.
    const uid = useId().replace(/[^a-zA-Z0-9_-]/g, "")
    const containerRef = useRef<HTMLDivElement>(null)
    const centerRef = useRef<HTMLDivElement>(null)
    const leftRefs = useRef<(HTMLDivElement | null)[]>([])
    const rightRefs = useRef<(HTMLDivElement | null)[]>([])

    const [svg, setSvg] = useState({ width: 0, height: 0 })
    const [beams, setBeams] = useState<Beam[]>([])

    const isThumbnail = RenderTarget.current() === RenderTarget.thumbnail

    const easeMap: Record<string, any> = {
        linear: "linear",
        easeOut: "easeOut",
        easeInOut: "easeInOut",
        expo: [0.16, 1, 0.3, 1],
    }
    const resolvedEase = easeMap[easing] ?? "linear"

    const leftKey = leftNodes.map((n) => n.label || n.image || "").join("|")
    const rightKey = rightNodes.map((n) => n.label || n.image || "").join("|")

    useEffect(() => {
        // Drop refs left over from removed nodes, otherwise stale beams stay on screen.
        leftRefs.current.length = leftNodes.length
        rightRefs.current.length = rightNodes.length

        const measure = () => {
            const container = containerRef.current
            const center = centerRef.current
            if (!container || !center) return

            const cRect = container.getBoundingClientRect()
            if (cRect.width === 0 || cRect.height === 0) return
            setSvg({ width: cRect.width, height: cRect.height })
            const half = cRect.height / 2 || 1

            const centerRect = center.getBoundingClientRect()
            const cx = centerRect.left - cRect.left + centerRect.width / 2
            const cy = centerRect.top - cRect.top + centerRect.height / 2

            const next: Beam[] = []
            const build = (el: HTMLDivElement | null, isRight: boolean, index: number, order: number) => {
                if (!el) return
                const r = el.getBoundingClientRect()
                // Start at the chip's inner edge, so the beam touches the chip rather than its centre.
                const sx = isRight ? r.left - cRect.left : r.right - cRect.left
                const sy = r.top - cRect.top + r.height / 2
                const dy = sy - cy
                const sign = dy === 0 ? 0 : dy < 0 ? -1 : 1
                const controlY = sy - curvature * (dy / half)
                const midX = (sx + cx) / 2
                const endY = cy + sign * endYOffset
                const d = `M ${sx},${sy} Q ${midX},${controlY} ${cx},${endY}`

                // Inward: left beams run left→right, right beams reversed, so both converge on the centre.
                // Outward flips both, so the change spreads from the centre to every chip.
                const baseReverse = isRight
                const reverse = outward ? !baseReverse : baseReverse

                // The gradient sweeps across the full width (10%→110% or 90%→-10%), so the
                // time it reaches a chip depends on the chip's x position.
                const xFrac = sx / cRect.width
                const arrival = Math.min(1, Math.max(0, isRight ? xFrac - 0.1 : 0.9 - xFrac))

                next.push({
                    d,
                    reverse,
                    delay: delay + order * stagger,
                    duration: speedVariation > 0 ? duration + ((order * 1.3) % (speedVariation * 2)) : duration,
                    arrival,
                    side: isRight ? "r" : "l",
                    index,
                })
            }

            leftRefs.current.forEach((el, i) => build(el, false, i, i))
            rightRefs.current.forEach((el, i) => build(el, true, i, leftNodes.length + i))
            setBeams(next)
        }

        measure()
        const raf = requestAnimationFrame(measure)
        const ro = new ResizeObserver(() => measure())
        if (containerRef.current) ro.observe(containerRef.current)
        window.addEventListener("resize", measure)
        // Web fonts change chip widths after load.
        document.fonts?.ready.then(measure).catch(() => {})

        return () => {
            cancelAnimationFrame(raf)
            ro.disconnect()
            window.removeEventListener("resize", measure)
        }
    }, [
        leftKey,
        rightKey,
        leftNodes.length,
        rightNodes.length,
        nodeHeight,
        centerSize,
        padding,
        gap,
        curvature,
        endYOffset,
        delay,
        stagger,
        duration,
        speedVariation,
        outward,
    ])

    const beamFor = (side: "l" | "r", index: number) => beams.find((b) => b.side === side && b.index === index)

    const containerStyle: CSSProperties = {
        position: "relative",
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        overflow: "hidden",
        padding,
        boxSizing: "border-box",
        ...style,
    }

    const columnStyle: CSSProperties = {
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-around",
        gap,
        height: "100%",
        zIndex: 1,
    }

    const chipStyle: CSSProperties = {
        height: nodeHeight,
        padding: `0 ${Math.round(nodeHeight * 0.4)}px`,
        flex: "none",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 6,
        borderRadius: nodeRadius,
        background: nodeBackground,
        border: `${nodeBorderWidth}px solid ${nodeBorderColor}`,
        color: nodeTextColor,
        boxSizing: "border-box",
        whiteSpace: "nowrap",
        fontFamily: SANS,
        fontSize: 13,
        fontWeight: 500,
        ...labelFont,
    }

    const Chip = (item: NodeItem, side: "l" | "r", i: number) => {
        const beam = beamFor(side, i)
        const pulse = highlight && outward && !isThumbnail && beam
        const cycle = beam ? beam.duration + repeatDelay : 1
        // Light up when the beam arrives, hold briefly, fade back.
        const t0 = beam ? (beam.duration * beam.arrival) / cycle : 0
        const t1 = Math.min(0.999, t0 + 0.08)
        const t2 = Math.min(1, t0 + 0.3)
        return (
            <motion.div
                key={`${side}-${i}`}
                ref={(el) => {
                    if (side === "l") leftRefs.current[i] = el
                    else rightRefs.current[i] = el
                }}
                style={chipStyle}
                animate={
                    pulse
                        ? {
                              backgroundColor: [nodeBackground, nodeBackground, highlightBackground, nodeBackground],
                              borderColor: [nodeBorderColor, nodeBorderColor, highlightBorder, nodeBorderColor],
                              color: [nodeTextColor, nodeTextColor, highlightText, nodeTextColor],
                          }
                        : undefined
                }
                transition={
                    pulse
                        ? {
                              duration: cycle,
                              times: [0, Math.max(0, t0 - 0.001), t1, t2],
                              delay: beam!.delay,
                              repeat: Infinity,
                              ease: "easeOut",
                          }
                        : undefined
                }
            >
                {item.image ? (
                    <img src={item.image} alt="" draggable={false} style={{ width: 14, height: 14, objectFit: "contain" }} />
                ) : null}
                {item.label}
            </motion.div>
        )
    }

    const gradientCoords = (reverse: boolean) =>
        reverse
            ? { x1: ["90%", "-10%"], x2: ["100%", "0%"], y1: ["0%", "0%"], y2: ["0%", "0%"] }
            : { x1: ["10%", "110%"], x2: ["0%", "100%"], y1: ["0%", "0%"], y2: ["0%", "0%"] }

    return (
        <div ref={containerRef} style={containerStyle}>
            <div style={{ ...columnStyle, alignItems: "flex-start" }}>{leftNodes.map((item, i) => Chip(item, "l", i))}</div>

            <div style={{ ...columnStyle, justifyContent: "center", alignItems: "center", position: "relative" }}>
                <div
                    ref={centerRef}
                    style={{
                        width: centerSize,
                        height: centerSize,
                        flex: "none",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        borderRadius: 12,
                        background: centerBackground,
                        color: centerTextColor,
                        fontFamily: MONO,
                        fontSize: Math.round(centerSize * 0.3),
                        fontWeight: 500,
                        fontVariantNumeric: "tabular-nums",
                        overflow: "hidden",
                        boxSizing: "border-box",
                        ...centerFont,
                    }}
                >
                    {centerImage ? (
                        <img src={centerImage} alt="" draggable={false} style={{ width: "70%", height: "70%", objectFit: "contain" }} />
                    ) : (
                        centerLabel
                    )}
                </div>
                {centerCaption ? (
                    <div
                        style={{
                            position: "absolute",
                            top: `calc(50% + ${centerSize / 2 + 10}px)`,
                            left: "50%",
                            transform: "translateX(-50%)",
                            whiteSpace: "nowrap",
                            fontFamily: SANS,
                            fontSize: 12,
                            color: captionColor,
                            ...captionFont,
                        }}
                    >
                        {centerCaption}
                    </div>
                ) : null}
            </div>

            <div style={{ ...columnStyle, alignItems: "flex-end" }}>{rightNodes.map((item, i) => Chip(item, "r", i))}</div>

            <svg
                fill="none"
                width={svg.width}
                height={svg.height}
                viewBox={`0 0 ${svg.width || 1} ${svg.height || 1}`}
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden
                style={{ pointerEvents: "none", position: "absolute", left: 0, top: 0, transform: "translateZ(0)" }}
            >
                {beams.map((beam, i) => {
                    const gradId = `beam-${uid}-${i}`
                    const coords = gradientCoords(beam.reverse)
                    return (
                        <g key={i}>
                            <path d={beam.d} stroke={pathColor} strokeWidth={pathWidth} strokeOpacity={pathOpacity} strokeLinecap="round" />
                            <path d={beam.d} stroke={`url(#${gradId})`} strokeWidth={pathWidth} strokeLinecap="round" />
                            <defs>
                                <motion.linearGradient
                                    id={gradId}
                                    gradientUnits="userSpaceOnUse"
                                    initial={{ x1: "0%", x2: "0%", y1: "0%", y2: "0%" }}
                                    animate={
                                        isThumbnail
                                            ? { x1: "40%", x2: "50%", y1: "0%", y2: "0%" }
                                            : { x1: coords.x1, x2: coords.x2, y1: coords.y1, y2: coords.y2 }
                                    }
                                    transition={
                                        isThumbnail
                                            ? { duration: 0 }
                                            : {
                                                  delay: beam.delay,
                                                  duration: beam.duration,
                                                  ease: resolvedEase,
                                                  repeat: Infinity,
                                                  repeatDelay,
                                              }
                                    }
                                >
                                    <stop stopColor={gradientStartColor} stopOpacity="0" />
                                    <stop stopColor={gradientStartColor} />
                                    <stop offset="32.5%" stopColor={gradientStopColor} />
                                    <stop offset="100%" stopColor={gradientStopColor} stopOpacity="0" />
                                </motion.linearGradient>
                            </defs>
                        </g>
                    )
                })}
            </svg>
        </div>
    )
}

const nodeControl = {
    type: ControlType.Object,
    controls: {
        label: { type: ControlType.String, title: "Label", defaultValue: "Chip" },
        image: { type: ControlType.Image, title: "Icon" },
    },
}

addPropertyControls(DiffBeam, {
    centerLabel: { type: ControlType.String, title: "Center", defaultValue: "v2" },
    centerCaption: { type: ControlType.String, title: "Caption", defaultValue: "“Add SpO2 and skin-temperature sensing”" },
    centerImage: { type: ControlType.Image, title: "Center Image" },
    leftNodes: { type: ControlType.Array, title: "Left Chips", control: nodeControl, defaultValue: defaultLeft, maxCount: 6 },
    rightNodes: { type: ControlType.Array, title: "Right Chips", control: nodeControl, defaultValue: defaultRight, maxCount: 6 },

    labelFont: {
        type: ControlType.Font,
        title: "Chip Font",
        controls: "extended",
        defaultFontType: "sans-serif",
        defaultValue: { fontSize: 13, lineHeight: "1em" },
    },
    centerFont: {
        type: ControlType.Font,
        title: "Center Font",
        controls: "extended",
        defaultFontType: "monospace",
        defaultValue: { fontSize: 22, lineHeight: "1em" },
    },
    captionFont: {
        type: ControlType.Font,
        title: "Caption Font",
        controls: "extended",
        defaultFontType: "sans-serif",
        defaultValue: { fontSize: 12, lineHeight: "1.3em" },
    },

    nodeHeight: { type: ControlType.Number, title: "Chip Height", min: 20, max: 64, defaultValue: 32 },
    centerSize: { type: ControlType.Number, title: "Center Size", min: 32, max: 200, defaultValue: 72 },
    padding: { type: ControlType.Number, title: "Padding", min: 0, max: 200, defaultValue: 24 },
    gap: { type: ControlType.Number, title: "Chip Gap", min: 0, max: 120, defaultValue: 20 },

    nodeBackground: { type: ControlType.Color, title: "Chip Fill", defaultValue: "rgba(239, 237, 232, 0.8)" },
    nodeBorderColor: { type: ControlType.Color, title: "Chip Border", defaultValue: "rgba(0, 0, 0, 0)" },
    nodeTextColor: { type: ControlType.Color, title: "Chip Text", defaultValue: "#5F5E5A" },
    nodeBorderWidth: { type: ControlType.Number, title: "Border W", min: 0, max: 4, step: 0.5, defaultValue: 0 },
    nodeRadius: { type: ControlType.Number, title: "Chip Radius", min: 0, max: 999, defaultValue: 999 },
    centerBackground: { type: ControlType.Color, title: "Center Fill", defaultValue: "#111111" },
    centerTextColor: { type: ControlType.Color, title: "Center Text", defaultValue: "#FFFFFF" },
    captionColor: { type: ControlType.Color, title: "Caption", defaultValue: "#5F5E5A" },

    highlight: {
        type: ControlType.Boolean,
        title: "Light Up Chips",
        defaultValue: true,
        description: "Chips light up when their beam arrives (outward flow).",
    },
    highlightBackground: {
        type: ControlType.Color,
        title: "Lit Fill",
        defaultValue: "#FFF1EA",
        hidden: ({ highlight }: Props) => !highlight,
    },
    highlightBorder: {
        type: ControlType.Color,
        title: "Lit Border",
        defaultValue: "rgba(0, 0, 0, 0)",
        hidden: ({ highlight }: Props) => !highlight,
    },
    highlightText: {
        type: ControlType.Color,
        title: "Lit Text",
        defaultValue: "#C43C00",
        hidden: ({ highlight }: Props) => !highlight,
    },

    pathColor: { type: ControlType.Color, title: "Track", defaultValue: "#111111" },
    pathWidth: { type: ControlType.Number, title: "Beam Width", min: 0.5, max: 8, step: 0.5, defaultValue: 1.5 },
    pathOpacity: { type: ControlType.Number, title: "Track Opacity", min: 0, max: 1, step: 0.02, defaultValue: 0.12 },
    gradientStartColor: { type: ControlType.Color, title: "Beam A", defaultValue: "#FF4F00" },
    gradientStopColor: { type: ControlType.Color, title: "Beam B", defaultValue: "#FF6A26" },
    curvature: { type: ControlType.Number, title: "Curvature", min: 0, max: 200, defaultValue: 60 },
    endYOffset: { type: ControlType.Number, title: "End Offset", min: -40, max: 40, defaultValue: 0 },

    duration: {
        type: ControlType.Number,
        title: "Duration",
        min: 0.5,
        max: 30,
        step: 0.5,
        defaultValue: 3,
        description: "Higher = slower sweep",
    },
    delay: { type: ControlType.Number, title: "Delay", min: 0, max: 6, step: 0.1, defaultValue: 0 },
    stagger: { type: ControlType.Number, title: "Stagger", min: 0, max: 2, step: 0.05, defaultValue: 0.25 },
    repeatDelay: {
        type: ControlType.Number,
        title: "Repeat Delay",
        min: 0,
        max: 10,
        step: 0.25,
        defaultValue: 1.5,
        description: "Pause between sweeps",
    },
    speedVariation: {
        type: ControlType.Number,
        title: "Speed Variation",
        min: 0,
        max: 3,
        step: 0.1,
        defaultValue: 0,
        description: "0 = uniform timing (keeps the chips in sync)",
    },
    easing: {
        type: ControlType.Enum,
        title: "Easing",
        options: ["linear", "easeOut", "easeInOut", "expo"],
        optionTitles: ["Linear (steady)", "Ease Out", "Ease In-Out", "Expo (whoosh)"],
        defaultValue: "linear",
        description: "Linear keeps the chip highlight in sync with the beam",
    },
    outward: {
        type: ControlType.Boolean,
        title: "Flow",
        enabledTitle: "Out",
        disabledTitle: "In",
        defaultValue: true,
        description: "Out: the prompt spreads to every chip. In: the chips feed the centre.",
    },
})
