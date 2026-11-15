from app.logic import classify,price_stats,compare_guidance,verify_quote,stable_id

def test_classification():
    assert classify('Outcome of Board Meeting - Financial Results')[0]=='results'
    assert classify('Change in Management - CFO resignation')[0]=='management_change'
    assert classify('Closure of Trading Window')[2].startswith('Routine')
    assert classify('Acquisition of a subsidiary')[0]=='M&A'

def test_technical_indicators_exclude_current_volume():
    change,volume=price_stats([100]*20+[104],[100]*20+[250])
    assert change==4
    assert volume==2.5

def test_guidance_cases():
    assert compare_guidance(10,15,12,'%','%','FY2026','FY2026')[0]=='met'
    assert compare_guidance(10,15,8,'%','%','FY2026','FY2026')[0]=='missed'
    assert compare_guidance(10,15,None,'%','%','FY2026','FY2026')[0]=='pending'
    assert compare_guidance(10,15,12,'%','INR crore','FY2026','FY2026')[0]=='unverifiable'
    assert compare_guidance(10,15,12,'%','%','FY2026','FY2027')[0]=='unverifiable'

def test_exact_source_quote():
    text='The management indicated revenue growth is expected to range between 12 and 15 percent next year.'
    assert verify_quote('revenue growth is expected to range between 12 and 15 percent',text)
    assert not verify_quote('revenue growth is expected to be around 44 and 50 percent',text)

def test_stable_id():
    assert stable_id('a','b')==stable_id('a','b')
    assert stable_id('a','b')!=stable_id('a','c')


def test_volume_requires_20_baseline_sessions():
    assert price_stats([100,104],[100,250])[1] is None

def test_nse_timestamps_respect_india_timezone():
    from app.logic import normalize_date
    assert normalize_date('09-Nov-2026 18:00:00').hour == 12
