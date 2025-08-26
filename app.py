# app.py
# DB 연결 함수 + 사용자 등록 테스트ㅇㄹㄴㅇㄹㄴㄷ
#ㄴㄹ더나ㅣㄹㅇㄴㄹ
import pymysql
import pymysql.cursors
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# ✅ 1. DB 연결 함수
def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DB_NAME"),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
        
    )

# ✅ 2. 사용자 등록 함수 (회원가입 시 호출)
def insert_user(user_id, password, name, phone_number):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO user (id, password, name, phone_number)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (user_id, password, name, phone_number))
        conn.commit()
        print("✅ 사용자 등록 성공")
    except Exception as e:
        print("❌ 사용자 등록 실패:", e)
    finally:
        conn.close()

# ✅ 3. 테스트용 실행 코드
if __name__ == "__main__":
    insert_user(
        user_id="testuser01",
        password="1234",
        name="홍길동",
        phone_number="010-1234-5678"
    )
