"""
Модул за работа с база данни
SQLite база данни за GridPulse платформата
"""

import sqlite3
from datetime import datetime, timedelta
import secrets
from urllib.parse import urlparse, parse_qs

# Път към базата данни
DB_PATH = 'gridpulse.db'

# ============================================================
# ИНИЦИАЛИЗИРАНЕ НА БАЗАТА ДАННИ
# ============================================================

def init_database():
    """Създава базата данни и таблиците ако не съществуват"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица за потребители
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            referral_code TEXT UNIQUE NOT NULL,
            referred_by TEXT,
            balance_demo REAL DEFAULT 10000.0,
            balance_real REAL DEFAULT 0.0,
            subscription_active BOOLEAN DEFAULT 0,
            subscription_expiry TEXT,
            is_admin BOOLEAN DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Таблица за плащания
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            tx_hash TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Таблица за сделки
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exchange TEXT NOT NULL,
            pair TEXT NOT NULL,
            side TEXT NOT NULL,
            amount REAL NOT NULL,
            price REAL NOT NULL,
            is_demo BOOLEAN DEFAULT 1,
            profit_loss REAL DEFAULT 0.0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Таблица за реферални начисления
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER NOT NULL,
            payment_id INTEGER,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY (referrer_id) REFERENCES users(id),
            FOREIGN KEY (referred_id) REFERENCES users(id),
            FOREIGN KEY (payment_id) REFERENCES payments(id)
        )
    ''')
    
    # Таблица за API ключове на потребители
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exchange TEXT NOT NULL,
            api_key TEXT NOT NULL,
            api_secret TEXT NOT NULL,
            api_passphrase TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Базата данни е инициализирана!")

# ============================================================
# ПОТРЕБИТЕЛИ
# ============================================================

def register_user(email, password, referral_input=None):
    """
    Регистрира нов потребител
    
    Args:
        email: Имейл на потребителя
        password: Парола
        referral_input: Реферален код или линк (по избор)
    
    Returns:
        dict с резултат
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Генериране на уникален реферален код
    ref_code = secrets.token_hex(8)
    
    # Обработка на реферален вход (код или линк)
    referred_by = None
    if referral_input:
        referred_by = extract_referral_code(referral_input)
    
    try:
        cursor.execute('''
            INSERT INTO users (email, password, referral_code, referred_by, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (email, password, ref_code, referred_by, datetime.now().isoformat()))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'user_id': user_id,
            'referral_code': ref_code,
            'referred_by': referred_by
        }
        
    except sqlite3.IntegrityError as e:
        conn.close()
        return {
            'success': False,
            'error': str(e)
        }

def extract_referral_code(input_str):
    """
    Извлича реферален код от вход (код или линк)
    
    Примери:
        "ABC123" -> "ABC123"
        "https://gridpulse.app/register?ref=ABC123" -> "ABC123"
    """
    # Ако е линк
    if input_str.startswith('http'):
        parsed = urlparse(input_str)
        query_params = parse_qs(parsed.query)
        if 'ref' in query_params:
            return query_params['ref'][0]
        return None
    # Ако е директен код
    return input_str

def get_user_by_email(email):
    """Връща потребител по имейл"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            'id': user[0],
            'email': user[1],
            'password': user[2],
            'referral_code': user[3],
            'referred_by': user[4],
            'balance_demo': user[5],
            'balance_real': user[6],
            'subscription_active': bool(user[7]),
            'subscription_expiry': user[8],
            'is_admin': bool(user[9]),
            'created_at': user[10]
        }
    return None

def get_user_by_id(user_id):
    """Връща потребител по ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            'id': user[0],
            'email': user[1],
            'password': user[2],
            'referral_code': user[3],
            'referred_by': user[4],
            'balance_demo': user[5],
            'balance_real': user[6],
            'subscription_active': bool(user[7]),
            'subscription_expiry': user[8],
            'is_admin': bool(user[9]),
            'created_at': user[10]
        }
    return None

def get_user_by_referral_code(referral_code):
    """Връща потребител по реферален код"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE referral_code = ?', (referral_code,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            'id': user[0],
            'email': user[1],
            'password': user[2],
            'referral_code': user[3],
            'referred_by': user[4],
            'balance_demo': user[5],
            'balance_real': user[6],
            'subscription_active': bool(user[7]),
            'subscription_expiry': user[8],
            'is_admin': bool(user[9]),
            'created_at': user[10]
        }
    return None

def activate_subscription(user_id, months=1):
    """Активира абонамент за потребител"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Проверка дали вече има активен абонамент
    user = get_user_by_id(user_id)
    if user and user['subscription_expiry']:
        expiry_date = datetime.fromisoformat(user['subscription_expiry'])
        if expiry_date > datetime.now():
            # Добавяме още месеци към текущия абонамент
            new_expiry = expiry_date + timedelta(days=30*months)
        else:
            # Ако абонаментът е изтекъл, започваме от сега
            new_expiry = datetime.now() + timedelta(days=30*months)
    else:
        # Нов абонамент
        new_expiry = datetime.now() + timedelta(days=30*months)
    
    cursor.execute('''
        UPDATE users
        SET subscription_active = 1, subscription_expiry = ?
        WHERE id = ?
    ''', (new_expiry.isoformat(), user_id))
    
    conn.commit()
    conn.close()
    
    return {
        'success': True,
        'expiry_date': new_expiry.isoformat()
    }

def deactivate_subscription(user_id):
    """Деактивира абонамент за потребител"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users
        SET subscription_active = 0
        WHERE id = ?
    ''', (user_id,))
    
    conn.commit()
    conn.close()
    
    return {'success': True}

def get_user_referrals_count(user_id):
    """Връща брой реферали на потребител"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE referred_by = (SELECT referral_code FROM users WHERE id = ?)', (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    
    return count

# ============================================================
# АДМИН ФУНКЦИИ
# ============================================================

def set_user_as_admin(user_id):
    """Направи потребител админ (безплатен достъп завинаги)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users
        SET is_admin = 1
        WHERE id = ?
    ''', (user_id,))
    
    conn.commit()
    conn.close()
    
    return {'success': True, 'message': f'Потребител {user_id} е сега админ!'}

# ============================================================
# ПЛАЩАНИЯ
# ============================================================

def create_payment(user_id, amount, tx_hash):
    """Създава нов запис за плащане"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO payments (user_id, amount, tx_hash, status, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, amount, tx_hash, 'pending', datetime.now().isoformat()))
    
    payment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        'success': True,
        'payment_id': payment_id
    }

def update_payment_status(tx_hash, status):
    """Обновява статуса на плащане"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE payments
        SET status = ?
        WHERE tx_hash = ?
    ''', (status, tx_hash))
    
    conn.commit()
    conn.close()
    
    return {'success': True}

def confirm_payment(tx_hash):
    """Потвърждава плащане и активира абонамент + реферални начисления"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Намираме плащането
    cursor.execute('SELECT * FROM payments WHERE tx_hash = ?', (tx_hash,))
    payment = cursor.fetchone()
    
    if not payment:
        conn.close()
        return {'success': False, 'error': 'Плащането не е намерено'}
    
    user_id = payment[1]
    amount = payment[2]
    
    # Потвърждаваме плащането
    cursor.execute('UPDATE payments SET status = ? WHERE tx_hash = ?', ('confirmed', tx_hash))
    
    # Активираме абонамент за 1 месец
    activate_subscription(user_id, months=1)
    
    # Проверяваме дали потребителят е реферал
    user = get_user_by_id(user_id)
    if user and user['referred_by']:
        # Намираме реферала
        referrer = get_user_by_referral_code(user['referred_by'])
        if referrer:
            # Изчисляваме рефералното начисление (10%)
            referral_amount = amount * 0.10
            
            # Създаваме запис за реферално начисление
            cursor.execute('''
                INSERT INTO referrals (referrer_id, referred_id, payment_id, amount, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (referrer['id'], user_id, payment[0], referral_amount, 'pending', datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    return {
        'success': True,
        'message': 'Плащането е потвърдено и абонаментът е активиран'
    }

def get_payment_by_tx_hash(tx_hash):
    """Връща плащане по транзакционен хаш"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM payments WHERE tx_hash = ?', (tx_hash,))
    payment = cursor.fetchone()
    conn.close()
    
    if payment:
        return {
            'id': payment[0],
            'user_id': payment[1],
            'amount': payment[2],
            'tx_hash': payment[3],
            'status': payment[4],
            'created_at': payment[5]
        }
    return None

def get_user_payments(user_id):
    """Връща всички плащания на потребител"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM payments
        WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user_id,))
    
    payments = cursor.fetchall()
    conn.close()
    
    return [
        {
            'id': p[0],
            'user_id': p[1],
            'amount': p[2],
            'tx_hash': p[3],
            'status': p[4],
            'created_at': p[5]
        }
        for p in payments
    ]

# ============================================================
# РЕФЕРАЛИ
# ============================================================

def create_referral(referrer_id, referred_id, payment_id, amount):
    """Създава запис за реферално начисление"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO referrals (referrer_id, referred_id, payment_id, amount, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (referrer_id, referred_id, payment_id, amount, 'pending', datetime.now().isoformat()))
    
    referral_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        'success': True,
        'referral_id': referral_id
    }

def get_user_referrals(user_id):
    """Връща всички реферали на потребител"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT r.*, u.email as referred_email
        FROM referrals r
        JOIN users u ON r.referred_id = u.id
        WHERE r.referrer_id = ?
        ORDER BY r.created_at DESC
    ''', (user_id,))
    
    referrals = cursor.fetchall()
    conn.close()
    
    return [
        {
            'id': r[0],
            'referrer_id': r[1],
            'referred_id': r[2],
            'payment_id': r[3],
            'amount': r[4],
            'status': r[5],
            'created_at': r[6],
            'referred_email': r[7]
        }
        for r in referrals
    ]

def get_total_referral_earnings(user_id):
    """Връща общите реферални печалби на потребител"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT SUM(amount) FROM referrals
        WHERE referrer_id = ? AND status = 'confirmed'
    ''', (user_id,))
    
    total = cursor.fetchone()[0]
    conn.close()
    
    return total if total else 0.0

# ============================================================
# СДЕЛКИ
# ============================================================

def create_trade(user_id, exchange, pair, side, amount, price, is_demo=True, profit_loss=0.0):
    """Записва нова сделка"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO trades (user_id, exchange, pair, side, amount, price, is_demo, profit_loss, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, exchange, pair, side, amount, price, is_demo, profit_loss, datetime.now().isoformat()))
    
    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {
        'success': True,
        'trade_id': trade_id
    }

def get_user_trades(user_id, limit=50):
    """Връща последните сделки на потребител"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM trades
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    
    trades = cursor.fetchall()
    conn.close()
    
    return [
        {
            'id': t[0],
            'user_id': t[1],
            'exchange': t[2],
            'pair': t[3],
            'side': t[4],
            'amount': t[5],
            'price': t[6],
            'is_demo': bool(t[7]),
            'profit_loss': t[8],
            'created_at': t[9]
        }
        for t in trades
    ]

def get_user_trade_stats(user_id):
    """Връща статистика за сделките на потребител"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Общ брой сделки
    cursor.execute('SELECT COUNT(*) FROM trades WHERE user_id = ?', (user_id,))
    total_trades = cursor.fetchone()[0]
    
    # Брой печеливши сделки
    cursor.execute('SELECT COUNT(*) FROM trades WHERE user_id = ? AND profit_loss > 0', (user_id,))
    winning_trades = cursor.fetchone()[0]
    
    # Обща печалба/загуба
    cursor.execute('SELECT SUM(profit_loss) FROM trades WHERE user_id = ?', (user_id,))
    total_pnl = cursor.fetchone()[0] or 0.0
    
    conn.close()
    
    return {
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': total_trades - winning_trades,
        'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
        'total_pnl': total_pnl
    }

# ============================================================
# API КЛЮЧОВЕ
# ============================================================

def save_api_keys(user_id, exchange, api_key, api_secret, api_passphrase=None):
    """Записва API ключове за потребител"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Проверка дали вече има ключове за тази борса
    cursor.execute('''
        SELECT id FROM api_keys
        WHERE user_id = ? AND exchange = ?
    ''', (user_id, exchange))
    
    existing = cursor.fetchone()
    
    if existing:
        # Обновяване на съществуващите ключове
        cursor.execute('''
            UPDATE api_keys
            SET api_key = ?, api_secret = ?, api_passphrase = ?, is_active = 1
            WHERE user_id = ? AND exchange = ?
        ''', (api_key, api_secret, api_passphrase, user_id, exchange))
    else:
        # Създаване на нов запис
        cursor.execute('''
            INSERT INTO api_keys (user_id, exchange, api_key, api_secret, api_passphrase, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, 1, ?)
        ''', (user_id, exchange, api_key, api_secret, api_passphrase, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    return {'success': True}

def get_user_api_keys(user_id):
    """Връща всички API ключове на потребител (без секретните стойности)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, exchange, is_active, created_at
        FROM api_keys
        WHERE user_id = ?
    ''', (user_id,))
    
    keys = cursor.fetchall()
    conn.close()
    
    return [
        {
            'id': k[0],
            'exchange': k[1],
            'is_active': bool(k[2]),
            'created_at': k[3]
        }
        for k in keys
    ]

def get_user_api_key(user_id, exchange):
    """Връща конкретен API ключ за борса"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT api_key, api_secret, api_passphrase
        FROM api_keys
        WHERE user_id = ? AND exchange = ? AND is_active = 1
    ''', (user_id, exchange))
    
    key = cursor.fetchone()
    conn.close()
    
    if key:
        return {
            'api_key': key[0],
            'api_secret': key[1],
            'api_passphrase': key[2]
        }
    return No
