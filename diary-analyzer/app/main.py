import os
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Diary
from dotenv import load_dotenv
from anthropic import Anthropic

# Load environment variables
load_dotenv()
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("Anthropic API key not found in environment!")
client = Anthropic(api_key=api_key)

# Database configuration
DATABASE_URL = "sqlite:///diary_analyzer.db"
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)

def analyze_diary_entry(entry: str) -> str:
    prompt = (
        "你是一个日记分析助手。请根据以下日记内容，提取关键词、判断整体情绪、给出简短反馈，并推荐一个积极的任务。\n"
        f"日记内容：{entry}\n"
        "请用如下格式输出：\n"
        "关键词: ...\n情绪: ...\n反馈: ...\n推荐任务: ..."
    )
    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=300,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        raise Exception(f"Error analyzing diary: {e}")

def parse_analysis_result(result: str) -> tuple:
    lines = result.split("\n")
    keywords = lines[0].replace("关键词: ", "").strip() if lines[0].startswith("关键词:") else ""
    mood = lines[1].replace("情绪: ", "").strip() if lines[1].startswith("情绪:") else ""
    return keywords, mood

def init_db():
    Base.metadata.create_all(bind=engine)

def add_diary_entry(entry_date, entry_text, mood=None, keywords=None):
    session = SessionLocal()
    try:
        diary = Diary(
            date=entry_date,
            text=entry_text,
            mood=mood,
            keywords=keywords
        )
        session.add(diary)
        session.commit()
        print("日记已写入数据库。")
    except Exception as e:
        print(f"Error adding diary entry: {e}")
    finally:
        session.close()

def view_diary_entries():
    session = SessionLocal()
    try:
        diaries = session.query(Diary).order_by(Diary.date.desc()).all()
        if not diaries:
            print("No diary entries found in the database.")
            return
        print("\nDiary Entries:")
        for diary in diaries:
            print(f"ID: {diary.id}")
            print(f"Date: {diary.date}")
            print(f"Text: {diary.text[:100] + '...' if len(diary.text) > 100 else diary.text}")
            print(f"Mood: {diary.mood or 'Not set'}")
            print(f"Keywords: {diary.keywords or 'Not set'}")
            print("-" * 50)
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    init_db()
    # Read diary.txt
    try:
        with open("diary.txt", "r", encoding="utf-8") as f:
            diary = f.read()
        if not diary.strip():
            print("Error: diary.txt is empty!")
            exit(1)
    except FileNotFoundError:
        print("Error: diary.txt not found!")
        exit(1)
    except Exception as e:
        print(f"Error reading diary.txt: {e}")
        exit(1)

    # Analyze and store diary
    try:
        result = analyze_diary_entry(diary)
        print("\n分析结果：")
        print(result)
        keywords, mood = parse_analysis_result(result)
        add_diary_entry(date.today(), diary, mood=mood, keywords=keywords)
    except Exception as e:
        print(f"Error processing diary: {e}")
        exit(1)

    # View all entries
    view_diary_entries()