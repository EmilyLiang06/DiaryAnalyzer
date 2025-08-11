from flask import Flask, render_template_string, request, redirect, url_for
import os
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Diary
from dotenv import load_dotenv
from anthropic import Anthropic
from collections import Counter

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

def init_db():
    Base.metadata.create_all(bind=engine)

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

def parse_analysis_result(result: str) -> dict:
    lines = result.split("\n")
    analysis = {
        "keywords": lines[0].replace("关键词: ", "").strip()[:256] if lines[0].startswith("关键词:") else "Not available",
        "mood": lines[1].replace("情绪: ", "").strip()[:32] if lines[1].startswith("情绪:") else "Not available",
        "feedback": lines[2].replace("反馈: ", "").strip() if lines[2].startswith("反馈:") else "Not available",
        "recommended_task": lines[3].replace("推荐任务: ", "").strip() if lines[3].startswith("推荐任务:") else "Not available"
    }
    return analysis

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
        return True
    except Exception as e:
        print(f"Error adding diary entry: {e}")
        return False
    finally:
        session.close()

def get_all_diaries():
    session = SessionLocal()
    try:
        return session.query(Diary).order_by(Diary.date.desc()).all()
    except Exception as e:
        print(f"Error fetching diaries: {e}")
        return []
    finally:
        session.close()

def get_diary_by_id(diary_id):
    session = SessionLocal()
    try:
        return session.query(Diary).filter(Diary.id == diary_id).first()
    except Exception as e:
        print(f"Error fetching diary: {e}")
        return None
    finally:
        session.close()

def get_mood_stats():
    session = SessionLocal()
    try:
        moods = [diary.mood for diary in session.query(Diary).all() if diary.mood]
        if not moods:
            return {"Happy": 0, "Sad": 0, "Neutral": 0}
        mood_counts = Counter(moods)
        total = sum(mood_counts.values())
        return {mood: (count / total * 100) for mood, count in mood_counts.items()}
    except Exception as e:
        print(f"Error fetching mood stats: {e}")
        return {"Happy": 0, "Sad": 0, "Neutral": 0}
    finally:
        session.close()

# Flask app setup
app = Flask(__name__)
init_db()  # Initialize database on startup

# HTML templates with custom styles using your colors
HOME_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Diary Analyzer</title>
    <style>
        body {
            background-color: #faf7ea; /* 浅黄 */
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            display: flex;
            height: 100vh;
            box-sizing: border-box;
        }
        .history-container {
            width: 30%;
            padding-right: 20px;
            border-right: 1px solid #d3d3d3;
            position: relative;
        }
        .input-container {
            width: 70%;
            padding-left: 20px;
            position: relative;
        }
        .scrollable {
            overflow-y: auto;
            max-height: 80vh;
            border: 2px solid #d3d3d3;
            border-radius: 15px;
            padding: 10px;
            margin-top: 40px; /* Space for hide button */
        }
        ul {
            list-style-type: none;
            padding: 0;
        }
        li {
            margin: 10px 0;
            background-color: #d2e2fd; /* 浅蓝 100% */
            padding: 10px;
            border-radius: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        li .date {
            font-weight: bold;
            margin-right: 10px;
        }
        li .keywords {
            color: #555;
        }
        a {
            color: #1e90ff;
            text-decoration: none;
            width: 100%;
            display: block;
        }
        a:hover {
            text-decoration: underline;
        }
        h1 {
            color: #333;
            font-size: 24px;
        }
        textarea {
            width: 100%;
            height: 300px;
            border-radius: 15px;
            border: 2px solid #d3d3d3;
            padding: 10px;
            margin: 10px 0;
            resize: none;
            background-color: #ffffff; /* 纯白 */
        }
        textarea:focus {
            outline: none;
        }
        textarea:placeholder-shown {
            color: #888;
        }
        .buttons {
            text-align: right;
            margin-right: 20px; /* 靠右 */
        }
        input[type="submit"] {
            padding: 10px 20px;
            margin: 5px;
            border-radius: 15px;
            border: none;
            cursor: pointer;
        }
        #save-btn {
            background-color: #dde8ca; /* 浅绿 */
        }
        #report-btn {
            background-color: #d2e2fd; /* 浅蓝 */
        }
        #hide-btn {
            position: absolute;
            top: 0;
            left: 0;
            background-color: #d2e2fd; /* 浅蓝 */
            border: none;
            padding: 5px 10px;
            border-radius: 5px;
            cursor: pointer;
        }
        .slider {
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            width: 10px;
            height: 300px;
            background-color: rgba(210, 226, 253, 0.3); /* 浅蓝 30% 透明 */
            border-radius: 5px;
            cursor: pointer;
        }
    </style>
    <script>
        function toggleHistory() {
            var history = document.getElementById('history-list');
            var btn = document.getElementById('hide-btn');
            if (history.style.display === 'none') {
                history.style.display = 'block';
                btn.textContent = '隐藏历史';
            } else {
                history.style.display = 'none';
                btn.textContent = '显示历史';
            }
        }
        document.getElementById('diary').addEventListener('focus', function() {
            if (this.value === '输入...') this.value = '';
        });
        document.getElementById('diary').addEventListener('blur', function() {
            if (this.value === '') this.value = '输入...';
        });
    </script>
</head>
<body>
    <div class="history-container">
        <button id="hide-btn" onclick="toggleHistory()">隐藏历史</button>
        <div id="history-list" class="scrollable">
            {% if diaries %}
            <ul>
                {% for diary in diaries %}
                <li>
                    <span class="date">{{ diary.date.strftime('%m月%d日，%Y') }}</span>
                    <span class="keywords">{{ diary.keywords or '无关键词' }}</span>
                </li>
                {% endfor %}
            </ul>
            {% else %}
            <p>没有找到日记条目。</p>
            {% endif %}
        </div>
    </div>
    <div class="input-container">
        <h1>今天发生了什么？</h1>
        <form method="POST" action="/analyze">
            <textarea id="diary" name="diary" placeholder="输入..." required>输入...</textarea>
            <div class="slider"></div>
            <div class="buttons">
                <input type="submit" id="save-btn" value="保存">
                <input type="submit" id="report-btn" value="生成报告" formaction="/analysis">
            </div>
        </form>
    </div>
</body>
</html>
"""

RESULT_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>分析结果</title>
    <style>
        body {
            background-color: #faf7ea; /* 浅黄 */
            font-family: Arial, sans-serif;
            margin: 20px;
            text-align: center;
        }
        .container {
            background-color: #fff;
            border-radius: 20px;
            padding: 20px;
            width: 500px;
            margin: 0 auto;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            font-size: 24px;
        }
        p {
            margin: 10px 0;
        }
        a {
            color: #1e90ff;
            text-decoration: none;
            margin: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>分析结果</h1>
        <p><strong>关键词:</strong> {{ analysis.keywords }}</p>
        <p><strong>情绪:</strong> {{ analysis.mood }}</p>
        <p><strong>反馈:</strong> {{ analysis.feedback }}</p>
        <p><strong>推荐任务:</strong> {{ analysis.recommended_task }}</p>
        <p><strong>日记已保存:</strong> {{ saved }}</p>
        <a href="/">返回输入</a>
    </div>
</body>
</html>
"""

DETAIL_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>日记详情</title>
    <style>
        body {
            background-color: #faf7ea; /* 浅黄 */
            font-family: Arial, sans-serif;
            margin: 20px;
            text-align: center;
        }
        .container {
            background-color: #fff;
            border-radius: 20px;
            padding: 20px;
            width: 500px;
            margin: 0 auto;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            font-size: 24px;
        }
        p, pre {
            margin: 10px 0;
        }
        pre {
            white-space: pre-wrap;
            border: 2px solid #d3d3d3;
            border-radius: 15px;
            padding: 10px;
            text-align: left;
        }
        a {
            color: #1e90ff;
            text-decoration: none;
            margin: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>日记详情</h1>
        {% if diary %}
        <p><strong>日期:</strong> {{ diary.date.strftime('%m月%d日，%Y') }}</p>
        <p><strong>情绪:</strong> {{ diary.mood or '未设置' }}</p>
        <p><strong>关键词:</strong> {{ diary.keywords or '未设置' }}</p>
        <p><strong>全文:</strong></p>
        <pre>{{ diary.text }}</pre>
        {% else %}
        <p>未找到日记条目。</p>
        {% endif %}
        <br>
        <a href="/">返回主页</a>
    </div>
</body>
</html>
"""

ANALYSIS_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>分析报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            background-color: #faf7ea; /* 浅黄 */
            font-family: Arial, sans-serif;
            margin: 20px;
            text-align: center;
        }
        .container {
            background-color: #fff;
            border-radius: 20px;
            padding: 20px;
            width: 600px;
            margin: 0 auto;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1, h2 {
            color: #333;
            font-size: 24px;
        }
        canvas {
            margin: 20px 0;
        }
        a {
            color: #1e90ff;
            text-decoration: none;
            margin: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>分析报告</h1>
        <h2>情绪统计</h2>
        <canvas id="moodChart" width="400" height="200"></canvas>
        <script>
            const moodData = {
                labels: {{ mood_stats_labels|tojson }},
                datasets: [{
                    data: {{ mood_stats_values|tojson }},
                    backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56']
                }]
            };
            new Chart(document.getElementById('moodChart'), {
                type: 'pie',
                data: moodData,
            });
        </script>
        <h2>情绪趋势</h2>
        <canvas id="trendChart" width="400" height="200"></canvas>
        <script>
            const trendData = {
                labels: {{ trend_labels|tojson }},
                datasets: [{
                    label: 'Mood Score',
                    data: {{ trend_values|tojson }},
                    borderColor: '#36A2EB',
                    fill: false
                }]
            };
            new Chart(document.getElementById('trendChart'), {
                type: 'line',
                data: trendData,
            });
        </script>
        <br>
        <a href="/">返回主页</a>
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def home():
    diaries = get_all_diaries()
    return render_template_string(HOME_TEMPLATE, diaries=diaries)

@app.route("/analyze", methods=["POST"])
def analyze():
    diary = request.form.get("diary")
    if not diary.strip() or diary == "输入...":
        return "Error: Diary entry is empty!", 400

    try:
        result = analyze_diary_entry(diary)
        analysis = parse_analysis_result(result)
        saved = add_diary_entry(date.today(), diary, mood=analysis["mood"], keywords=analysis["keywords"])
        return render_template_string(RESULT_TEMPLATE, analysis=analysis, saved="Yes" if saved else "No")
    except Exception as e:
        return f"Error processing diary: {e}", 500

@app.route("/diary/<int:diary_id>", methods=["GET"])
def view_diary(diary_id):
    diary = get_diary_by_id(diary_id)
    return render_template_string(DETAIL_TEMPLATE, diary=diary)

@app.route("/analysis", methods=["GET"])
def analysis():
    mood_stats = get_mood_stats()
    trend_labels = [d.date.strftime('%Y-%m-%d') for d in get_all_diaries()]
    trend_values = [20, 25, 30, 35, 40]  # Placeholder, replace with mood score logic
    if not trend_labels:
        trend_labels = [date.today().strftime('%Y-%m-%d')]
        trend_values = [0]
    return render_template_string(ANALYSIS_TEMPLATE, 
                                 mood_stats_labels=list(mood_stats.keys()),
                                 mood_stats_values=[round(val, 2) for val in mood_stats.values()],
                                 trend_labels=trend_labels,
                                 trend_values=trend_values)

if __name__ == "__main__":
    app.run(debug=True)