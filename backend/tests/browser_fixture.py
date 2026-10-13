"""Synthetic HTTP fixture for browser QA only. Never import from the application."""
import asyncio
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()
dist = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='assets')
leads = {key: dict(id=key, name=f'Test Buyer {key}', company=f'Test Company {key}', stage='Discovery', status='Active', assigned_to='Test Rep') for key in ['1', '2']}
sync_calls = 0


def card(key):
    return dict(lead_id=key, overall_score=8.1 if key == '1' else 0,
        classification='Warm' if key == '1' else 'At risk',
        score_breakdown=dict(sentiment_score=0, engagement_score=0, intent_score=0, risk_penalty=0),
        emotional_dimensions=dict(trust_and_rapport=0, commercial_urgency=0, negotiation_stance='Unknown'),
        sentiment_summary=f'Synthetic test analysis for lead {key}.', sentiment_trend='Stable',
        next_best_action='Confirm requirements.', channel_sentiments=[], positive_drivers=[], friction_drivers=[],
        competitors=[], objections=[], buying_signals=[], recommended_talk_tracks=[], interaction_sentiments=[],
        analyzed_interactions_count=1, last_synced_at='2026-10-13T10:00:00Z', purchase_outlook='undecided', confidence='low')

@app.get('/')
def index(): return FileResponse(dist / 'index.html')
@app.get('/favicon.svg')
def favicon(): return FileResponse(dist / 'favicon.svg')
@app.get('/api/health')
def health(): return dict(database_connected=True, status='healthy')
@app.get('/api/leads')
def listing(offset: int = 0, limit: int = 200): return list(leads.values())[offset:offset+limit]
@app.get('/api/leads/{key}/timeline')
def timeline(key: str): return dict(lead=leads[key], interactions=[dict(id='1', lead_id=key, content=f'Test conversation for {key}', interaction_type='email', direction='inbound', created_at='2026-10-13T10:00:00Z')])
@app.get('/api/leads/{key}/battlecard')
def score(key: str): return card(key)
@app.post('/api/leads/{key}/sync')
async def sync(key: str):
    global sync_calls
    sync_calls += 1
    if key == '2': raise HTTPException(503, 'Synthetic network failure')
    await asyncio.sleep(1.5)
    return card(key)
@app.patch('/api/leads/{key}')
def update(key: str, changes: dict):
    if changes.get('name') == 'FAIL': raise HTTPException(503, 'Synthetic save failure')
    leads[key].update(changes)
    return leads[key]
@app.get('/__test/stats')
def stats(): return dict(sync_calls=sync_calls)
