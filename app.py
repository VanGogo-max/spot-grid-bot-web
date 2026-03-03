"""
GridPulse — Автоматизирана крипто търговска платформа
Версия: 2.0 (с база данни и плащания)
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3
import os
from datetime import datetime
import secrets

# Импортиране на модули
from database import (
    init_database,
    register_user,
    get_user_by_email,
    get_user_by_id,
    activate_subscription,
    create_payment,
    confirm_payment,
    get_payment_by_tx_hash,
    get_user_payments,
    get_user_trades,
    get_user_referrals,
    get_total_referral_earnings,
    get_user_api_keys,
    get_user_referrals_count,
    get_user_trade_stats,
    get_dashboard_stats
)

from payments.polygon_handler import (
    init_polygon_handler,
    verify_payment,
    get_wallet_balance,
    generate_payment_address
)

import config

# Инициализация на Flask приложението
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Случаен секретен ключ

# ============================================================
# ИНИЦИАЛИЗИРАНЕ ПРИ СТАРТИРАНЕ
# ============================================================

# Създаване на базата данни при първо стартиране
if not os.path.exists('gridpulse.db'):
    init_database()
    print("✅ Базата данни е създадена!")

# Инициализация на Polygon handler
init_polygon_handler(config)
print("✅ Polygon handler е инициализиран!")

# ============================================================
# СТРАНИЦИ НА САЙТА
# ============================================================

@app.route('/')
def index():
    """Лендинг страница"""
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Регистрация на нов потребител"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        referral = request.form.get('referral', None)
        
        # Регистрация
        result = register_user(email, password, referral)
        
        if result['success']:
            flash('Регистрацията е успешна! Можете да влезете.', 'success')
            return redirect(url_for('login'))
        else:
            flash(f'Грешка: {result["error"]}', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Вход на потребител"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Проверка на потребител
        user = get_user_by_email(email)
        
        if user and user['password'] == password:
            session['user_id'] = user['id']
            session['email'] = user['email']
            flash('Успешно влизане!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Грешен имейл или парола!', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Потребителски панел"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Статистика
    trades = get_user_trades(user_id, limit=10)
    trade_stats = get_user_trade_stats(user_id)
    api_keys = get_user_api_keys(user_id)
    referrals_count = get_user_referrals_count(user_id)
    total_referral_earnings = get_total_referral_earnings(user_id)
    
    # Реферален линк
    referral_link = f"https://gridpulse.app/register?ref={user['referral_code']}"
    
    return render_template('dashboard.html',
                         user=user,
                         trades=trades,
                         trade_stats=trade_stats,
                         api_keys=api_keys,
                         referrals_count=referrals_count,
                         total_referral_earnings=total_referral_earnings,
                         referral_link=referral_link)

@app.route('/logout')
def logout():
    """Изход от акаунта"""
    session.clear()
    flash('Успешно излизане!', 'success')
    return redirect(url_for('index'))

# ============================================================
# ПЛАЩАНИЯ
# ============================================================

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    """Страница за плащане"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    
    if request.method == 'POST':
        tx_hash = request.form.get('tx_hash')
        
        if not tx_hash:
            flash('Моля, въведете хеш на транзакцията!', 'error')
            return redirect(url_for('payment'))
        
        # Създаване на запис за плащане
        payment_result = create_payment(user_id, config.MONTHLY_FEE_USDT, tx_hash)
        
        if payment_result['success']:
            flash('Плащането е регистрирано! Изчакайте потвърждение...', 'success')
            return redirect(url_for('payment_status', tx_hash=tx_hash))
        else:
            flash('Грешка при регистриране на плащането!', 'error')
    
    # Генериране на адрес за плащане
    payment_address = generate_payment_address(user_id)
    
    return render_template('payment.html',
                         payment_address=payment_address,
                         fee=config.MONTHLY_FEE_USDT)

@app.route('/payment/status/<tx_hash>')
def payment_status(tx_hash):
    """Статус на плащане"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    payment = get_payment_by_tx_hash(tx_hash)
    
    if not payment:
        flash('Плащането не е намерено!', 'error')
        return redirect(url_for('dashboard'))
    
    # Проверка на статуса
    status_message = {
        'pending': '⏳ Изчаква потвърждение...',
        'confirmed': '✅ Плащането е потвърдено!',
        'failed': '❌ Плащането е неуспешно!'
    }.get(payment['status'], 'Неизвестен статус')
    
    return render_template('payment_status.html',
                         payment=payment,
                         status_message=status_message)

@app.route('/api/verify-payment', methods=['POST'])
def api_verify_payment():
    """API endpoint за проверка на плащане"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Не сте влезли в системата'}), 401
    
    data = request.get_json()
    tx_hash = data.get('tx_hash')
    
    if not tx_hash:
        return jsonify({'success': False, 'error': 'Липсва хеш на транзакцията'}), 400
    
    # Проверка на транзакцията
    result = verify_payment(tx_hash, config.MONTHLY_FEE_USDT)
    
    if result['success']:
        # Потвърждаване на плащането в базата данни
        confirm_result = confirm_payment(tx_hash)
        
        if confirm_result['success']:
            return jsonify({
                'success': True,
                'message': 'Плащането е потвърдено!',
                'amount': result['amount']
            })
        else:
            return jsonify({
                'success': False,
                'error': confirm_result.get('error', 'Грешка при потвърждаване')
            })
    else:
        return jsonify({
            'success': False,
            'error': result['error']
        })

# ============================================================
# РЕФЕРАЛИ
# ============================================================

@app.route('/referrals')
def referrals():
    """Страница с реферали"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = get_user_by_id(user_id)
    
    # Получаване на рефералите
    referrals_list = get_user_referrals(user_id)
    total_earnings = get_total_referral_earnings(user_id)
    referrals_count = get_user_referrals_count(user_id)
    
    # Реферален линк
    referral_link = f"https://gridpulse.app/register?ref={user['referral_code']}"
    
    return render_template('referrals.html',
                         referrals=referrals_list,
                         total_earnings=total_earnings,
                         referrals_count=referrals_count,
                         referral_link=referral_link)

# ============================================================
# АДМИН ПАНЕЛ
# ============================================================

@app.route('/admin')
def admin_panel():
    """Админ панел"""
    # За сега достъпен за всички (ще се добави защита по-късно)
    
    # Статистика
    stats = get_dashboard_stats()
    total_balance = get_wallet_balance()
    
    return render_template('admin.html',
                         stats=stats,
                         total_balance=total_balance)

# ============================================================
# API ENDPOINTS
# ============================================================

@app.route('/api/user/<int:user_id>')
def api_get_user(user_id):
    """API за получаване на информация за потребител"""
    user = get_user_by_id(user_id)
    
    if user:
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'referral_code': user['referral_code'],
                'subscription_active': user['subscription_active'],
                'subscription_expiry': user['subscription_expiry']
            }
        })
    else:
        return jsonify({'success': False, 'error': 'Потребител не е намерен'}), 404

@app.route('/api/trades/<int:user_id>')
def api_get_trades(user_id):
    """API за получаване на сделки на потребител"""
    trades = get_user_trades(user_id, limit=50)
    return jsonify({'success': True, 'trades': trades})

@app.route('/api/payments/<int:user_id>')
def api_get_payments(user_id):
    """API за получаване на плащания на потребител"""
    payments = get_user_payments(user_id)
    return jsonify({'success': True, 'payments': payments})

# ============================================================
# СТАРТИРАНЕ НА СЪРВЕРА
# ============================================================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 GridPulse платформа стартира...")
    print("📍 URL: http://localhost:5000")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
