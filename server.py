from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
import sqlite3
import shutil
from pathlib import Path
import uvicorn
from fastapi.staticfiles import StaticFiles

# FastAPIのインスタンスを作成
app = FastAPI()

# アップロードディレクトリを指定
UPLOAD_DIR = 'uploads'
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)  # アップロードディレクトリを作成

# CORSミドルウェアの設定（開発時のみ使用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルの提供設定（uploadsディレクトリを公開）
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# データベース初期化関数
def init_db():
    with sqlite3.connect("music.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS music (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                filename TEXT NOT NULL,
                completed BOOLEAN DEFAULT FALSE
            )
        """)

# データベース初期化
init_db()

# 音楽データ用のPydanticモデル
class Music(BaseModel):
    title: str
    completed: bool = False

# 音楽ファイルのアップロードエンドポイント
@app.post("/music/upload")
async def upload_music(file: UploadFile = File(...)):
    try:
        file_location = f"{UPLOAD_DIR}/{file.filename}"
        with open(file_location, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # 音楽情報をデータベースに保存
        with sqlite3.connect("music.db") as conn:
            cursor = conn.execute(
                "INSERT INTO music (title, filename, completed) VALUES (?, ?, ?)",
                (file.filename, file.filename, False),
            )
            music_id = cursor.lastrowid

        return {"id": music_id, "title": file.filename, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail="File upload failed")

# 音楽リストを取得するエンドポイント
@app.get("/music")
def get_music():
    with sqlite3.connect("music.db") as conn:
        music_list = conn.execute("SELECT * FROM music").fetchall()
        return [{"id": row[0], "title": row[1], "filename": row[2], "completed": row[3]} for row in music_list]

# 音楽IDで特定の音楽情報を取得するエンドポイント
@app.get("/music/{music_id}")
def get_music_by_id(music_id: int):
    with sqlite3.connect("music.db") as conn:
        music = conn.execute("SELECT * FROM music WHERE id = ?", (music_id,)).fetchone()
        if not music:
            raise HTTPException(status_code=404, detail="Music not found")
        return {"id": music[0], "title": music[1], "filename": music[2], "completed": music[3]}

# 音楽を削除するエンドポイント
@app.delete("/music/{music_id}")
def delete_music(music_id: int):
    with sqlite3.connect("music.db") as conn:
        cursor = conn.execute("DELETE FROM music WHERE id = ?", (music_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Music not found")
        return {"message": "Music deleted"}
    
# ルートエンドポイントを追加
@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("client.html", "r", encoding="utf-8") as f:
        return f.read()

# FastAPIアプリケーションを起動
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)  #uvicorn server:app --host 0.0.0.0 --reload


