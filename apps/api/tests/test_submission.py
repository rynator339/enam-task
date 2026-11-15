from datetime import datetime, timezone
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from openai import OpenAI
from app import ai, service
from app.db import SessionLocal
from app.logic import compare_guidance, normalize_date
from app.main import app


def test_snapshot_readable_on_repeat_start():
    for _ in range(2):
        with TestClient(app) as c:
            assert c.get('/api/companies').json()['count'] == 18
            p = c.get('/api/companies/INFY/promises').json()['promises']
            assert len(p) == 1 and (p[0]['actual'], p[0]['status']) == (21.1, 'met')
            assert p[0]['source_url'] != p[0]['actual_url']


def test_historical_alert_thresholds_and_exact_cutoff():
    with TestClient(app) as c:
        def feed(hours, price, volume):
            return c.get('/api/feed', params=dict(saved=True, window_hours=hours,
                         price_threshold=price, volume_threshold=volume, category='market_move')).json()
        loose, strict = feed(168, .5, 1), feed(168, 10, 5)
        assert loose['count'] > strict['count']
        assert len({i['published_at'][:10] for i in loose['items']}) > 1
        end = datetime.fromisoformat(loose['as_of'])
        for item in loose['items']:
            assert 0 <= (end - datetime.fromisoformat(item['published_at'])).total_seconds() <= 168*3600
            assert item['is_illustrative'] is False
        assert feed(1, .5, 1)['items'] == []


def test_evidence_only_company_isolation():
    with TestClient(app) as c:
        for symbol in ('INFY','TRENT','HAL','PERSISTENT'):
            result = c.post('/api/research', json={'ticker':symbol,'question':'What does management report?'}).json()
            assert result['citations'] and not result['ai_generated']
            urls={d['url'] for d in c.get('/api/companies/'+symbol).json()['documents']}
            assert all(citation['url'] in urls for citation in result['citations'])


def test_original_quotes_must_contain_proposed_numbers(monkeypatch):
    quote='Our operating margin guidance for FY2025 is 20% to 22%.'
    suggestion=dict(metric='operating_margin', period='FY2025',low=17,high=22,unit='%',
                    basis='consolidated',quote=quote,page=4)
    monkeypatch.setattr(ai,'json_completion',lambda *args:[suggestion])
    assert ai.extract_guidance('INFY',[{'page':4,'content':quote}])==[]
    suggestion['low']=20
    assert ai.extract_guidance('INFY',[{'page':4,'content':quote}])[0]['target_low']==20


def test_unknown_basis_and_date_do_not_create_market_facts():
    assert compare_guidance(20,22,21.1,'%','%','FY2025','FY2025','unspecified','consolidated')[0]=='unverifiable'
    with pytest.raises(ValueError):
        normalize_date('')


def test_rag_provider_contract_and_bad_citation(monkeypatch):
    response_text='The stated margin range was 20% to 22% [D1 p.4].'
    def respond(request):
        payload=json.loads(request.content)
        prompt=payload['messages'][1]['content']
        assert 'Our operating margin guidance' in prompt and 'We had growth' in prompt
        assert 'Hindustan Aeronautics' not in prompt
        return httpx.Response(200,json={'id':'offline-contract','object':'chat.completion','created':1,
            'model':'test','choices':[{'index':0,'message':{'role':'assistant','content':response_text},
            'finish_reason':'stop'}]})
    client=OpenAI(api_key='offline-contract-test',base_url='https://provider.invalid/v1',
                  http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    monkeypatch.setattr(ai,'_client',lambda:client)
    monkeypatch.setattr(ai,'llm_ready',lambda:True)
    with TestClient(app) as c:
        request={'ticker':'INFY','question':'What was the operating margin guidance and outcome?'}
        assert c.post('/api/research',json=request).json()['ai_generated'] is True
        response_text='An unsupported claim [D99 p.1].'
        fallback=c.post('/api/research',json=request).json()
        assert fallback['ai_generated'] is False and fallback['citations']
    client.close()
