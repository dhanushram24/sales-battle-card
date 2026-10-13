"""
Mock Database Initialization and Seeding Script for Paramantra SalesBattlecard.
Creates all communication tables (whats_app, rep_thread, pm1cti_event, pm1call_log, ticket_email, customer_thread)
and populates realistic omnichannel mock interactions for Lead 123 (and others).
"""

import pymysql
from datetime import datetime, timedelta, timezone

import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import settings

parser = argparse.ArgumentParser(description="Create an isolated SalesBattle demo database without replacing existing leads.")
parser.add_argument("--database", default="salesbattle_demo", help="Must end with _demo")



def init_database():
    args = parser.parse_args()
    if not args.database.endswith("_demo") or not args.database.replace("_", "").isalnum():
        parser.error("Use a separate database name ending with _demo")
    DB_HOST, DB_PORT = settings.DB_HOST, settings.DB_PORT
    DB_USER, DB_PASSWORD = settings.DB_USER, settings.DB_PASSWORD
    DB_NAME = args.database
    print(f"Connecting to MySQL at {DB_HOST}:{DB_PORT} as {DB_USER}...")
    conn = pymysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD)
    cursor = conn.cursor()

    # 1. Create Database
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` DEFAULT CHARACTER SET utf8mb4;")
    cursor.execute(f"USE `{DB_NAME}`;")
    print(f"Database `{DB_NAME}` verified.")

    # 2. Create Tables
    tables = {
        "leads": """
            CREATE TABLE IF NOT EXISTS leads (
                id VARCHAR(50) PRIMARY KEY,
                name VARCHAR(150),
                company VARCHAR(150),
                email VARCHAR(150),
                phone VARCHAR(50),
                status VARCHAR(50),
                stage VARCHAR(50),
                assigned_to VARCHAR(100),
                created_at DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        "whats_app": """
            CREATE TABLE IF NOT EXISTS whats_app (
                id INT AUTO_INCREMENT PRIMARY KEY,
                lead_id VARCHAR(50),
                message TEXT,
                sender_type VARCHAR(20), -- 'customer' or 'rep'
                created_at DATETIME,
                INDEX (lead_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        "rep_thread": """
            CREATE TABLE IF NOT EXISTS rep_thread (
                id INT AUTO_INCREMENT PRIMARY KEY,
                lead_id VARCHAR(50),
                note TEXT,
                rep_name VARCHAR(100),
                created_at DATETIME,
                INDEX (lead_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        "pm1cti_event": """
            CREATE TABLE IF NOT EXISTS pm1cti_event (
                id INT AUTO_INCREMENT PRIMARY KEY,
                lead_id VARCHAR(50),
                event_type VARCHAR(50), -- 'CALL_ANSWERED', 'CALL_HANGUP', 'DISPOSITION'
                disposition VARCHAR(100),
                duration_sec INT,
                created_at DATETIME,
                INDEX (lead_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        "pm1call_log": """
            CREATE TABLE IF NOT EXISTS pm1call_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                lead_id VARCHAR(50),
                call_type VARCHAR(50), -- 'Inbound', 'Outbound'
                duration INT,
                call_remarks TEXT,
                created_at DATETIME,
                INDEX (lead_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        "ticket_email": """
            CREATE TABLE IF NOT EXISTS ticket_email (
                id INT AUTO_INCREMENT PRIMARY KEY,
                lead_id VARCHAR(50),
                subject VARCHAR(255),
                email_body TEXT,
                direction VARCHAR(20), -- 'inbound', 'outbound'
                sender VARCHAR(150),
                created_at DATETIME,
                INDEX (lead_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        "customer_thread": """
            CREATE TABLE IF NOT EXISTS customer_thread (
                id INT AUTO_INCREMENT PRIMARY KEY,
                lead_id VARCHAR(50),
                query_text TEXT,
                channel VARCHAR(50), -- 'portal', 'web_form', 'chat'
                created_at DATETIME,
                INDEX (lead_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        "lead_battlecard_cache": """
            CREATE TABLE IF NOT EXISTS lead_battlecard_cache (
                lead_id VARCHAR(100) PRIMARY KEY,
                overall_score FLOAT,
                battlecard_json LONGTEXT,
                updated_at DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    }

    for table_name, create_sql in tables.items():
        cursor.execute(create_sql)
        print(f" - Table `{table_name}` ready.")

    conn.commit()

    # 3. Seed Mock Data for Lead 123
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    t_minus_5d = now - timedelta(days=5)
    t_minus_4d = now - timedelta(days=4)
    t_minus_3d = now - timedelta(days=3)
    t_minus_2d = now - timedelta(days=2)
    t_minus_1d = now - timedelta(days=1)
    t_today = now

    # Never replace an existing lead or its conversation history.
    cursor.execute("SELECT id FROM leads WHERE id = '123'")
    if cursor.fetchone():
        print("Demo lead already exists; no records were changed.")
        conn.close()
        return

    print("\nInserting realistic omnichannel mock interactions for Lead 123...")

    # Lead Master Profile
    cursor.execute("""
        INSERT INTO leads (id, name, company, email, phone, status, stage, assigned_to, created_at)
        VALUES ('123', 'Rajesh Sharma', 'Apex Enterprise Solutions', 'rajesh.sharma@apexenterprise.in', '+91 98765 43210', 'In Progress', 'Proposal Under Review', 'Vikram rep', %s)
    """, (t_minus_5d,))

    # 1. Customer Thread (Initial Web Form Inquiry)
    cursor.execute("""
        INSERT INTO customer_thread (lead_id, query_text, channel, created_at)
        VALUES ('123', 'We are looking for a complete CRM with telephony CTI integration for our 35-member sales team. Currently evaluating Paramantra and Salesforce.', 'web_form', %s)
    """, (t_minus_5d,))

    # 2. PM1 CTI Event & Call Log (Day 4)
    cursor.execute("""
        INSERT INTO pm1cti_event (lead_id, event_type, disposition, duration_sec, created_at)
        VALUES ('123', 'CALL_DISPOSITION', 'Connected - Demo Scheduled', 420, %s)
    """, (t_minus_4d,))

    cursor.execute("""
        INSERT INTO pm1call_log (lead_id, call_type, duration, call_remarks, created_at)
        VALUES ('123', 'Outbound', 420, 'Spoke with Rajesh (VP of Sales). Very impressed with Paramantras native CTI integration. His major concern is migration from their current Excel/Salesforce setup and annual licensing pricing.', %s)
    """, (t_minus_4d,))

    # 3. Rep Internal Thread (Day 4)
    cursor.execute("""
        INSERT INTO rep_thread (lead_id, note, rep_name, created_at)
        VALUES ('123', 'Client is keen on our automatic call recording and WhatsApp logging features. Needs pricing proposal by Wednesday. Mentioned Salesforce is quoting $75/user/month.', 'Vikram rep', %s)
    """, (t_minus_4d + timedelta(hours=2),))

    # 4. WhatsApp Messages (Day 3 & 2)
    whatsapp_data = [
        ('123', 'Hi Vikram, can you please share the proposal with breakdown for 35 user licenses?', 'customer', t_minus_3d),
        ('123', 'Hi Rajesh sir, sending the customized proposal right away on email with our enterprise discount.', 'rep', t_minus_3d + timedelta(minutes=15)),
        ('123', 'Reviewed the proposal. The feature set matches our requirements, but the implementation cost is a bit higher than expected. Can we discuss a waiver on setup fees?', 'customer', t_minus_2d),
        ('123', 'Definitely Rajesh sir, let us have a quick call tomorrow to work this out.', 'rep', t_minus_2d + timedelta(minutes=40)),
    ]
    for row in whatsapp_data:
        cursor.execute("INSERT INTO whats_app (lead_id, message, sender_type, created_at) VALUES (%s, %s, %s, %s)", row)

    # 5. Ticket Emails (Day 1 & Today)
    cursor.execute("""
        INSERT INTO ticket_email (lead_id, subject, email_body, direction, sender, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        '123',
        'Paramantra Enterprise Proposal - Apex Solutions',
        'Dear Rajesh, please find attached our comprehensive proposal for 35 users including CTI integration and WhatsApp messaging modules.',
        'outbound',
        'vikram@paramantra.com',
        t_minus_1d
    ))

    cursor.execute("""
        INSERT INTO ticket_email (lead_id, subject, email_body, direction, sender, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        '123',
        'Re: Paramantra Enterprise Proposal - Apex Solutions',
        'Thanks Vikram. If you can provide a 10% discount on first-year licensing and waive the onboarding charges, we are ready to issue the PO by this Friday before our quarter ends.',
        'inbound',
        'rajesh.sharma@apexenterprise.in',
        t_today
    ))

    conn.commit()
    cursor.close()
    conn.close()
    print("\n[SUCCESS] Successfully initialized `paramantra_salesbattle` database and inserted omnichannel mock data for Lead 123!")


if __name__ == "__main__":
    init_database()
