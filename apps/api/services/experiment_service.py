import re
import uuid
import json
import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from models.entities import (
    Experiment, ExperimentVariant, ExperimentResult, Publication,
    PostMetricSnapshot, ContentPattern, ContentRecommendation, Content
)
from utils.logging import get_logger

logger = get_logger("ExperimentService")

class ExperimentService:

    # --------------------------------------------------------------------------
    # 1. Experiment Creation & Design Validation
    # --------------------------------------------------------------------------

    async def create_experiment(
        self,
        db: AsyncSession,
        name: str,
        hypothesis: str,
        platform: str,
        primary_metric: str,
        scope: str,
        control_content_id: str,
        treatment_content_id: str,
        control_variant_id: Optional[str] = None,
        treatment_variant_id: Optional[str] = None,
        control_publication_id: Optional[str] = None,
        treatment_publication_id: Optional[str] = None,
        secondary_metrics: Optional[List[str]] = None,
        minimum_sample_size: int = 5,
        confidence_level: float = 0.95,
        recommendation_id: Optional[str] = None,
        created_by: Optional[str] = None,
        evaluation_window_hours: int = 24
    ) -> Experiment:
        """
        Creates and validates a new experiment.
        """
        # Validate scope
        valid_scopes = ["HOOK", "CAPTION", "THUMBNAIL", "TITLE", "DURATION", "FORMAT", "CAROUSEL_TEMPLATE", "CTA", "POSTING_WINDOW"]
        if scope not in valid_scopes:
            raise ValueError(f"Invalid scope '{scope}'. Must be one of {valid_scopes}")

        # Validate metrics
        valid_metrics = ["engagement_rate", "views", "completion_rate", "click_rate", "likes", "comments", "shares", "saves", "watch_time_seconds"]
        if primary_metric not in valid_metrics:
            raise ValueError(f"Invalid primary metric '{primary_metric}'.")

        # 1. Validation: Single Variable Principle & Mismatches
        if control_content_id != treatment_content_id and scope not in ["DURATION", "FORMAT", "CAROUSEL_TEMPLATE"]:
            # If they are different source contents but we claim to test hook, caption, etc., raise error or warning
            raise ValueError("Control and Treatment must share the same source Content family for hook/caption/CTA/thumbnail/posting_window tests.")

        # Expose design validation: control vs treatment must have same platform
        # Let's verify publications if provided
        if control_publication_id and treatment_publication_id:
            ctrl_pub = await db.get(Publication, control_publication_id)
            treat_pub = await db.get(Publication, treatment_publication_id)
            if ctrl_pub and treat_pub:
                if ctrl_pub.platform != treat_pub.platform:
                    raise ValueError("Control and Treatment publications must be on the same platform.")

        exp_id = f"exp_{uuid.uuid4().hex[:8]}"
        
        # Set titles/variable_tested for backwards compatibility with Phase 11
        experiment = Experiment(
            id=exp_id,
            name=name,
            title=name,  # compatibility
            description=f"Controlled experiment testing {scope} on {platform}",
            hypothesis=hypothesis,
            status="DRAFT",
            scope=scope,
            variable_tested=scope,  # compatibility
            platform=platform,
            created_at=datetime.utcnow(),
            minimum_sample_size=minimum_sample_size,
            target_sample_size=minimum_sample_size,  # compatibility
            primary_metric=primary_metric,
            success_metric=primary_metric,  # compatibility
            secondary_metrics=secondary_metrics or [],
            confidence_level=confidence_level,
            created_by=created_by,
            recommendation_id=recommendation_id,
            results_json=json.dumps({"evaluation_window_hours": evaluation_window_hours})
        )
        db.add(experiment)
        await db.flush()

        # Add Control Variant
        ctrl_var = ExperimentVariant(
            id=f"var_ctrl_{uuid.uuid4().hex[:8]}",
            experiment_id=exp_id,
            name="Control Variant",
            description="Default baseline variant",
            content_id=control_content_id,
            content_variant_id=control_variant_id,
            publication_id=control_publication_id,
            variant_type=scope,
            role="CONTROL",
            created_at=datetime.utcnow()
        )
        db.add(ctrl_var)

        # Add Treatment Variant
        treat_var = ExperimentVariant(
            id=f"var_treat_{uuid.uuid4().hex[:8]}",
            experiment_id=exp_id,
            name="Treatment Variant",
            description="Variant containing the tested hypothesis modification",
            content_id=treatment_content_id,
            content_variant_id=treatment_variant_id,
            publication_id=treatment_publication_id,
            variant_type=scope,
            role="TREATMENT",
            created_at=datetime.utcnow()
        )
        db.add(treat_var)

        await db.commit()
        logger.info(f"Experiment '{name}' ({exp_id}) created in DRAFT.")
        return experiment

    # --------------------------------------------------------------------------
    # 2. Confound & Design Warning Generator
    # --------------------------------------------------------------------------

    async def detect_confounds(self, db: AsyncSession, experiment: Experiment) -> List[Dict[str, str]]:
        """
        Scans variants and publications for experimental confounds.
        """
        warnings = []
        # Query variants explicitly to prevent lazy load MissingGreenlet error
        res_vars = await db.execute(
            select(ExperimentVariant).where(ExperimentVariant.experiment_id == experiment.id)
        )
        variants = res_vars.scalars().all()
        if len(variants) < 2:
            return [{"code": "INSUFFICIENT_VARIANTS", "message": "Experiment requires at least one Control and one Treatment variant."}]

        control = next((v for v in variants if v.role == "CONTROL"), None)
        treatment = next((v for v in variants if v.role == "TREATMENT"), None)

        if not control or not treatment:
            return [{"code": "INSUFFICIENT_DESIGN", "message": "Experiment must specify exactly one CONTROL and one TREATMENT."}]

        # 1. Content mismatch warning
        if control.content_id != treatment.content_id:
            if experiment.scope not in ["DURATION", "FORMAT", "CAROUSEL_TEMPLATE"]:
                warnings.append({
                    "code": "CONTENT_MISMATCH",
                    "message": f"Variants belong to different source contents ({control.content_id} vs {treatment.content_id}). This introduces thematic confounds."
                })

        # 2. Platform mismatch warning/error
        ctrl_pub = await db.get(Publication, control.publication_id) if control.publication_id else None
        treat_pub = await db.get(Publication, treatment.publication_id) if treatment.publication_id else None

        if ctrl_pub and treat_pub:
            if ctrl_pub.platform != treat_pub.platform:
                warnings.append({
                    "code": "PLATFORM_MISMATCH",
                    "message": f"Control is published on {ctrl_pub.platform} while Treatment is on {treat_pub.platform}. Platforms are not comparable."
                })
            
            # Audience mismatch (different connection/account)
            # Fetch connections for credentials to compare account ids or names if possible
            if ctrl_pub.platform_connection_id != treat_pub.platform_connection_id:
                warnings.append({
                    "code": "AUDIENCE_MISMATCH",
                    "message": "Variants were published to different accounts/connections. Audience distributions differ."
                })

            # Posting Time Confound
            if ctrl_pub.published_at and treat_pub.published_at:
                time_diff = abs(ctrl_pub.published_at - treat_pub.published_at)
                if time_diff > timedelta(days=2):
                    warnings.append({
                        "code": "POSTING_TIME_MISMATCH",
                        "message": f"Variants were published {time_diff.days} days apart. Weekly audience cycles may confound results."
                    })
                
                # Check hour difference
                ctrl_hour = ctrl_pub.published_at.hour
                treat_hour = treat_pub.published_at.hour
                hour_diff = abs(ctrl_hour - treat_hour)
                if hour_diff > 4 and hour_diff < 20:
                    warnings.append({
                        "code": "POSTING_HOUR_MISMATCH",
                        "message": f"Variants were published at different times of day ({ctrl_hour}:00 vs {treat_hour}:00 UTC). Daily usage patterns differ."
                    })
        else:
            warnings.append({
                "code": "INSUFFICIENT_METRICS",
                "message": "One or both variants do not have publications mapped yet."
            })

        return warnings

    # --------------------------------------------------------------------------
    # 3. Statistical Calculations Engine
    # --------------------------------------------------------------------------

    def calculate_rate_z_test(
        self,
        ctrl_successes: int,
        ctrl_trials: int,
        treat_successes: int,
        treat_trials: int,
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        Calculates Two-Proportion Z-Test metrics, confidence intervals, p-value, and significance.
        """
        if ctrl_trials <= 0 or treat_trials <= 0:
            return {
                "p_value": None,
                "statistical_significance": False,
                "confidence_interval_low": None,
                "confidence_interval_high": None,
                "effect_size_absolute": 0.0,
                "effect_size_relative": None
            }

        p1 = ctrl_successes / ctrl_trials
        p2 = treat_successes / treat_trials

        # Absolute & Relative differences
        abs_diff = p2 - p1
        rel_diff = (p2 - p1) / p1 if p1 > 0 else None

        # Pooled proportion
        p_pool = (ctrl_successes + treat_successes) / (ctrl_trials + treat_trials)
        
        # Standard Error (pooled for hypothesis test)
        if p_pool <= 0 or p_pool >= 1:
            z_score = 0.0
            p_value = 1.0
        else:
            se_pool = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / ctrl_trials + 1.0 / treat_trials))
            z_score = abs_diff / se_pool if se_pool > 0 else 0.0
            # Two-sided p-value using erfc
            p_value = math.erfc(abs(z_score) / math.sqrt(2.0))

        # Confidence Interval for difference (unpooled standard error)
        se_diff = math.sqrt((p1 * (1.0 - p1) / ctrl_trials) + (p2 * (1.0 - p2) / treat_trials))
        
        # Critical value for confidence level (default 95% -> 1.96)
        # Simple lookup for common confidence levels
        if confidence_level >= 0.99:
            z_crit = 2.576
        elif confidence_level >= 0.95:
            z_crit = 1.96
        elif confidence_level >= 0.90:
            z_crit = 1.645
        else:
            z_crit = 1.28

        ci_margin = z_crit * se_diff
        ci_low = abs_diff - ci_margin
        ci_high = abs_diff + ci_margin

        # Alpha threshold
        alpha = 1.0 - confidence_level
        stat_sig = p_value < alpha if p_value is not None else False

        return {
            "p_value": p_value,
            "statistical_significance": stat_sig,
            "confidence_interval_low": ci_low,
            "confidence_interval_high": ci_high,
            "effect_size_absolute": abs_diff,
            "effect_size_relative": rel_diff
        }

    def calculate_continuous_t_test(
        self,
        ctrl_values: List[float],
        treat_values: List[float],
        confidence_level: float = 0.95
    ) -> Dict[str, Any]:
        """
        Calculates simple two-sample T-test with Welch's normal approximation for continuous variables.
        """
        n1 = len(ctrl_values)
        n2 = len(treat_values)

        if n1 <= 0 or n2 <= 0:
            return {
                "p_value": None,
                "statistical_significance": False,
                "confidence_interval_low": None,
                "confidence_interval_high": None,
                "effect_size_absolute": 0.0,
                "effect_size_relative": None
            }

        mean1 = sum(ctrl_values) / n1
        mean2 = sum(treat_values) / n2

        abs_diff = mean2 - mean1
        rel_diff = (mean2 - mean1) / mean1 if mean1 > 0 else None

        # Sample variances
        var1 = sum((x - mean1)**2 for x in ctrl_values) / max(1, n1 - 1)
        var2 = sum((x - mean2)**2 for x in treat_values) / max(1, n2 - 1)

        # Standard error of difference
        se = math.sqrt((var1 / n1) + (var2 / n2))
        z_score = abs_diff / se if se > 0 else 0.0
        p_value = math.erfc(abs(z_score) / math.sqrt(2.0))

        # Confidence limits
        if confidence_level >= 0.99:
            z_crit = 2.576
        elif confidence_level >= 0.95:
            z_crit = 1.96
        elif confidence_level >= 0.90:
            z_crit = 1.645
        else:
            z_crit = 1.28

        ci_margin = z_crit * se
        ci_low = abs_diff - ci_margin
        ci_high = abs_diff + ci_margin

        alpha = 1.0 - confidence_level
        stat_sig = p_value < alpha if p_value is not None else False

        return {
            "p_value": p_value,
            "statistical_significance": stat_sig,
            "confidence_interval_low": ci_low,
            "confidence_interval_high": ci_high,
            "effect_size_absolute": abs_diff,
            "effect_size_relative": rel_diff
        }

    # --------------------------------------------------------------------------
    # 4. Asynchronous Evaluation Logic
    # --------------------------------------------------------------------------

    async def evaluate_experiment(self, db: AsyncSession, experiment_id: str) -> Dict[str, Any]:
        """
        Pulls metric snapshots at aligned windows and recalculates stats.
        """
        logger.info(f"Evaluating experiment: {experiment_id}")
        res_exp = await db.execute(
            select(Experiment)
            .where(Experiment.id == experiment_id)
            .options(selectinload(Experiment.variants))
        )
        experiment = res_exp.scalar_one_or_none()
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found.")

        # Get window hours config
        window_hours = 24
        try:
            cfg = json.loads(experiment.results_json)
            window_hours = cfg.get("evaluation_window_hours", 24)
        except:
            pass

        variants = experiment.variants
        control = next((v for v in variants if v.role == "CONTROL"), None)
        treatment = next((v for v in variants if v.role == "TREATMENT"), None)

        if not control or not treatment:
            experiment.status = "INSUFFICIENT_DATA"
            await db.commit()
            return {"status": "error", "message": "Missing Control or Treatment variant."}

        # Retrieve publications mapped to each
        # We can map single publication or list of publications.
        # Let's search publications associated with the variant (either linked directly by publication_id or by content_id + content_variant_id)
        async def get_variant_publications(variant: ExperimentVariant) -> List[Publication]:
            if variant.publication_id:
                pub = await db.get(Publication, variant.publication_id)
                return [pub] if pub else []
            # Else, find all publications matching content_id and content_variant_id and platform
            q = select(Publication).where(
                and_(
                    Publication.content_id == variant.content_id,
                    Publication.variant_id == variant.content_variant_id,
                    Publication.status == "PUBLISHED"
                )
            )
            res = await db.execute(q)
            return res.scalars().all()

        ctrl_pubs = await get_variant_publications(control)
        treat_pubs = await get_variant_publications(treatment)

        # Time aligned snapshot fetching
        async def fetch_aligned_snapshot_metrics(pub: Publication) -> Optional[PostMetricSnapshot]:
            if not pub.published_at:
                return None
            target_time = pub.published_at + timedelta(hours=window_hours)
            
            # Fetch all snapshots for this publication
            res = await db.execute(
                select(PostMetricSnapshot)
                .where(PostMetricSnapshot.publication_id == pub.id)
            )
            snaps = res.scalars().all()
            if not snaps:
                return None

            # Sort in memory by closeness to the evaluation window target time
            # Only compare variants using equivalent observation windows.
            # If the publication hasn't reached the evaluation window age yet, we flag it or warn.
            target_ts = target_time.timestamp()
            now_ts = datetime.utcnow().timestamp()
            
            # If now is before target_time, and post age is less than evaluation window, this publication is not ready
            pub_age_hours = (datetime.utcnow() - pub.published_at).total_seconds() / 3600.0
            if pub_age_hours < window_hours:
                # Flag to prevent declaring winner on incomplete window
                return "PENDING"

            best_snap = min(snaps, key=lambda s: abs(s.captured_at.timestamp() - target_ts))
            return best_snap

        # Collect aligned metrics for control
        ctrl_snaps = []
        ctrl_pending = False
        for p in ctrl_pubs:
            snap = await fetch_aligned_snapshot_metrics(p)
            if snap == "PENDING":
                ctrl_pending = True
            elif snap:
                ctrl_snaps.append(snap)

        # Collect aligned metrics for treatment
        treat_snaps = []
        treat_pending = False
        for p in treat_pubs:
            snap = await fetch_aligned_snapshot_metrics(p)
            if snap == "PENDING":
                treat_pending = True
            elif snap:
                treat_snaps.append(snap)

        total_samples = len(ctrl_snaps) + len(treat_snaps)
        experiment.current_sample_size = total_samples

        # Check for unequal evaluation windows or pending publications
        if ctrl_pending or treat_pending:
            # We have publications that are not yet aged enough
            experiment.status = "RUNNING"
            await db.commit()
            return {
                "status": "collecting_data",
                "message": "Some publications have not reached the evaluation window age yet."
            }

        # Check sample size threshold
        if total_samples < experiment.minimum_sample_size:
            experiment.status = "INSUFFICIENT_DATA"
            await db.commit()
            return {
                "status": "insufficient_data",
                "message": f"Sample size {total_samples} is below the minimum threshold ({experiment.minimum_sample_size})."
            }

        # Extract metric values
        metric = experiment.primary_metric

        def get_metric_val(snap: PostMetricSnapshot, metric_name: str) -> Optional[float]:
            val = getattr(snap, metric_name, None)
            if val is not None:
                return float(val)
            # Custom ER or other math
            if metric_name == "engagement_rate":
                eng = getattr(snap, "engagements", None)
                reach = getattr(snap, "reach", None) or getattr(snap, "views", None)
                if eng is not None and reach and reach > 0:
                    return float(eng) / float(reach)
            return None

        ctrl_vals = [get_metric_val(s, metric) for s in ctrl_snaps if get_metric_val(s, metric) is not None]
        treat_vals = [get_metric_val(s, metric) for s in treat_snaps if get_metric_val(s, metric) is not None]

        # Robust trimmed median filtering to resist viral outliers
        def get_robust_values(values: List[float]) -> List[float]:
            if len(values) < 5:
                return values
            # Trim top/bottom 5%
            sorted_v = sorted(values)
            trim_cnt = max(1, int(len(values) * 0.05))
            return sorted_v[trim_cnt:-trim_cnt]

        ctrl_vals_clean = get_robust_values(ctrl_vals)
        treat_vals_clean = get_robust_values(treat_vals)

        # Run stats
        is_rate = metric in ["engagement_rate", "completion_rate", "click_rate"]
        
        if is_rate:
            # Back-calculate aggregated successes and trials to run Two-Proportion Z-Test
            ctrl_trials = 0
            ctrl_success = 0
            for s in ctrl_snaps:
                trials = getattr(s, "reach", None) or getattr(s, "views", None) or 1
                rate = get_metric_val(s, metric) or 0.0
                ctrl_trials += int(trials)
                ctrl_success += int(rate * trials)

            treat_trials = 0
            treat_success = 0
            for s in treat_snaps:
                trials = getattr(s, "reach", None) or getattr(s, "views", None) or 1
                rate = get_metric_val(s, metric) or 0.0
                treat_trials += int(trials)
                treat_success += int(rate * trials)

            stats = self.calculate_rate_z_test(
                ctrl_success, ctrl_trials,
                treat_success, treat_trials,
                experiment.confidence_level
            )
            ctrl_metric_mean = ctrl_success / ctrl_trials if ctrl_trials > 0 else 0.0
            treat_metric_mean = treat_success / treat_trials if treat_trials > 0 else 0.0
        else:
            # Raw count metric (e.g. views)
            stats = self.calculate_continuous_t_test(
                ctrl_vals_clean, treat_vals_clean,
                experiment.confidence_level
            )
            ctrl_metric_mean = sum(ctrl_vals_clean) / len(ctrl_vals_clean) if ctrl_vals_clean else 0.0
            treat_metric_mean = sum(treat_vals_clean) / len(treat_vals_clean) if treat_vals_clean else 0.0

        # Determine winner logic
        conclusion = "NO_CLEAR_WINNER"
        winner_id = None
        
        # Practical significance threshold (e.g., minimum absolute effect size or relative change)
        min_practical_effect = 0.01  # 1 percentage point for rates, or 5% relative for counts
        effect_abs = stats["effect_size_absolute"] or 0.0
        effect_rel = stats["effect_size_relative"]

        practical_sig = False
        if is_rate:
            practical_sig = abs(effect_abs) >= min_practical_effect
        else:
            if effect_rel is not None:
                practical_sig = abs(effect_rel) >= 0.05

        if stats["statistical_significance"] and practical_sig:
            if effect_abs > 0:
                conclusion = "VARIANT_B_WINS"  # Treatment wins
                winner_id = treatment.id
            else:
                conclusion = "VARIANT_A_WINS"  # Control wins
                winner_id = control.id
        elif stats["statistical_significance"]:
            # Statistically significant but practically irrelevant
            conclusion = "NO_CLEAR_WINNER"
        else:
            conclusion = "NO_CLEAR_WINNER"

        # Update experiment state
        experiment.status = "COMPLETED"
        experiment.winner_variant_id = winner_id
        experiment.conclusion = conclusion

        # Clear old results to prevent duplicates and maintain history
        await db.execute(delete(ExperimentResult).where(ExperimentResult.experiment_id == experiment_id))

        # Save result card for Control
        ctrl_res = ExperimentResult(
            id=f"res_{uuid.uuid4().hex[:8]}",
            experiment_id=experiment_id,
            evaluated_at=datetime.utcnow(),
            variant_id=control.id,
            sample_size=len(ctrl_snaps),
            primary_metric=metric,
            metric_value=ctrl_metric_mean,
            status=conclusion
        )
        db.add(ctrl_res)

        # Save result card for Treatment
        treat_res = ExperimentResult(
            id=f"res_{uuid.uuid4().hex[:8]}",
            experiment_id=experiment_id,
            evaluated_at=datetime.utcnow(),
            variant_id=treatment.id,
            sample_size=len(treat_snaps),
            primary_metric=metric,
            metric_value=treat_metric_mean,
            confidence_interval_low=stats["confidence_interval_low"],
            confidence_interval_high=stats["confidence_interval_high"],
            effect_size_absolute=stats["effect_size_absolute"],
            effect_size_relative=stats["effect_size_relative"],
            p_value=stats["p_value"],
            statistical_significance=stats["statistical_significance"],
            practical_significance=practical_sig,
            status=conclusion
        )
        db.add(treat_res)

        # Closed-loop intelligence feedback update
        await self.run_feedback_loop(db, experiment, conclusion)

        await db.commit()
        logger.info(f"Experiment {experiment_id} evaluated. Winner: {winner_id}, Conclusion: {conclusion}")
        return {
            "status": "completed",
            "conclusion": conclusion,
            "winner_variant_id": winner_id,
            "effect_size_absolute": stats["effect_size_absolute"],
            "p_value": stats["p_value"]
        }

    # --------------------------------------------------------------------------
    # 5. Closed-Loop Intelligence Feedback Hook
    # --------------------------------------------------------------------------

    async def run_feedback_loop(self, db: AsyncSession, experiment: Experiment, conclusion: str):
        """
        Integrates experiment outcomes back into Content Intelligence (Phase 11).
        Updates confidence levels and correlation ratios of matching patterns/recommendations.
        """
        if conclusion == "NO_CLEAR_WINNER":
            return

        # Find matching content patterns in database
        # E.g. scope is HOOK, variable_tested is hook_type, etc.
        # Find recommendation linked
        rec = None
        if experiment.recommendation_id:
            rec = await db.get(ContentRecommendation, experiment.recommendation_id)

        # Find associated patterns to update
        # If TREATMENT wins, it verifies our pattern/hypothesis.
        # If CONTROL wins, it refutes the hypothesis.
        is_hypothesis_verified = (conclusion == "VARIANT_B_WINS")

        # Let's search pattern matching variable/scope and primary platform
        q_pat = select(ContentPattern).where(
            and_(
                ContentPattern.pattern_type == experiment.scope,
                ContentPattern.created_at >= datetime.utcnow() - timedelta(days=90)
            )
        )
        res_pat = await db.execute(q_pat)
        patterns = res_pat.scalars().all()

        for pat in patterns:
            # Update pattern correlation ratio and confidence
            if is_hypothesis_verified:
                pat.correlation_ratio = (pat.correlation_ratio or 1.0) * 1.10
                pat.sample_size = (pat.sample_size or 0) + experiment.current_sample_size
            else:
                pat.correlation_ratio = (pat.correlation_ratio or 1.0) * 0.90
                pat.sample_size = (pat.sample_size or 0) + experiment.current_sample_size

        if rec:
            if is_hypothesis_verified:
                rec.confidence = "HIGH"
            else:
                rec.confidence = "LOW"
                rec.status = "DISMISSED"

        logger.info(f"Feedback loop processed. Updated patterns and recommendation {rec.id if rec else 'None'} confidence.")

# Instantiate Singleton service
experiment_service = ExperimentService()
