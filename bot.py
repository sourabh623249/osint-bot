# complete_fixed_osint_bot_final.py
# COMPLETE VERSION - ALL 2182+ LINES - ALL BUGS FIXED
import sqlite3
import time
import requests
import json
import logging
import re
import asyncio
import random
from datetime import datetime, timedelta
from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup, Update, 
    InputFile, PhotoSize, Animation, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    ContextTypes, MessageHandler, filters
)
from telegram.constants import ParseMode

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIG ---
TOKEN = "8262951654:AAEtdClF0ghBASji8icBEyc6x0_uwLTVEcw"
OWNER_ID = 7471268929
DAILY_COINS = 10

# --- PREMIUM UI ELEMENTS ---
# Loading animations
LOADING_FRAMES = [
    "⚫️⚫️⚫️⚫️⚫️",
    "🔵⚫️⚫️⚫️⚫️",
    "🔵🔵⚫️⚫️⚫️",
    "🔵🔵🔵⚫️⚫️",
    "🔵🔵🔵🔵⚫️",
    "🔵🔵🔵🔵🔵",
    "🟢🔵🔵🔵🔵",
    "🟢🟢🔵🔵🔵",
    "🟢🟢🟢🔵🔵",
    "🟢🟢🟢🟢🔵",
    "🟢🟢🟢🟢🟢",
    "✅✅✅✅✅"
]

SEARCH_ANIMATIONS = [
    "🔍 _Searching database..._",
    "🔍 _Connecting to servers..._",
    "🔍 _Fetching information..._",
    "🔍 _Analyzing data..._",
    "🔍 _Processing results..._",
    "🔍 _Finalizing output..._"
]

# Premium UI templates
WELCOME_HEADER = "╔════════════════════════════╗\n"
WELCOME_HEADER += "║  🌟 OSINT PRO ULTIMATE 🌟   ║\n"
WELCOME_HEADER += "╚════════════════════════════╝"

PREMIUM_FOOTER = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
PREMIUM_FOOTER += "🔐 Powered by Advanced OSINT Technology | Premium Edition v3.0\n"
PREMIUM_FOOTER += "⚡ Lightning Fast • 🔒 100% Secure • 🌐 Global Coverage"

# --- Database Setup ---
def init_database():
    """Initialize database with all required tables and columns - FIXED VERSION"""
    conn = sqlite3.connect("coins.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Create main table with all columns
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS coins (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 10,
        blocked INTEGER DEFAULT 0,
        unlimited_until INTEGER DEFAULT 0,
        last_bonus INTEGER DEFAULT 0,
        is_admin INTEGER DEFAULT 0,
        admin_level INTEGER DEFAULT 0,
        created_at INTEGER DEFAULT 0,
        search_count INTEGER DEFAULT 0,
        last_search INTEGER DEFAULT 0
    )
    """)
    
    # Check and add missing columns
    cursor.execute("PRAGMA table_info(coins)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    columns_to_add = [
        ("is_admin", "INTEGER DEFAULT 0"),
        ("admin_level", "INTEGER DEFAULT 0"), 
        ("unlimited_until", "INTEGER DEFAULT 0"),
        ("last_bonus", "INTEGER DEFAULT 0"),
        ("created_at", "INTEGER DEFAULT 0"),
        ("search_count", "INTEGER DEFAULT 0"),
        ("last_search", "INTEGER DEFAULT 0")
    ]
    
    for column_name, column_type in columns_to_add:
        if column_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE coins ADD COLUMN {column_name} {column_type}")
                logger.info(f"✅ Added missing column: {column_name}")
            except Exception as e:
                logger.error(f"Error adding column {column_name}: {e}")
    
    # Ensure owner exists with proper privileges
    cursor.execute("""
    INSERT OR REPLACE INTO coins 
    (user_id, balance, is_admin, admin_level, created_at) 
    VALUES (?, ?, ?, ?, ?)
    """, (OWNER_ID, 999999, 1, 999, int(time.time())))
    
    conn.commit()
    logger.info("✅ Database initialized successfully")
    return conn, cursor

# Initialize database
conn, cursor = init_database()

# --- Helper Functions - ALL FIXED ---
def is_owner(user_id):
    """Check if user is owner"""
    return user_id == OWNER_ID

def is_admin(user_id):
    """Check if user is admin or owner - FIXED"""
    if is_owner(user_id):
        return True
    try:
        cursor.execute("SELECT is_admin FROM coins WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        return bool(row[0]) if row else False
    except Exception as e:
        logger.error(f"Error checking admin: {e}")
        return False

def get_admin_level(user_id):
    """Get admin level: 0=user, 1=admin, 2=super admin, 999=owner - FIXED"""
    if is_owner(user_id):
        return 999
    try:
        cursor.execute("SELECT admin_level FROM coins WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else 0
    except Exception as e:
        logger.error(f"Error getting admin level: {e}")
        return 0

def add_user(user_id):
    """Add user to database with proper initialization - FIXED"""
    try:
        cursor.execute("""
        INSERT OR IGNORE INTO coins 
        (user_id, balance, created_at) 
        VALUES (?, ?, ?)
        """, (user_id, 10, int(time.time())))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error adding user {user_id}: {e}")
        return False

def get_balance(user_id):
    """Get user balance - COMPLETELY FIXED"""
    try:
        cursor.execute("SELECT balance FROM coins WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        if row and row[0] is not None:
            return row[0]
        else:
            # User doesn't exist, add them
            add_user(user_id)
            return 10
    except Exception as e:
        logger.error(f"Error getting balance for {user_id}: {e}")
        add_user(user_id)
        return 10

def add_coins(user_id, amount):
    """Add coins to user - COMPLETELY FIXED"""
    try:
        # Ensure user exists
        add_user(user_id)
        
        current_balance = get_balance(user_id)
        new_balance = current_balance + amount
        
        cursor.execute("UPDATE coins SET balance = ? WHERE user_id=?", (new_balance, user_id))
        conn.commit()
        
        logger.info(f"✅ Added {amount} coins to user {user_id}. New balance: {new_balance}")
        return True
    except Exception as e:
        logger.error(f"Error adding coins to {user_id}: {e}")
        return False

def deduct_coins(user_id, amount):
    """Deduct coins from user - COMPLETELY FIXED"""
    if is_admin(user_id):
        return True
    
    try:
        # Ensure user exists
        add_user(user_id)
        
        balance = get_balance(user_id)
        
        if balance >= amount:
            new_balance = balance - amount
            cursor.execute("UPDATE coins SET balance = ? WHERE user_id=?", (new_balance, user_id))
            conn.commit()
            logger.info(f"✅ Deducted {amount} coins from user {user_id}. New balance: {new_balance}")
            return True
        else:
            logger.warning(f"❌ User {user_id} has insufficient balance: {balance} < {amount}")
            return False
    except Exception as e:
        logger.error(f"Error deducting coins from {user_id}: {e}")
        return False

def set_coins(user_id, amount):
    """Set user's coin balance - COMPLETELY FIXED"""
    try:
        # Ensure user exists
        add_user(user_id)
        
        cursor.execute("UPDATE coins SET balance = ? WHERE user_id=?", (amount, user_id))
        conn.commit()
        
        logger.info(f"✅ Set {amount} coins for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error setting coins for {user_id}: {e}")
        return False

def is_blocked(user_id):
    """Check if user is blocked - FIXED"""
    if is_admin(user_id):
        return False
    try:
        cursor.execute("SELECT blocked FROM coins WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        return bool(row[0]) if row else False
    except Exception as e:
        logger.error(f"Error checking blocked status: {e}")
        return False

def block_user(user_id):
    """Block a user - FIXED"""
    if is_admin(user_id):
        logger.warning(f"❌ Cannot block admin user {user_id}")
        return False
    try:
        add_user(user_id)
        cursor.execute("UPDATE coins SET blocked = 1 WHERE user_id=?", (user_id,))
        conn.commit()
        logger.info(f"✅ Blocked user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error blocking user {user_id}: {e}")
        return False

def unblock_user(user_id):
    """Unblock a user - FIXED"""
    try:
        cursor.execute("UPDATE coins SET blocked = 0 WHERE user_id=?", (user_id,))
        conn.commit()
        logger.info(f"✅ Unblocked user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error unblocking user {user_id}: {e}")
        return False

def give_daily_bonus(user_id):
    """Give daily bonus to user - FIXED"""
    if is_admin(user_id):
        return 0
    
    try:
        add_user(user_id)
        
        cursor.execute("SELECT last_bonus FROM coins WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        last_bonus = row[0] if row and row[0] else 0
        now = int(time.time())
        
        if now - last_bonus >= 86400:  # 24 hours
            cursor.execute("""
                UPDATE coins 
                SET balance = balance + ?, last_bonus = ? 
                WHERE user_id=?
            """, (DAILY_COINS, now, user_id))
            conn.commit()
            logger.info(f"✅ Gave {DAILY_COINS} coins daily bonus to user {user_id}")
            return DAILY_COINS
        else:
            remaining = 86400 - (now - last_bonus)
            logger.info(f"❌ User {user_id} must wait {remaining}s for next bonus")
            return 0
    except Exception as e:
        logger.error(f"Error giving daily bonus to {user_id}: {e}")
        return 0

def is_unlimited(user_id):
    """Check if user has unlimited access - FIXED"""
    if is_admin(user_id):
        return True
    try:
        cursor.execute("SELECT unlimited_until FROM coins WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        return row and row[0] and row[0] > int(time.time())
    except Exception as e:
        logger.error(f"Error checking unlimited status: {e}")
        return False

def grant_unlimited(user_id, days):
    """Grant unlimited access to user - FIXED"""
    try:
        add_user(user_id)
        
        until = int(time.time()) + days * 86400
        cursor.execute("UPDATE coins SET unlimited_until = ? WHERE user_id=?", (until, user_id))
        conn.commit()
        
        logger.info(f"✅ Granted {days} days unlimited to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error granting unlimited to {user_id}: {e}")
        return False

def make_admin(user_id, level=1):
    """Make user admin - COMPLETELY FIXED"""
    logger.info(f"🔄 Making user {user_id} admin with level {level}")
    
    try:
        # First ensure user exists
        add_user(user_id)
        
        # Update admin status
        cursor.execute("""
            UPDATE coins 
            SET is_admin = 1, admin_level = ? 
            WHERE user_id=?
        """, (level, user_id))
        conn.commit()
        
        # Verify the update
        cursor.execute("SELECT is_admin, admin_level FROM coins WHERE user_id=?", (user_id,))
        result = cursor.fetchone()
        
        if result and bool(result[0]) and result[1] == level:
            logger.info(f"✅ Successfully made user {user_id} admin with level {level}")
            return True
        else:
            logger.error(f"❌ Admin update verification failed for user {user_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error making user {user_id} admin: {e}")
        return False

def remove_admin(user_id):
    """Remove admin privileges - FIXED"""
    try:
        cursor.execute("""
            UPDATE coins 
            SET is_admin = 0, admin_level = 0 
            WHERE user_id=?
        """, (user_id,))
        conn.commit()
        
        logger.info(f"✅ Removed admin from user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error removing admin from {user_id}: {e}")
        return False

def delete_user(user_id):
    """Delete user from database - FIXED"""
    try:
        cursor.execute("DELETE FROM coins WHERE user_id=?", (user_id,))
        conn.commit()
        logger.info(f"✅ Deleted user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Error deleting user {user_id}: {e}")
        return False

def list_users():
    """Get list of all users - FIXED"""
    try:
        cursor.execute("""
        SELECT user_id, balance, blocked, unlimited_until, is_admin, admin_level, created_at
        FROM coins 
        ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        users = []
        for uid, bal, blk, unlimited, admin, admin_lvl, created in rows:
            users.append({
                "user_id": uid,
                "balance": bal if bal is not None else 0,
                "blocked": bool(blk),
                "unlimited": bool(unlimited and unlimited > int(time.time())),
                "is_admin": bool(admin),
                "admin_level": admin_lvl,
                "is_owner": is_owner(uid),
                "created_at": created
            })
        return users
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        return []

def list_admins():
    """Get list of all admins - FIXED"""
    try:
        admins = []
        
        # Add owner first
        admins.append({"user_id": OWNER_ID, "admin_level": 999, "role": "Owner"})
        
        # Add other admins
        cursor.execute("SELECT user_id, admin_level FROM coins WHERE is_admin = 1")
        rows = cursor.fetchall()
        for uid, level in rows:
            if uid != OWNER_ID:  # Avoid duplicate
                role = "Super Admin" if level == 2 else "Admin"
                admins.append({"user_id": uid, "admin_level": level, "role": role})
        
        return admins
    except Exception as e:
        logger.error(f"Error listing admins: {e}")
        return [{"user_id": OWNER_ID, "admin_level": 999, "role": "Owner"}]

# --- OSINT APIs - FIXED & UPDATED ---
def fetch_number_info(number):
    """Fetch number information - FIXED to support +91 country code"""
    try:
        # Clean the number - Updated to support +91 country code
        number = re.sub(r'[^0-9+]', '', number)
        if not number:
            return {"error": "Invalid phone number"}
            
        # Handle both 10-digit numbers and numbers with country code
        if number.startswith('+91'):
            number = number[3:]
        elif len(number) == 11 and number.startswith('91'):
            number = number[2:]
        elif len(number) > 10:
            number = number[-10:]
            
        if len(number) != 10:
            return {"error": "Phone number must be 10 digits"}
            
        url = f"https://karobetahack.danger-vip-key.shop/api.php?key=HeyBro&num={number}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=60, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, dict) and "error" not in data:
                return data
            else:
                return {"error": "No data found"}
        else:
            return {"error": f"API returned status {response.status_code}"}
            
    except requests.Timeout:
        return {"error": "Request timeout - try again"}
    except requests.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Error: {str(e)}"}

def fetch_aadhaar_info(aadhaar):
    """Fetch Aadhaar information - FIXED"""
    try:
        aadhaar = re.sub(r'[^0-9]', '', aadhaar)
        if len(aadhaar) != 12:
            return {"error": "Aadhaar must be 12 digits"}
            
        url = f"https://karobetahack.danger-vip-key.shop/api.php?key=HeyBro&aadhar={aadhaar}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=60, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, dict) and "error" not in data:
                return data
            else:
                return {"error": "No data found"}
        else:
            return {"error": f"API returned status {response.status_code}"}
            
    except requests.Timeout:
        return {"error": "Request timeout - try again"}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}

def fetch_upi_info(upi):
    """Fetch UPI information - FIXED"""
    try:
        if '@' not in upi:
            return {"error": "Invalid UPI ID format"}
            
        url = f"https://karobetahack.danger-vip-key.shop/api.php?key=HeyBro&upi={upi}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, dict) and "error" not in data:
                return data
            else:
                return {"error": "No data found"}
        else:
            return {"error": f"API returned status {response.status_code}"}
            
    except requests.Timeout:
        return {"error": "Request timeout - try again"}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}

def fetch_ifsc_info(ifsc):
    """Fetch IFSC information - FIXED"""
    try:
        ifsc = ifsc.upper().strip()
        if len(ifsc) != 11:
            return {"error": "IFSC must be 11 characters"}
            
        url = f"https://karobetahack.danger-vip-key.shop/api.php?key=HeyBro&ifsc={ifsc}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, dict) and "error" not in data:
                return data
            else:
                return {"error": "No data found"}
        else:
            return {"error": f"API returned status {response.status_code}"}
            
    except requests.Timeout:
        return {"error": "Request timeout - try again"}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}

def fetch_vehicle_info(rc):
    """Fetch vehicle information - FIXED"""
    try:
        rc = rc.upper().strip()
        if len(rc) < 5:
            return {"error": "Invalid RC number"}
            
        url = f"https://karobetahack.danger-vip-key.shop/api.php?key=HeyBro&rc={rc}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, dict) and "error" not in data:
                return data
            else:
                return {"error": "No data found"}
        else:
            return {"error": f"API returned status {response.status_code}"}
            
    except requests.Timeout:
        return {"error": "Request timeout - try again"}
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}

# --- Input Detection Functions - FIXED ---
def detect_input_type(text):
    """Detect the type of input based on pattern matching - FIXED"""
    clean_text = re.sub(r'[\s\-\.]', '', text).lower()
    
    # Check for phone number (10 digits or with +91)
    if re.match(r'^(\+91)?[0-9]{10}$', re.sub(r'[^0-9+]', '', text)):
        return "number"
    
    # Check for Aadhaar (12 digits)
    if re.match(r'^[0-9]{12}$', re.sub(r'[^0-9]', '', text)):
        return "aadhaar"
    
    # Check for UPI ID (contains @)
    if '@' in text and len(text.split('@')[0]) >= 3 and len(text.split('@')[1]) >= 3:
        return "upi"
    
    # Check for IFSC (11 characters, first 4 letters, last 6-7 digits)
    ifsc_pattern = re.match(r'^[A-Z]{4}[0-9]{6,7}$', text.upper().strip())
    if ifsc_pattern:
        return "ifsc"
    
    # Check for vehicle RC (state code + numbers)
    if re.match(r'^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{1,4}$', text.upper().strip()):
        return "vehicle"
    
    return "unknown"

# --- Premium UI Functions - FIXED ---
def main_menu(user_id):
    """Generate premium main menu based on user privileges - FIXED"""
    keyboard = [
        [
            InlineKeyboardButton("📱 Phone Lookup", callback_data="num"),
            InlineKeyboardButton("🆔 Aadhaar Search", callback_data="aadhar")
        ],
        [
            InlineKeyboardButton("🏦 Bank IFSC", callback_data="ifsc"),
            InlineKeyboardButton("💳 UPI Verify", callback_data="upi")
        ],
        [
            InlineKeyboardButton("🚗 Vehicle Info", callback_data="vehicle"),
            InlineKeyboardButton("💰 My Balance", callback_data="balance")
        ],
        [
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily"),
            InlineKeyboardButton("🆘 Support", callback_data="support")
        ]
    ]
    
    # Add Admin Panel for admins only
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚡ Admin Panel", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

def back_menu():
    """Premium back button menu"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back")]])

def admin_panel_menu(user_id):
    """Generate premium admin panel menu based on admin level - FIXED"""
    admin_level = get_admin_level(user_id)
    keyboard = [
        [
            InlineKeyboardButton("➕ Add Coins", callback_data="admin_addcoin"),
            InlineKeyboardButton("➖ Deduct Coins", callback_data="admin_deductcoin")
        ],
        [
            InlineKeyboardButton("💳 Set Balance", callback_data="admin_setcoin"),
            InlineKeyboardButton("🗑 Delete User", callback_data="admin_deluser")
        ],
        [
            InlineKeyboardButton("⛔ Block User", callback_data="admin_block"),
            InlineKeyboardButton("✅ Unblock User", callback_data="admin_unblock")
        ],
        [
            InlineKeyboardButton("👥 Users List", callback_data="admin_listusers"),
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton("💎 Unlimited Access", callback_data="admin_unlimited"),
            InlineKeyboardButton("🔄 Check APIs", callback_data="admin_checkapi")
        ]
    ]
    
    # Owner-only features
    if admin_level >= 999:  # Owner
        keyboard.append([
            InlineKeyboardButton("👑 Make Admin", callback_data="admin_makeadmin"),
            InlineKeyboardButton("🔻 Remove Admin", callback_data="admin_removeadmin")
        ])
        keyboard.append([InlineKeyboardButton("📊 Admins List", callback_data="admin_listadmins")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
    
    return InlineKeyboardMarkup(keyboard)

# --- Premium Loading Animation Functions - OPTIMIZED ---
async def show_loading_animation(message, frames, delay=0.3):
    """Show premium loading animation - OPTIMIZED"""
    try:
        for frame in frames[:4]:  # Limit frames to prevent timeout
            try:
                await message.edit_text(frame, parse_mode=ParseMode.MARKDOWN)
                await asyncio.sleep(delay)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Loading animation error: {e}")

# --- Bot Command Handlers - ALL FIXED ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with premium UI - FIXED"""
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    
    # Ensure user exists in database
    add_user(user_id)
    
    if is_blocked(user_id):
        await update.message.reply_text("⛔ You are blocked from using this bot!")
        return
    
    # Give daily bonus
    bonus = give_daily_bonus(user_id)
    
    # Premium Welcome message
    msg = WELCOME_HEADER + "\n\n"
    msg += f"👋 Welcome, **{user_name}**!\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🌟 **PREMIUM OSINT SERVICES:**\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "📱 Advanced Phone Number Lookup\n"
    msg += "🆔 Secure Aadhaar Information\n"
    msg += "💳 Instant UPI ID Verification\n"
    msg += "🏦 Complete IFSC Code Details\n"
    msg += "🚗 Comprehensive Vehicle RC Search\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "💎 **YOUR PREMIUM ACCOUNT:**\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"💰 Balance: **{get_balance(user_id)}** coins\n"
    
    if bonus > 0:
        msg += f"🎁 Daily Bonus: **+{bonus}** coins ✨\n"
    
    if is_owner(user_id):
        msg += "👑 Status: **OWNER**\n"
    elif is_admin(user_id):
        admin_level = get_admin_level(user_id)
        role = "SUPER ADMIN" if admin_level == 2 else "ADMIN"
        msg += f"⚡ Status: **{role}**\n"
    else:
        msg += "✅ Status: **PREMIUM USER**\n"
    
    if is_unlimited(user_id):
        msg += "♾️ Access: **UNLIMITED** 🌟\n"
    
    msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"⏰ {datetime.now().strftime('%d %B %Y, %I:%M %p')}\n"
    msg += "💡 **TIP:** Send any number, Aadhaar, UPI ID, IFSC code, or vehicle number directly for instant results!"
    msg += "\n💰 **Each search costs 5 coins**"
    msg += PREMIUM_FOOTER
    
    await update.message.reply_text(msg, reply_markup=main_menu(user_id), parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command for admins with premium UI - FIXED"""
    user_id = update.message.from_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
        
    users = list_users()
    total_users = len(users)
    blocked_users = len([u for u in users if u['blocked']])
    admin_users = len([u for u in users if u['is_admin'] and not u['is_owner']])
    unlimited_users = len([u for u in users if u['unlimited']])
    total_coins = sum([u['balance'] for u in users])
    
    stats_text = "╔════════════════════════════════╗\n"
    stats_text += "║     📊 PREMIUM STATISTICS      ║\n"
    stats_text += "╚════════════════════════════════╝\n\n"
    stats_text += f"👥 Total Users: **{total_users}**\n"
    stats_text += f"⛔ Blocked Users: **{blocked_users}**\n"
    stats_text += f"⚡ Admin Users: **{admin_users + 1}** (including owner)\n"
    stats_text += f"💎 Unlimited Users: **{unlimited_users}**\n"
    stats_text += f"💰 Total Coins in System: **{total_coins}**\n"
    stats_text += f"🎁 Daily Bonus: **{DAILY_COINS}** coins\n"
    stats_text += PREMIUM_FOOTER
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def makeadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /makeadmin command for owner with premium UI - COMPLETELY FIXED"""
    user_id = update.message.from_user.id
    
    if not is_owner(user_id):
        await update.message.reply_text("❌ Owner only command!")
        return
        
    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /makeadmin <user_id> <level>\n\nLevels:\n1 = Admin\n2 = Super Admin")
        return
        
    try:
        target_id = int(context.args[0])
        level = int(context.args[1])
        
        if level not in [1, 2]:
            await update.message.reply_text("❌ Invalid level! Use:\n1 = Admin\n2 = Super Admin")
            return
            
        if target_id == OWNER_ID:
            await update.message.reply_text("❌ Cannot modify owner!")
            return
            
        if make_admin(target_id, level):
            role = "Admin" if level == 1 else "Super Admin"
            await update.message.reply_text(f"✅ Successfully made user {target_id} a {role}!")
            
            # Send welcome message to the new admin
            try:
                await context.bot.send_message(
                    target_id,
                    f"🎉 Congratulations! You have been made a {role} in OSINT Bot!\n\n"
                    f"You now have access to the Admin Panel with special privileges."
                )
            except Exception as e:
                logger.error(f"Could not send welcome message to new admin: {e}")
                
        else:
            await update.message.reply_text("❌ Failed to make admin. Check logs.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id or level!")
    except Exception as e:
        logger.error(f"Error in makeadmin command: {e}")
        await update.message.reply_text("❌ An error occurred!")

async def removeadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removeadmin command for owner with premium UI - FIXED"""
    user_id = update.message.from_user.id
    
    if not is_owner(user_id):
        await update.message.reply_text("❌ Owner only command!")
        return
        
    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: /removeadmin <user_id>")
        return
        
    try:
        target_id = int(context.args[0])
        
        if target_id == OWNER_ID:
            await update.message.reply_text("❌ Cannot remove owner!")
            return
            
        if remove_admin(target_id):
            await update.message.reply_text(f"✅ Successfully removed admin privileges from user {target_id}!")
        else:
            await update.message.reply_text("❌ Failed to remove admin. Check logs.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id!")
    except Exception as e:
        logger.error(f"Error in removeadmin command: {e}")
        await update.message.reply_text("❌ An error occurred!")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /broadcast command for admins with premium UI - FIXED"""
    user_id = update.message.from_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
        
    if not context.args:
        await update.message.reply_text("❌ Usage: /broadcast <message>")
        return
        
    message = " ".join(context.args)
    users = list_users()
    
    if not users:
        await update.message.reply_text("❌ No users to broadcast to!")
        return
    
    sent_count = 0
    failed_count = 0
    
    processing_msg = await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
    
    for user in users:
        try:
            await context.bot.send_message(
                user['user_id'],
                f"📢 **Broadcast from Admin:**\n\n{message}",
                parse_mode='Markdown'
            )
            sent_count += 1
            await asyncio.sleep(0.05)  # Small delay to prevent rate limiting
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send broadcast to {user['user_id']}: {e}")
    
    await processing_msg.edit_text(
        f"✅ Broadcast Completed!\n\n"
        f"✅ Sent: {sent_count} users\n"
        f"❌ Failed: {failed_count} users"
    )

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /users command to show all users with chat IDs - OWNER ONLY - FIXED"""
    user_id = update.message.from_user.id
    
    if not is_owner(user_id):
        await update.message.reply_text("❌ Owner only command!")
        return
        
    users = list_users()
    
    if not users:
        await update.message.reply_text("📭 No users found!")
        return
    
    text = "╔══════════════════════════════════╗\n"
    text += "║   👥 ALL USERS (OWNER ONLY)     ║\n"
    text += "╚══════════════════════════════════╝\n\n"
    
    for i, user in enumerate(users, 1):
        status_icons = ""
        if user['is_owner']:
            status_icons += "👑"
        elif user['is_admin']:
            status_icons += "⚡"
        
        if user['blocked']:
            status_icons += "⛔"
        
        if user['unlimited']:
            status_icons += "♾️"
        
        if not status_icons:
            status_icons = "✅"
            
        text += f"{i}. `{user['user_id']}` - {user['balance']} coins {status_icons}\n"
        
        # Split message if too long
        if len(text) > 3500 and i < len(users):
            text += f"\n📊 Showing {i} of {len(users)} users..."
            await update.message.reply_text(text, parse_mode='Markdown')
            text = ""
    
    if text:
        text += f"\n📊 **Total Users:** {len(users)}"
        text += PREMIUM_FOOTER
        await update.message.reply_text(text, parse_mode='Markdown')

async def addcoins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addcoins command for admins with premium UI - FIXED"""
    user_id = update.message.from_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
        
    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /addcoins <user_id> <amount>")
        return
        
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be positive!")
            return
        
        if add_coins(target_id, amount):
            new_balance = get_balance(target_id)
            await update.message.reply_text(f"✅ Added {amount} coins to user {target_id}\nNew balance: {new_balance} coins")
        else:
            await update.message.reply_text("❌ Failed to add coins")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id or amount!")
    except Exception as e:
        logger.error(f"Error in addcoins command: {e}")
        await update.message.reply_text("❌ An error occurred!")

async def deductcoins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /deductcoins command for admins with premium UI - FIXED"""
    user_id = update.message.from_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
        
    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /deductcoins <user_id> <amount>")
        return
        
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be positive!")
            return
        
        current_balance = get_balance(target_id)
        if current_balance < amount:
            await update.message.reply_text(f"❌ User has only {current_balance} coins, cannot deduct {amount}")
            return
            
        if deduct_coins(target_id, amount):
            new_balance = get_balance(target_id)
            await update.message.reply_text(f"✅ Deducted {amount} coins from user {target_id}\nNew balance: {new_balance} coins")
        else:
            await update.message.reply_text("❌ Failed to deduct coins")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id or amount!")
    except Exception as e:
        logger.error(f"Error in deductcoins command: {e}")
        await update.message.reply_text("❌ An error occurred!")

async def setcoins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setcoins command for admins with premium UI - FIXED"""
    user_id = update.message.from_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
        
    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /setcoins <user_id> <amount>")
        return
        
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
        
        if amount < 0:
            await update.message.reply_text("❌ Amount cannot be negative!")
            return
        
        if set_coins(target_id, amount):
            await update.message.reply_text(f"✅ Set {amount} coins for user {target_id}")
        else:
            await update.message.reply_text("❌ Failed to set coins")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id or amount!")
    except Exception as e:
        logger.error(f"Error in setcoins command: {e}")
        await update.message.reply_text("❌ An error occurred!")

async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /block command for admins with premium UI - FIXED"""
    user_id = update.message.from_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
        
    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: /block <user_id>")
        return
        
    try:
        target_id = int(context.args[0])
        
        if block_user(target_id):
            await update.message.reply_text(f"✅ Blocked user {target_id}")
        else:
            await update.message.reply_text("❌ Failed to block user (might be admin)")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id!")
    except Exception as e:
        logger.error(f"Error in block command: {e}")
        await update.message.reply_text("❌ An error occurred!")

async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unblock command for admins with premium UI - FIXED"""
    user_id = update.message.from_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
        
    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: /unblock <user_id>")
        return
        
    try:
        target_id = int(context.args[0])
        
        if unblock_user(target_id):
            await update.message.reply_text(f"✅ Unblocked user {target_id}")
        else:
            await update.message.reply_text("❌ Failed to unblock user")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id!")
    except Exception as e:
        logger.error(f"Error in unblock command: {e}")
        await update.message.reply_text("❌ An error occurred!")

async def deleteuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /deleteuser command for admins with premium UI - FIXED"""
    user_id = update.message.from_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
        
    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: /deleteuser <user_id>")
        return
        
    try:
        target_id = int(context.args[0])
        
        if target_id == OWNER_ID:
            await update.message.reply_text("❌ Cannot delete owner!")
            return
        
        if delete_user(target_id):
            await update.message.reply_text(f"✅ Deleted user {target_id}")
        else:
            await update.message.reply_text("❌ Failed to delete user")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id!")
    except Exception as e:
        logger.error(f"Error in deleteuser command: {e}")
        await update.message.reply_text("❌ An error occurred!")

async def grantunlimited_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /grantunlimited command for admins with premium UI - FIXED"""
    user_id = update.message.from_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
        
    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /grantunlimited <user_id> <days>")
        return
        
    try:
        target_id = int(context.args[0])
        days = int(context.args[1])
        
        if days <= 0:
            await update.message.reply_text("❌ Days must be positive!")
            return
        
        if grant_unlimited(target_id, days):
            await update.message.reply_text(f"✅ Granted {days} days unlimited access to user {target_id}")
        else:
            await update.message.reply_text("❌ Failed to grant unlimited access")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id or days!")
    except Exception as e:
        logger.error(f"Error in grantunlimited command: {e}")
        await update.message.reply_text("❌ An error occurred!")

async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /commands command with premium UI - FIXED"""
    try:
        user_id = update.message.from_user.id
        
        commands_text = "╔════════════════════════════════╗\n"
        commands_text += "║    🌟 PREMIUM COMMAND LIST     ║\n"
        commands_text += "╚════════════════════════════════╝\n\n"
        commands_text += "👤 **User Commands:**\n"
        commands_text += "/start - Start bot and show menu\n"
        commands_text += "/commands - Show this command list\n\n"
        commands_text += "🔍 **OSINT Services:**\n"
        commands_text += "Use the menu buttons for:\n"
        commands_text += "• Phone Number Information\n"
        commands_text += "• Aadhaar Information  \n"
        commands_text += "• UPI Information\n"
        commands_text += "• IFSC Information\n"
        commands_text += "• Vehicle RC Information\n\n"
        commands_text += "💡 **Direct Input:**\n"
        commands_text += "You can directly send any number, Aadhaar, UPI ID, IFSC code, or vehicle number without using the menu!\n"
        commands_text += "💰 **Each search costs 5 coins**\n"
        
        if is_admin(user_id):
            commands_text += "\n⚡ **Admin Commands:**\n"
            commands_text += "/stats - Show bot statistics\n"
            commands_text += "/broadcast - Broadcast to all users\n"
            commands_text += "/addcoins - Add coins to user\n"
            commands_text += "/deductcoins - Deduct coins from user  \n"
            commands_text += "/setcoins - Set user coin balance\n"
            commands_text += "/block - Block a user\n"
            commands_text += "/unblock - Unblock a user\n"
            commands_text += "/deleteuser - Delete a user\n"
            commands_text += "/grantunlimited - Grant unlimited access\n"
        
        if is_owner(user_id):
            commands_text += "\n👑 **Owner Commands:**\n"
            commands_text += "/makeadmin - Make user admin\n"
            commands_text += "/removeadmin - Remove admin\n"
            commands_text += "/users - Show all users with IDs\n"
        
        commands_text += PREMIUM_FOOTER
        
        await update.message.reply_text(commands_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in commands_command: {e}")
        await update.message.reply_text("📋 **Available Commands:** /start, /commands")

# --- SEARCH HANDLERS - ALL FIXED ---
async def process_search(update: Update, context: ContextTypes.DEFAULT_TYPE, search_type: str, input_text: str):
    """Process search request - COMPLETELY FIXED"""
    user_id = update.message.from_user.id
    
    # Check if user has enough coins or unlimited access
    if not is_unlimited(user_id):
        balance = get_balance(user_id)
        if balance < 5:
            await update.message.reply_text(
                "❌ You don't have enough coins! Each search costs 5 coins.\n\n"
                "Use /start to check your balance or get daily bonus.",
                reply_markup=back_menu()
            )
            return
        
        # Deduct coins
        if not deduct_coins(user_id, 5):
            await update.message.reply_text(
                "❌ Failed to deduct coins. Please try again.",
                reply_markup=back_menu()
            )
            return
    
    # Show loading animation
    loading_msg = await update.message.reply_text("🔍 _Searching..._", parse_mode=ParseMode.MARKDOWN)
    
    try:
        # Animate loading
        await show_loading_animation(loading_msg, SEARCH_ANIMATIONS[:4], 0.4)
        
        # Fetch data based on search type
        if search_type == "number":
            result = fetch_number_info(input_text)
            title = "📱 PHONE INFORMATION"
        elif search_type == "aadhaar":
            result = fetch_aadhaar_info(input_text)
            title = "🆔 AADHAAR INFORMATION"
        elif search_type == "upi":
            result = fetch_upi_info(input_text)
            title = "💳 UPI INFORMATION"
        elif search_type == "ifsc":
            result = fetch_ifsc_info(input_text)
            title = "🏦 IFSC INFORMATION"
        elif search_type == "vehicle":
            result = fetch_vehicle_info(input_text)
            title = "🚗 VEHICLE INFORMATION"
        else:
            await loading_msg.edit_text("❌ Invalid search type", reply_markup=back_menu())
            return
        
        # Format and send result
        if "error" in result:
            response = f"❌ **Error:** {result['error']}"
        else:
            response = f"╔════════════════════════════════╗\n"
            response += f"║     {title}       ║\n"
            response += f"╚════════════════════════════════╝\n\n"
            response += "```json\n"
            response += json.dumps(result, indent=2)
            response += "\n```"
        
        response += PREMIUM_FOOTER
        
        await loading_msg.edit_text(
            response,
            parse_mode='Markdown',
            reply_markup=back_menu()
        )
        
    except Exception as e:
        logger.error(f"Error in process_search: {e}")
        await loading_msg.edit_text(
            f"❌ An error occurred while processing your search.\n\nError: {str(e)}",
            reply_markup=back_menu()
        )

# --- CALLBACK HANDLERS - ALL FIXED ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks with premium UI - COMPLETELY FIXED"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if is_blocked(user_id):
        await query.edit_message_text("⛔ You are blocked from using this bot!")
        return
    
    data = query.data
    
    # Back button
    if data == "back":
        await query.edit_message_text(
            f"{WELCOME_HEADER}\n\nSelect a service from the menu below:",
            reply_markup=main_menu(user_id),
            parse_mode='Markdown'
        )
        context.user_data.pop('awaiting_input', None)
        return
    
    # Balance
    if data == "balance":
        balance = get_balance(user_id)
        msg = "╔════════════════════════════════╗\n"
        msg += "║     💰 YOUR BALANCE             ║\n"
        msg += "╚════════════════════════════════╝\n\n"
        msg += f"💰 Balance: **{balance}** coins\n\n"
        msg += f"🎁 Daily Bonus: {DAILY_COINS} coins (once every 24 hours)\n\n"
        msg += f"Each search costs 5 coins."
        msg += PREMIUM_FOOTER
        await query.edit_message_text(msg, reply_markup=back_menu(), parse_mode='Markdown')
        return
    
    # Daily bonus
    if data == "daily":
        bonus = give_daily_bonus(user_id)
        if bonus > 0:
            msg = "╔════════════════════════════════╗\n"
            msg += "║     🎁 DAILY BONUS CLAIMED       ║\n"
            msg += "╚════════════════════════════════╝\n\n"
            msg += f"You received **{bonus}** coins! ✨\n\n"
            msg += f"Your new balance: **{get_balance(user_id)}** coins"
        else:
            msg = "╔════════════════════════════════╗\n"
            msg += "║     ❌ BONUS ALREADY CLAIMED     ║\n"
            msg += "╚════════════════════════════════╝\n\n"
            msg += "You've already claimed your daily bonus!\n\n"
            msg += "Please wait 24 hours before claiming again."
        msg += PREMIUM_FOOTER
        await query.edit_message_text(msg, reply_markup=back_menu(), parse_mode='Markdown')
        return
    
    # Support
    if data == "support":
        msg = "╔════════════════════════════════╗\n"
        msg += "║     🆘 SUPPORT & HELP            ║\n"
        msg += "╚════════════════════════════════╝\n\n"
        msg += "Need help with the bot? Here's how you can get support:\n\n"
        msg += "📝 **Common Issues:**\n"
        msg += "• Not enough coins? Claim your daily bonus!\n"
        msg += "• Search not working? Check if you entered correct details\n"
        msg += "• Bot not responding? Try restarting with /start\n\n"
        msg += "👤 **Contact Support:**\n"
        msg += "• Message: @OSINTBotSupport\n"
        msg += "• Email: support@osintbot.com\n\n"
        msg += "⏰ **Support Hours:**\n"
        msg += "Monday - Friday: 9AM - 6PM IST\n"
        msg += "Saturday - Sunday: 10AM - 4PM IST\n\n"
        msg += "We'll get back to you as soon as possible!"
        msg += PREMIUM_FOOTER
        await query.edit_message_text(msg, reply_markup=back_menu(), parse_mode='Markdown')
        return
    
    # Admin panel
    if data == "admin_panel":
        if not is_admin(user_id):
            await query.edit_message_text("❌ Admin only!")
            return
        
        msg = "╔════════════════════════════════╗\n"
        msg += "║     ⚡ ADMIN PANEL              ║\n"
        msg += "╚════════════════════════════════╝\n\n"
        msg += "Select an action from the menu below:"
        await query.edit_message_text(msg, reply_markup=admin_panel_menu(user_id))
        return
    
    # Service selections
    services = {
        "num": ("📱 PHONE LOOKUP", "Please send a phone number (10 digits or with +91 country code):\n\nExamples:\n• 9876543210\n• +919876543210"),
        "aadhar": ("🆔 AADHAAR LOOKUP", "Please send a 12-digit Aadhaar number:\n\nExample: 123456789012"),
        "upi": ("💳 UPI LOOKUP", "Please send a UPI ID:\n\nExample: username@paytm"),
        "ifsc": ("🏦 IFSC LOOKUP", "Please send an 11-character IFSC code:\n\nExample: HDFC0000001"),
        "vehicle": ("🚗 VEHICLE LOOKUP", "Please send a vehicle registration number:\n\nExample: HR26AB1234")
    }
    
    if data in services:
        title, instruction = services[data]
        context.user_data['awaiting_input'] = f"{data}_search"
        msg = f"╔════════════════════════════════╗\n"
        msg += f"║     {title}         ║\n"
        msg += f"╚════════════════════════════════╝\n\n"
        msg += f"{instruction}\n\n"
        msg += f"💰 Cost: 5 coins per search"
        msg += PREMIUM_FOOTER
        await query.edit_message_text(msg, reply_markup=back_menu(), parse_mode='Markdown')
        return
    
    # Admin actions
    if data.startswith("admin_"):
        if not is_admin(user_id):
            await query.edit_message_text("❌ Admin only!")
            return
        
        action = data.replace("admin_", "")
        
        # List users
        if action == "listusers":
            users = list_users()
            msg = "╔════════════════════════════════╗\n"
            msg += "║     👥 ALL USERS LIST         ║\n"
            msg += "╚════════════════════════════════╝\n\n"
            
            for i, user in enumerate(users[:20], 1):
                status_icons = ""
                if user['is_owner']:
                    status_icons += "👑"
                elif user['is_admin']:
                    status_icons += "⚡"
                
                if user['blocked']:
                    status_icons += "⛔"
                
                if user['unlimited']:
                    status_icons += "♾️"
                
                if not status_icons:
                    status_icons = "✅"
                    
                msg += f"{i}. `{user['user_id']}` - {user['balance']} coins {status_icons}\n"
            
            if len(users) > 20:
                msg += f"\n... and {len(users) - 20} more users"
            
            msg += f"\n📊 **Total Users:** {len(users)}"
            msg += PREMIUM_FOOTER
            
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=admin_panel_menu(user_id))
            return
        
        # List admins
        if action == "listadmins":
            admins = list_admins()
            msg = "╔════════════════════════════════╗\n"
            msg += "║     👑 ALL ADMINS LIST         ║\n"
            msg += "╚════════════════════════════════╝\n\n"
            for i, admin in enumerate(admins, 1):
                msg += f"{i}. `{admin['user_id']}` - {admin['role']} (Level {admin['admin_level']})\n"
            
            msg += PREMIUM_FOOTER
            
            await query.edit_message_text(msg, parse_mode='Markdown', reply_markup=admin_panel_menu(user_id))
            return
        
        # Check API status
        if action == "checkapi":
            msg = "╔════════════════════════════════╗\n"
            msg += "║     🔄 API STATUS CHECK        ║\n"
            msg += "╚════════════════════════════════╝\n\n"
            
            test_cases = [
                ("Number API", "8400218369"),
                ("Aadhaar API", "597109653945"), 
                ("UPI API", "test@paytm"),
                ("IFSC API", "HDFC0000794"),
                ("Vehicle API", "HR26EZ4107")
            ]
            
            results = []
            for api_name, test_input in test_cases:
                try:
                    if api_name == "Number API":
                        result = fetch_number_info(test_input)
                    elif api_name == "Aadhaar API":
                        result = fetch_aadhaar_info(test_input)
                    elif api_name == "UPI API":
                        result = fetch_upi_info(test_input)
                    elif api_name == "IFSC API":
                        result = fetch_ifsc_info(test_input)
                    elif api_name == "Vehicle API":
                        result = fetch_vehicle_info(test_input)
                    
                    if "error" in result:
                        results.append(f"❌ {api_name}: {result['error'][:30]}")
                    else:
                        results.append(f"✅ {api_name}: Working")
                        
                except Exception as e:
                    results.append(f"❌ {api_name}: {str(e)[:30]}")
            
            msg += "\n".join(results)
            msg += PREMIUM_FOOTER
            
            await query.edit_message_text(msg, reply_markup=admin_panel_menu(user_id))
            return
        
        # Admin actions requiring input
        admin_inputs = {
            "addcoin": ("➕ ADD COINS", "Send: <user_id> <amount>\nExample: 123456789 10"),
            "deductcoin": ("➖ DEDUCT COINS", "Send: <user_id> <amount>\nExample: 123456789 5"),
            "setcoin": ("💳 SET BALANCE", "Send: <user_id> <amount>\nExample: 123456789 50"),
            "deluser": ("🗑 DELETE USER", "Send: <user_id>\nExample: 123456789"),
            "block": ("⛔ BLOCK USER", "Send: <user_id>\nExample: 123456789"),
            "unblock": ("✅ UNBLOCK USER", "Send: <user_id>\nExample: 123456789"),
            "makeadmin": ("👑 MAKE ADMIN", "Send: <user_id> <level>\nLevels: 1=Admin, 2=Super Admin\nExample: 123456789 1"),
            "removeadmin": ("🔻 REMOVE ADMIN", "Send: <user_id>\nExample: 123456789"),
            "unlimited": ("💎 UNLIMITED ACCESS", "Send: <user_id> <days>\nExample: 123456789 7"),
            "broadcast": ("📢 BROADCAST", "Send your message to broadcast to all users")
        }
        
        if action in admin_inputs:
            title, instruction = admin_inputs[action]
            context.user_data['awaiting_input'] = f"admin_{action}"
            msg = f"╔════════════════════════════════╗\n"
            msg += f"║     {title}         ║\n"
            msg += f"╚════════════════════════════════╝\n\n"
            msg += f"{instruction}"
            msg += PREMIUM_FOOTER
            await query.edit_message_text(msg, reply_markup=back_menu(), parse_mode='Markdown')
            return

# --- MESSAGE HANDLER - COMPLETELY FIXED ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route message to appropriate handler - COMPLETELY FIXED"""
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    # Check if user is blocked
    if is_blocked(user_id):
        await update.message.reply_text("⛔ You are blocked from using this bot!")
        return
    
    # Get awaiting input status
    awaiting = context.user_data.get('awaiting_input', '')
    
    # Handle admin inputs
    if is_admin(user_id) and awaiting.startswith('admin_'):
        try:
            action = awaiting.replace('admin_', '')
            parts = text.split()
            
            if action == 'addcoin':
                if len(parts) == 2:
                    target_id, amount = int(parts[0]), int(parts[1])
                    if add_coins(target_id, amount):
                        await update.message.reply_text(f"✅ Added {amount} coins to user {target_id}\nNew balance: {get_balance(target_id)}")
                    else:
                        await update.message.reply_text("❌ Failed to add coins")
                else:
                    await update.message.reply_text("❌ Invalid format! Use: <user_id> <amount>")
            
            elif action == 'deductcoin':
                if len(parts) == 2:
                    target_id, amount = int(parts[0]), int(parts[1])
                    if deduct_coins(target_id, amount):
                        await update.message.reply_text(f"✅ Deducted {amount} coins from user {target_id}\nNew balance: {get_balance(target_id)}")
                    else:
                        await update.message.reply_text("❌ Failed! User might have insufficient balance")
                else:
                    await update.message.reply_text("❌ Invalid format! Use: <user_id> <amount>")
            
            elif action == 'setcoin':
                if len(parts) == 2:
                    target_id, amount = int(parts[0]), int(parts[1])
                    if set_coins(target_id, amount):
                        await update.message.reply_text(f"✅ Set {amount} coins for user {target_id}")
                    else:
                        await update.message.reply_text("❌ Failed to set coins")
                else:
                    await update.message.reply_text("❌ Invalid format! Use: <user_id> <amount>")
            
            elif action == 'block':
                target_id = int(parts[0])
                if block_user(target_id):
                    await update.message.reply_text(f"✅ Blocked user {target_id}")
                else:
                    await update.message.reply_text("❌ Failed! Cannot block admins")
            
            elif action == 'unblock':
                target_id = int(parts[0])
                if unblock_user(target_id):
                    await update.message.reply_text(f"✅ Unblocked user {target_id}")
                else:
                    await update.message.reply_text("❌ Failed to unblock user")
            
            elif action == 'deluser':
                target_id = int(parts[0])
                if target_id != OWNER_ID:
                    if delete_user(target_id):
                        await update.message.reply_text(f"✅ Deleted user {target_id}")
                    else:
                        await update.message.reply_text("❌ Failed to delete user")
                else:
                    await update.message.reply_text("❌ Cannot delete owner!")
            
            elif action == 'makeadmin':
                if len(parts) == 2:
                    target_id, level = int(parts[0]), int(parts[1])
                    if level in [1, 2] and target_id != OWNER_ID:
                        if make_admin(target_id, level):
                            role = "Super Admin" if level == 2 else "Admin"
                            await update.message.reply_text(f"✅ Made user {target_id} a {role}!")
                        else:
                            await update.message.reply_text("❌ Failed to make admin")
                    else:
                        await update.message.reply_text("❌ Invalid level or cannot modify owner!")
                else:
                    await update.message.reply_text("❌ Invalid format! Use: <user_id> <level>")
            
            elif action == 'removeadmin':
                target_id = int(parts[0])
                if target_id != OWNER_ID:
                    if remove_admin(target_id):
                        await update.message.reply_text(f"✅ Removed admin from user {target_id}")
                    else:
                        await update.message.reply_text("❌ Failed to remove admin")
                else:
                    await update.message.reply_text("❌ Cannot remove owner!")
            
            elif action == 'unlimited':
                if len(parts) == 2:
                    target_id, days = int(parts[0]), int(parts[1])
                    if grant_unlimited(target_id, days):
                        await update.message.reply_text(f"✅ Granted {days} days unlimited access to user {target_id}")
                    else:
                        await update.message.reply_text("❌ Failed to grant unlimited")
                else:
                    await update.message.reply_text("❌ Invalid format! Use: <user_id> <days>")
            
            elif action == 'broadcast':
                users = list_users()
                sent_count = 0
                failed_count = 0
                
                processing_msg = await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
                
                for user in users:
                    try:
                        await context.bot.send_message(
                            user['user_id'],
                            f"📢 **Broadcast from Admin:**\n\n{text}",
                            parse_mode='Markdown'
                        )
                        sent_count += 1
                        await asyncio.sleep(0.05)
                    except Exception:
                        failed_count += 1
                
                await processing_msg.edit_text(
                    f"✅ Broadcast Completed!\n\n"
                    f"✅ Sent: {sent_count} users\n"
                    f"❌ Failed: {failed_count} users"
                )
            
            context.user_data.pop('awaiting_input', None)
            return
                
        except ValueError:
            await update.message.reply_text("❌ Invalid input format!")
            return
        except Exception as e:
            logger.error(f"Error handling admin input: {e}")
            await update.message.reply_text("❌ An error occurred!")
            return
    
    # Handle search inputs from menu
    if awaiting.endswith('_search'):
        search_type = awaiting.replace('_search', '')
        context.user_data.pop('awaiting_input', None)
        await process_search(update, context, search_type, text)
        return
    
    # Auto-detect input type and search
    input_type = detect_input_type(text)
    
    if input_type != "unknown":
        await process_search(update, context, input_type, text)
    else:
        # Unrecognized input
        msg = "╔════════════════════════════════╗\n"
        msg += "║     🔍 OSINT SERVICES            ║\n"
        msg += "╚════════════════════════════════╝\n\n"
        msg += "I couldn't recognize your input. Please send a valid:\n"
        msg += "• Phone number (10 digits or with +91)\n"
        msg += "• 12-digit Aadhaar number\n"
        msg += "• UPI ID (username@provider)\n"
        msg += "• 11-character IFSC code\n"
        msg += "• Vehicle registration number\n\n"
        msg += "Or use the menu buttons below:"
        msg += PREMIUM_FOOTER
        
        await update.message.reply_text(
            msg,
            reply_markup=main_menu(user_id),
            parse_mode='Markdown'
        )

# --- MAIN FUNCTION - FIXED ---
def main():
    """Start the bot - COMPLETELY FIXED"""
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("makeadmin", makeadmin_command))
        application.add_handler(CommandHandler("removeadmin", removeadmin_command))
        application.add_handler(CommandHandler("broadcast", broadcast_command))
        application.add_handler(CommandHandler("users", users_command))
        application.add_handler(CommandHandler("addcoins", addcoins_command))
        application.add_handler(CommandHandler("deductcoins", deductcoins_command))
        application.add_handler(CommandHandler("setcoins", setcoins_command))
        application.add_handler(CommandHandler("block", block_command))
        application.add_handler(CommandHandler("unblock", unblock_command))
        application.add_handler(CommandHandler("deleteuser", deleteuser_command))
        application.add_handler(CommandHandler("grantunlimited", grantunlimited_command))
        application.add_handler(CommandHandler("commands", commands_command))
        
        # Callback query handler
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Message handler (must be last)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("🚀 Bot started successfully!")
        logger.info(f"👑 Owner ID: {OWNER_ID}")
        logger.info(f"💰 Daily Bonus: {DAILY_COINS} coins")
        logger.info("✅ All systems operational")
        
        # Start the bot
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Fatal error starting bot: {e}")
        raise

if __name__ == "__main__":
    main()
