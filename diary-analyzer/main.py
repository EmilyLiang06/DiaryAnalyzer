import anthropic
import os
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Diary

client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# 数据库配置
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
    response = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=300,
        temperature=0.7,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    return response.content[0].text

def init_db():
    Base.metadata.create_all(bind=engine)

def add_diary_entry(entry_date, entry_text, mood=None, keywords=None):
    session = SessionLocal()
    diary = Diary(
        date=entry_date,
        text=entry_text,
        mood=mood,
        keywords=keywords
    )
    session.add(diary)
    session.commit()
    session.close()
    print("日记已写入数据库。")

if __name__ == "__main__":
    init_db()
    # 读取 diary.txt 文件内容
    with open("diary.txt", "r", encoding="utf-8") as f:
        diary = f.read()
    # AI分析
    result = analyze_diary_entry(diary)
    print("\n分析结果：")
    print(result)
    # 可选：将分析结果简单解析后入库
    today = date.today()
    add_diary_entry(today, diary)