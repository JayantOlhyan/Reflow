import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

# Lightweight persistent JSON/SQLite store for zero-config out-of-the-box local operation
DATA_FILE = os.path.join(os.path.dirname(__file__), "reflow_data.json")

DEFAULT_DATA = {
    "content": [
        {
            "id": "cnt-1",
            "title": "Building an AI SaaS in 24 Hours",
            "type": "video",
            "source": "/storage/sample_video_1.mp4",
            "thumbnail": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=600&auto=format&fit=crop&q=80",
            "duration": 742,
            "status": "published",
            "created_at": "2026-08-28T14:30:00Z",
            "destinations": ["youtube", "instagram", "tiktok"],
            "variants": [
                {"platform": "youtube", "format": "16:9", "status": "published"},
                {"platform": "instagram", "format": "9:16", "status": "published"},
                {"platform": "tiktok", "format": "9:16", "status": "published"}
            ]
        },
        {
            "id": "cnt-2",
            "title": "10 AI Tools that 10x Productivity",
            "type": "carousel",
            "source": "",
            "thumbnail": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=600&auto=format&fit=crop&q=80",
            "slide_count": 8,
            "status": "published",
            "created_at": "2026-08-27T10:15:00Z",
            "destinations": ["linkedin", "instagram"],
            "variants": [
                {"platform": "linkedin", "format": "4:5", "status": "published"},
                {"platform": "instagram", "format": "1:1", "status": "published"}
            ]
        },
        {
            "id": "cnt-3",
            "title": "Automation Workflow Breakdown",
            "type": "image",
            "source": "/storage/sample_infographic.png",
            "thumbnail": "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600&auto=format&fit=crop&q=80",
            "dimensions": "1080x1350",
            "status": "scheduled",
            "created_at": "2026-08-26T18:00:00Z",
            "destinations": ["x", "linkedin"],
            "variants": [
                {"platform": "x", "format": "16:9", "status": "scheduled"},
                {"platform": "linkedin", "format": "4:5", "status": "scheduled"}
            ]
        },
        {
            "id": "cnt-4",
            "title": "My Learnings From 30 Days of Building",
            "type": "text",
            "source": "",
            "thumbnail": "https://images.unsplash.com/photo-1517842645767-c639042777db?w=600&auto=format&fit=crop&q=80",
            "status": "draft",
            "created_at": "2026-08-25T09:40:00Z",
            "destinations": ["x", "linkedin", "threads"],
            "variants": []
        }
    ],
    "connections": [
        {"id": "youtube", "name": "YouTube", "handle": "@JayantOlhyan", "connected": True, "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100", "capabilities": ["video", "thumbnail", "description", "scheduling"]},
        {"id": "instagram", "name": "Instagram", "handle": "@jayantolhyan", "connected": True, "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100", "capabilities": ["video", "image", "carousel", "caption", "scheduling"]},
        {"id": "tiktok", "name": "TikTok", "handle": "@jayant.olhyan", "connected": True, "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100", "capabilities": ["video", "caption", "scheduling"]},
        {"id": "linkedin", "name": "LinkedIn", "handle": "Jayant Olhyan", "connected": True, "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100", "capabilities": ["video", "image", "carousel", "text", "scheduling"]},
        {"id": "x", "name": "X (Twitter)", "handle": "@JayantOlhyan", "connected": True, "avatar": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100", "capabilities": ["video", "image", "text", "thread", "scheduling"]},
        {"id": "facebook", "name": "Facebook", "handle": "", "connected": False, "avatar": "", "capabilities": ["video", "image", "text", "scheduling"]},
        {"id": "pinterest", "name": "Pinterest", "handle": "", "connected": False, "avatar": "", "capabilities": ["image", "video", "scheduling"]},
        {"id": "threads", "name": "Threads", "handle": "", "connected": False, "avatar": "", "capabilities": ["text", "image", "video", "scheduling"]}
    ],
    "workflows": [
        {
            "id": "wf-1",
            "name": "YouTube to Everywhere",
            "active": True,
            "description": "Automatically repurpose long YouTube videos into vertical Reels, Shorts, TikToks, and text summaries.",
            "trigger": "YouTube New Video",
            "nodes": [
                {"id": "n1", "type": "trigger", "label": "YouTube New Video", "position": {"x": 50, "y": 100}},
                {"id": "n2", "type": "ai_processing", "label": "AI Repurpose Engine", "position": {"x": 300, "y": 100}},
                {"id": "n3", "type": "split", "label": "Split Content Formats", "position": {"x": 550, "y": 100}},
                {"id": "n4", "type": "output", "platform": "instagram", "label": "Instagram Reel (9:16)", "position": {"x": 800, "y": 20}},
                {"id": "n5", "type": "output", "platform": "tiktok", "label": "TikTok Video (9:16)", "position": {"x": 800, "y": 90}},
                {"id": "n6", "type": "output", "platform": "youtube", "label": "YouTube Shorts (9:16)", "position": {"x": 800, "y": 160}},
                {"id": "n7", "type": "output", "platform": "linkedin", "label": "LinkedIn Post (Text)", "position": {"x": 800, "y": 230}},
                {"id": "n8", "type": "output", "platform": "x", "label": "X Thread", "position": {"x": 800, "y": 300}}
            ]
        },
        {
            "id": "wf-2",
            "name": "PDF / Article to Carousel",
            "active": True,
            "description": "Extract structure from uploaded document, generate 8-slide summary carousel for LinkedIn and Instagram.",
            "trigger": "Upload PDF",
            "nodes": [
                {"id": "n1", "type": "trigger", "label": "Upload PDF", "position": {"x": 50, "y": 100}},
                {"id": "n2", "type": "ai_processing", "label": "AI Slide Deck Generator", "position": {"x": 300, "y": 100}},
                {"id": "n3", "type": "output", "platform": "linkedin", "label": "LinkedIn Carousel (PDF)", "position": {"x": 600, "y": 50}},
                {"id": "n4", "type": "output", "platform": "instagram", "label": "Instagram Carousel (Images)", "position": {"x": 600, "y": 150}}
            ]
        }
    ],
    "scheduled_posts": [
        {
            "id": "sch-1",
            "content_id": "cnt-1",
            "title": "Building an AI SaaS in 24 Hours",
            "platform": "instagram",
            "format": "Reel",
            "scheduled_time": "2026-08-30T19:30:00Z",
            "status": "scheduled"
        },
        {
            "id": "sch-2",
            "content_id": "cnt-1",
            "title": "Building an AI SaaS in 24 Hours",
            "platform": "youtube",
            "format": "Short",
            "scheduled_time": "2026-08-30T20:00:00Z",
            "status": "scheduled"
        },
        {
            "id": "sch-3",
            "content_id": "cnt-3",
            "title": "Automation Workflow Breakdown",
            "platform": "linkedin",
            "format": "Post",
            "scheduled_time": "2026-08-31T15:00:00Z",
            "status": "scheduled"
        },
        {
            "id": "sch-4",
            "content_id": "cnt-3",
            "title": "Automation Workflow Breakdown",
            "platform": "x",
            "format": "Thread",
            "scheduled_time": "2026-08-31T17:30:00Z",
            "status": "scheduled"
        },
        {
            "id": "sch-5",
            "content_id": "cnt-2",
            "title": "10 AI Tools that 10x Productivity",
            "platform": "tiktok",
            "format": "Video",
            "scheduled_time": "2026-09-01T18:00:00Z",
            "status": "scheduled"
        }
    ],
    "carousels": [
        {
            "id": "car-1",
            "title": "Automate Your Workflow",
            "theme": {
                "background": "#0F172A",
                "font_family": "Inter",
                "accent_color": "#6366F1",
                "text_color": "#FFFFFF"
            },
            "slides": [
                {"id": "s1", "title": "Automate Your Workflow", "subtitle": "01 / 05", "body": "Stop doing repetitive manual tasks. Here is the modern content engine breakdown.", "tag": "GUIDE"},
                {"id": "s2", "title": "01. Create Once", "subtitle": "02 / 05", "body": "Focus 80% of your energy on high-signal core ideas rather than platform formatting.", "tag": "FOUNDATION"},
                {"id": "s3", "title": "02. Aspect Ratio Transformation", "subtitle": "03 / 05", "body": "Transform landscape video into 9:16 vertical clips with dynamic captions and smart reframing.", "tag": "MEDIA"},
                {"id": "s4", "title": "03. Native Platform Copy", "subtitle": "04 / 05", "body": "Never copy-paste identical text. Adapt hooks, character constraints, and formatting for LinkedIn vs X.", "tag": "AI"},
                {"id": "s5", "title": "04. Distribute & Reflow", "subtitle": "05 / 05", "body": "Schedule once, review live queues, and analyze cross-platform distribution seamlessly.", "tag": "LAUNCH"}
            ]
        }
    ],
    "publishing_jobs": [
        {"id": "job-1", "content_title": "Instagram Reel (Building in Public Day 20)", "platform": "instagram", "status": "published", "time": "2m ago", "retry_count": 0},
        {"id": "job-2", "content_title": "YouTube Short (AI Automation System)", "platform": "youtube", "status": "processing", "time": "5m ago", "retry_count": 0},
        {"id": "job-3", "content_title": "LinkedIn Post (10 Lessons from building)", "platform": "linkedin", "status": "scheduled", "time": "1h ago", "retry_count": 0},
        {"id": "job-4", "content_title": "X Post (Quick update on the build)", "platform": "x", "status": "published", "time": "2h ago", "retry_count": 0},
        {"id": "job-5", "content_title": "TikTok Video (Behind the scenes)", "platform": "tiktok", "status": "failed", "time": "3h ago", "retry_count": 2, "error": "Token expired or missing permissions"}
    ],
    "logs": [
        {"id": "log-1", "level": "INFO", "timestamp": "2026-08-29 15:30:12", "service": "MediaWorker", "message": "FFmpeg transcoding completed for asset cnt-1 (1080x1920 9:16 vertical output generated)"},
        {"id": "log-2", "level": "INFO", "timestamp": "2026-08-29 15:31:05", "service": "AIEngine", "message": "AI platform copy generation succeeded for Instagram, LinkedIn, X, and YouTube"},
        {"id": "log-3", "level": "INFO", "timestamp": "2026-08-29 15:32:00", "service": "Publisher", "message": "Instagram Reel published successfully (ID: ig_8941249)"},
        {"id": "log-4", "level": "WARN", "timestamp": "2026-08-29 15:33:14", "service": "Publisher", "message": "TikTok publishing API returned rate-limit delay; queued for automatic backoff retry #1"},
        {"id": "log-5", "level": "ERROR", "timestamp": "2026-08-29 15:34:50", "service": "Publisher", "message": "TikTok publishing failed after retry #2: OAuth scope missing or expired session"}
    ]
}

class Database:
    def __init__(self):
        if not os.path.exists(DATA_FILE):
            self.save(DEFAULT_DATA)

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(DATA_FILE):
            self.save(DEFAULT_DATA)
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_DATA

    def save(self, data: Dict[str, Any]):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

db = Database()
