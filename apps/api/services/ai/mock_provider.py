import re
from typing import Dict, Any, List, Optional
from services.ai.base_provider import BaseAIProvider

class MockAIProvider(BaseAIProvider):
    provider_name: str = "mock"
    model_name: str = "mock-reflow-v1"

    async def transcribe(self, audio_file_path: str) -> Dict[str, Any]:
        """Returns deterministic, timestamped mock transcript segments."""
        return {
            "text": "Welcome to Reflow. Today we are breaking down how creators can turn one source video into multi-platform distribution. We cover aspect ratios, AI intelligence, and multi-slide carousels.",
            "language": "en",
            "duration": 18.5,
            "segments": [
                {
                    "sequence": 1,
                    "start_time": 0.0,
                    "end_time": 4.2,
                    "text": "Welcome to Reflow."
                },
                {
                    "sequence": 2,
                    "start_time": 4.2,
                    "end_time": 9.5,
                    "text": "Today we are breaking down how creators can turn one source video into multi-platform distribution."
                },
                {
                    "sequence": 3,
                    "start_time": 9.5,
                    "end_time": 14.0,
                    "text": "We cover aspect ratios, AI intelligence, and multi-slide carousels."
                },
                {
                    "sequence": 4,
                    "start_time": 14.0,
                    "end_time": 18.5,
                    "text": "Let's dive right into the architectural breakdown."
                }
            ]
        }

    async def analyze_content(
        self,
        title: str,
        transcript_text: str,
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Returns a structured, deterministic ContentBrief."""
        return {
            "title": title or "Content Repurposing Architecture",
            "summary": "A comprehensive walkthrough on automating content distribution across social channels from a single canonical media asset.",
            "topics": ["Content Automation", "Media Processing", "FFmpeg Pipelines", "AI Repurposing"],
            "keywords": ["reflow", "ffmpeg", "transcoding", "ai-brief", "distribution"],
            "audience": "Software Engineers, Technical Creators & Agency Operators",
            "tone": "Authoritative, Practical & High Signal",
            "key_points": [
                "Single source assets maximize creative leverage while minimizing production overhead.",
                "Automated aspect ratio adaptation prevents platform-specific formatting fatigue.",
                "AI content briefs enable rapid generation of high-retention text formats."
            ],
            "hooks": [
                "Stop manually editing video dimensions for 6 different social apps.",
                "How we built an automated content operating system with FFmpeg and AI.",
                "The 3-layer architecture for 10x content velocity."
            ],
            "quotes": [
                "Create once. Transform everywhere.",
                "Focus 80% of your energy on high-signal core ideas rather than platform formatting."
            ],
            "cta_suggestions": [
                "Try Reflow open-source on GitHub today.",
                "Star the repository and deploy locally with Docker."
            ]
        }

    async def generate_platform(
        self,
        platform: str,
        brief: Dict[str, Any],
        segments: Optional[List[Dict[str, Any]]] = None,
        tone: str = "professional",
        custom_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """Returns platform-specific structured copies based on the brief."""
        plat = platform.upper()
        title = brief.get("title", "High-Signal Architecture")
        summary = brief.get("summary", "")
        hooks = brief.get("hooks", ["Automate your content distribution today."])
        key_points = brief.get("key_points", ["Scale your creative output efficiently."])

        if plat == "LINKEDIN":
            return {
                "title": f"{title} | Deep Dive",
                "hook": hooks[0],
                "body": f"Most creators spend 80% of their time on repetitive distribution work.\n\nHere is how to solve it:\n" + "\n".join([f"• {kp}" for kp in key_points]) + f"\n\n{summary}",
                "key_takeaway": "Automate the transformation pipeline so you can focus exclusively on core thesis development.",
                "call_to_action": "What is the biggest bottleneck in your publishing pipeline?",
                "hashtags": ["#ContentEngineering", "#OpenSource", "#AIAutomation", "#SoftwareArchitecture"]
            }

        elif plat == "INSTAGRAM":
            return {
                "hook": f"🚀 {hooks[0]}",
                "caption": f"{hooks[0]}\n\n{summary}\n\nKey Takeaways:\n" + "\n".join([f"⚡ {kp}" for kp in key_points]) + "\n\nSave this reel for your next production build.",
                "call_to_action": "Drop a comment below with your thoughts!",
                "hashtags": ["#creatoreconomy", "#coding", "#buildinpublic", "#automation", "#softwaredev"]
            }

        elif plat == "X":
            posts = [
                f"1/4 {hooks[0]}\n\nA breakdown on building automated content pipelines 🧵👇",
                f"2/4 The core bottleneck:\n\n{key_points[0] if key_points else 'Manual formatting wastes hours.'}",
                f"3/4 How to solve it with Reflow:\n\n{key_points[1] if len(key_points) > 1 else 'Use automated transcoding & AI brief extraction.'}",
                f"4/4 In summary:\n\n{summary[:180]}\n\nCheck out Reflow on GitHub! 🚀"
            ]
            return {
                "thread_title": f"Thread: {title}",
                "posts": posts,
                "total_posts": len(posts)
            }

        elif plat == "YOUTUBE":
            chapters = []
            if segments:
                for seg in segments:
                    mins = int(seg["start_time"] // 60)
                    secs = int(seg["start_time"] % 60)
                    chapters.append({
                        "timestamp": f"{mins:02d}:{secs:02d}",
                        "title": seg["text"][:35]
                    })
            else:
                chapters = [
                    {"timestamp": "00:00", "title": "Introduction & Problem"},
                    {"timestamp": "00:45", "title": "System Architecture Overview"},
                    {"timestamp": "01:30", "title": "Live Automation Demo"},
                    {"timestamp": "02:15", "title": "Conclusion & Next Steps"}
                ]

            return {
                "title": f"{title} (Full Walkthrough)".strip()[:100],
                "description": f"{summary}\n\nChapters:\n" + "\n".join([f"{ch['timestamp']} - {ch['title']}" for ch in chapters]) + "\n\n#Reflow #OpenSource",
                "tags": ["Reflow", "Open Source", "Content Repurposing", "FastAPI", "NextJS"],
                "chapters": chapters
            }

        else:
            return {"raw_text": f"{title}\n\n{summary}"}

    async def plan_carousel(
        self,
        title: str,
        brief: Optional[Dict[str, Any]] = None,
        transcript_text: Optional[str] = None,
        target_slide_count: int = 5,
        template: str = "MINIMAL",
        tone: str = "informative",
        custom_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """Returns deterministic, high-quality structured carousel slides."""
        deck_title = title or (brief.get("title") if brief else "Automated Content Operating System")
        summary = brief.get("summary", "How to 10x your creative output with automated pipelines.") if brief else "The definitive breakdown for modern creators."
        key_points = brief.get("key_points", [
            "Create once and transform everywhere.",
            "Aspect ratio conversion eliminates manual cropping.",
            "Structured AI brief extraction preserves core thesis."
        ]) if brief else [
            "Create once and transform everywhere.",
            "Aspect ratio conversion eliminates manual cropping.",
            "Structured AI brief extraction preserves core thesis."
        ]

        count = max(4, min(12, target_slide_count))
        slides = []

        # Slide 1: HOOK / Title
        slides.append({
            "position": 1,
            "purpose": "HOOK",
            "layout": "TITLE",
            "headline": deck_title[:60],
            "body": summary[:140],
            "tag": "FOUNDATION"
        })

        # Slide 2: PROBLEM
        slides.append({
            "position": 2,
            "purpose": "PROBLEM",
            "layout": "TITLE_BODY",
            "headline": "The Distribution Bottleneck",
            "body": "Creators waste over 15 hours every week manually adapting content across Instagram, LinkedIn, and YouTube.",
            "tag": "PROBLEM"
        })

        # Dynamic Key Point slides
        for i in range(3, count):
            kp_idx = (i - 3) % len(key_points)
            slides.append({
                "position": i,
                "purpose": "KEY_POINT",
                "layout": "TITLE_BODY",
                "headline": f"0{i-2}. {key_points[kp_idx][:40]}",
                "body": key_points[kp_idx],
                "tag": "INSIGHT"
            })

        # Final Slide: CTA
        slides.append({
            "position": count,
            "purpose": "CTA",
            "layout": "CTA",
            "headline": "Deploy Reflow Today",
            "body": "Run locally with Docker in under 2 minutes or star the open-source repo on GitHub.",
            "tag": "ACTION"
        })

        return {
            "title": deck_title,
            "template": template.upper(),
            "slides": slides
        }

    async def discover_clips(
        self,
        title: str,
        transcript_text: str,
        segments: List[Dict[str, Any]],
        brief: Optional[Dict[str, Any]] = None,
        min_duration: float = 15.0,
        max_duration: float = 90.0,
        target_count: int = 5
    ) -> Dict[str, Any]:
        """Returns deterministic, timestamp-aligned clip candidates."""
        candidates = []
        hooks = brief.get("hooks", []) if brief else [
            "Why most AI automation projects fail before launch",
            "The architecture secrets of high-performance media transcoding",
            "Stop manually resizing your content for every platform"
        ]
        key_points = brief.get("key_points", []) if brief else [
            "Decouple heavy video encoding from synchronous HTTP requests",
            "Structured briefs ensure the core thesis is never lost",
            "Aspect ratio conversion eliminates manual editing"
        ]

        if segments and len(segments) >= 2:
            seg_count = len(segments)
            step = max(1, seg_count // target_count)
            for idx in range(0, seg_count, step):
                if len(candidates) >= target_count:
                    break
                s_seg = segments[idx]
                e_idx = min(seg_count - 1, idx + max(1, int(step * 0.8)))
                e_seg = segments[e_idx]

                s_time = float(s_seg.get("start_time", 0.0))
                e_time = float(e_seg.get("end_time", s_time + 30.0))
                dur = e_time - s_time
                if dur < min_duration:
                    e_time = s_time + min_duration
                elif dur > max_duration:
                    e_time = s_time + max_duration

                hook_text = hooks[len(candidates) % len(hooks)] if hooks else s_seg.get("text", "Engaging opening hook")
                cand_title = f"{title}: {key_points[len(candidates) % len(key_points)][:35]}" if key_points else f"Highlight #{len(candidates)+1}"
                matched_seg_ids = [str(s.get("id") or f"seg_{i}") for i, s in enumerate(segments[idx:e_idx+1])]

                candidates.append({
                    "title": cand_title,
                    "start_time": round(s_time, 2),
                    "end_time": round(e_time, 2),
                    "reason": "High emotional resonance with actionable technical walkthrough and complete thought.",
                    "hook": hook_text[:120],
                    "score": round(88.0 - (len(candidates) * 2.5), 1),
                    "source_segment_ids": matched_seg_ids
                })
        else:
            base_times = [
                (0.0, 25.0, "Why content repurposing is broken", "Stop wasting hours on manual editing"),
                (26.0, 58.0, "The unified transformation architecture", "Here is how to create once and transform everywhere"),
                (60.0, 90.0, "FFmpeg asynchronous variant pipeline", "Transcode 9:16 and 1:1 without blocking your server")
            ]
            for i, (st, et, t_title, hk) in enumerate(base_times[:target_count]):
                candidates.append({
                    "title": t_title,
                    "start_time": st,
                    "end_time": et,
                    "reason": "Clear standalone takeaway with high value for developer and creator audiences.",
                    "hook": hk,
                    "score": 85.0 - (i * 3.0),
                    "source_segment_ids": [f"seg_{i}"]
                })

        return {"candidates": candidates}

