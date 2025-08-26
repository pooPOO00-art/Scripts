# server.py 아니이건왜 동기화가 안돼
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify
from app import get_connection
from flask_cors import CORS
from pymysql.cursors import DictCursor


app = Flask(__name__)
CORS(app)


# ✅ 사용자 로그인
@app.route("/user/login", methods=["POST"])
def login_user():
    print("✅ [서버] /user/login 요청 도착")
    data = request.get_json()
    user_id = data.get("id")
    password = data.get("password")

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = """
                SELECT user_id, id, password, name, phone_number
                FROM user
                WHERE id = %s AND password = %s
            """
            cursor.execute(sql, (user_id, password))
            user = cursor.fetchone()

            if user:
                return jsonify({
                    "success": True,
                    "user": {
                        "userId": user["user_id"],
                        "id": user["id"],
                        "password": user["password"],
                        "name": user["name"],
                        "phone": user["phone_number"]
                    }
                })
            else:
                return jsonify({"success": False, "message": "아이디 또는 비밀번호가 틀렸습니다."}), 401
    except Exception as e:
        import traceback
        print("❌ 서버 오류 발생:", str(e))
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


# ✅ 카테고리 목록 조회
@app.route("/category/list", methods=["GET"])
def get_categories():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = "SELECT category_id, parent_id, category_name FROM service_category"
            cursor.execute(sql)
            categories = cursor.fetchall()
        return jsonify({"success": True, "categories": categories})
    except Exception as e:
        print("❌ 카테고리 로드 실패:", e)
        return jsonify({"success": False, "message": str(e)})
    finally:
        if 'conn' in locals():
            conn.close()


@app.route("/experts/filter", methods=["GET"])
def get_experts_by_filter():
    category_id = request.args.get("category_id", type=int)
    district_id = request.args.get("district_id", type=int)
    region_id = request.args.get("region_id", type=int)
    keyword = request.args.get("keyword", type=str)

    try:
        conn = get_connection()
        cursor = conn.cursor(DictCursor)  # ✅ dictionary=True → DictCursor

        sql = """
            SELECT e.expert_id, e.company_name, e.description, e.profile_image
            FROM expert e
            JOIN expert_condition ec ON e.expert_id = ec.expert_id
            WHERE 1=1
        """
        params = []

        if category_id is not None:
            sql += " AND ec.service_detail_id = %s "
            params.append(category_id)

        if keyword:
            sql += " AND e.company_name LIKE %s "
            params.append(f"%{keyword}%")

        # 지역 필터링
        
                # ✅ 지역 필터링 (None 안전 처리)
        if district_id is None:
            # district_id가 없는 경우 → 지역 조건 없음
            pass
        elif district_id == -1:
            # 전국 전체
            pass
        elif 47 <= district_id <= 63:
            # 도 전체
            sql += """
                AND (
                    ec.district_id = %s
                    OR ec.district_id IN (
                        SELECT district_id FROM district
                        WHERE region_id = %s
                        AND district_name != '전체'
                    )
                )
            """
            params.extend([district_id, region_id])
        else:
            # 개별 시군구
            sql += " AND ec.district_id = %s "
            params.append(district_id)



        sql += " GROUP BY e.expert_id "

        cursor.execute(sql, tuple(params))
        experts = cursor.fetchall()

        return jsonify({"success": True, "experts": experts})

    except Exception as e:
        print("❌ 전문가 조회 실패:", e)
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        if 'conn' in locals():
            conn.close()  # ✅ is_connected 제거

            
@app.route("/regions", methods=["GET"])
def get_regions():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = "SELECT region_id, region_name FROM region"
            cursor.execute(sql)
            rows = cursor.fetchall()

        # 결과를 JSON 형식으로 가공
        regions = []
        for row in rows:
            regions.append({
                "region_id": row["region_id"],
                "region_name": row["region_name"]
            })

        return jsonify(regions)  # ✅ 리스트로 반환
    except Exception as e:
        print("❌ 지역 목록 로드 실패:", e)
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route("/regions/<int:region_id>/districts", methods=["GET"])
def get_districts(region_id):
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = """
                SELECT district_id, district_name
                FROM district
                WHERE region_id = %s
            """
            cursor.execute(sql, (region_id,))
            rows = cursor.fetchall()

        # 결과를 JSON 리스트로 가공
        districts = []
        for row in rows:
            districts.append({
                "district_id": row["district_id"],
                "district_name": row["district_name"]
            })

        return jsonify(districts)
    except Exception as e:
        print(f"❌ 시군구 목록 조회 실패 (region_id={region_id}):", e)
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route("/districts", methods=["GET"])
def get_all_districts():
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = "SELECT district_id, region_id, district_name FROM district"
            cursor.execute(sql)
            rows = cursor.fetchall()

        districts = []
        for row in rows:
            districts.append({
                "district_id": row["district_id"],
                "region_id": row["region_id"],
                "district_name": row["district_name"]
            })

        return jsonify(districts)
    except Exception as e:
        print("❌ 전체 시군구 조회 실패:", e)
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()
            
@app.route("/questions", methods=["GET"])
def get_questions():
    category_id = request.args.get("categoryId", type=int)
    print(f"✅ [서버] 질문 조회 요청: categoryId={category_id}")

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # 1️⃣ 질문 목록 조회
            sql_question = """
                SELECT question_id, question_content
                FROM question
                WHERE service_detail_id = %s
                ORDER BY question_id
            """
            cursor.execute(sql_question, (category_id,))
            questions = cursor.fetchall()

            result = []
            for q in questions:
                # 2️⃣ 질문별 옵션 조회
                sql_option = """
                    SELECT option_id, option_content
                    FROM question_option
                    WHERE question_id = %s
                    ORDER BY option_id
                """
                cursor.execute(sql_option, (q["question_id"],))
                options = cursor.fetchall()

                # Python dict 형태로 조합
                result.append({
                    "question_id": q["question_id"],
                    "content": q["question_content"],
                    "options": [
                        {"option_id": opt["option_id"], "content": opt["option_content"]}
                        for opt in options
                    ]
                })

        return jsonify(result)
    except Exception as e:
        print("❌ 질문 조회 실패:", e)
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# ✅ 견적 요청 저장 API
@app.route("/estimate", methods=["POST"])
def submit_estimate():
    """
    사용자가 견적 요청을 보낼 때 호출되는 API
    - user_id, category_id, district_id는 필수
    - expert_id가 0이면 NULL로 저장 (아직 전문가 배정되지 않음)
    - 옵션(option_ids)은 별도 테이블(user_selected_option)에 저장
    """
    data = request.get_json()
    user_id = data.get("user_id")
    category_id = data.get("category_id")
    district_id = data.get("district_id")
    selected_options = data.get("option_ids", [])
    expert_id = data.get("expert_id")  # 직접견적 여부 (없으면 0)

    print(f"✅ [서버] 견적 요청: user_id={user_id}, category_id={category_id}, "
          f"district_id={district_id}, expert_id={expert_id}, options={selected_options}")

    # ✅ expert_id가 0이면 NULL로 변환 (FK 위반 방지)
    if not expert_id or expert_id == 0:
        expert_id = None

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # 1️⃣ estimate_request 저장
            sql_insert_request = """
                INSERT INTO estimate_request 
                    (user_id, category_id, district_id, expert_id, status, created_at)
                VALUES (%s, %s, %s, %s, '요청중', NOW())
            """
            cursor.execute(sql_insert_request, 
                           (user_id, category_id, district_id, expert_id))
            estimate_id = cursor.lastrowid  # 방금 삽입된 PK

            # 2️⃣ 선택된 옵션 저장
            sql_insert_option = """
                INSERT INTO user_selected_option (estimate_id, option_id)
                VALUES (%s, %s)
            """
            for option_id in selected_options:
                cursor.execute(sql_insert_option, (estimate_id, option_id))

            conn.commit()

        print(f"✅ 견적 저장 완료: estimate_id={estimate_id}")
        return jsonify({"success": True, "estimate_id": estimate_id})

    except Exception as e:
        print("❌ 견적 저장 실패:", e)
        return jsonify({"success": False, "message": str(e)}), 500

    finally:
        if 'conn' in locals():
            conn.close()



            
 # ✅ /experts → /experts/filter 리다이렉트
@app.route("/experts", methods=["GET"])
def redirect_experts():
    from flask import redirect, request
    # 기존 쿼리스트링 유지
    return redirect("/experts/filter?" + request.query_string.decode())

@app.route("/estimate/list", methods=["GET"])
def get_estimate_list():
    user_id = request.args.get("userId", type=int)
    print(f"✅ [서버] /estimate/list 요청: userId={user_id}")

    try:
        conn = get_connection()
        with conn.cursor(DictCursor) as cursor:
            sql = """
                SELECT 
                    er.estimate_id AS estimateId,
                    er.user_id AS userId,
                    er.category_id AS categoryId,
                    sc.category_name AS categoryName,
                    er.district_id AS districtId,
                    d.district_name AS districtName,
                    er.created_at AS createdAt,
                    er.expert_id AS expertId,                -- ✅ 직접 견적 여부 확인
                    IF(er.expert_id IS NOT NULL, 1, 0) AS isDirect, -- ✅ 바로 앱에서 구분
                    TIMESTAMPDIFF(
                        HOUR, 
                        NOW(), 
                        DATE_ADD(er.created_at, INTERVAL 48 HOUR)
                    ) AS hoursLeft,
                    (
                        SELECT COUNT(*) 
                        FROM expert_estimate ee
                        WHERE ee.estimate_id = er.estimate_id
                    ) AS receivedCount
                FROM estimate_request er
                JOIN service_category sc ON er.category_id = sc.category_id
                JOIN district d ON er.district_id = d.district_id
                WHERE er.user_id = %s
                ORDER BY er.created_at DESC
            """
            cursor.execute(sql, (user_id,))
            rows = cursor.fetchall()

            # 🔹 상태 계산 로직
            for row in rows:
                hours_left = row.get("hoursLeft", 0)
                received_count = row.get("receivedCount", 0)
                is_direct = row.get("isDirect", 0) == 1

                # ✅ 직접견적이면 바로 표시
                if is_direct:
                    if received_count > 0:
                        row["status"] = "직접견적(응답중)"
                    else:
                        row["status"] = "직접견적"
                else:
                    if hours_left <= 0:
                        row["status"] = "만료"
                    elif received_count > 0:
                        row["status"] = "응답중"
                    else:
                        row["status"] = "요청중"

        return jsonify(rows)

    except Exception as e:
        print("❌ 받은 견적 조회 실패:", e)
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()





# ✅ 전문가 프로필 조회
@app.route("/expert/profile", methods=["GET"])
def get_expert_profile():
    expert_id = request.args.get("expertId", type=int)
    print(f"✅ [서버] 전문가 프로필 요청: expertId={expert_id}")

    try:
        conn = get_connection()
        with conn.cursor(DictCursor) as cursor:
            sql = """
                SELECT 
                    e.expert_id,
                    e.company_name,
                    e.company_address,
                    e.description,
                    e.profile_image,
                    e.phone_number,
                    e.ceo_name,
                    e.career_years,
                    ec.service_detail_id AS category_id, -- ✅ 추가
                    -- 대표 서비스/지역
                    CONCAT(
                        COALESCE(sc.category_name, '서비스없음'),
                        ' · ',
                        COALESCE(d.district_name, '지역없음')
                    ) AS service_info
                FROM expert e
                LEFT JOIN expert_condition ec
                    ON e.expert_id = ec.expert_id
                   AND ec.is_primary = 1
                LEFT JOIN service_category sc
                    ON ec.service_detail_id = sc.category_id
                LEFT JOIN district d
                    ON ec.district_id = d.district_id
                WHERE e.expert_id = %s
            """
            cursor.execute(sql, (expert_id,))
            expert = cursor.fetchone()

        if not expert:
            return jsonify({"success": False, "message": "전문가를 찾을 수 없습니다."}), 404

        return jsonify({"success": True, "expert": expert})

    except Exception as e:
        print("❌ 전문가 프로필 조회 실패:", e)
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route("/estimate/detail", methods=["GET"])
def get_estimate_detail():
    estimate_id = request.args.get("estimateId", type=int)
    print(f"✅ [서버] /estimate/detail 요청: estimateId={estimate_id}")

    try:
        conn = get_connection()
        with conn.cursor(DictCursor) as cursor:
            sql = """
                SELECT 
                    ee.expert_estimate_id AS expertEstimateId,
                    ee.expert_id AS expertId,
                    e.company_name AS companyName,
                    e.profile_image AS profileImage,
                    ee.price AS price,
                    ee.message AS message,
                    ee.created_at AS createdAt
                FROM expert_estimate ee
                JOIN expert e ON ee.expert_id = e.expert_id
                WHERE ee.estimate_id = %s
                ORDER BY ee.created_at ASC
            """
            cursor.execute(sql, (estimate_id,))
            rows = cursor.fetchall()

        return jsonify({"success": True, "estimates": rows})

    except Exception as e:
        print("❌ 견적 상세 조회 실패:", e)
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# ✅ 사용자 회원가입
@app.route("/user/register", methods=["POST"])
def register_user():
    data = request.get_json()
    user_id = data.get("id")
    password = data.get("password")
    name = data.get("name")
    phone = data.get("phone")

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # 1️⃣ 아이디 중복 확인
            cursor.execute("SELECT COUNT(*) AS cnt FROM user WHERE id = %s", (user_id,))
            if cursor.fetchone()["cnt"] > 0:
                return jsonify({"success": False, "message": "이미 사용중인 아이디입니다."}), 400

            # 2️⃣ 회원정보 저장
            sql = """
                INSERT INTO user (id, password, name, phone_number)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (user_id, password, name, phone))
            conn.commit()

        return jsonify({"success": True, "message": "회원가입 성공!"})

    except Exception as e:
        print("❌ 회원가입 실패:", e)
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# ✅ 전문가 견적 등록 (응답중 상태로 변경) 
@app.route("/expert/estimate", methods=["POST"])
def submit_expert_estimate():
    """
    전문가가 견적을 등록하면 expert_estimate 테이블에 추가하고
    estimate_request.status = '응답중'으로 변경
    """
    data = request.get_json()
    expert_id = data.get("expertId")
    estimate_id = data.get("estimateId")
    price = data.get("price")
    message = data.get("message", "")

    print(f"✅ 전문가 견적 등록: expertId={expert_id}, estimateId={estimate_id}, price={price}")

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # 1️⃣ 전문가 견적 저장
            sql_insert = """
                INSERT INTO expert_estimate (estimate_id, expert_id, price, message, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """
            cursor.execute(sql_insert, (estimate_id, expert_id, price, message))

            # 2️⃣ 상태를 '응답중'으로 변경 (현재 요청중일 경우에만)
            sql_update = """
                UPDATE estimate_request
                SET status = '응답중'
                WHERE estimate_id = %s AND status = '요청중'
            """
            cursor.execute(sql_update, (estimate_id,))

            conn.commit()

        return jsonify({"success": True, "message": "전문가 견적 등록 완료!"})

    except Exception as e:
        print("❌ 전문가 견적 등록 실패:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


# ✅ 예약 완료 처리 (상태를 '만료'로 변경)
@app.route("/estimate/complete", methods=["POST"])
def complete_estimate():
    """
    사용자가 특정 전문가를 선택해 예약을 완료할 때 호출
    1. 예약 테이블에 기록(있다면)
    2. estimate_request.status = '만료'로 변경
    """
    data = request.get_json()
    estimate_id = data.get("estimateId")
    expert_id = data.get("expertId")  # 선택된 전문가

    print(f"✅ 예약 완료 처리: estimateId={estimate_id}, expertId={expert_id}")

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            # 1️⃣ 예약 테이블에 기록 (reservation 테이블이 있다면)
            # sql_reservation = """
            #     INSERT INTO reservation (estimate_id, expert_id, created_at)
            #     VALUES (%s, %s, NOW())
            # """
            # cursor.execute(sql_reservation, (estimate_id, expert_id))

            # 2️⃣ 상태 '만료'로 변경
            sql_update = """
                UPDATE estimate_request
                SET status = '만료'
                WHERE estimate_id = %s
            """
            cursor.execute(sql_update, (estimate_id,))

            conn.commit()

        return jsonify({"success": True, "message": "예약 완료 처리됨!"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# ✅ 전문가 전체 통계 조회 (대표 서비스/지역 1개만)
# ✅ 전문가 전체 통계 조회 (대표 서비스/지역 1개 + 업체 설명 포함)
@app.route("/experts/stats", methods=["GET"])
def get_experts_with_stats():
    try:
        conn = get_connection()
        with conn.cursor(DictCursor) as cursor:
            sql = """
                SELECT 
                    e.expert_id,
                    e.company_name,
                    e.profile_image,
                    e.career_years,
                    ANY_VALUE(e.description) AS description,
                    IFNULL(COUNT(DISTINCT r.reservation_id),0) AS reservation_count,
                    IFNULL(ROUND(AVG(rv.rating),1),0) AS avg_rating,
                    IFNULL(COUNT(rv.review_id),0) AS review_count,
                    CONCAT(
                        COALESCE(ANY_VALUE(sc.category_name), '서비스없음'),
                        ' · ',
                        COALESCE(ANY_VALUE(d.district_name), '지역없음')
                    ) AS service_info
                FROM expert e
                LEFT JOIN reservation r 
                    ON e.expert_id = r.expert_id
                LEFT JOIN review rv 
                    ON r.reservation_id = rv.reservation_id
                LEFT JOIN expert_condition ec 
                    ON e.expert_id = ec.expert_id 
                    AND ec.is_primary = 1
                LEFT JOIN service_category sc 
                    ON ec.service_detail_id = sc.category_id
                LEFT JOIN district d 
                    ON ec.district_id = d.district_id
                GROUP BY e.expert_id
            """
            cursor.execute(sql)
            experts = cursor.fetchall()

        return jsonify({"success": True, "experts": experts})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


# ✅ 전문가 통계 + 필터 조회 (카테고리/지역/키워드)
@app.route("/experts/stats/filter", methods=["GET"])
def get_experts_with_stats_filter():
    category_id = request.args.get("category_id", type=int)
    district_id = request.args.get("district_id", type=int)
    region_id = request.args.get("region_id", type=int)  # 현재 사용 안함
    keyword = request.args.get("keyword", type=str)

    try:
        conn = get_connection()
        with conn.cursor(DictCursor) as cursor:
            sql = """
                SELECT 
                    e.expert_id,
                    e.company_name,
                    e.profile_image,
                    e.career_years,
                    ANY_VALUE(e.description) AS description,
                    IFNULL(COUNT(DISTINCT r.reservation_id),0) AS reservation_count,
                    IFNULL(ROUND(AVG(rv.rating),1),0) AS avg_rating,
                    IFNULL(COUNT(rv.review_id),0) AS review_count,
                    CONCAT(
                        COALESCE(ANY_VALUE(sc.category_name), '서비스없음'),
                        ' · ',
                        COALESCE(ANY_VALUE(d.district_name), '지역없음')
                    ) AS service_info
                FROM expert e
                LEFT JOIN reservation r 
                    ON e.expert_id = r.expert_id
                LEFT JOIN review rv 
                    ON r.reservation_id = rv.reservation_id
                JOIN expert_condition ec 
                    ON e.expert_id = ec.expert_id 
                    AND ec.is_primary = 1
                LEFT JOIN service_category sc 
                    ON ec.service_detail_id = sc.category_id
                LEFT JOIN district d 
                    ON ec.district_id = d.district_id
                WHERE 1=1
            """
            params = []

            # ✅ 카테고리 필터
            if category_id:
                sql += " AND ec.service_detail_id = %s "
                params.append(category_id)

            # ✅ 키워드 필터
            if keyword:
                sql += " AND e.company_name LIKE %s "
                params.append(f"%{keyword}%")

            # ✅ 지역 필터
            if district_id is not None and district_id > 0:
                sql += " AND ec.district_id = %s "
                params.append(district_id)

            sql += " GROUP BY e.expert_id "

            cursor.execute(sql, tuple(params))
            experts = cursor.fetchall()

        return jsonify({"success": True, "experts": experts})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()
# ✅ 견적 상태 수동 업데이트 (앱에서 PATCH 요청 시 호출)
@app.route("/estimate/status", methods=["PATCH"])
def update_estimate_status():
    """
    안드로이드에서 요청한 상태로 DB를 업데이트
    PATCH /estimate/status?estimateId=1&status=응답중
    """
    estimate_id = request.args.get("estimateId", type=int)
    status = request.args.get("status", type=str)

    print(f"✅ [서버] /estimate/status 요청: estimateId={estimate_id}, status={status}")

    if not estimate_id or not status:
        return jsonify({"success": False, "message": "estimateId와 status는 필수입니다."}), 400

    # ENUM 유효성 체크 (옵션)
    if status not in ["요청중", "응답중", "만료"]:
        return jsonify({"success": False, "message": "유효하지 않은 상태값"}), 400

    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            sql = """
                UPDATE estimate_request
                SET status = %s
                WHERE estimate_id = %s
            """
            cursor.execute(sql, (status, estimate_id))
            conn.commit()

        return jsonify({"success": True, "message": f"상태가 {status}로 변경됨"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# ------------------------------
# 1️⃣ 채팅방 생성/조회
# ------------------------------
@app.route("/chat/room", methods=["POST"])
def create_or_get_chat_room():
    data = request.get_json()
    user_id = data.get("user_id")
    expert_id = data.get("expert_id")

    if not user_id or not expert_id:
        return jsonify({"success": False, "message": "user_id, expert_id는 필수"}), 400

    try:
        conn = get_connection()
        with conn.cursor(DictCursor) as cursor:
            # 기존 채팅방 있는지 확인
            cursor.execute("""
                SELECT room_id FROM chat_room 
                WHERE user_id=%s AND expert_id=%s
            """, (user_id, expert_id))
            room = cursor.fetchone()

            if room:
                room_id = room["room_id"]
            else:
                cursor.execute("""
                    INSERT INTO chat_room (user_id, expert_id)
                    VALUES (%s, %s)
                """, (user_id, expert_id))
                conn.commit()
                room_id = cursor.lastrowid

        return jsonify({"success": True, "room_id": room_id})

    except Exception as e:
        print("❌ 채팅방 생성 실패:", e)
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# ------------------------------
# 2️⃣ 내 채팅방 목록 조회
# ------------------------------
# file: server.py (기존 /chat/list 교체)
# 기능: 사용자(user_id)의 채팅방 리스트 반환
# - 응답을 루트 배열로 내려서 Android의 Call<List<ChatRoom>>에 맞춘다.
# - 키를 모델(ChatRoom)의 필드명과 동일하게 별칭 처리한다.

@app.route("/chat/list", methods=["GET"])
def get_chat_list():
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"success": False, "message": "user_id 필수"}), 400

    try:
        conn = get_connection()
        with conn.cursor(DictCursor) as cursor:
            sql = """
                SELECT 
                    cr.room_id               AS roomId,
                    cr.expert_id             AS expertId,
                    e.company_name           AS expertName,
                    e.profile_image          AS profileImage,
                    COALESCE(
                        cr.last_message_preview,
                        (SELECT cm.message_content
                           FROM chat_message cm
                          WHERE cm.room_id = cr.room_id
                          ORDER BY cm.created_at DESC, cm.message_id DESC
                          LIMIT 1)
                    )                         AS lastMessage,
                    COALESCE(
                        cr.last_message_at,
                        (SELECT cm.created_at
                           FROM chat_message cm
                          WHERE cm.room_id = cr.room_id
                          ORDER BY cm.created_at DESC, cm.message_id DESC
                          LIMIT 1)
                    )                         AS lastTime
                FROM chat_room cr
                JOIN expert e ON cr.expert_id = e.expert_id
                WHERE cr.user_id = %s
                ORDER BY (lastTime IS NULL), lastTime DESC
            """
            cursor.execute(sql, (user_id,))
            rows = cursor.fetchall()

        # ✅ 루트 배열로 반환 (성공 래퍼 제거)
        return jsonify(rows)

    except Exception as e:
        print("❌ 채팅방 목록 조회 실패:", e)
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()

# 기능: 채팅방 메시지 히스토리 조회
# - 모델(ChatMessage) 필드와 키를 일치시킨다.
# - 시간/ID 정렬을 보장한다.
# server.py
# 기능: 채팅방 메시지 히스토리 조회 (루트 배열 + 카멜케이스 키)
# server.py (/chat/messages) — 기존 라우트 수정
# 목적: 히스토리 조회에 sender_type 포함 + 정렬 안정화
@app.route("/chat/messages", methods=["GET"])
def get_chat_messages():
    room_id = request.args.get("room_id", type=int)
    if not room_id:
        return jsonify({"success": False, "message": "room_id 필수"}), 400

    try:
        conn = get_connection()
        with conn.cursor(DictCursor) as cursor:
            cursor.execute("""
                SELECT
                    message_id, room_id, sender_id,
                    sender_type,                      -- ✅ 추가
                    message_content, created_at
                FROM chat_message
                WHERE room_id=%s
                ORDER BY created_at ASC, message_id ASC
            """, (room_id,))
            rows = cursor.fetchall()

        # 기존 구조 유지(래퍼)
        return jsonify({"success": True, "messages": rows})
    finally:
        if 'conn' in locals(): conn.close()




@app.route("/chat/create", methods=["POST"])
def create_chat_room():
    data = request.get_json()
    user_id = data.get("user_id")
    expert_id = data.get("expert_id")

    # DB에서 기존 채팅방 확인
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = "SELECT room_id FROM chat_room WHERE user_id=%s AND expert_id=%s"
        cursor.execute(sql, (user_id, expert_id))
        row = cursor.fetchone()

        if row:
            room_id = row['room_id']
        else:
            sql_insert = "INSERT INTO chat_room (user_id, expert_id) VALUES (%s, %s)"
            cursor.execute(sql_insert, (user_id, expert_id))
            conn.commit()
            room_id = cursor.lastrowid

    return jsonify({"success": True, "room_id": room_id})

# file: server.py
# 기능: 테스트용 HTTP 라우트로 전문가 메시지 전송(저장 + last_* 갱신 + 소켓 broadcast)

@app.route("/chat/test/expert", methods=["POST"])
def test_send_as_expert():
    """
    요청 예시:
      POST /chat/test/expert
      { "room_id": 1, "expert_id": 5, "message": "전문가 답변입니다" }
    """
    data = request.get_json()
    room_id   = data.get("room_id")
    expert_id = data.get("expert_id")
    message   = data.get("message", "")

    if not room_id or not expert_id or not message:
        return jsonify({"success": False, "message": "room_id, expert_id, message 필수"}), 400

    # 기존 소켓 저장 로직과 동일하게 처리
    try:
        conn = get_connection()
        with conn.cursor(DictCursor) as cursor:
            cursor.execute("""
                INSERT INTO chat_message
                  (room_id, sender_id, sender_type, message_type, message_content, created_at)
                VALUES (%s, %s, 'EXPERT', 'text', %s, NOW())
            """, (room_id, expert_id, message))
            message_id = cursor.lastrowid

            cursor.execute("SELECT created_at FROM chat_message WHERE message_id=%s", (message_id,))
            created_at = cursor.fetchone()["created_at"]

            preview = message[:60] if message else ""
            cursor.execute("""
                UPDATE chat_room
                   SET last_message_id = %s,
                       last_message_at = NOW(),
                       last_message_preview = %s
                 WHERE room_id = %s
            """, (message_id, preview, room_id))
            conn.commit()

        # 실시간으로 클라에 뿌리기 (ChatFragment가 수신함)
        socketio.emit('receive_message', {
            "messageId":  message_id,
            "roomId":     room_id,
            "senderId":   expert_id,
            "senderType": "EXPERT",
            "message":    message,
            "createdAt":  str(created_at)
        }, room=str(room_id))

        return jsonify({"success": True, "messageId": message_id})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        if 'conn' in locals():
            conn.close()



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
