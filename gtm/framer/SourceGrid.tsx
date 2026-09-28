import { useEffect, useState, type CSSProperties, type ReactNode } from "react"
import { addPropertyControls, ControlType, useIsStaticRenderer } from "framer"
import { AnimatePresence, motion, useReducedMotion } from "framer-motion"

// Replaces the Fantom logo wall ("Trusted by some of the big companies").
// Each cell shows a data source by name, flips to what we take from it, then moves on to the next source.
// Text only on purpose: no third-party logos, so it never reads as an endorsement.
// Defaults follow mvp/docs/BRAND.md after W26: sentence-case sans labels (no mono capitals), radius 12, no borders.

interface SourceItem {
    name: string
    tag?: string
    detail?: string
}

interface SourceGridProps {
    sources: SourceItem[]
    ariaLabel: string
    showLabel: boolean
    labelText: string
    autoplay: boolean
    interval: number
    stagger: number
    rows: number
    columns: number
    direction: "Up" | "Down"
    springStiffness: number
    springDamping: number
    transitionBlur: number
    nameFont: CSSProperties
    detailFont: CSSProperties
    tagFont: CSSProperties
    surface: string
    cardBackground: string
    borderColor: string
    nameColor: string
    textColor: string
    mutedColor: string
    labelDot: string
    labelTint: string
    labelInk: string
    radius: string
    gap: number
    padding: number
    cellPadding: number
    alignment: "start" | "center" | "end"
    style?: CSSProperties
}

// Facts from gtm/landing_copy_fantom.md (Sources table). Update the dates when the snapshots refresh.
const defaultSources: SourceItem[] = [
    { name: "LCSC", tag: "Parts", detail: "29,976 in-stock parts, priced. Snapshot 26 Sep 2026." },
    { name: "USITC HTS", tag: "Duties", detail: "US tariff lines and duty rates, by product code." },
    { name: "CBP rulings", tag: "Classification", detail: "8 of 10 test products matched to an official ruling." },
    { name: "Drewry WCI", tag: "Freight", detail: "Sea-freight index for the shipping lane. 24 Sep 2026." },
    { name: "EU PVGIS", tag: "Energy", detail: "Solar yield per roof and per site, from the EU JRC." },
    { name: "eCFR", tag: "Standards", detail: "FCC and US federal rules, cited line by line." },
]

const SANS = '"Inter Tight", Inter, system-ui, sans-serif'

/**
 * @framerIntrinsicWidth 1200
 * @framerIntrinsicHeight 140
 * @framerSupportedLayoutWidth any-prefer-fixed
 * @framerSupportedLayoutHeight auto
 */
export default function SourceGrid(props: SourceGridProps) {
    const {
        sources = defaultSources,
        ariaLabel = "Data sources behind every number",
        showLabel = true,
        labelText = "Sourced",
        autoplay = true,
        interval = 3200,
        stagger = 180,
        rows = 1,
        columns = 4,
        direction = "Up",
        springStiffness = 230,
        springDamping = 22,
        transitionBlur = 4,
        nameFont,
        detailFont,
        tagFont,
        surface = "transparent",
        cardBackground = "transparent",
        borderColor = "transparent",
        nameColor = "#111111",
        textColor = "#5F5E5A",
        mutedColor = "#8A8883",
        labelDot = "#2F6FD6",
        labelTint = "#EDF2FB",
        labelInk = "#2556A8",
        radius = "12px",
        gap = 12,
        padding = 0,
        cellPadding = 16,
        alignment = "center",
    } = props

    const items = sources.length > 0 ? sources : defaultSources
    const cellCount = Math.max(1, Math.round(rows) * Math.round(columns))
    const isStatic = useIsStaticRenderer()
    const reducedMotion = useReducedMotion()
    // Per cell: even step = source name, odd step = its detail. Every two steps the cell moves to the
    // next source it owns (cell i shows sources i, i + cellCount, …), so all sources appear even with fewer cells.
    const [steps, setSteps] = useState<number[]>(() => Array(cellCount).fill(0))

    useEffect(() => {
        setSteps(Array(cellCount).fill(0))
    }, [cellCount, items.length])

    useEffect(() => {
        if (typeof window === "undefined" || isStatic || reducedMotion || !autoplay) return

        const timers = Array.from({ length: cellCount }, (_, cellIndex) => {
            const advance = () =>
                setSteps((current) => current.map((value, index) => (index === cellIndex ? value + 1 : value)))
            const timer: { delay: number; loop?: number } = { delay: 0 }
            timer.delay = window.setTimeout(
                () => {
                    advance()
                    timer.loop = window.setInterval(advance, Math.max(1200, interval))
                },
                Math.max(0, cellIndex * stagger + interval)
            )
            return timer
        })

        return () => {
            timers.forEach(({ delay, loop }) => {
                window.clearTimeout(delay)
                if (loop) window.clearInterval(loop)
            })
        }
    }, [autoplay, cellCount, interval, isStatic, reducedMotion, stagger])

    const slideDistance = direction === "Up" ? 24 : -24
    const exitDistance = -slideDistance
    const flexAlign = alignment === "start" ? "flex-start" : alignment === "end" ? "flex-end" : "center"
    const textAlign = alignment === "start" ? "left" : alignment === "end" ? "right" : "center"

    const faceStyle: CSSProperties = {
        gridArea: "1 / 1",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: flexAlign,
        gap: 8,
        textAlign,
    }

    const nameFace = (item: SourceItem): ReactNode => (
        <>
            <span
                style={{
                    fontFamily: SANS,
                    fontSize: 22,
                    fontWeight: 600,
                    lineHeight: 1.15,
                    letterSpacing: "-0.015em",
                    ...nameFont,
                    color: nameColor,
                }}
            >
                {item.name}
            </span>
            {item.tag ? (
                <span
                    style={{
                        fontFamily: SANS,
                        fontSize: 12.5,
                        fontWeight: 500,
                        lineHeight: "18px",
                        ...tagFont,
                        color: mutedColor,
                    }}
                >
                    {item.tag}
                </span>
            ) : null}
        </>
    )

    const detailFace = (item: SourceItem): ReactNode => (
        <>
            {showLabel ? (
                <span
                    style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 6,
                        height: 22,
                        padding: "0 9px",
                        borderRadius: 999,
                        background: labelTint,
                        color: labelInk,
                        fontFamily: SANS,
                        fontSize: 12,
                        fontWeight: 500,
                        whiteSpace: "nowrap",
                    }}
                >
                    <span style={{ width: 6, height: 6, borderRadius: 999, background: labelDot, flex: "none" }} />
                    {labelText} · {item.name}
                </span>
            ) : null}
            <span
                style={{
                    fontFamily: SANS,
                    fontSize: 15,
                    lineHeight: 1.45,
                    ...detailFont,
                    color: textColor,
                    maxWidth: "30ch",
                }}
            >
                {item.detail}
            </span>
        </>
    )

    return (
        <section
            aria-label={ariaLabel}
            style={{
                ...props.style,
                position: "relative",
                width: "100%",
                boxSizing: "border-box",
                padding,
                background: surface,
            }}
        >
            <div
                role="list"
                style={{
                    display: "grid",
                    gridTemplateColumns: `repeat(${Math.max(1, Math.round(columns))}, minmax(0, 1fr))`,
                    gridAutoRows: "auto",
                    gap,
                    width: "100%",
                }}
            >
                {Array.from({ length: cellCount }, (_, cellIndex) => {
                    const step = steps[cellIndex] ?? 0
                    const cycle = Math.floor(step / 2)
                    const itemIndex = (cellIndex + cycle * cellCount) % items.length
                    const item = items[itemIndex]
                    const showDetail = step % 2 === 1 && !!item.detail
                    // The cell reserves the height of the tallest face of every source it can show,
                    // so nothing is clipped and the row never jumps.
                    const ownedIndexes = new Set(
                        Array.from({ length: items.length }, (_, c) => (cellIndex + c * cellCount) % items.length)
                    )
                    const owned = items.filter((_, i) => ownedIndexes.has(i))
                    return (
                        <div
                            key={cellIndex}
                            role="listitem"
                            aria-label={item.detail ? `${item.name}: ${item.detail}` : item.name}
                            style={{
                                position: "relative",
                                display: "grid",
                                boxSizing: "border-box",
                                padding: cellPadding,
                                border: `1px solid ${borderColor}`,
                                borderRadius: radius,
                                background: cardBackground,
                                overflow: "hidden",
                            }}
                        >
                            {owned.map((o, i) => (
                                <div key={`size-n-${i}`} aria-hidden style={{ ...faceStyle, visibility: "hidden" }}>
                                    {nameFace(o)}
                                </div>
                            ))}
                            {owned.map((o, i) =>
                                o.detail ? (
                                    <div key={`size-d-${i}`} aria-hidden style={{ ...faceStyle, visibility: "hidden" }}>
                                        {detailFace(o)}
                                    </div>
                                ) : null
                            )}
                            <AnimatePresence initial={false} mode="sync">
                                <motion.div
                                    key={`${cellIndex}-${step}`}
                                    aria-hidden
                                    initial={
                                        reducedMotion
                                            ? false
                                            : { y: slideDistance, opacity: 0, filter: `blur(${transitionBlur}px)` }
                                    }
                                    animate={{ y: 0, opacity: 1, filter: "blur(0px)" }}
                                    exit={
                                        reducedMotion
                                            ? undefined
                                            : { y: exitDistance, opacity: 0, filter: `blur(${transitionBlur}px)` }
                                    }
                                    transition={
                                        reducedMotion
                                            ? { duration: 0 }
                                            : {
                                                  type: "spring",
                                                  stiffness: springStiffness,
                                                  damping: springDamping,
                                                  mass: 0.68,
                                                  // A spring overshoots below zero, and blur(<0) is invalid: tween these two.
                                                  filter: { type: "tween", duration: 0.3, ease: "easeOut" },
                                                  opacity: { type: "tween", duration: 0.3, ease: "easeOut" },
                                              }
                                    }
                                    style={faceStyle}
                                >
                                    {showDetail ? detailFace(item) : nameFace(item)}
                                </motion.div>
                            </AnimatePresence>
                        </div>
                    )
                })}
            </div>
        </section>
    )
}

addPropertyControls(SourceGrid, {
    sources: {
        type: ControlType.Array,
        title: "Sources",
        description: "Each cell shows a name, flips to its detail, then moves to the next source.",
        maxCount: 12,
        control: {
            type: ControlType.Object,
            controls: {
                name: { type: ControlType.String, title: "Name", defaultValue: "Source" },
                tag: { type: ControlType.String, title: "Tag", defaultValue: "" },
                detail: { type: ControlType.String, title: "Detail", displayTextArea: true, defaultValue: "" },
            },
        },
        defaultValue: defaultSources,
    },
    ariaLabel: { type: ControlType.String, title: "A11y Label", defaultValue: "Data sources behind every number" },
    showLabel: { type: ControlType.Boolean, title: "Trust Pill", defaultValue: true },
    labelText: {
        type: ControlType.String,
        title: "Pill Text",
        defaultValue: "Sourced",
        hidden: ({ showLabel }: SourceGridProps) => !showLabel,
    },
    nameFont: {
        type: ControlType.Font,
        title: "Name Font",
        controls: "extended",
        defaultFontType: "sans-serif",
        defaultValue: { fontSize: 22, letterSpacing: "-0.015em", lineHeight: "1.15em" },
    },
    detailFont: {
        type: ControlType.Font,
        title: "Detail Font",
        controls: "extended",
        defaultFontType: "sans-serif",
        defaultValue: { fontSize: 15, lineHeight: "1.45em" },
    },
    tagFont: {
        type: ControlType.Font,
        title: "Tag Font",
        controls: "extended",
        defaultFontType: "sans-serif",
        defaultValue: { fontSize: 12.5, lineHeight: "18px" },
    },
    autoplay: { type: ControlType.Boolean, title: "Autoplay", defaultValue: true },
    rows: { type: ControlType.Number, title: "Rows", defaultValue: 1, min: 1, max: 6, step: 1 },
    columns: { type: ControlType.Number, title: "Columns", defaultValue: 4, min: 1, max: 6, step: 1 },
    direction: { type: ControlType.Enum, title: "Direction", options: ["Up", "Down"], defaultValue: "Up" },
    interval: { type: ControlType.Number, title: "Interval", defaultValue: 3200, min: 1200, max: 10000, step: 100, unit: "ms" },
    stagger: {
        type: ControlType.Number,
        title: "Stagger",
        defaultValue: 180,
        min: 0,
        max: 800,
        step: 10,
        unit: "ms",
        hidden: ({ autoplay }: SourceGridProps) => !autoplay,
    },
    springStiffness: {
        type: ControlType.Number,
        title: "Spring Strength",
        defaultValue: 230,
        min: 100,
        max: 400,
        step: 5,
        hidden: ({ autoplay }: SourceGridProps) => !autoplay,
    },
    springDamping: {
        type: ControlType.Number,
        title: "Spring Damping",
        defaultValue: 22,
        min: 10,
        max: 35,
        step: 1,
        hidden: ({ autoplay }: SourceGridProps) => !autoplay,
    },
    transitionBlur: {
        type: ControlType.Number,
        title: "Transition Blur",
        defaultValue: 4,
        min: 0,
        max: 20,
        step: 1,
        unit: "px",
        hidden: ({ autoplay }: SourceGridProps) => !autoplay,
    },
    surface: { type: ControlType.Color, title: "Surface", defaultValue: "transparent" },
    cardBackground: { type: ControlType.Color, title: "Card Fill", defaultValue: "transparent" },
    borderColor: { type: ControlType.Color, title: "Border", defaultValue: "transparent" },
    nameColor: { type: ControlType.Color, title: "Name", defaultValue: "#111111" },
    textColor: { type: ControlType.Color, title: "Detail", defaultValue: "#5F5E5A" },
    mutedColor: { type: ControlType.Color, title: "Tag", defaultValue: "#8A8883" },
    labelDot: {
        type: ControlType.Color,
        title: "Pill Dot",
        defaultValue: "#2F6FD6",
        hidden: ({ showLabel }: SourceGridProps) => !showLabel,
    },
    labelTint: {
        type: ControlType.Color,
        title: "Pill Fill",
        defaultValue: "#EDF2FB",
        hidden: ({ showLabel }: SourceGridProps) => !showLabel,
    },
    labelInk: {
        type: ControlType.Color,
        title: "Pill Text",
        defaultValue: "#2556A8",
        hidden: ({ showLabel }: SourceGridProps) => !showLabel,
    },
    radius: { type: ControlType.BorderRadius, title: "Radius", defaultValue: "12px" },
    gap: { type: ControlType.Number, title: "Grid Gap", defaultValue: 12, min: 0, max: 36, step: 1, unit: "px" },
    padding: { type: ControlType.Number, title: "Outer Padding", defaultValue: 0, min: 0, max: 100, step: 1, unit: "px" },
    cellPadding: { type: ControlType.Number, title: "Cell Padding", defaultValue: 16, min: 0, max: 80, step: 1, unit: "px" },
    alignment: {
        type: ControlType.Enum,
        title: "Alignment",
        options: ["start", "center", "end"],
        optionTitles: ["Start", "Center", "End"],
        defaultValue: "center",
    },
})
