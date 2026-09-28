import { useEffect, useRef, useState, type CSSProperties } from "react"
import { addPropertyControls, ControlType, RenderTarget } from "framer"
import { AnimatePresence, motion, useReducedMotion } from "framer-motion"

/**
 * HERO STUDIO — the hero illustration for the PhysicalLovableX landing (466 × 593).
 * Plays the Studio in one loop: the prompt types itself, the AI writes the CAD,
 * answers with measured / estimated numbers, then the product appears in 3D with
 * two refine chips. Replaces the template's 5-variant chat mock.
 * Colours and type follow mvp/docs/BRAND.md (after W26). Numbers are the drone showcase's:
 * size Measured on the CAD, unit cost an Estimate, factories fictional demo data.
 *
 * @framerSupportedLayoutWidth any-prefer-fixed
 * @framerSupportedLayoutHeight any-prefer-fixed
 * @framerIntrinsicWidth 466
 * @framerIntrinsicHeight 593
 */

interface Props {
    prompt: string
    statusWorking: string
    statusDone: string
    reply: string
    image?: string
    sizeText: string
    costText: string
    chipA: string
    chipB: string
    placeholder: string
    loop: boolean
    speed: number
    font: CSSProperties
    monoFont: CSSProperties
    panelBackground: string
    accent: string
    style?: CSSProperties
}

const SANS = '"Inter Tight", Inter, system-ui, sans-serif'
const MONO = '"Geist Mono", ui-monospace, SFMono-Regular, Menlo, monospace'
const INK = "#111111"
const INK2 = "#5F5E5A"
const INK3 = "#8A8883"
const PAPER = "#F7F6F3"
const PAPER2 = "#EFEDE8"
const MEASURED = "#1F8A4C"
const ESTIMATE = "#C98A0B"
const FLOAT =
    "0 0 0 1px rgb(17 17 17 / .06), 0 2px 4px rgb(17 17 17 / .04), 0 12px 32px -12px rgb(17 17 17 / .18)"

// The real 3D render of the "Kitesurf follow-me drone" showcase (Overview, 3D model view), inlined.
const DRONE_RENDER = "data:image/jpeg;base64,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jARtCosVQhC9B8B02Lf5/sM4uofcY5ljnmShjkY8jqbGBlIj7gb2XMUGW+gtMracliEkMudsQjAQsiFJhkUmxCEI2KiF6Dq+BXJqX5LXOCxjyMwYxjyOhjo6x5Zw0RcEiGJTohIWRCMBCyIRgI2qrAqIQhcT4GxsbGySxMLPzkiUMppSGxtDdxsZQNjHkY+IaWBCyIRgIWRCgwLGyRCxwIQuJ0dGPFHRTaU+4uNn1NjGPIzAYxq40NEEEGGjEta7LahIgi4kJCWEhK4kJGFVRcK43wMfDgMY8jQlhoaIuQNEED3CGVjEld4KFQi4kJCWEhK4kJCxTaFRY4VxsfA+M0yLjTEcEMhkOSGMSJEpJUJoJEpEwmEcCTEnIkyGI4FJukCwKiovUfAx4rFyBLEEEXIGrVMqiEGRBAliDdVim6IXAhcb4XwMeB02WHEFqWkgapBFyCBJQQiLliwsUtNELFN1XsGPheKNGyBq1IIuQOypFyCBKxBFyCBKxBFyKLHCvYvheK7o1YikXo1Yggi5BAlYgi9IFim6pWIIqvYvhddkDmCCGQ5IfQacEPoX6EOdEPoQ+gk40X6EOSC4k4IZuqxTdV7SKOu6PFYvRq1dkECVqbqsUi5BAlb2H//aAAwDAQACAAMAAAAQ9999999ddptdVNp9ddtt999999999999t9dNJNNlNZNFVpt99999999999559R5l1xZ1lxZZl59199999999159xZZllxZ1lxZZlx911999999999p9VVpp9Vpp9VVpp999999999ddt5tlldZtl5JNllZZ9Vd999999dVtZFla5dhtxJNllZZddd9999991VllHc0lxhjXfD3LjBFZ15999991Rhf6d1VFgVEhblRllxZ15999999NE5COySOunjhbp9pp911999995CU/J6CaWEaPFvvCpdRNl1t999t0r9WJ+aKCiOiY4TLb3vBt1t999tdjb/wD+XqggqpKYfQYSdYQVefffffZV5w4EJhgqlofAbbQRaUeafffffeTVU7bfdUQSesxYcbdVcTdXfffXacQV2cddbUO/0ASeTZZSeSRffeRXXQc8aWeZUE2JXUTacVbbbVffTaYcQZTVeSaXbYTYTWXecYeWXffaadRZbQaUQcUTQecXTWaSVdRfffcRfVbaQfSYWZdaRZYVWaTWZffffffTXYXa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"

// Timeline in ms at speed 1. Step: 0 empty · 1 typing · 2 working · 3 done · 4 reply · 5 product · 6 chips
const T = { start: 500, typePerChar: 34, working: 1500, done: 700, reply: 900, product: 800, hold: 5200 }

export default function HeroStudio(props: Props) {
    const {
        prompt = "A foldable drone that follows me while I kitesurf.",
        statusWorking = "Writing the CAD…",
        statusDone = "v1 built in about 20 s",
        reply = "v1 is ready: measured on the CAD, costed at three volumes, with three factories to compare (demo data).",
        image,
        sizeText = "234 × 262 × 92 mm",
        costText = "$190.54 at 2k",
        chipA = "Anatomy ▸",
        chipB = "Make it matte black",
        placeholder = "Type a change",
        loop = true,
        speed = 1,
        font,
        monoFont,
        panelBackground = "#FFFFFF",
        accent = "#FF4F00",
        style,
    } = props

    const reduced = useReducedMotion()
    const isStatic = RenderTarget.current() === RenderTarget.canvas || RenderTarget.current() === RenderTarget.thumbnail
    const still = reduced || isStatic

    const [step, setStep] = useState(still ? 6 : 0)
    const [typed, setTyped] = useState(still ? prompt.length : 0)
    const [cycle, setCycle] = useState(0)
    const timers = useRef<number[]>([])

    useEffect(() => {
        if (still) {
            setStep(6)
            setTyped(prompt.length)
            return
        }
        const k = 1 / Math.max(0.25, speed)
        const at = (ms: number, fn: () => void) => timers.current.push(window.setTimeout(fn, ms * k))
        setStep(0)
        setTyped(0)
        let t = T.start
        at(t, () => setStep(1))
        for (let i = 1; i <= prompt.length; i++) at(t + i * T.typePerChar, () => setTyped(i))
        t += prompt.length * T.typePerChar + 350
        at(t, () => setStep(2))
        t += T.working
        at(t, () => setStep(3))
        t += T.done
        at(t, () => setStep(4))
        t += T.reply
        at(t, () => setStep(5))
        t += T.product
        at(t, () => setStep(6))
        t += T.hold
        if (loop) at(t, () => setCycle((c) => c + 1))
        return () => {
            timers.current.forEach((id) => window.clearTimeout(id))
            timers.current = []
        }
    }, [still, prompt, speed, loop, cycle])

    const text: CSSProperties = { fontFamily: SANS, ...font }
    const mono: CSSProperties = { fontFamily: MONO, fontVariantNumeric: "tabular-nums", ...monoFont }
    const enter = still
        ? { initial: false as const, animate: { opacity: 1, y: 0 } }
        : { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0 }, transition: { duration: 0.42, ease: [0.2, 0.7, 0.2, 1] } }

    const Dot = ({ color }: { color: string }) => (
        <span style={{ width: 6, height: 6, borderRadius: 999, background: color, flex: "none", display: "inline-block" }} />
    )

    return (
        <div
            style={{
                position: "relative",
                width: "100%",
                height: "100%",
                boxSizing: "border-box",
                padding: 18,
                display: "flex",
                flexDirection: "column",
                borderRadius: 20,
                background: panelBackground,
                boxShadow: FLOAT,
                overflow: "hidden",
                ...style,
            }}
        >
            {/* Conversation, anchored to the bottom like a real chat */}
            <div
                style={{
                    flex: 1,
                    minHeight: 0,
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "flex-end",
                    gap: 14,
                    overflow: "hidden",
                    // Older messages fade out at the top, like a scrolled chat
                    WebkitMaskImage: "linear-gradient(to bottom, transparent 0, #000 28px)",
                    maskImage: "linear-gradient(to bottom, transparent 0, #000 28px)",
                }}
            >
                <AnimatePresence mode="popLayout">
                    {step >= 1 && (
                        <motion.div key={`u-${cycle}`} {...enter} layout style={{ alignSelf: "flex-end", maxWidth: "82%" }}>
                            <div
                                style={{
                                    ...text,
                                    fontSize: 14,
                                    lineHeight: "21px",
                                    color: INK,
                                    background: PAPER2,
                                    padding: "10px 14px",
                                    borderRadius: 16,
                                    borderBottomRightRadius: 6,
                                }}
                            >
                                {prompt.slice(0, typed)}
                                {step === 1 && typed < prompt.length ? (
                                    <span style={{ display: "inline-block", width: 1.5, height: 15, marginLeft: 1, background: INK, verticalAlign: "-2px" }} />
                                ) : null}
                            </div>
                        </motion.div>
                    )}

                    {step >= 2 && (
                        <motion.div key={`s-${cycle}`} {...enter} layout style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            {step === 2 ? (
                                <span style={{ display: "inline-flex", gap: 3 }}>
                                    {[0, 1, 2].map((i) => (
                                        <motion.span
                                            key={i}
                                            style={{ width: 5, height: 5, borderRadius: 999, background: accent, display: "inline-block" }}
                                            animate={still ? undefined : { opacity: [0.25, 1, 0.25] }}
                                            transition={{ duration: 1, repeat: Infinity, delay: i * 0.16 }}
                                        />
                                    ))}
                                </span>
                            ) : (
                                <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
                                    <path d="M2 6.2l2.6 2.6L10 3.4" stroke={MEASURED} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                            )}
                            <span style={{ ...text, fontSize: 12.5, lineHeight: "16px", fontWeight: 500, color: INK3 }}>
                                {step === 2 ? statusWorking : statusDone}
                            </span>
                        </motion.div>
                    )}

                    {step >= 4 && (
                        <motion.div
                            key={`r-${cycle}`}
                            {...enter}
                            layout
                            style={{ ...text, fontSize: 14, lineHeight: "21px", color: INK, maxWidth: "92%" }}
                        >
                            {reply}
                        </motion.div>
                    )}

                    {step >= 5 && (
                        <motion.div key={`p-${cycle}`} {...enter} layout style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                            <div
                                style={{
                                    position: "relative",
                                    borderRadius: 14,
                                    overflow: "hidden",
                                    background: PAPER,
                                    boxShadow: "inset 0 0 0 1px rgb(0 0 0 / .06)",
                                    height: 212,
                                    width: "100%",
                                }}
                            >
                                <motion.img
                                    src={image || DRONE_RENDER}
                                    alt="3D model of the follow-me drone, generated from the CAD"
                                    draggable={false}
                                    style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "50% 45%", display: "block" }}
                                    initial={still ? false : { scale: 1.06 }}
                                    animate={{ scale: 1 }}
                                    transition={{ duration: 1.2, ease: [0.2, 0.7, 0.2, 1] }}
                                />
                                <span
                                    style={{
                                        position: "absolute",
                                        top: 10,
                                        right: 10,
                                        display: "flex",
                                        padding: 2,
                                        borderRadius: 8,
                                        background: PAPER2,
                                    }}
                                >
                                    <span style={{ ...text, fontSize: 11, lineHeight: "14px", fontWeight: 500, color: INK, background: "#FFFFFF", borderRadius: 6, padding: "3px 8px", boxShadow: "0 0 0 1px rgb(17 17 17 / .06)" }}>
                                        3D
                                    </span>
                                    <span style={{ ...text, fontSize: 11, lineHeight: "14px", fontWeight: 500, color: INK2, padding: "3px 8px" }}>Photo</span>
                                </span>
                            </div>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
                                <span style={{ ...mono, fontSize: 11.5, lineHeight: "16px", color: INK }}>{sizeText}</span>
                                <Dot color={MEASURED} />
                                <span style={{ color: "#B9B6AF", fontSize: 11 }}>·</span>
                                <span style={{ ...mono, fontSize: 11.5, lineHeight: "16px", color: INK }}>{costText}</span>
                                <Dot color={ESTIMATE} />
                            </div>
                        </motion.div>
                    )}

                    {step >= 6 && (
                        <motion.div key={`c-${cycle}`} {...enter} layout style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                            {[chipA, chipB].filter(Boolean).map((c, i) => (
                                <span
                                    key={c}
                                    style={{
                                        ...text,
                                        fontSize: 13,
                                        lineHeight: "18px",
                                        fontWeight: 500,
                                        padding: "6px 12px",
                                        borderRadius: 999,
                                        background: i === 0 ? INK : "rgb(239 237 232 / .8)",
                                        color: i === 0 ? "#FFFFFF" : INK2,
                                    }}
                                >
                                    {c}
                                </span>
                            ))}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Composer */}
            <div
                style={{
                    marginTop: 16,
                    flex: "none",
                    borderRadius: 16,
                    background: "#FFFFFF",
                    boxShadow: FLOAT,
                    padding: "12px 12px 10px 14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 14,
                }}
            >
                <span style={{ ...text, fontSize: 14, lineHeight: "20px", color: INK3 }}>{placeholder}</span>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ ...text, fontSize: 11, lineHeight: "14px", color: INK3 }}>Enter to send</span>
                    <span
                        style={{
                            width: 32,
                            height: 32,
                            borderRadius: 999,
                            background: step === 1 ? accent : PAPER2,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            transition: "background 200ms",
                        }}
                    >
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
                            <path d="M8 13V3M8 3L3.5 7.5M8 3l4.5 4.5" stroke={step === 1 ? INK : "#B9B6AF"} strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                    </span>
                </div>
            </div>
        </div>
    )
}

addPropertyControls(HeroStudio, {
    prompt: { type: ControlType.String, title: "Prompt", displayTextArea: true, defaultValue: "A foldable drone that follows me while I kitesurf." },
    statusWorking: { type: ControlType.String, title: "Working", defaultValue: "Writing the CAD…" },
    statusDone: { type: ControlType.String, title: "Done", defaultValue: "v1 built in about 20 s" },
    reply: {
        type: ControlType.String,
        title: "Reply",
        displayTextArea: true,
        defaultValue: "v1 is ready: measured on the CAD, costed at three volumes, with three factories to compare (demo data).",
    },
    image: { type: ControlType.Image, title: "Product image" },
    sizeText: { type: ControlType.String, title: "Size (Measured)", defaultValue: "234 × 262 × 92 mm" },
    costText: { type: ControlType.String, title: "Cost (Estimate)", defaultValue: "$190.54 at 2k" },
    chipA: { type: ControlType.String, title: "Chip 1", defaultValue: "Anatomy ▸" },
    chipB: { type: ControlType.String, title: "Chip 2", defaultValue: "Make it matte black" },
    placeholder: { type: ControlType.String, title: "Placeholder", defaultValue: "Type a change" },
    loop: { type: ControlType.Boolean, title: "Loop", defaultValue: true },
    speed: { type: ControlType.Number, title: "Speed", min: 0.5, max: 2, step: 0.1, defaultValue: 1 },
    font: { type: ControlType.Font, title: "Font", controls: "basic", defaultFontType: "sans-serif" },
    monoFont: { type: ControlType.Font, title: "Mono font", controls: "basic", defaultFontType: "monospace" },
    panelBackground: { type: ControlType.Color, title: "Panel", defaultValue: "#FFFFFF" },
    accent: { type: ControlType.Color, title: "Accent", defaultValue: "#FF4F00" },
})
