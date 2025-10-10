import sqlite3
from utils.config import DB_PATH

with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.cursor()
    # 마지막으로 추가된 레코드의 id 찾기
    cursor.execute("SELECT id FROM image_logs ORDER BY id DESC LIMIT 1")
    last_id = cursor.fetchone()
    if last_id:
        cursor.execute("DELETE FROM image_logs WHERE id = ?", (last_id[0],))
        conn.commit()
        print(f"최근 기록(id={last_id[0]}) 삭제 완료")
    else:
        print("삭제할 기록이 없습니다.")
