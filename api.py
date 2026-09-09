"""
api.py
------
שכבת ה-API ש"ההנחיות מניחות שכבר קיימת". בפרויקט האמצע לא היה REST API
בכלל (רק CLI), אז זו למעשה גם ההשלמה של החסר וגם השכבה שהצ'אטבוט קורא לה.

עקרון אבטחה מרכזי (דרישה קשיחה בהנחיות):
  לפני אימות ת"ז מוצלח - אסור לחשוף שום פרט תור.
  לכן: /api/customers/search מחזיר רק id + full_name (בלי ת"ז, בלי תורים).
  /api/appointments דורש token שמתקבל *רק* אחרי אימות מוצלח ב-/api/customers/verify.
  זה אוכף את הדרישה גם ברמת ה-API עצמו, לא רק בלוגיקת הצ'אטבוט.
"""

import secrets
import time
from flask import Blueprint, request, jsonify

import db_manager

api_bp = Blueprint('api', __name__, url_prefix='/api')

# טוקן זמני: token -> (customer_id, expires_at_epoch)
# מימוש in-memory מספיק לפרויקט לימודי; לא שורד ריסטארט/multi-process.
_VERIFIED_TOKENS = {}
TOKEN_TTL_SECONDS = 600  # 10 דקות


def _new_token(customer_id):
    token = secrets.token_urlsafe(16)
    _VERIFIED_TOKENS[token] = (customer_id, time.time() + TOKEN_TTL_SECONDS)
    return token


def _check_token(token, customer_id):
    entry = _VERIFIED_TOKENS.get(token)
    if not entry:
        return False
    cust_id, expires_at = entry
    if time.time() > expires_at:
        _VERIFIED_TOKENS.pop(token, None)
        return False
    return cust_id == customer_id


@api_bp.route('/customers/search', methods=['GET'])
def search_customers():
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({"error": "missing 'name' query param"}), 400
    results = db_manager.find_customers_by_name(name)
    # במכוון: רק id + full_name. שום פרט מזהה/תור לא חוזר כאן.
    return jsonify({"matches": results})


@api_bp.route('/customers/verify', methods=['POST'])
def verify_customer():
    data = request.get_json(force=True) or {}
    customer_id = data.get('customer_id')
    teudat_zehut = data.get('teudat_zehut')
    if not customer_id or not teudat_zehut:
        return jsonify({"error": "missing customer_id or teudat_zehut"}), 400

    ok = db_manager.verify_customer_id(customer_id, teudat_zehut)
    if not ok:
        return jsonify({"verified": False})

    token = _new_token(customer_id)
    return jsonify({"verified": True, "token": token})


@api_bp.route('/appointments', methods=['GET'])
def get_appointments():
    customer_id = request.args.get('customer_id', type=int)
    token = request.args.get('token', '')
    if not customer_id or not token:
        return jsonify({"error": "missing customer_id or token"}), 400
    if not _check_token(token, customer_id):
        return jsonify({"error": "not verified"}), 403

    appts = db_manager.get_appointments_by_customer(customer_id)
    return jsonify({"appointments": appts})
