from flask import Flask
from flask_socketio import SocketIO, emit, join_room
import pymysql
from pymysql.cursors import DictCursor
from flask import request, jsonify  # 파일 상단 import 구역에 존재해야 함1

#ㄴ어리ㅏㅈㄷ동기홛가ㅑㄹㄷ저ㅐ랴
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")  # 모든 출처 허용

# ------------------------------
# DB 연결 함수
# ------------------------------
def get_connection():
    return pymysql.connect(
        host='127.0.0.1',       # DB 주소
        user='root',            # DB 계정
        password='1234',        # DB 비밀번호
        db='my_o2o_app',              # DB 이름
        charset='utf8mb4',
        cursorclass=DictCursor
    )

# ------------------------------
# 1️⃣ 채팅방 입장
# ------------------------------
@socketio.on('join_room')
def handle_join_room(data):
    """
    안드로이드에서 room_id를 보내면 해당 채팅방에 join
    data: { "room_id": 10, "user_id": 1 }
    """
    room_id = data.get("room_id")
    user_id = data.get("user_id")
    if not room_id:
        return

    join_room(str(room_id))
    print(f"✅ [Socket] user_id={user_id} join room_id={room_id}")

    # 필요 시 채팅방 히스토리 로딩도 가능
    # emit('load_history', messages, room=request.sid)

# ------------------------------
# 2️⃣ 메시지 수신 & DB 저장
# ------------------------------
# 기능: 실시간 메시지 저장 + 방 메타 업데이트 + 브로드캐스트
# - DB A안에 맞춰 sender_type을 저장한다.
# - emit 시에도 senderType/createdAt을 내려서 클라 분기가 가능하도록 한다.

@socketio.on('send_message')
def handle_send_message(data):
    """
    기능: 메시지 저장 → 방금 저장된 행을 SELECT → DB의 created_at 포함해 브로드캐스트
    """
    room_id     = data.get("room_id")
    sender_id   = data.get("sender_id")
    sender_type = (data.get("sender_type") or "USER").upper()
    message     = data.get("message")

    if not room_id or not sender_id or not message:
        print("❌ 메시지 형식 오류:", data); return
    if sender_type not in ("USER", "EXPERT"):
        print("❌ sender_type 오류:", sender_type); return

    try:
        conn = get_connection()
        with conn.cursor(DictCursor) as cursor:
            # 1) INSERT
            cursor.execute("""
                INSERT INTO chat_message
                    (room_id, sender_id, sender_type, message_type, message_content, created_at)
                VALUES (%s, %s, %s, 'text', %s, NOW())
            """, (room_id, sender_id, sender_type, message))
            message_id = cursor.lastrowid

            # 2) SELECT (포맷 고정: yyyy-MM-dd HH:mm:ss)
            cursor.execute("""
                SELECT
                    message_id      AS messageId,
                    room_id         AS roomId,
                    sender_id       AS senderId,
                    sender_type     AS senderType,
                    message_content AS message,
                    DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:%%i:%%s') AS createdAt
                FROM chat_message
                WHERE message_id = %s
            """, (message_id,))
            row = cursor.fetchone()

            # 2-1) 방 메타 갱신
            preview = message[:60]
            cursor.execute("""
                UPDATE chat_room
                SET last_message_id = %s,
                    last_message_at = NOW(),
                    last_message_preview = %s
                WHERE room_id = %s
            """, (message_id, preview, room_id))
            conn.commit()

        # 3) 브로드캐스트 (camelCase)
        socketio.emit('receive_message', row, room=str(room_id))
        print(f"✅ 메시지 저장/전송 완료: room={room_id}, id={message_id}")

    except Exception as e:
        print("❌ 메시지 저장 실패:", e)
    finally:
        if 'conn' in locals(): conn.close()

# ------------------------------
# 업체 채팅보내기
# ------------------------------
@app.route("/chat/test/expert", methods=["POST"])
def test_send_as_expert():
    """
    기능: 전문가가 보낸 것처럼 테스트 메시지 저장 후 같은 소켓 인스턴스로 브로드캐스트
    """
    data = request.get_json() or {}
    room_id   = data.get("room_id")
    expert_id = data.get("expert_id")
    message   = (data.get("message") or "").strip()

    if not room_id or not expert_id or not message:
        return jsonify({"success": False, "message": "room_id, expert_id, message 필수"}), 400

    try:
        conn = get_connection()
        with conn.cursor(DictCursor) as cursor:
            # 1) INSERT
            cursor.execute("""
                INSERT INTO chat_message
                  (room_id, sender_id, sender_type, message_type, message_content, created_at)
                VALUES (%s, %s, 'EXPERT', 'text', %s, NOW())
            """, (room_id, expert_id, message))
            msg_id = cursor.lastrowid

            # 2) SELECT (포맷 고정)
            cursor.execute("""
                SELECT
                    message_id      AS messageId,
                    room_id         AS roomId,
                    sender_id       AS senderId,
                    sender_type     AS senderType,
                    message_content AS message,
                    DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:%%i:%%s') AS createdAt
                FROM chat_message
                WHERE message_id = %s
            """, (msg_id,))
            row = cursor.fetchone()

            # 3) 방 메타 갱신
            preview = message[:60]
            cursor.execute("""
                UPDATE chat_room
                   SET last_message_id = %s,
                       last_message_at = NOW(),
                       last_message_preview = %s
                 WHERE room_id = %s
            """, (msg_id, preview, room_id))
            conn.commit()

        # 4) 소켓 브로드캐스트
        socketio.emit('receive_message', row, room=str(room_id))
        return jsonify({"success": True, "messageId": msg_id})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals(): conn.close()


# ------------------------------
# 채팅 시간 관리?
# ------------------------------
@app.get("/api/rooms/<int:room_id>/messages")
def get_messages(room_id: int):
    conn = get_connection()
    try:
        with conn.cursor(DictCursor) as cursor:
            cursor.execute("""
                SELECT
                    message_id      AS messageId,
                    room_id         AS roomId,
                    sender_id       AS senderId,
                    sender_type     AS senderType,
                    message_content AS message,
                    DATE_FORMAT(created_at, '%%Y-%%m-%%d %%H:%%i:%%s') AS createdAt
                FROM chat_message
                WHERE room_id = %s
                ORDER BY created_at ASC, message_id ASC
            """, (room_id,))
            rows = cursor.fetchall()
        return jsonify({"success": True, "messages": rows})
    except Exception as e:
        print("get_messages error:", e)
        return jsonify({"success": False, "messages": []}), 500
    finally:
        conn.close()       

# ------------------------------
# 서버 실행
# ------------------------------
if __name__ == '__main__':
    # 채팅 서버는 5001번 포트
    socketio.run(app, host='0.0.0.0', port=5001)
