from datetime import datetime,timezone
from app import ai,service
from app.db import SessionLocal,Company,Announcement,Price
from app.logic import stable_id
from sqlalchemy import select


def test_results_extraction_accepts_only_verified_quotes(monkeypatch):
    passage='REVENUE FROM OPERATIONS 1750 1600 1420 for the quarters ended on specified dates'
    proposed={
      'basis':'consolidated','period':'Q2FY2027','rows':[
         {'metric':'revenue','current':1750,'previous':1600,'year_ago':1420,'unit':'INR crore','quote':passage,'page':2},
         {'metric':'pat','current':800,'previous':700,'year_ago':600,'unit':'INR crore','quote':'Unsupported fabricated quote of a very long metric statement 800','page':2}
      ]
    }
    monkeypatch.setattr(ai,'json_completion',lambda *a,**kw:proposed)
    result=ai.extract_quarterly_results('TEST',[{'page':2,'content':passage}])
    assert len(result['rows'])==1
    row=result['rows'][0]
    assert row['metric']=='revenue'
    assert row['qoq_pct']==9.38
    assert row['yoy_pct']==23.24


def test_mock_source_ingestion_has_real_provenance_and_no_demo_label(monkeypatch):
    ticker='INTEGRATIONTEST'
    source_url='https://nsearchives.nseindia.com/corporate/verified-example.pdf'
    monkeypatch.setattr(service.sources,'fetch_market_prices',lambda t:[{'day':f'2026-10-{d:02d}','close':100.0+d,'volume':1000} for d in range(1,24)])
    monkeypatch.setattr(service.sources,'fetch_nse_announcements',lambda t,days:[{'ticker':ticker,'title':'Financial Results for Quarter Ended Sep 2026','body':'The company informed the Exchange of its quarterly financial results','published_at':datetime(2026,11,7,10,tzinfo=timezone.utc),'source_url':source_url,'source':'NSE','source_id':'mock-verified-source'}])
    with SessionLocal() as db:
        try:
            service.ensure_company(db,ticker)
            assert service.ingest_prices(db,ticker)==23
            assert service.ingest_filings(db,ticker)==1
            a=db.execute(select(Announcement).where(Announcement.ticker==ticker)).scalar_one()
            p=db.execute(select(Price).where(Price.ticker==ticker).order_by(Price.day.desc())).scalars().first()
            assert a.category=='results' and a.priority=='high'
            assert a.source_url==source_url and not a.is_illustrative
            assert p.volume_multiple==1.0 and p.day_change_pct is not None
        finally:
            db.query(Announcement).filter(Announcement.ticker==ticker).delete()
            db.query(Price).filter(Price.ticker==ticker).delete()
            db.query(Company).filter(Company.ticker==ticker).delete()
            db.commit()
