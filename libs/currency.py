import streamlit as st
from libs.db import get_conn
from datetime import datetime, timedelta

def get_user_currency(user_id):
    """Get user's current currency balance"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT currency FROM users WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    return result[0] if result else 0

def transfer_currency(from_user_id, to_user_id, amount, description=""):
    """Transfer currency between users (only teachers can do this)"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Check if sender is a teacher
    cur.execute("SELECT role FROM users WHERE user_id = %s", (from_user_id,))
    sender_role = cur.fetchone()[0]
    if sender_role != 'teacher':
        raise PermissionError("Only teachers can transfer currency")
    
    # Check if sender has enough currency
    sender_balance = get_user_currency(from_user_id)
    if sender_balance < amount:
        raise ValueError("Insufficient balance")
    
    # Perform transaction
    try:
        # Update balances
        cur.execute("UPDATE users SET currency = currency - %s WHERE user_id = %s", (amount, from_user_id))
        cur.execute("UPDATE users SET currency = currency + %s WHERE user_id = %s", (amount, to_user_id))
        
        # Record transaction
        cur.execute("""
            INSERT INTO transactions (from_user_id, to_user_id, amount, type, description, created_by)
            VALUES (%s, %s, %s, 'transfer', %s, %s)
        """, (from_user_id, to_user_id, amount, description, from_user_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e

def create_job(name, salary, description, created_by):
    """Create a new job with salary"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO jobs (name, salary, description, created_by)
        VALUES (%s, %s, %s, %s)
        RETURNING job_id
    """, (name, salary, description, created_by))
    job_id = cur.fetchone()[0]
    conn.commit()
    return job_id

def assign_job(user_id, job_id):
    """Assign a job to a user"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET job_id = %s WHERE user_id = %s", (job_id, user_id))
    conn.commit()

def process_monthly_salaries():
    """Process monthly salaries for all users with jobs"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get all users with jobs
    cur.execute("""
        SELECT u.user_id, j.salary
        FROM users u
        JOIN jobs j ON u.job_id = j.job_id
    """)
    users_with_jobs = cur.fetchall()
    
    for user_id, salary in users_with_jobs:
        # Add salary to user's balance
        cur.execute("UPDATE users SET currency = currency + %s WHERE user_id = %s", (salary, user_id))
        
        # Record transaction
        cur.execute("""
            INSERT INTO transactions (from_user_id, to_user_id, amount, type, description, created_by)
            VALUES (NULL, %s, %s, 'salary', 'Monthly salary', %s)
        """, (user_id, salary, user_id))
    
    conn.commit()

def create_quest(title, description, reward, created_by, is_daily=False):
    """Create a new quest"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO quests (title, description, reward, created_by, is_daily)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING quest_id
    """, (title, description, reward, created_by, is_daily))
    quest_id = cur.fetchone()[0]
    conn.commit()
    return quest_id

def complete_quest(user_id, quest_id, verified_by):
    """Mark a quest as completed and reward the user"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get quest details
    cur.execute("SELECT reward FROM quests WHERE quest_id = %s", (quest_id,))
    reward = cur.fetchone()[0]
    
    # Record completion
    cur.execute("""
        INSERT INTO quest_completions (quest_id, user_id, verified_by, verified_at)
        VALUES (%s, %s, %s, now())
    """, (quest_id, user_id, verified_by))
    
    # Add reward to user's balance
    cur.execute("UPDATE users SET currency = currency + %s WHERE user_id = %s", (reward, user_id))
    
    # Record transaction
    cur.execute("""
        INSERT INTO transactions (from_user_id, to_user_id, amount, type, description, created_by)
        VALUES (NULL, %s, %s, 'quest', 'Quest reward', %s)
    """, (user_id, reward, verified_by))
    
    conn.commit()

def get_rankings():
    """Get user rankings by currency"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT username, currency, role
        FROM users
        ORDER BY currency DESC
    """)
    return cur.fetchall() 