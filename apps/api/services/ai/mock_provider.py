import re
from typing import Dict, Any, List, Optional
from services.ai.base_provider import BaseAIProvider

class MockAIProvider(BaseAIProvider):
    provider_name: str = "mock"
    model_name: str = "mock-deterministic-v1"

    async def transcribe(self, audio_file_path: str) -> Dict[str, Any]:
        """Generates realistic timestamped transcript for testing/offline mode."""
        sample_text = (
            "Welcome to Reflow. In this episode, we are discussing how to turn a single source asset "
            "into native multi-platform content. Instead of manually formatting clips for Instagram, "
            "LinkedIn, X, and YouTube, we build an asynchronous engine that handles video transcoding, "
            "speech recognition, and structured intelligence. This delivers 10x leverage for modern builders."
        )
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', sample_text) if s.strip()]
        segments = []
        cur_time = 0.0
        for i, sentence in enumerate(sentences):
            duration = max(2.5, len(sentence.split()) * 0.4)
            segments.append({
                "sequence": i + 1,
                "start_time": round(cur_time, 2),
                "end_time": round(cur_time + duration, 2),
                "text": sentence
            })
            cur_time += duration

        return {
            "text": sample_text,
            "language": "en",
            "duration": round(cur_time, 2),
            "segments": segments
        }

    async def analyze_content(
        self,
        title: str,
        transcript_text: str,
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        return {
            "title": title or "Content Operating System Blueprint",
            "summary": f"A comprehensive breakdown of '{title}', examining how modular pipelines, local-first workflows, and unified media engines empower creators to automate multi-platform distribution.",
            "topics": ["Content Automation", "Software Architecture", "Creator Economy", "AI Pipelines"],
            "keywords": ["Reflow", "FastAPI", "FFmpeg", "Transcoding", "Next.js", "Self-Hosted"],
            "audience": "Software Engineers, Solopreneurs, Technical Content Creators",
            "tone": "Insightful, Pragmatic & Actionable",
            "key_points": [
                "Single-asset canonical ingestion eliminates redundant creative friction.",
                "Deterministic media transcoding produces clean 9:16, 1:1, and 4:5 aspect ratios without distortion.",
                "Background Redis workers prevent API blocking during CPU-intensive media transformations."
            ],
            "hooks": [
                "Stop spending 10 hours formatting clips for 5 platforms.",
                "How to build a personal content operating system from scratch.",
                "The secret to shipping cross-platform without burning out."
            ],
            "quotes": [
                "Create once. Transform everywhere."
            ],
            "cta_suggestions": [
                "Deploy Reflow on your own infrastructure with Docker today.",
                "Drop your biggest content bottleneck in the comments below."
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
        title = brief.get("title", "Content Strategy")
        summary = brief.get("summary", "")
        key_points = brief.get("key_points", [])
        hooks = brief.get("hooks", ["Automate your content engine"])
        cta = brief.get("cta_suggestions", ["Check out the repo!"])[0] if brief.get("cta_suggestions") else "Follow for more!"

        plt = platform.upper()
        if plt == "LINKEDIN":
            points_formatted = "\n\n".join([f"• {pt}" for pt in key_points])
            body = f"{summary}\n\nKey Engineering Takeaways:\n\n{points_formatted}"
            return {
                "title": f"How We Engineered: {title}",
                "hook": hooks[0] if hooks else "Modern content velocity requires modern architecture.",
                "body": body,
                "key_takeaway": "Decoupling canonical asset ingestion from platform formatting delivers 10x leverage.",
                "call_to_action": cta,
                "hashtags": ["#SoftwareEngineering", "#Architecture", "#Automation", "#OpenSource"]
            }

        elif plt == "INSTAGRAM":
            return {
                "hook": hooks[0] if hooks else "Stop doing repetitive work manually 🔥",
                "caption": f"{summary}\n\nHere is how to automate your pipeline 👇\n\n1. Ingest canonical source\n2. Deterministic aspect-ratio transforms\n3. Structured AI synthesis\n\nSave this post for your next architecture review! 📌",
                "call_to_action": cta,
                "hashtags": ["#buildinpublic", "#softwaredeveloper", "#automation", "#techstack", "#saas"]
            }

        elif plt == "X":
            post1 = f"{hooks[0] if hooks else title}\n\nA breakdown of how to build a unified content distribution engine 🧵👇"
            post2 = f"1/ The Bottleneck:\nCreators waste 15+ hours weekly reformatting 1 video for 5 platforms.\n\nSolution: Canonical asset ingestion with background worker dispatch."
            post3 = f"2/ The Pipeline:\n• FFmpeg for 9:16, 1:1, 4:5\n• Speech transcription\n• Structured ContentBrief synthesis\n• Native platform adaptation"
            post4 = f"3/ The Result:\nCreate once. Transform everywhere.\n\n{cta}"
            return {
                "thread_title": f"Breakdown: {title}",
                "posts": [post1, post2, post3, post4],
                "total_posts": 4
            }

        elif plt == "YOUTUBE":
            # Generate chapters using real timestamps from segments if available
            chapters = []
            if segments and len(segments) >= 2:
                for seg in segments[:5]:
                    secs = int(seg.get("start_time", 0))
                    mins = secs // 60
                    remainder = secs % 60
                    ts_str = f"{mins:02d}:{remainder:02d}"
                    txt_snip = seg.get("text", "Section")[:30].strip()
                    chapters.append({"timestamp": ts_str, "title": txt_snip})
            else:
                chapters = [
                    {"timestamp": "00:00", "title": "Introduction & Overview"},
                    {"timestamp": "01:15", "title": "System Architecture"},
                    {"timestamp": "03:40", "title": "Media Engine & Transcoding"},
                    {"timestamp": "06:10", "title": "Summary & Next Steps"}
                ]

            return {
                "title": f"{title} — Full Engineering & Content Breakdown"[:100],
                "description": f"In this video, we dive deep into {title}.\n\n{summary}\n\n⏱️ Chapters:\n" + "\n".join([f"{c['timestamp']} - {c['title']}" for c in chapters]) + f"\n\n👉 {cta}",
                "tags": ["Reflow", "Engineering", "Python", "Nextjs", "AI", "OpenSource"],
                "chapters": chapters
            }

        else:
            return {
                "title": title,
                "content": summary,
                "cta": cta
            }
