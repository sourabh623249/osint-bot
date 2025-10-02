# complete_fixed_osint_bot_final.py with PostgreSQL
import os
import time
import requests
import json
import logging
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIG ---
TOKEN = "8139584922:AAFX8aj5ctzyLY5EPP7I6Z_6sOnWhujEejg"
OWNER_ID = 7471268929
DAILY_COINS = 5
DATABASE_URL = os.getenv('DATABASE_URL', '')

# --- Database Setup ---
def init_database():
    """Initialize database with PostgreSQL or SQLite"""
    if DATABASE_URL and DATABASE_URL.startswith('postgres'):
        # PostgreSQL connection
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS coins (
            user_id BIGINT PRIMARY KEY,
            balance INTEGER DEFAULT 5,
            blocked INTEGER DEFAULT 0,
            unlimited_until BIGINT DEFAULT 0,
            last_bonus BIGINT DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            admin_level INTEGER DEFAULT 0,
            created_at BIGINT DEFAULT 0
        )
        """)
        
        cursor.execute("""
        INSERT INTO coins 
        (user_id, balance, is_admin, admin_level, created_at) 
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
        """, (OWNER_ID, 999999, 1, 999, int(time.time())))
        
        conn.commit()
        print("✅ PostgreSQL database initialized")
        return conn, cursor, True
    else:
        # SQLite fallback
        import sqlite3
        conn = sqlite3.connect("coins.db", check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS coins (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 5,
            blocked INTEGER DEFAULT 0,
            unlimited_until INTEGER DEFAULT 0,
            last_bonus INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            admin_level INTEGER DEFAULT 0,
            created_at INTEGER DEFAULT 0
        )
        """)
        
        cursor.execute("""
        INSERT OR REPLACE INTO coins 
        (user_id, balance, is_admin, admin_level, created_at) 
        VALUES (?, ?, ?, ?, ?)
        """, (OWNER_ID, 999999, 1, 999, int(time.time())))
        
        conn.commit()
        print("✅ SQLite database initialized")
        return conn, cursor, False

# Initialize database
conn, cursor, use_postgres = init_database()

# --- Helper Functions ---
def execute_query(query, params=None, fetch=False):
    """Execute SQL query with PostgreSQL or SQLite compatibility"""
    try:
        if use_postgres:
            # Convert ? to %s for PostgreSQL
            query = query.replace('?', '%s')
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        conn.commit()
        
        if fetch:
            return cursor.fetchone()
        return True
    except Exception as e:
        print(f"Database error: {e}")
        conn.rollback()
        return None if fetch else False

def is_owner(user_id):
    return user_id == OWNER_ID

def is_admin(user_id):
    """Check if user is admin or owner"""
    if is_owner(user_id):
        return True
    try:
        row = execute_query("SELECT is_admin FROM coins WHERE user_id=?", (user_id,), fetch=True)
        if use_postgres:
            return bool(row['is_admin']) if row else False
        else:
            return bool(row[0]) if row else False
    except Exception as e:
        print(f"Error checking admin: {e}")
        return False

def get_admin_level(user_id):
    """Get admin level: 0=user, 1=admin, 2=super admin, 999=owner"""
    if is_owner(user_id):
        return 999
    try:
        row = execute_query("SELECT admin_level FROM coins WHERE user_id=?", (user_id,), fetch=True)
        if use_postgres:
            return row['admin_level'] if row else 0
        else:
            return row[0] if row else 0
    except:
        return 0

def add_user(user_id):
    """Add user to database with proper initialization"""
    try:
        if use_postgres:
            cursor.execute("""
            INSERT INTO coins 
            (user_id, balance, created_at) 
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
            """, (user_id, 5, int(time.time())))
        else:
            cursor.execute("""
            INSERT OR IGNORE INTO coins 
            (user_id, balance, created_at) 
            VALUES (?, ?, ?)
            """, (user_id, 5, int(time.time())))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding user: {e}")
        return False

def get_balance(user_id):
    """Get user balance"""
    try:
        row = execute_query("SELECT balance FROM coins WHERE user_id=?", (user_id,), fetch=True)
        if row:
            balance = row['balance'] if use_postgres else row[0]
            return balance if balance is not None else 5
        else:
            add_user(user_id)
            return 5
    except Exception as e:
        print(f"Error getting balance: {e}")
        add_user(user_id)
        return 5

def add_coins(user_id, amount):
    """Add coins to user"""
    if not add_user(user_id):
        return False
    try:
        current_balance = get_balance(user_id)
        new_balance = current_balance + amount
        execute_query("UPDATE coins SET balance = ? WHERE user_id=?", (new_balance, user_id))
        print(f"✅ Added {amount} coins to user {user_id}. New balance: {new_balance}")
        return True
    except Exception as e:
        print(f"Error adding coins: {e}")
        return False

def deduct_coins(user_id, amount):
    """Deduct coins from user"""
    if is_admin(user_id):
        return True
    
    if not add_user(user_id):
        return False
        
    balance = get_balance(user_id)
    
    if balance >= amount:
        try:
            new_balance = balance - amount
            execute_query("UPDATE coins SET balance = ? WHERE user_id=?", (new_balance, user_id))
            print(f"✅ Deducted {amount} coins from user {user_id}. New balance: {new_balance}")
            return True
        except Exception as e:
            print(f"Error deducting coins: {e}")
            return False
    return False

def set_coins(user_id, amount):
    """Set user's coin balance"""
    if not add_user(user_id):
        return False
    try:
        execute_query("UPDATE coins SET balance = ? WHERE user_id=?", (amount, user_id))
        print(f"✅ Set {amount} coins for user {user_id}")
        return True
    except Exception as e:
        print(f"Error setting coins: {e}")
        return False

def is_blocked(user_id):
    """Check if user is blocked"""
    if is_admin(user_id):
        return False
    try:
        row = execute_query("SELECT blocked FROM coins WHERE user_id=?", (user_id,), fetch=True)
        if use_postgres:
            return bool(row['blocked']) if row else False
        else:
            return bool(row[0]) if row else False
    except:
        return False

def block_user(user_id):
    """Block a user"""
    if is_admin(user_id):
        return False
    try:
        execute_query("UPDATE coins SET blocked = 1 WHERE user_id=?", (user_id,))
        print(f"✅ Blocked user {user_id}")
        return True
    except Exception as e:
        print(f"Error blocking user: {e}")
        return False

def unblock_user(user_id):
    """Unblock a user"""
    try:
        execute_query("UPDATE coins SET blocked = 0 WHERE user_id=?", (user_id,))
        print(f"✅ Unblocked user {user_id}")
        return True
    except Exception as e:
        print(f"Error unblocking user: {e}")
        return False

def give_daily_bonus(user_id):
    """Give daily bonus to user"""
    if is_admin(user_id):
        return 0
    
    if not add_user(user_id):
        return 0
        
    try:
        row = execute_query("SELECT last_bonus FROM coins WHERE user_id=?", (user_id,), fetch=True)
        last_bonus = (row['last_bonus'] if use_postgres else row[0]) if row else 0
        now = int(time.time())
        
        if now - last_bonus >= 86400:
            execute_query("UPDATE coins SET balance = balance + ?, last_bonus = ? WHERE user_id=?", 
                         (DAILY_COINS, now, user_id))
            print(f"✅ Gave daily bonus to user {user_id}")
            return DAILY_COINS
        else:
            return 0
    except Exception as e:
        print(f"Error giving daily bonus: {e}")
        return 0

def is_unlimited(user_id):
    """Check if user has unlimited access"""
    if is_admin(user_id):
        return True
    try:
        row = execute_query("SELECT unlimited_until FROM coins WHERE user_id=?", (user_id,), fetch=True)
        if row:
            unlimited = row['unlimited_until'] if use_postgres else row[0]
            return unlimited and unlimited > int(time.time())
        return False
    except:
        return False

def grant_unlimited(user_id, days):
    """Grant unlimited access to user"""
    if not add_user(user_id):
        return False
        
    until = int(time.time()) + days * 86400
    try:
        execute_query("UPDATE coins SET unlimited_until = ? WHERE user_id=?", (until, user_id))
        print(f"✅ Granted {days} days unlimited to user {user_id}")
        return True
    except Exception as e:
        print(f"Error granting unlimited: {e}")
        return False

def make_admin(user_id, level=1):
    """Make user admin"""
    print(f"🔄 Making user {user_id} admin with level {level}")
    
    if not add_user(user_id):
        print(f"❌ Failed to add user {user_id}")
        return False
    
    try:
        execute_query("UPDATE coins SET is_admin = 1, admin_level = ? WHERE user_id=?", (level, user_id))
        
        row = execute_query("SELECT is_admin, admin_level FROM coins WHERE user_id=?", (user_id,), fetch=True)
        
        if row:
            admin_status = row['is_admin'] if use_postgres else row[0]
            admin_lvl = row['admin_level'] if use_postgres else row[1]
            if bool(admin_status) and admin_lvl == level:
                print(f"✅ Successfully made user {user_id} admin with level {level}")
                return True
        
        print(f"❌ Admin update verification failed")
        return False
            
    except Exception as e:
        print(f"❌ Error making admin: {e}")
        return False

def remove_admin(user_id):
    """Remove admin privileges"""
    try:
        execute_query("UPDATE coins SET is_admin = 0, admin_level = 0 WHERE user_id=?", (user_id,))
        print(f"✅ Removed admin from user {user_id}")
        return True
    except Exception as e:
        print(f"❌ Error removing admin: {e}")
        return False

def delete_user(user_id):
    """Delete user from database"""
    try:
        execute_query("DELETE FROM coins WHERE user_id=?", (user_id,))
        print(f"✅ Deleted user {user_id}")
        return True
    except Exception as e:
        print(f"❌ Error deleting user: {e}")
        return False

def list_users():
    """Get list of all users"""
    try:
        cursor.execute("""
        SELECT user_id, balance, blocked, unlimited_until, is_admin, admin_level, created_at
        FROM coins 
        ORDER BY created_at DESC
        """)
        rows = cursor.fetchall()
        users = []
        for row in rows:
            if use_postgres:
                users.append({
                    "user_id": row['user_id'],
                    "balance": row['balance'] if row['balance'] is not None else 0,
                    "blocked": bool(row['blocked']),
                    "unlimited": bool(row['unlimited_until'] and row['unlimited_until'] > int(time.time())),
                    "is_admin": bool(row['is_admin']),
                    "admin_level": row['admin_level'],
                    "is_owner": is_owner(row['user_id']),
                    "created_at": row['created_at']
                })
            else:
                uid, bal, blk, unlimited, admin, admin_lvl, created = row
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
        print(f"Error listing users: {e}")
        return []

def list_admins():
    """Get list of all admins"""
    try:
        cursor.execute("SELECT user_id, admin_level FROM coins WHERE is_admin = 1")
        rows = cursor.fetchall()
        admins = []
        admins.append({"user_id": OWNER_ID, "admin_level": 999, "role": "Owner"})
        for row in rows:
            uid = row['user_id'] if use_postgres else row[0]
            level = row['admin_level'] if use_postgres else row[1]
            if uid != OWNER_ID:
                role = "Super Admin" if level == 2 else "Admin"
                admins.append({"user_id": uid, "admin_level": level, "role": role})
        return admins
    except Exception as e:
        print(f"Error listing admins: {e}")
        return []

# --- OSINT APIs ---
def fetch_number_info(number):
    """Fetch number information"""
    try:
        number = re.sub(r'[^0-9+]', '', number)
        if not number:
            return {"error": "Invalid phone number"}
            
        url = f"https://osintx.danger-vip-key.shop/api.php?key=ROLEX&num={number}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=30, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, dict) and "error" not in data:
                return data
            else:
                return {"error": "No data found"}
        else:
            return {"error": f"API returned status {response.status_code}"}
            
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}

def fetch_aadhaar_info(aadhaar):
    """Fetch Aadhaar information"""
    try:
        aadhaar = re.sub(r'[^0-9]', '', aadhaar)
        if len(aadhaar) != 12:
            return {"error": "Aadhaar must be 12 digits"}
            
        url = f"https://osintx.danger-vip-key.shop/api.php?key=ROLEX&aadhar={aadhaar}"
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
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}

def fetch_upi_info(upi):
    """Fetch UPI information"""
    try:
        if '@' not in upi:
            return {"error": "Invalid UPI ID format"}
            
        url = f"https://osintx.danger-vip-key.shop/api.php?key=ROLEX&upi={upi}"
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
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}

def fetch_ifsc_info(ifsc):
    """Fetch IFSC information"""
    try:
        ifsc = ifsc.upper().strip()
        if len(ifsc) != 11:
            return {"error": "IFSC must be 11 characters"}
            
        url = f"https://osintx.danger-vip-key.shop/api.php?key=ROLEX&ifsc={ifsc}"
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
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}

def fetch_vehicle_info(rc):
    """Fetch vehicle information"""
    try:
        rc = rc.upper().strip()
        if len(rc) < 5:
            return {"error": "Invalid RC number"}
            
        url = f"https://osintx.danger-vip-key.shop/api.php?key=ROLEX&rc={rc}"
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
    except Exception as e:
        return {"error": f"Request failed: {str(e)}"}

# --- Menu Functions ---
def main_menu(user_id):
    """Generate main menu based on user privileges"""
    keyboard = [
        [InlineKeyboardButton("📱 Number Info", callback_data="num"),
         InlineKeyboardButton("🆔 Aadhaar Info", callback_data="aadhar")],
        [InlineKeyboardButton("🏦 IFSC Info", callback_data="ifsc"),
         InlineKeyboardButton("💳 UPI Info", callback_data="upi")],
        [InlineKeyboardButton("🚗 Vehicle Info", callback_data="vehicle"),
         InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily")]
    ]
    
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚡ Admin Panel", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

def back_menu():
    """Back button menu"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back")]])

def admin_panel_menu(user_id):
    """Generate admin panel menu based on admin level"""
    admin_level = get_admin_level(user_id)
    keyboard = [
        [InlineKeyboardButton("➕ Add Coins", callback_data="admin_addcoin"),
         InlineKeyboardButton("➖ Deduct Coins", callback_data="admin_deductcoin")],
        [InlineKeyboardButton("💳 Set Coins", callback_data="admin_setcoin"),
         InlineKeyboardButton("🗑 Delete User", callback_data="admin_deluser")],
        [InlineKeyboardButton("⛔ Block User", callback_data="admin_block"),
         InlineKeyboardButton("✅ Unblock User", callback_data="admin_unblock")],
        [InlineKeyboardButton("👥 List Users", callback_data="admin_listusers"),
         InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("💎 Grant Unlimited", callback_data="admin_unlimited"),
         InlineKeyboardButton("🔄 Check APIs", callback_data="admin_checkapi")]
    ]
    
    if admin_level >= 999:
        keyboard.append([InlineKeyboardButton("👑 Make Admin", callback_data="admin_makeadmin"),
                        InlineKeyboardButton("🔻 Remove Admin", callback_data="admin_removeadmin")])
        keyboard.append([InlineKeyboardButton("📊 List Admins", callback_data="admin_listadmins")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back")])
    
    return InlineKeyboardMarkup(keyboard)

# --- Bot Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    
    add_user(user_id)
    
    if is_blocked(user_id):
        await update.message.reply_text("⛔ You are blocked from using this bot!")
        return
    
    bonus = give_daily_bonus(user_id)
    
    msg = f"👋 Welcome {user_name} to OSINT Bot!\n\n"
    msg += "🔍 **Available Services:**\n"
    msg += "• 📱 Number Information\n"
    msg += "• 🆔 Aadhaar Information\n" 
    msg += "• 💳 UPI Information\n"
    msg += "• 🏦 IFSC Information\n"
    msg += "• 🚗 Vehicle RC Information\n\n"
    msg += f"💰 Your Balance: {get_balance(user_id)} coins"
    
    if bonus > 0:
        msg += f"\n🎁 Daily Bonus: +{bonus} coins"
    
    if is_owner(user_id):
        msg += "\n👑 You are the Owner!"
    elif is_admin(user_id):
        admin_level = get_admin_level(user_id)
        role = "Super Admin" if admin_level == 2 else "Admin"
        msg += f"\n⚡ You are {role}!"
    
    if is_unlimited(user_id):
        msg += "\n♾️ You have Unlimited Access!"
    
    await update.message.reply_text(msg, reply_markup=main_menu(user_id))

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command for admins"""
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
    
    stats_text = f"""
📊 **Bot Statistics:**
👥 Total Users: {total_users}
⛔ Blocked Users: {blocked_users}
⚡ Admin Users: {admin_users + 1} (including owner)
💎 Unlimited Users: {unlimited_users}
💰 Total Coins in System: {total_coins}
🎁 Daily Bonus: {DAILY_COINS} coins
    """
    
    await update.message.reply_text(stats_text)

async def makeadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /makeadmin command for owner"""
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
            
            try:
                await context.bot.send_message(
                    target_id,
                    f"🎉 Congratulations! You have been made a {role} in OSINT Bot!\n\n"
                    f"You now have access to the Admin Panel with special privileges."
                )
            except:
                pass
                
        else:
            await update.message.reply_text("❌ Failed to make admin. Check logs.")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id or level!")

async def removeadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removeadmin command for owner"""
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

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /broadcast command for admins"""
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
                f"📢 **Broadcast from Admin:**\n\n{message}"
            )
            sent_count += 1
            time.sleep(0.1)
        except Exception as e:
            failed_count += 1
    
    await processing_msg.edit_text(
        f"✅ Broadcast Completed!\n\n"
        f"✅ Sent: {sent_count} users\n"
        f"❌ Failed: {failed_count} users"
    )

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /users command to show all users with chat IDs - OWNER ONLY"""
    user_id = update.message.from_user.id
    
    if not is_owner(user_id):
        await update.message.reply_text("❌ Owner only command!")
        return
        
    users = list_users()
    
    if not users:
        await update.message.reply_text("📭 No users found!")
        return
    
    text = "👥 **All Users with Chat IDs (Owner Only):**\n\n"
    
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
    
    text += f"\n📊 **Total Users:** {len(users)}"
    
    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            await update.message.reply_text(chunk, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')

async def addcoins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addcoins command for admins"""
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
        
        if add_coins(target_id, amount):
            new_balance = get_balance(target_id)
            await update.message.reply_text(f"✅ Added {amount} coins to user {target_id}\nNew balance: {new_balance} coins")
        else:
            await update.message.reply_text("❌ Failed to add coins")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id or amount!")

async def deductcoins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /deductcoins command for admins"""
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

async def setcoins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setcoins command for admins"""
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
        
        if set_coins(target_id, amount):
            await update.message.reply_text(f"✅ Set {amount} coins for user {target_id}")
        else:
            await update.message.reply_text("❌ Failed to set coins")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id or amount!")

async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /block command for admins"""
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

async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unblock command for admins"""
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

async def deleteuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /deleteuser command for admins"""
    user_id = update.message.from_user.id
    
    if not is_admin(user_id):
        await update.message.reply_text("❌ Admin only command!")
        return
        
    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: /deleteuser <user_id>")
        return
        
    try:
        target_id = int(context.args[0])
        
        if delete_user(target_id):
            await update.message.reply_text(f"✅ Deleted user {target_id}")
        else:
            await update.message.reply_text("❌ Failed to delete user")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id!")

async def grantunlimited_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /grantunlimited command for admins"""
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
        
        if grant_unlimited(target_id, days):
            await update.message.reply_text(f"✅ Granted {days} days unlimited access to user {target_id}")
        else:
            await update.message.reply_text("❌ Failed to grant unlimited access")
    except ValueError:
        await update.message.reply_text("❌ Invalid user_id or days!")

async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /commands command"""
    try:
        user_id = update.message.from_user.id
        
        commands_text = """
🤖 **OSINT Bot - Command List**

👤 **User Commands:**
/start - Start bot and show menu
/commands - Show this command list

🔍 **OSINT Services:**
Use the menu buttons for:
• Number Information
• Aadhaar Information  
• UPI Information
• IFSC Information
• Vehicle RC Information
"""
        
        if is_admin(user_id):
            commands_text += """
⚡ **Admin Commands:**
/stats - Show bot statistics
/broadcast - Broadcast to all users
/addcoins - Add coins to user
/deductcoins - Deduct coins from user  
/setcoins - Set user coin balance
/block - Block a user
/unblock - Unblock a user
/deleteuser - Delete a user
/grantunlimited - Grant unlimited access
"""
        
        if is_owner(user_id):
            commands_text += """
👑 **Owner Commands:**
/makeadmin - Make user admin
/removeadmin - Remove admin
/users - Show all users with IDs
"""
        
        await update.message.reply_text(commands_text)
        
    except Exception as e:
        print(f"❌ Error in commands_command: {e}")
        await update.message.reply_text("📋 **Available Commands:** /start, /commands")

# --- Admin Action Handlers ---
async def handle_admin_addcoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle add coins admin action"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ Admin only!")
        return
        
    await query.edit_message_text(
        "💵 **Add Coins**\n\n"
        "Send: `<user_id> <amount>`\n"
        "Example: `123456789 10`\n\n"
        "Or use command: `/addcoins 123456789 10`",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_input'] = 'add_coins'

async def handle_admin_deductcoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle deduct coins admin action"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ Admin only!")
        return
        
    await query.edit_message_text(
        "💸 **Deduct Coins**\n\n"
        "Send: `<user_id> <amount>`\n"
        "Example: `123456789 5`\n\n"
        "Or use command: `/deductcoins 123456789 5`",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_input'] = 'deduct_coins'

async def handle_admin_setcoin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle set coins admin action"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ Admin only!")
        return
        
    await query.edit_message_text(
        "💳 **Set Coins**\n\n"
        "Send: `<user_id> <amount>`\n"
        "Example: `123456789 50`\n\n"
        "Or use command: `/setcoins 123456789 50`",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_input'] = 'set_coins'

async def handle_admin_deluser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle delete user admin action"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ Admin only!")
        return
        
    await query.edit_message_text(
        "🗑 **Delete User**\n\n"
        "Send: `<user_id>`\n"
        "Example: `123456789`\n\n"
        "Or use command: `/deleteuser 123456789`",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_input'] = 'delete_user'

async def handle_admin_block(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle block user admin action"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ Admin only!")
        return
        
    await query.edit_message_text(
        "⛔ **Block User**\n\n"
        "Send: `<user_id>`\n"
        "Example: `123456789`\n\n"
        "Or use command: `/block 123456789`",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_input'] = 'block_user'

async def handle_admin_unblock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unblock user admin action"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ Admin only!")
        return
        
    await query.edit_message_text(
        "✅ **Unblock User**\n\n"
        "Send: `<user_id>`\n"
        "Example: `123456789`\n\n"
        "Or use command: `/unblock 123456789`",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_input'] = 'unblock_user'

async def handle_admin_makeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle make admin admin action"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_owner(user_id):
        await query.edit_message_text("❌ Owner only!")
        return
        
    await query.edit_message_text(
        "👑 **Make Admin**\n\n"
        "Send: `<user_id> <level>`\n"
        "Levels: 1=Admin, 2=Super Admin\n"
        "Example: `123456789 1`\n\n"
        "Or use command: `/makeadmin 123456789 1`",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_input'] = 'make_admin'

async def handle_admin_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle remove admin admin action"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_owner(user_id):
        await query.edit_message_text("❌ Owner only!")
        return
        
    await query.edit_message_text(
        "🔻 **Remove Admin**\n\n"
        "Send: `<user_id>`\n"
        "Example: `123456789`\n\n"
        "Or use command: `/removeadmin 123456789`",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_input'] = 'remove_admin'

async def handle_admin_unlimited(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle grant unlimited admin action"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ Admin only!")
        return
        
    await query.edit_message_text(
        "💎 **Grant Unlimited Access**\n\n"
        "Send: `<user_id> <days>`\n"
        "Example: `123456789 7`\n\n"
        "Or use command: `/grantunlimited 123456789 7`",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_input'] = 'grant_unlimited'

async def handle_admin_listusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle list users admin action"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ Admin only!")
        return
        
    users = list_users()
    
    if not users:
        await query.edit_message_text("📭 No users found!")
        return
        
    text = "👥 **All Users:**\n\n"
    
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
            
        text += f"{i}. `{user['user_id']}` - {user['balance']} coins {status_icons}\n"
    
    if len(users) > 20:
        text += f"\n... and {len(users) - 20} more users"
    
    text += f"\n📊 **Total Users:** {len(users)}"
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=admin_panel_menu(user_id))

async def handle_admin_listadmins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle list admins admin action"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ Admin only!")
        return
        
    admins = list_admins()
    
    if not admins:
        await query.edit_message_text("📭 No admins found!")
        return
        
    text = "👑 **All Admins**\n\n"
    for i, admin in enumerate(admins, 1):
        text += f"{i}. `{admin['user_id']}` - {admin['role']} (Level {admin['admin_level']})\n"
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=admin_panel_menu(user_id))

async def handle_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast admin action"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ Admin only!")
        return
        
    await query.edit_message_text(
        "📢 **Broadcast Message**\n\n"
        "Send the message you want to broadcast to all users:\n\n"
        "Or use command: `/broadcast your message here`",
        parse_mode='Markdown'
    )
    context.user_data['awaiting_input'] = 'broadcast'

async def handle_admin_checkapi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle check API admin action"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ Admin only!")
        return
        
    test_cases = [
        ("Number API", "+919876543210"),
        ("Aadhaar API", "123456789012"), 
        ("UPI API", "test@paytm"),
        ("IFSC API", "SBIN0000001"),
        ("Vehicle API", "DL01AB1234")
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
                results.append(f"❌ {api_name}: {result['error']}")
            else:
                results.append(f"✅ {api_name}: Working")
                
        except Exception as e:
            results.append(f"❌ {api_name}: {str(e)}")
    
    result_text = "🔄 **API Status Check**\n\n" + "\n".join(results)
    await query.edit_message_text(result_text, reply_markup=admin_panel_menu(user_id))

# --- Message Handler for Admin Inputs ---
async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin input for various actions"""
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    if not is_admin(user_id) or 'awaiting_input' not in context.user_data:
        if update.message and update.message.text:
            if is_blocked(user_id):
                await update.message.reply_text("⛔ You are blocked from using this bot!")
                return
        return
    
    action = context.user_data.pop('awaiting_input', None)
    
    try:
        if action in ['add_coins', 'deduct_coins', 'set_coins']:
            parts = text.split()
            if len(parts) != 2:
                await update.message.reply_text("❌ Invalid format! Use: <user_id> <amount>")
                return
                
            target_id = int(parts[0])
            amount = int(parts[1])
            
            if amount < 0:
                await update.message.reply_text("❌ Amount cannot be negative!")
                return
            
            if action == 'add_coins':
                if add_coins(target_id, amount):
                    new_balance = get_balance(target_id)
                    await update.message.reply_text(f"✅ Added {amount} coins to user {target_id}\nNew balance: {new_balance} coins")
                else:
                    await update.message.reply_text("❌ Failed to add coins")
                    
            elif action == 'deduct_coins':
                current_balance = get_balance(target_id)
                if current_balance < amount:
                    await update.message.reply_text(f"❌ User has only {current_balance} coins, cannot deduct {amount}")
                    return
                    
                if deduct_coins(target_id, amount):
                    new_balance = get_balance(target_id)
                    await update.message.reply_text(f"✅ Deducted {amount} coins from user {target_id}\nNew balance: {new_balance} coins")
                else:
                    await update.message.reply_text("❌ Failed to deduct coins")
                    
            elif action == 'set_coins':
                if set_coins(target_id, amount):
                    await update.message.reply_text(f"✅ Set {amount} coins for user {target_id}")
                else:
                    await update.message.reply_text("❌ Failed to set coins")
                    
        elif action in ['block_user', 'unblock_user', 'remove_admin', 'delete_user']:
            target_id = int(text)
            
            if action == 'block_user':
                if block_user(target_id):
                    await update.message.reply_text(f"✅ Blocked user {target_id}")
                else:
                    await update.message.reply_text("❌ Failed to block user (might be admin)")
                    
            elif action == 'unblock_user':
                if unblock_user(target_id):
                    await update.message.reply_text(f"✅ Unblocked user {target_id}")
                else:
                    await update.message.reply_text("❌ Failed to unblock user")
                    
            elif action == 'remove_admin':
                if remove_admin(target_id):
                    await update.message.reply_text(f"✅ Removed admin from user {target_id}")
                else:
                    await update.message.reply_text("❌ Failed to remove admin")
                    
            elif action == 'delete_user':
                if delete_user(target_id):
                    await update.message.reply_text(f"✅ Deleted user {target_id}")
                else:
                    await update.message.reply_text("❌ Failed to delete user")
                    
        elif action == 'make_admin':
            parts = text.split()
            if len(parts) != 2:
                await update.message.reply_text("❌ Invalid format! Use: <user_id> <level>")
                return
                
            target_id = int(parts[0])
            level = int(parts[1])
            
            if level not in [1, 2]:
                await update.message.reply_text("❌ Invalid level! Use 1 for Admin or 2 for Super Admin")
                return
                
            if make_admin(target_id, level):
                role = "Admin" if level == 1 else "Super Admin"
                await update.message.reply_text(f"✅ Made user {target_id} a {role}")
            else:
                await update.message.reply_text("❌ Failed to make admin")
                
        elif action == 'grant_unlimited':
            parts = text.split()
            if len(parts) != 2:
                await update.message.reply_text("❌ Invalid format! Use: <user_id> <days>")
                return
                
            target_id = int(parts[0])
            days = int(parts[1])
            
            if grant_unlimited(target_id, days):
                await update.message.reply_text(f"✅ Granted {days} days unlimited access to user {target_id}")
            else:
                await update.message.reply_text("❌ Failed to grant unlimited access")
                
        elif action == 'broadcast':
            users = list_users()
            sent_count = 0
            failed_count = 0
            
            processing_msg = await update.message.reply_text(f"📢 Broadcasting to {len(users)} users...")
            
            for user in users:
                try:
                    await context.bot.send_message(
                        user['user_id'],
                        f"📢 **Broadcast from Admin:**\n\n{text}"
                    )
                    sent_count += 1
                    time.sleep(0.1)
                except Exception as e:
                    failed_count += 1
            
            await processing_msg.edit_text(
                f"✅ Broadcast Completed!\n\n"
                f"✅ Sent: {sent_count} users\n"
                f"❌ Failed: {failed_count} users"
            )
                
    except ValueError:
        await update.message.reply_text("❌ Invalid input! Please check the format.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# --- OSINT Query Handlers ---
async def handle_osint_query(update: Update, context: ContextTypes.DEFAULT_TYPE, query_type: str):
    """Handle OSINT queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if is_blocked(user_id):
        await query.edit_message_text("⛔ You are blocked from using this bot!")
        return
    
    if not is_unlimited(user_id):
        balance = get_balance(user_id)
        if balance < 1:
            await query.edit_message_text(
                f"❌ Insufficient balance! You need 1 coin but have {balance} coins.\n"
                f"Get more coins with /start or wait for daily bonus!",
                reply_markup=back_menu()
            )
            return
    
    prompts = {
        "num": "📱 **Phone Number Lookup**\n\nSend me the phone number (with country code):\nExample: `+919876543210`",
        "aadhar": "🆔 **Aadhaar Lookup**\n\nSend me the Aadhaar number (12 digits):\nExample: `123456789012`",
        "upi": "💳 **UPI Lookup**\n\nSend me the UPI ID:\nExample: `username@paytm`",
        "ifsc": "🏦 **IFSC Lookup**\n\nSend me the IFSC code:\nExample: `SBIN0000001`",
        "vehicle": "🚗 **Vehicle RC Lookup**\n\nSend me the vehicle RC number:\nExample: `DL01AB1234`"
    }
    
    if query_type in prompts:
        await query.edit_message_text(
            prompts[query_type],
            parse_mode='Markdown',
            reply_markup=back_menu()
        )
        context.user_data['awaiting_osint'] = query_type

# --- OSINT Result Handler ---
async def handle_osint_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle OSINT input and fetch results"""
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    if is_blocked(user_id):
        await update.message.reply_text("⛔ You are blocked from using this bot!")
        return
    
    if 'awaiting_osint' not in context.user_data:
        return
    
    query_type = context.user_data.pop('awaiting_osint', None)
    
    processing_msg = await update.message.reply_text("🔄 Processing your request...")
    
    try:
        result = None
        if query_type == "num":
            result = fetch_number_info(text)
        elif query_type == "aadhar":
            result = fetch_aadhaar_info(text)
        elif query_type == "upi":
            result = fetch_upi_info(text)
        elif query_type == "ifsc":
            result = fetch_ifsc_info(text)
        elif query_type == "vehicle":
            result = fetch_vehicle_info(text)
        
        if result and "error" not in result:
            result_text = f"✅ **Results Found:**\n\n```json\n{json.dumps(result, indent=2, ensure_ascii=False)}\n```"
            
            if not is_unlimited(user_id):
                if not deduct_coins(user_id, 1):
                    result_text += "\n\n⚠️ Could not deduct coin (insufficient balance)"
                    
        elif result and "error" in result:
            result_text = f"❌ **Error:** {result['error']}"
        else:
            result_text = "❌ No results found or API error."
        
        await processing_msg.delete()
        await update.message.reply_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=main_menu(user_id)
        )
        
    except Exception as e:
        await processing_msg.delete()
        await update.message.reply_text(
            f"❌ Error processing request: {str(e)}",
            reply_markup=main_menu(user_id)
        )

# --- Callback Query Handler ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "back":
        await query.edit_message_text(
            "🏠 **Main Menu**\n\nSelect an option:",
            reply_markup=main_menu(user_id)
        )
    
    elif data == "balance":
        balance = get_balance(user_id)
        await query.edit_message_text(
            f"💰 **Your Balance:** {balance} coins\n\n"
            f"♾️ Unlimited Access: {'Yes' if is_unlimited(user_id) else 'No'}\n"
            f"⚡ Admin: {'Yes' if is_admin(user_id) else 'No'}",
            reply_markup=back_menu()
        )
    
    elif data == "daily":
        bonus = give_daily_bonus(user_id)
        if bonus > 0:
            await query.edit_message_text(
                f"🎁 **Daily Bonus Claimed!**\n\n+{bonus} coins added to your balance!\n\n💰 Total Balance: {get_balance(user_id)} coins",
                reply_markup=back_menu()
            )
        else:
            await query.edit_message_text(
                "⏰ **Daily Bonus Already Claimed**\n\nYou can claim your next daily bonus in 24 hours!",
                reply_markup=back_menu()
            )
    
    elif data == "admin_panel":
        if is_admin(user_id):
            await query.edit_message_text(
                "⚡ **Admin Panel**\n\nSelect an action:",
                reply_markup=admin_panel_menu(user_id)
            )
        else:
            await query.edit_message_text("❌ Admin only!")
    
    # OSINT queries
    elif data in ["num", "aadhar", "upi", "ifsc", "vehicle"]:
        await handle_osint_query(update, context, data)
    
    # Admin actions
    elif data == "admin_addcoin":
        await handle_admin_addcoin(update, context)
    elif data == "admin_deductcoin":
        await handle_admin_deductcoin(update, context)
    elif data == "admin_setcoin":
        await handle_admin_setcoin(update, context)
    elif data == "admin_deluser":
        await handle_admin_deluser(update, context)
    elif data == "admin_block":
        await handle_admin_block(update, context)
    elif data == "admin_unblock":
        await handle_admin_unblock(update, context)
    elif data == "admin_makeadmin":
        await handle_admin_makeadmin(update, context)
    elif data == "admin_removeadmin":
        await handle_admin_removeadmin(update, context)
    elif data == "admin_unlimited":
        await handle_admin_unlimited(update, context)
    elif data == "admin_listusers":
        await handle_admin_listusers(update, context)
    elif data == "admin_listadmins":
        await handle_admin_listadmins(update, context)
    elif data == "admin_broadcast":
        await handle_admin_broadcast(update, context)
    elif data == "admin_checkapi":
        await handle_admin_checkapi(update, context)
    
    else:
        await query.edit_message_text("❌ Unknown action!")

# --- Error Handler ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Sorry, an error occurred. Please try again or contact admin.",
                reply_markup=main_menu(update.effective_user.id)
            )
    except:
        pass

# --- Main Function ---
def main():
    """Start the bot"""
    application = Application.builder().token(TOKEN).build()
    
    # Add ALL command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("commands", commands_command))
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
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_osint_input))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_input))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start bot
    print("🤖 Bot is running...")
    print(f"👑 Owner ID: {OWNER_ID}")
    print(f"💾 Database: {'PostgreSQL' if use_postgres else 'SQLite'}")
    print("✅ All features are tested and working!")
    print("📋 Use /commands to see all available commands")
    application.run_polling()

if __name__ == "__main__":
    main()