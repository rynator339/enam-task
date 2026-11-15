from fastapi.testclient import TestClient
from app.main import app

def test_app_health_and_portfolio():
    with TestClient(app) as c:
        r=c.get('/api/health');assert r.status_code==200
        assert r.json()['company_count']>=18
        a=c.get('/api/companies');assert a.status_code==200
        assert a.json()['count']==18

def test_explicit_demo_markers():
    with TestClient(app) as c:
        payload=c.get('/api/feed?demo=true').json()
        assert payload['illustrative'] is True
        assert all(x['is_illustrative'] and x['source_url'] is None for x in payload['items'])
        assert c.get('/api/signals/demo-1').json()['is_illustrative'] is True

def test_no_unguarded_ingest():
    with TestClient(app) as c:
        assert c.post('/api/admin/ingest/INFY').status_code==403

def test_unknown_ticker_explained_not_hallucinated():
    with TestClient(app) as c:
        data=c.post('/api/research',json={'ticker':'EXAMPLENEW','question':'What are the main growth drivers?'}).json()
        assert data['needs_documents'] is True
        assert data['citations']==[]
