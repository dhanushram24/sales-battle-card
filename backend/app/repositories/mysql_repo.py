import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.repositories.base import BaseLeadRepository
from app.schemas.lead import LeadInfo, LeadInteraction, LeadUpdate


class InteractionSourceError(RuntimeError):
    pass

logger = logging.getLogger(__name__)


class MySQLLeadRepository(BaseLeadRepository):
    """
    MySQL implementation querying Paramantra CRM tables.
    Uses configurable table & column names defined in Settings / .env.
    """

    def __init__(self, db: Session):
        self.db = db
        self.sources = {s.strip() for s in settings.INTERACTION_SOURCES.split(",")}

    def _source_rows(self, source, query, lead_id):
        if source not in self.sources:
            return []
        return self.db.execute(query, {"lead_id": lead_id}).mappings().all()

    def update_lead(self, lead_id: str, changes: LeadUpdate) -> LeadInfo:
        columns = {"name": settings.COL_LEAD_NAME, "company": settings.COL_LEAD_COMPANY,
                   "status": settings.COL_LEAD_STATUS, "stage": settings.COL_LEAD_STAGE,
                   "assigned_to": settings.COL_LEAD_ASSIGNED_TO}
        values = changes.model_dump(exclude_unset=True)
        try:
            if not self.get_lead_by_id(lead_id):
                raise KeyError("Lead not found")
            assignments = ", ".join(f"{columns[key]} = :{key}" for key in values)
            self.db.execute(text(f"UPDATE {settings.TABLE_LEADS} SET {assignments} WHERE {settings.COL_LEAD_ID} = :lead_id"),
                            {**values, "lead_id": lead_id})
            self.db.commit()
            return self.get_lead_by_id(lead_id)
        except Exception:
            self.db.rollback()
            raise


    def get_lead_by_id(self, lead_id: str) -> Optional[LeadInfo]:
        """Queries the leads table for lead profile information."""
        query = text(f"""
            SELECT 
                {settings.COL_LEAD_ID} AS id,
                {settings.COL_LEAD_NAME} AS name,
                {settings.COL_LEAD_COMPANY} AS company,
                {settings.COL_LEAD_STATUS} AS status,
                {settings.COL_LEAD_STAGE} AS stage,
                {settings.COL_LEAD_ASSIGNED_TO} AS assigned_to
            FROM {settings.TABLE_LEADS}
            WHERE {settings.COL_LEAD_ID} = :lead_id
            LIMIT 1
        """)

        try:
            result = self.db.execute(query, {"lead_id": lead_id}).mappings().first()
            if not result:
                return None

            return LeadInfo(
                id=str(result["id"]),
                name=result.get("name") or "Unknown Contact",
                company=result.get("company") or "Unknown Company",
                status=result.get("status"),
                stage=result.get("stage"),
                assigned_to=result.get("assigned_to"),
                interactions=[]
            )
        except Exception as e:
            logger.error("Error querying lead from MySQL (%s)", type(e).__name__)
            raise

    def get_lead_interactions(self, lead_id: str) -> List[LeadInteraction]:
        """
        Gathers and aggregates communication history across Paramantra CRM tables:
        - whats_app
        - ticket_email
        - pm1call_log
        - pm1cti_event
        - customer_thread
        - rep_thread
        - generic lead_interactions (if present)
        """
        interactions: List[LeadInteraction] = []

        # 1. WhatsApp Messages
        try:
            wa_query = text("""
                SELECT id, lead_id, message AS content, 'whatsapp' AS interaction_type,
                       CASE WHEN sender_type = 'customer' THEN 'inbound' ELSE 'outbound' END AS direction,
                       created_at
                FROM whats_app
                WHERE lead_id = :lead_id
            """)
            for row in self._source_rows("whats_app", wa_query, lead_id):
                if row.get("content"):
                    interactions.append(LeadInteraction(
                        id=str(row["id"]), lead_id=str(row["lead_id"]), content=row["content"],
                        interaction_type="whatsapp", direction=row["direction"], created_at=row.get("created_at")
                    ))
        except Exception as e:
            raise InteractionSourceError("Could not load whats_app interactions. Check the configured source table and connection; analysis was stopped to avoid an incomplete score.") from e

        # 2. Ticket Emails
        try:
            email_query = text("""
                SELECT id, lead_id, CONCAT(IFNULL(subject, ''), ': ', IFNULL(email_body, '')) AS content,
                       'email' AS interaction_type, direction, created_at
                FROM ticket_email
                WHERE lead_id = :lead_id
            """)
            for row in self._source_rows("ticket_email", email_query, lead_id):
                if row.get("content"):
                    interactions.append(LeadInteraction(
                        id=str(row["id"]), lead_id=str(row["lead_id"]), content=row["content"],
                        interaction_type="email", direction=row.get("direction") or "inbound", created_at=row.get("created_at")
                    ))
        except Exception as e:
            raise InteractionSourceError("Could not load ticket_email interactions. Check the configured source table and connection; analysis was stopped to avoid an incomplete score.") from e

        # 3. PM1 Call Logs (Voice Remarks)
        try:
            call_query = text("""
                SELECT id, lead_id, call_remarks AS content, 'call' AS interaction_type,
                       CASE WHEN call_type = 'Inbound' THEN 'inbound' ELSE 'outbound' END AS direction,
                       created_at
                FROM pm1call_log
                WHERE lead_id = :lead_id
            """)
            for row in self._source_rows("pm1call_log", call_query, lead_id):
                if row.get("content"):
                    interactions.append(LeadInteraction(
                        id=str(row["id"]), lead_id=str(row["lead_id"]), content=row["content"],
                        interaction_type="call", direction=row["direction"], created_at=row.get("created_at")
                    ))
        except Exception as e:
            raise InteractionSourceError("Could not load pm1call_log interactions. Check the configured source table and connection; analysis was stopped to avoid an incomplete score.") from e

        # 4. PM1 CTI Telephony Events
        try:
            cti_query = text("""
                SELECT id, lead_id, 
                       CONCAT('Telephony Event: ', event_type, ' | Disposition: ', IFNULL(disposition, 'None'), ' | Duration: ', IFNULL(duration_sec, 0), 's') AS content,
                       'cti_event' AS interaction_type, 'system' AS direction, created_at
                FROM pm1cti_event
                WHERE lead_id = :lead_id
            """)
            for row in self._source_rows("pm1cti_event", cti_query, lead_id):
                if row.get("content"):
                    interactions.append(LeadInteraction(
                        id=str(row["id"]), lead_id=str(row["lead_id"]), content=row["content"],
                        interaction_type="cti_event", direction="system", created_at=row.get("created_at")
                    ))
        except Exception as e:
            raise InteractionSourceError("Could not load pm1cti_event interactions. Check the configured source table and connection; analysis was stopped to avoid an incomplete score.") from e

        # 5. Customer Thread (Web forms, portal queries)
        try:
            cust_query = text("""
                SELECT id, lead_id, query_text AS content, 'customer_thread' AS interaction_type,
                       'inbound' AS direction, created_at
                FROM customer_thread
                WHERE lead_id = :lead_id
            """)
            for row in self._source_rows("customer_thread", cust_query, lead_id):
                if row.get("content"):
                    interactions.append(LeadInteraction(
                        id=str(row["id"]), lead_id=str(row["lead_id"]), content=row["content"],
                        interaction_type="customer_thread", direction="inbound", created_at=row.get("created_at")
                    ))
        except Exception as e:
            raise InteractionSourceError("Could not load customer_thread interactions. Check the configured source table and connection; analysis was stopped to avoid an incomplete score.") from e

        # 6. Rep Thread (Internal agent notes)
        try:
            rep_query = text("""
                SELECT id, lead_id, CONCAT('Rep Note (', IFNULL(rep_name, 'Agent'), '): ', IFNULL(note, '')) AS content,
                       'rep_note' AS interaction_type, 'internal' AS direction, created_at
                FROM rep_thread
                WHERE lead_id = :lead_id
            """)
            for row in self._source_rows("rep_thread", rep_query, lead_id):
                if row.get("content"):
                    interactions.append(LeadInteraction(
                        id=str(row["id"]), lead_id=str(row["lead_id"]), content=row["content"],
                        interaction_type="rep_note", direction="internal", created_at=row.get("created_at")
                    ))
        except Exception as e:
            raise InteractionSourceError("Could not load rep_thread interactions. Check the configured source table and connection; analysis was stopped to avoid an incomplete score.") from e

        if "generic" in self.sources:
            query = text(f"""SELECT {settings.COL_INT_ID} AS id,
                {settings.COL_INT_LEAD_ID} AS lead_id, {settings.COL_INT_CONTENT} AS content,
                {settings.COL_INT_TYPE} AS interaction_type, {settings.COL_INT_DIRECTION} AS direction,
                {settings.COL_INT_CREATED_AT} AS created_at FROM {settings.TABLE_INTERACTIONS}
                WHERE {settings.COL_INT_LEAD_ID} = :lead_id""")
            try:
                for row in self._source_rows("generic", query, lead_id):
                    if row.get("content"):
                        interactions.append(LeadInteraction(**{**row, "id": str(row["id"]), "lead_id": str(row["lead_id"])}))
            except Exception as e:
                raise InteractionSourceError("Could not load generic interactions. Check the configured table and columns.") from e

        # Sort all aggregated interactions chronologically
        interactions.sort(key=lambda item: (item.created_at or datetime.min.replace(tzinfo=timezone.utc), item.interaction_type or "", item.id or ""))
        return interactions

    def _ensure_cache_table(self):
        """Creates the lead_battlecard_cache table if it does not exist yet."""
        create_table_sql = text("""
            CREATE TABLE IF NOT EXISTS lead_battlecard_cache (
                lead_id VARCHAR(100) PRIMARY KEY,
                overall_score FLOAT,
                battlecard_json LONGTEXT,
                updated_at DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        try:
            self.db.execute(create_table_sql)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise

    def get_cached_battlecard(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached battlecard payload if previously analyzed."""
        try:
            self._ensure_cache_table()
            query = text("""
                SELECT battlecard_json 
                FROM lead_battlecard_cache 
                WHERE lead_id = :lead_id
                LIMIT 1
            """)
            row = self.db.execute(query, {"lead_id": lead_id}).mappings().first()
            if row and row.get("battlecard_json"):
                return json.loads(row["battlecard_json"])
            return None
        except Exception as e:
            self.db.rollback()
            logger.warning("Cache lookup failed (%s)", type(e).__name__)
            return None

    def save_battlecard(self, lead_id: str, data: Dict[str, Any]) -> None:
        """Saves/updates the battlecard record in the cache table."""
        try:
            self._ensure_cache_table()
            upsert_sql = text("""
                INSERT INTO lead_battlecard_cache (lead_id, overall_score, battlecard_json, updated_at)
                VALUES (:lead_id, :score, :json_data, :updated_at)
                ON DUPLICATE KEY UPDATE 
                    overall_score = VALUES(overall_score),
                    battlecard_json = VALUES(battlecard_json),
                    updated_at = VALUES(updated_at)
            """)
            self.db.execute(upsert_sql, {
                "lead_id": lead_id,
                "score": data.get("overall_score", 0.0),
                "json_data": json.dumps(data, default=str),
                "updated_at": datetime.now()
            })
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise
