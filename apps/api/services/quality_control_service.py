import os
import re
import json
import uuid
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy import select, and_, func
from database import async_session_factory
from models.entities import (
    Content, ContentVariant, ClipVariant, Publication, 
    QualityCheck, BrandProfile, GovernancePolicy, GovernanceOverride, 
    GovernanceResult, ContentClaim
)
from services.media_service import media_processor
from services.ai_service import AIService
from utils.logging import get_logger

logger = get_logger("QualityControlService")

class QualityControlService:
    def __init__(self):
        self.ai_service = AIService()

    def get_jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calculates Jaccard word set similarity between two text strings."""
        if not text1 or not text2:
            return 0.0
        words1 = set(re.findall(r"\w+", text1.lower()))
        words2 = set(re.findall(r"\w+", text2.lower()))
        if not words1 or not words2:
            return 0.0
        return len(words1.intersection(words2)) / len(words1.union(words2))

    async def get_active_policy(self, session: Any, scope: str = "GLOBAL") -> Optional[GovernancePolicy]:
        """Fetches the active/enabled policy matching the scope."""
        res = await session.execute(
            select(GovernancePolicy).where(
                and_(GovernancePolicy.enabled == True, GovernancePolicy.scope == scope)
            ).order_by(GovernancePolicy.policy_version.desc())
        )
        return res.scalars().first()

    async def check_media_validity(self, file_path: str, content_type: str) -> Dict[str, Any]:
        """Performs technical checks on video, image, or PDF files."""
        if not os.path.exists(file_path):
            return {
                "status": "FAILED",
                "severity": "BLOCKING",
                "message": f"Media file not found at path: {file_path}",
                "details": {"path": file_path}
            }

        file_size = os.path.getsize(file_path)
        file_size_mb = file_size / (1024 * 1024)

        if content_type == "VIDEO":
            try:
                info = await media_processor.probe_media(file_path)
                # Check for video codec and audio stream
                if not info.get("codec"):
                    return {
                        "status": "FAILED",
                        "severity": "BLOCKING",
                        "message": "Video stream is missing or codec is invalid.",
                        "details": info
                    }
                if not info.get("has_audio"):
                    return {
                        "status": "WARNING",
                        "severity": "WARNING",
                        "message": "Video does not contain an audio stream.",
                        "details": info
                    }
                if (info.get("duration") or 0) <= 0:
                    return {
                        "status": "FAILED",
                        "severity": "BLOCKING",
                        "message": "Invalid video duration detected (0 seconds).",
                        "details": info
                    }
                return {
                    "status": "PASSED",
                    "severity": "INFO",
                    "message": "Technical video checks passed successfully.",
                    "details": info
                }
            except Exception as e:
                return {
                    "status": "FAILED",
                    "severity": "BLOCKING",
                    "message": f"FFprobe failed to read video headers (file may be corrupted): {str(e)}",
                    "details": {"error": str(e)}
                }

        elif content_type == "IMAGE":
            # Basic image format validation
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
                return {
                    "status": "FAILED",
                    "severity": "BLOCKING",
                    "message": f"Unsupported image format: {ext}",
                    "details": {"extension": ext, "file_size_mb": file_size_mb}
                }
            # Mock image dimensions check
            return {
                "status": "PASSED",
                "severity": "INFO",
                "message": "Technical image checks passed successfully.",
                "details": {"file_size_mb": file_size_mb, "extension": ext, "width": 1080, "height": 1080}
            }

        elif content_type == "CAROUSEL" or file_path.endswith(".pdf"):
            # PDF validation
            try:
                with open(file_path, "rb") as f:
                    header = f.read(5)
                if header != b"%PDF-":
                    return {
                        "status": "FAILED",
                        "severity": "BLOCKING",
                        "message": "File does not contain valid PDF magic headers.",
                        "details": {"header": str(header)}
                    }
                # Simple page count estimate or return successful
                return {
                    "status": "PASSED",
                    "severity": "INFO",
                    "message": "Technical PDF checks passed successfully.",
                    "details": {"file_size_mb": file_size_mb, "pages": 5}
                }
            except Exception as e:
                return {
                    "status": "FAILED",
                    "severity": "BLOCKING",
                    "message": f"Failed to parse PDF document structure: {str(e)}",
                    "details": {"error": str(e)}
                }

        return {
            "status": "PASSED",
            "severity": "INFO",
            "message": "No technical media checks required for text content.",
            "details": {"file_size_mb": file_size_mb}
        }

    async def check_platform_compatibility(self, platform: str, content_type: str, text_content: str, media_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Validates platform limits based on character counts, dimensions, and types."""
        plat = platform.lower()
        text_len = len(text_content or "")

        # Target capacities matrix
        limits = {
            "x": {"max_len": 280, "video": True, "image": True, "carousel": False},
            "linkedin": {"max_len": 3000, "video": True, "image": True, "carousel": True},
            "instagram": {"max_len": 2200, "video": True, "image": True, "carousel": True},
            "youtube": {"max_len": 5000, "video": True, "image": False, "carousel": False}
        }

        limit = limits.get(plat, {"max_len": 2000, "video": True, "image": True, "carousel": True})

        if text_len > limit["max_len"]:
            return {
                "status": "FAILED",
                "severity": "BLOCKING",
                "message": f"Caption exceeds the {platform.upper()} maximum limit of {limit['max_len']} characters (Current: {text_len}).",
                "details": {"limit": limit["max_len"], "current": text_len}
            }

        # Check aspect ratios for specific platforms
        if media_info and content_type == "VIDEO":
            width = media_info.get("width")
            height = media_info.get("height")
            if width and height:
                ratio = width / height
                # Instagram Reels prefers 9:16 (around 0.56)
                if plat == "instagram" and ratio > 1.0:
                    return {
                        "status": "WARNING",
                        "severity": "WARNING",
                        "message": f"Instagram Reels recommends vertical aspect ratios (9:16). Current ratio is landscape ({width}x{height}).",
                        "details": {"width": width, "height": height, "ratio": ratio}
                    }

        return {
            "status": "PASSED",
            "severity": "INFO",
            "message": f"Content is compatible with {platform.upper()} specifications.",
            "details": limit
        }

    async def check_duplicates(self, session: Any, platform: str, text_content: str, source_content_id: Optional[str]) -> List[Dict[str, Any]]:
        """Scans historical publications to prevent duplicate posts."""
        checks = []
        if not text_content:
            return checks

        # Fetch recent publications in the last 24h
        yesterday = datetime.utcnow() - timedelta(hours=24)
        pub_res = await session.execute(
            select(Publication).where(
                and_(
                    Publication.platform == platform.lower(),
                    Publication.created_at >= yesterday,
                    Publication.status == "PUBLISHED"
                )
            )
        )
        recent_pubs = pub_res.scalars().all()

        for pub in recent_pubs:
            pub_text = pub.caption or ""
            # Exact match
            if pub_text.strip() == text_content.strip():
                checks.append({
                    "status": "FAILED",
                    "severity": "BLOCKING",
                    "message": "Exact duplicate content was published to this platform within the last 24 hours.",
                    "details": {"publication_id": pub.id, "similarity": 1.0}
                })
                break
            
            # Near duplicate
            similarity = self.get_jaccard_similarity(text_content, pub_text)
            if similarity > 0.85:
                checks.append({
                    "status": "WARNING",
                    "severity": "WARNING",
                    "message": f"High text similarity ({int(similarity*100)}%) detected compared to a recent post.",
                    "details": {"publication_id": pub.id, "similarity": similarity}
                })

        return checks

    async def check_brand_compliance(self, text_content: str, profile: BrandProfile) -> List[Dict[str, Any]]:
        """Validates forbidden terms, required terms, tone checks, CTAs, hashtag and mention rules."""
        checks = []
        text = text_content or ""
        text_lower = text.lower()

        # 1. Forbidden terms (BLOCKING)
        for term in profile.forbidden_terms:
            if term.lower() in text_lower:
                checks.append({
                    "status": "FAILED",
                    "severity": "BLOCKING",
                    "message": f"Brand compliance violation: Contains forbidden term '{term}'.",
                    "details": {"term": term}
                })

        # 2. Required terms (WARNING)
        for term in profile.required_terms:
            if term.lower() not in text_lower:
                checks.append({
                    "status": "WARNING",
                    "severity": "WARNING",
                    "message": f"Brand compliance warning: Missing required phrase/term '{term}'.",
                    "details": {"term": term}
                })

        # 3. Hashtag counts
        hashtag_rules = profile.hashtag_rules
        max_hashtags = hashtag_rules.get("max_count", 8)
        actual_hashtags = len(re.findall(r"#\w+", text))
        if actual_hashtags > max_hashtags:
            checks.append({
                "status": "WARNING",
                "severity": "WARNING",
                "message": f"Brand compliance warning: Contains {actual_hashtags} hashtags. Brand profile limit is {max_hashtags}.",
                "details": {"limit": max_hashtags, "actual": actual_hashtags}
            })

        # 4. Link validation rules
        links = re.findall(r"https?://\S+", text)
        link_rules = profile.link_rules
        allowed_protocols = link_rules.get("allowed_protocols", ["https"])
        for link in links:
            if link.startswith("http://") and "https" in allowed_protocols and "http" not in allowed_protocols:
                checks.append({
                    "status": "FAILED",
                    "severity": "BLOCKING",
                    "message": f"Insecure URL detected: '{link}'. Only HTTPS allowed by brand profile.",
                    "details": {"url": link}
                })

        return checks

    async def evaluate_ai_claims(self, session: Any, content_id: str, text_content: str) -> List[Dict[str, Any]]:
        """Compares claims in copy against transcript/brief details to flag hallucinations."""
        checks = []
        # Find transcript
        content_res = await session.execute(select(Content).where(Content.id == content_id))
        content = content_res.scalar_one_or_none()
        if not content:
            return checks

        source_text = content.text_content or ""
        if content.transcripts:
            source_text = content.transcripts[0].text

        if not source_text:
            # No source context exists, cannot trace claims
            return [{
                "status": "WARNING",
                "severity": "WARNING",
                "message": "Factual verification skipped: No source transcript or brief exists to validate claims.",
                "details": {}
            }]

        # Extract mock claims for verification testing
        # In a real system, we'd prompt LLM. Let's do a deterministic parse of statements
        # We will split text into sentences and simulate fact validation
        sentences = [s.strip() for s in re.split(r"[.!?]", text_content) if len(s.strip()) > 10]
        
        # Save claims
        for sentence in sentences:
            # Simple simulation: if sentence contains terms not in source_text (e.g. random numbers not present), contradiction-flag it
            status = "SUPPORTED"
            # Look for numbers/percentages or specific claims
            numbers = re.findall(r"\b\d+%\b|\b\d{4}\b", sentence)
            for num in numbers:
                if num not in source_text:
                    status = "CONTRADICTED"
                    break

            claim = ContentClaim(
                id=f"clm_{uuid.uuid4().hex[:12]}",
                content_id=content_id,
                text=sentence,
                source_reference="Transcript sync matching",
                verification_status=status,
                severity="WARNING"
            )
            session.add(claim)

            if status == "CONTRADICTED":
                checks.append({
                    "status": "WARNING",
                    "severity": "WARNING",
                    "message": f"Potential AI Hallucination detected: Statement '{sentence}' contains claims unsupported by source transcript.",
                    "details": {"statement": sentence}
                })

        return checks

    async def run_pipeline(
        self,
        session: Any,
        content_id: str,
        variant_id: Optional[str] = None,
        publication_id: Optional[str] = None,
        platform: str = "linkedin"
    ) -> Dict[str, Any]:
        """Runs the complete validation pipeline returning aggregated GovernanceResult status."""
        logger.info(f"Executing Quality Control pipeline for Content {content_id}...")

        # 1. Fetch content
        content_res = await session.execute(select(Content).where(Content.id == content_id))
        content = content_res.scalar_one_or_none()
        if not content:
            raise ValueError(f"Content {content_id} not found.")

        # Resolve media path & copy text
        text_content = content.text_content or ""
        media_path = None
        content_type = content.content_type

        if variant_id:
            # Check ClipVariant
            cvar_res = await session.execute(select(ClipVariant).where(ClipVariant.id == variant_id))
            cvar = cvar_res.scalar_one_or_none()
            if cvar:
                media_path = media_processor.storage_service.get_real_path(cvar.storage_key)
                text_content = cvar.caption or text_content
            else:
                # Check ContentVariant
                var_res = await session.execute(select(ContentVariant).where(ContentVariant.id == variant_id))
                var = var_res.scalar_one_or_none()
                if var:
                    media_path = media_processor.storage_service.get_real_path(var.storage_key)
                    text_content = var.title or text_content

        # Get active policy version
        policy = await self.get_active_policy(session, scope="GLOBAL")
        policy_version = policy.policy_version if policy else 1

        # Delete historical checks for this run
        old_checks = await session.execute(
            select(QualityCheck).where(
                and_(
                    QualityCheck.content_id == content_id,
                    QualityCheck.variant_id == variant_id,
                    QualityCheck.publication_id == publication_id
                )
            )
        )
        for check in old_checks.scalars().all():
            await session.delete(check)

        # 2. RUN Technical Checks
        media_info = None
        if media_path:
            tech_res = await self.check_media_validity(media_path, content_type)
            if tech_res["status"] == "PASSED":
                media_info = tech_res["details"]
            
            qc_check = QualityCheck(
                id=f"qck_{uuid.uuid4().hex[:12]}",
                content_id=content_id,
                variant_id=variant_id,
                publication_id=publication_id,
                check_type="MEDIA_VALIDITY",
                status=tech_res["status"],
                severity=tech_res["severity"],
                message=tech_res["message"],
                details=tech_res["details"],
                policy_version=policy_version
            )
            session.add(qc_check)

        # 3. RUN Platform checks
        plat_res = await self.check_platform_compatibility(platform, content_type, text_content, media_info)
        qc_plat = QualityCheck(
            id=f"qck_{uuid.uuid4().hex[:12]}",
            content_id=content_id,
            variant_id=variant_id,
            publication_id=publication_id,
            check_type="PLATFORM_COMPATIBILITY",
            status=plat_res["status"],
            severity=plat_res["severity"],
            message=plat_res["message"],
            details=plat_res["details"],
            policy_version=policy_version
        )
        session.add(qc_plat)

        # 4. RUN Duplicate Checks
        dup_results = await self.check_duplicates(session, platform, text_content, content_id)
        for dup in dup_results:
            qc_dup = QualityCheck(
                id=f"qck_{uuid.uuid4().hex[:12]}",
                content_id=content_id,
                variant_id=variant_id,
                publication_id=publication_id,
                check_type="DUPLICATE_CONTENT",
                status=dup["status"],
                severity=dup["severity"],
                message=dup["message"],
                details=dup["details"],
                policy_version=policy_version
            )
            session.add(qc_dup)

        # 5. RUN Brand compliance checks
        brand_profile_res = await session.execute(select(BrandProfile))
        profile = brand_profile_res.scalars().first()
        if profile:
            brand_results = await self.check_brand_compliance(text_content, profile)
            for brd in brand_results:
                qc_brd = QualityCheck(
                    id=f"qck_{uuid.uuid4().hex[:12]}",
                    content_id=content_id,
                    variant_id=variant_id,
                    publication_id=publication_id,
                    check_type="BRAND_COMPLIANCE",
                    status=brd["status"],
                    severity=brd["severity"],
                    message=brd["message"],
                    details=brd["details"],
                    policy_version=policy_version
                )
                session.add(qc_brd)

        # 6. RUN AI Claim / Hallucination check
        ai_claims = await self.evaluate_ai_claims(session, content_id, text_content)
        for claim in ai_claims:
            qc_claim = QualityCheck(
                id=f"qck_{uuid.uuid4().hex[:12]}",
                content_id=content_id,
                variant_id=variant_id,
                publication_id=publication_id,
                check_type="AI_CONTENT_QUALITY",
                status=claim["status"],
                severity=claim["severity"],
                message=claim["message"],
                details=claim["details"],
                policy_version=policy_version
            )
            session.add(qc_claim)

        # Commit and aggregate
        await session.commit()

        # Reload all checks to calculate final outcome
        all_checks_res = await session.execute(
            select(QualityCheck).where(
                and_(
                    QualityCheck.content_id == content_id,
                    QualityCheck.variant_id == variant_id,
                    QualityCheck.publication_id == publication_id
                )
            )
        )
        all_checks = all_checks_res.scalars().all()

        blocking_count = 0
        warning_count = 0
        info_count = 0

        for check in all_checks:
            if check.status == "FAILED" and check.severity == "BLOCKING":
                blocking_count += 1
            elif check.status == "WARNING" or (check.status == "FAILED" and check.severity == "WARNING"):
                warning_count += 1
            else:
                info_count += 1

        final_status = "PASS"
        if blocking_count > 0:
            final_status = "BLOCKED"
        elif warning_count > 0:
            final_status = "PASS_WITH_WARNINGS"

        # Update GovernanceResult
        old_res = await session.execute(
            select(GovernanceResult).where(GovernanceResult.content_id == content_id)
        )
        for old in old_res.scalars().all():
            await session.delete(old)

        gov_res = GovernanceResult(
            id=f"gov_{uuid.uuid4().hex[:12]}",
            content_id=content_id,
            status=final_status,
            blocking_count=blocking_count,
            warning_count=warning_count,
            info_count=info_count,
            evaluated_at=datetime.utcnow(),
            policy_version=policy_version
        )
        session.add(gov_res)
        await session.commit()

        # Also update content status in lifecycle checks
        if final_status == "BLOCKED":
            content.status = "BLOCKED"
        elif content.status == "BLOCKED" and final_status != "BLOCKED":
            content.status = "READY"
        await session.commit()

        return {
            "status": final_status,
            "blocking_count": blocking_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "checks": all_checks
        }

    async def execute_autofix(self, text_content: str) -> str:
        """Deterministic fix: removes duplicate spaces and normalizes hashtags/spacing."""
        if not text_content:
            return ""
        # 1. Trims double whitespace
        fixed = re.sub(r"\s+", " ", text_content).strip()
        # 2. Removes spacing issues before hashtags
        fixed = re.sub(r"\s+#", " #", fixed)
        return fixed

quality_control_service = QualityControlService()
