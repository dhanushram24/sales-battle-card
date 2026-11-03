"""
Seed realistic dynamic pipeline leads into Paramantra CRM MySQL database.
Provides varied opportunities across Negotiation, Discovery, and Progress stages.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from app.core.database import SessionLocal

def seed():
    db = SessionLocal()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    leads_data = [
        ('124', 'Priya Patel', 'Zenith Tech Solutions', 'In Progress', 'Negotiation', 'Pooja Rep'),
        ('125', 'Amit Verma', 'CloudScale Systems', 'Evaluating', 'Discovery', 'Kavita Rep'),
        ('126', 'Vikrant Kapoor', 'Metro Logistics Corp', 'At Risk', 'Progress', 'Arun Rep')
    ]

    for lid, name, comp, stat, stg, rep in leads_data:
        existing = db.execute(text('SELECT id FROM leads WHERE id = :id'), {'id': lid}).first()
        if not existing:
            db.execute(text('''
                INSERT INTO leads (id, name, company, status, stage, assigned_to, created_at)
                VALUES (:id, :name, :comp, :stat, :stg, :rep, :now)
            '''), {'id': lid, 'name': name, 'comp': comp, 'stat': stat, 'stg': stg, 'rep': rep, 'now': now - timedelta(days=7)})
            print(f'Inserted Lead {lid}: {name}')

    # Lead 124: High readiness, comparing with Zoho CRM
    if not db.execute(text('SELECT id FROM whats_app WHERE lead_id = "124"')).first():
        db.execute(text('INSERT INTO whats_app (lead_id, message, sender_type, created_at) VALUES ("124", "Hi team, we reviewed the proposal for 50 licenses. The team loved the WhatsApp integration demo.", "customer", :dt)'), {'dt': now - timedelta(days=3)})
        db.execute(text('INSERT INTO whats_app (lead_id, message, sender_type, created_at) VALUES ("124", "Glad to hear that Priya! Sending over the SLA addendum for your review.", "rep", :dt)'), {'dt': now - timedelta(days=2)})
        db.execute(text('INSERT INTO ticket_email (lead_id, subject, email_body, direction, created_at) VALUES ("124", "Enterprise SLA query", "Can you guarantee 99.9% uptime SLA for telephony CTI gateway? We are comparing with Zoho CRM uptime specs.", "inbound", :dt)'), {'dt': now - timedelta(days=4)})
        db.execute(text('INSERT INTO pm1call_log (lead_id, call_type, duration, call_remarks, created_at) VALUES ("124", "Outbound", 480, "Call with Priya CTO. Strong interest in migrating from Zoho CRM. Ready to finalize contract pending SLA signoff.", :dt)'), {'dt': now - timedelta(days=1)})
        db.execute(text('INSERT INTO pm1cti_event (lead_id, event_type, disposition, duration_sec, created_at) VALUES ("124", "DISPOSITION", "Qualified - Ready to Close", 480, :dt)'), {'dt': now - timedelta(days=1)})
        db.execute(text('INSERT INTO rep_thread (lead_id, note, rep_name, created_at) VALUES ("124", "Priya confirmed budget is approved. Sending revised SLA agreement.", "Pooja Rep", :dt)'), {'dt': now - timedelta(hours=6)})
        print('Seeded interactions for Lead 124')

    # Lead 125: Discovery stage, comparing with HubSpot
    if not db.execute(text('SELECT id FROM whats_app WHERE lead_id = "125"')).first():
        db.execute(text('INSERT INTO whats_app (lead_id, message, sender_type, created_at) VALUES ("125", "Hello, looking for a CRM with native India telephony integration. Comparing with HubSpot.", "customer", :dt)'), {'dt': now - timedelta(days=5)})
        db.execute(text('INSERT INTO customer_thread (lead_id, query_text, channel, created_at) VALUES ("125", "Does Paramantra support multi-department routing for support tickets?", "portal", :dt)'), {'dt': now - timedelta(days=3)})
        db.execute(text('INSERT INTO pm1call_log (lead_id, call_type, duration, call_remarks, created_at) VALUES ("125", "Inbound", 320, "Discovery call with Amit. Impressed by native call recordings and auto-sync, but requested demo for support ticketing.", :dt)'), {'dt': now - timedelta(days=2)})
        db.execute(text('INSERT INTO rep_thread (lead_id, note, rep_name, created_at) VALUES ("125", "Scheduled product demo for Friday 3 PM.", "Kavita Rep", :dt)'), {'dt': now - timedelta(days=1)})
        print('Seeded interactions for Lead 125')

    # Lead 126: At-Risk stage, pricing friction, comparing with Freshsales
    if not db.execute(text('SELECT id FROM whats_app WHERE lead_id = "126"')).first():
        db.execute(text('INSERT INTO ticket_email (lead_id, subject, email_body, direction, created_at) VALUES ("126", "Pricing review", "The quoted annual license is currently over our Q3 budget. We may need to hold off until next quarter.", "inbound", :dt)'), {'dt': now - timedelta(days=4)})
        db.execute(text('INSERT INTO whats_app (lead_id, message, sender_type, created_at) VALUES ("126", "Can we get a discount or flexible quarterly payment terms? Freshsales is offering lower upfront cost.", "customer", :dt)'), {'dt': now - timedelta(days=2)})
        db.execute(text('INSERT INTO pm1call_log (lead_id, call_type, duration, call_remarks, created_at) VALUES ("126", "Outbound", 240, "Call with Vikrant. Major pushback on upfront cost. Considering Freshsales as lower-cost alternative.", :dt)'), {'dt': now - timedelta(days=1)})
        db.execute(text('INSERT INTO rep_thread (lead_id, note, rep_name, created_at) VALUES ("126", "Needs manager approval for quarterly milestone billing to avoid losing deal.", "Arun Rep", :dt)'), {'dt': now - timedelta(hours=4)})
        print('Seeded interactions for Lead 126')

    db.commit()
    all_leads = db.execute(text('SELECT id, name, company, stage, status, assigned_to FROM leads')).fetchall()
    print('\nActive CRM Leads in Database:')
    for l in all_leads:
        print(f' - Lead #{l[0]}: {l[1]} ({l[2]}) | Stage: {l[3]} | Assigned: {l[5]}')
    db.close()

if __name__ == '__main__':
    seed()
