import os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, String, Integer, Float, Text, DateTime, ForeignKey, Boolean, UniqueConstraint, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Mapped, mapped_column
from dotenv import load_dotenv

load_dotenv()
BASE = Path(__file__).resolve().parent.parent
DB_URL = os.environ.get('DATABASE_URL', f'sqlite:///{BASE / "finn.db"}')
if DB_URL.startswith('postgres://'):
    DB_URL = DB_URL.replace('postgres://', 'postgresql+psycopg://', 1)
engine = create_engine(DB_URL, pool_pre_ping=True, connect_args={'check_same_thread': False} if DB_URL.startswith('sqlite') else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
Base = declarative_base()

def utcnow():
    return datetime.now(timezone.utc)

class Company(Base):
    __tablename__ = 'companies'
    ticker: Mapped[str] = mapped_column(String(28), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    sector: Mapped[str] = mapped_column(String(100))
    in_watchlist: Mapped[bool] = mapped_column(Boolean, default=False)

class Price(Base):
    __tablename__ = 'prices_daily'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticker: Mapped[str] = mapped_column(String(28), index=True)
    day: Mapped[str] = mapped_column(String(12), index=True)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(Integer)
    day_change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    volume_multiple: Mapped[float | None] = mapped_column(Float, nullable=True)
    __table_args__ = (UniqueConstraint('ticker','day'),)

class Announcement(Base):
    __tablename__ = 'announcements'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(28), index=True)
    title: Mapped[str] = mapped_column(String(600))
    body: Mapped[str] = mapped_column(Text, default='')
    category: Mapped[str] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    analysis_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_illustrative: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(40), default='NSE')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Document(Base):
    __tablename__ = 'source_documents'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(28), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    published_label: Mapped[str] = mapped_column(String(80), default='')
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(20), default='indexed')
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

class Chunk(Base):
    __tablename__ = 'document_chunks'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(64), ForeignKey('source_documents.id'), index=True)
    ticker: Mapped[str] = mapped_column(String(28), index=True)
    page: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)

class Metric(Base):
    __tablename__ = 'financial_metrics'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(28), index=True)
    metric: Mapped[str] = mapped_column(String(60))
    period: Mapped[str] = mapped_column(String(60))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(40))
    basis: Mapped[str] = mapped_column(String(40), default='unspecified')
    document_id: Mapped[str] = mapped_column(String(64))
    page: Mapped[int] = mapped_column(Integer)
    quote: Mapped[str] = mapped_column(Text)

class Promise(Base):
    __tablename__ = 'guidance_claims'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(28), index=True)
    metric: Mapped[str] = mapped_column(String(60))
    period: Mapped[str] = mapped_column(String(60))
    target_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(40))
    basis: Mapped[str] = mapped_column(String(40), default='unspecified')
    quote: Mapped[str] = mapped_column(Text)
    document_id: Mapped[str] = mapped_column(String(64))
    page: Mapped[int] = mapped_column(Integer)
    actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    actual_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actual_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default='pending')
    rationale: Mapped[str] = mapped_column(Text, default='No comparable reported value found yet.')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

PORTFOLIO = [
 ('RELIANCE','Reliance Industries','Energy & Retail'),('TCS','Tata Consultancy Services','Information Technology'),
 ('INFY','Infosys','Information Technology'),('HDFCBANK','HDFC Bank','Banking'),('ICICIBANK','ICICI Bank','Banking'),
 ('ITC','ITC','Consumer'),('HINDUNILVR','Hindustan Unilever','Consumer'),('NTPC','NTPC','Power'),
 ('POWERGRID','Power Grid Corporation','Power'),('MARUTI','Maruti Suzuki','Automotive'),
 ('SUNPHARMA','Sun Pharmaceutical','Pharmaceuticals'),('DRREDDY',"Dr. Reddy's Laboratories",'Pharmaceuticals'),
 ('LT','Larsen & Toubro','Industrials'),('ULTRACEMCO','UltraTech Cement','Materials'),
 ('BHARTIARTL','Bharti Airtel','Telecom'),('DIXON','Dixon Technologies','Electronics'),
 ('POLYCAB','Polycab India','Electrical Equipment'),('CDSL','Central Depository Services','Financial Infrastructure')
]

def init_db():
    Base.metadata.create_all(engine)
    # Small additive migration for early prototype databases created before results analysis.
    columns={c["name"] for c in inspect(engine).get_columns("announcements")}
    if "analysis_json" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE announcements ADD COLUMN analysis_json TEXT"))
    with SessionLocal() as db:
        for symbol,name,sector in PORTFOLIO:
            item = db.get(Company, symbol)
            if item is None:
                db.add(Company(ticker=symbol, name=name, sector=sector, in_watchlist=True))
        db.commit()

def get_db():
    with SessionLocal() as db:
        yield db
