import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, update, delete

from database import async_session_factory
from models.entities import Incident, IncidentEvent, AlertRule, Notification, SystemEvent
from utils.logging import get_logger

logger = get_logger("IncidentService")

class IncidentService:
    """
    Real Incident Management, Deduplication, Alerting & Reliability Engine for Reflow.
    Groups identical failures into single incidents, tracks incident timelines,
    enforces resolution notes, evaluates alert rules with cooldowns, and manages Maintenance Mode.
    """
    _instance: Optional['IncidentService'] = None

    def __init__(self):
        self._maintenance_mode: bool = False
        self._maintenance_reason: str = ""

    @classmethod
    def get_instance(cls) -> 'IncidentService':
        if cls._instance is None:
            cls._instance = IncidentService()
        return cls._instance

    def is_maintenance_mode(self) -> bool:
        return self._maintenance_mode

    def set_maintenance_mode(self, enabled: bool, reason: str = "Operator maintenance"):
        self._maintenance_mode = enabled
        self._maintenance_reason = reason
        logger.info(f"Maintenance mode set to {enabled} (reason: '{reason}').")

    async def report_job_failure(
        self,
        component: str,
        error_code: str,
        message: str,
        job_id: Optional[str] = None,
        content_id: Optional[str] = None,
        severity: str = "HIGH"
    ) -> Incident:
        """
        Reports a component failure and automatically deduplicates/groups identical failures
        occurring for the same component + error_code within a 15-minute window.
        """
        async with async_session_factory() as session:
            window_start = datetime.utcnow() - timedelta(minutes=15)
            res = await session.execute(
                select(Incident).where(
                    Incident.component == component,
                    Incident.error_code == error_code,
                    Incident.status.in_(["OPEN", "INVESTIGATING"]),
                    Incident.started_at >= window_start
                ).order_by(Incident.started_at.desc())
            )
            existing_incident = res.scalars().first()

            if existing_incident:
                # Deduplicate & Append to existing incident affected resources
                try:
                    res_data = json.loads(existing_incident.affected_resources_json or "{}")
                except:
                    res_data = {}

                jobs = set(res_data.get("affected_jobs", []))
                contents = set(res_data.get("affected_content", []))
                if job_id: jobs.add(job_id)
                if content_id: contents.add(content_id)

                res_data["affected_jobs"] = list(jobs)
                res_data["affected_content"] = list(contents)
                res_data["failure_count"] = res_data.get("failure_count", 1) + 1

                existing_incident.affected_resources_json = json.dumps(res_data)

                # Timeline Event
                evt = IncidentEvent(
                    id=str(uuid.uuid4()),
                    incident_id=existing_incident.id,
                    event_type="FAILURE_RECURRED",
                    description=f"Recurred failure in {component}: {message}"
                )
                session.add(evt)
                await session.commit()
                logger.info(f"Deduplicated failure event into existing incident {existing_incident.id}")
                return existing_incident

            # Create New Grouped Incident
            inc_id = f"inc_{uuid.uuid4().hex[:10]}"
            title = f"Component Failure in {component} ({error_code})"
            res_data = {
                "affected_jobs": [job_id] if job_id else [],
                "affected_content": [content_id] if content_id else [],
                "failure_count": 1
            }

            incident = Incident(
                id=inc_id,
                title=title,
                severity=severity,
                status="OPEN",
                component=component,
                error_code=error_code,
                description=message,
                started_at=datetime.utcnow(),
                affected_resources_json=json.dumps(res_data)
            )
            session.add(incident)

            evt = IncidentEvent(
                id=str(uuid.uuid4()),
                incident_id=inc_id,
                event_type="INCIDENT_CREATED",
                description=f"Incident opened for {component}: {message}"
            )
            session.add(evt)
            await session.commit()

            logger.warning(f"Created new incident {inc_id} (severity={severity}, component={component})")
            return incident

    async def list_incidents(
        self,
        session,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        component: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Lists incidents with optional filtering."""
        query = select(Incident).order_by(Incident.started_at.desc())
        if status and status.upper() != "ALL":
            query = query.where(Incident.status == status.upper())
        if severity and severity.upper() != "ALL":
            query = query.where(Incident.severity == severity.upper())
        if component:
            query = query.where(Incident.component == component)

        res = await session.execute(query)
        incidents = res.scalars().all()
        results = []
        for inc in incidents:
            try:
                aff = json.loads(inc.affected_resources_json or "{}")
            except:
                aff = {}
            results.append({
                "id": inc.id,
                "title": inc.title,
                "severity": inc.severity,
                "status": inc.status,
                "component": inc.component,
                "error_code": inc.error_code,
                "description": inc.description,
                "started_at": inc.started_at,
                "resolved_at": inc.resolved_at,
                "acknowledged_at": inc.acknowledged_at,
                "acknowledged_by": inc.acknowledged_by,
                "resolution_note": inc.resolution_note,
                "affected_resources": aff
            })
        return results

    async def get_incident(self, session, incident_id: str) -> Optional[Dict[str, Any]]:
        """Gets detailed incident metadata including timeline history events."""
        res = await session.execute(select(Incident).where(Incident.id == incident_id))
        inc = res.scalar_one_or_none()
        if not inc:
            return None

        evt_res = await session.execute(
            select(IncidentEvent).where(IncidentEvent.incident_id == incident_id).order_by(IncidentEvent.created_at.asc())
        )
        events = evt_res.scalars().all()

        try:
            aff = json.loads(inc.affected_resources_json or "{}")
        except:
            aff = {}

        return {
            "id": inc.id,
            "title": inc.title,
            "severity": inc.severity,
            "status": inc.status,
            "component": inc.component,
            "error_code": inc.error_code,
            "description": inc.description,
            "started_at": inc.started_at,
            "resolved_at": inc.resolved_at,
            "acknowledged_at": inc.acknowledged_at,
            "acknowledged_by": inc.acknowledged_by,
            "resolution_note": inc.resolution_note,
            "affected_resources": aff,
            "timeline": [
                {
                    "id": e.id,
                    "event_type": e.event_type,
                    "description": e.description,
                    "created_at": e.created_at
                } for e in events
            ]
        }

    async def acknowledge_incident(self, session, incident_id: str, acknowledged_by: str = "Operator") -> Dict[str, Any]:
        """Marks an incident as INVESTIGATING and records operator acknowledgement."""
        res = await session.execute(select(Incident).where(Incident.id == incident_id))
        inc = res.scalar_one_or_none()
        if not inc:
            raise ValueError("INCIDENT_NOT_FOUND")

        inc.status = "INVESTIGATING"
        inc.acknowledged_at = datetime.utcnow()
        inc.acknowledged_by = acknowledged_by

        evt = IncidentEvent(
            id=str(uuid.uuid4()),
            incident_id=incident_id,
            event_type="ACKNOWLEDGED",
            description=f"Incident acknowledged by {acknowledged_by}."
        )
        session.add(evt)
        await session.commit()

        logger.info(f"Incident {incident_id} acknowledged by {acknowledged_by}.")
        return {"status": "success", "incident_id": incident_id, "state": "INVESTIGATING"}

    async def resolve_incident(self, session, incident_id: str, resolution_note: str) -> Dict[str, Any]:
        """Resolves an incident with mandatory resolution note explanation."""
        if not resolution_note or len(resolution_note.strip()) < 5:
            raise ValueError("RESOLUTION_NOTE_REQUIRED: Explicit resolution explanation required.")

        res = await session.execute(select(Incident).where(Incident.id == incident_id))
        inc = res.scalar_one_or_none()
        if not inc:
            raise ValueError("INCIDENT_NOT_FOUND")

        inc.status = "RESOLVED"
        inc.resolved_at = datetime.utcnow()
        inc.resolution_note = resolution_note.strip()

        evt = IncidentEvent(
            id=str(uuid.uuid4()),
            incident_id=incident_id,
            event_type="RESOLVED",
            description=f"Incident resolved: {resolution_note.strip()}"
        )
        session.add(evt)
        await session.commit()

        logger.info(f"Incident {incident_id} resolved with note: '{resolution_note}'")
        return {"status": "success", "incident_id": incident_id, "state": "RESOLVED"}

    async def evaluate_alert_rules(self, session) -> List[Dict[str, Any]]:
        """Evaluates declarative alert rules and triggers notifications respecting cooldown timers."""
        res = await session.execute(select(AlertRule).where(AlertRule.enabled == True))
        rules = res.scalars().all()
        triggered = []

        now = datetime.utcnow()
        for rule in rules:
            if rule.last_triggered_at:
                cooldown_expiry = rule.last_triggered_at + timedelta(minutes=rule.cooldown_minutes)
                if now < cooldown_expiry:
                    continue # Cooldown active

            # Evaluate condition
            should_trigger = False
            details_str = ""

            if rule.condition_type == "OPEN_INCIDENTS":
                inc_res = await session.execute(select(Incident).where(Incident.status.in_(["OPEN", "INVESTIGATING"])))
                open_count = len(inc_res.scalars().all())
                if open_count >= rule.threshold_value:
                    should_trigger = True
                    details_str = f"{open_count} active open incidents detected."

            if should_trigger:
                rule.last_triggered_at = now
                
                # Create In-App Notification
                notif = Notification(
                    id=str(uuid.uuid4()),
                    type="ALERT_TRIGGERED",
                    title=f"Alert: {rule.name}",
                    message=details_str,
                    severity="ERROR" if rule.severity == "HIGH" else "WARNING",
                    read=False
                )
                session.add(notif)
                triggered.append({"rule_id": rule.id, "name": rule.name, "message": details_str})

        if triggered:
            await session.commit()
        return triggered

incident_service = IncidentService.get_instance()
