import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta
from libs.db import get_conn
from libs.currency import get_user_currency

def update_stock_prices():
    """Update stock prices in the database"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get all stocks
    cur.execute("SELECT stock_id, symbol FROM stocks")
    stocks = cur.fetchall()
    
    for stock_id, symbol in stocks:
        try:
            stock = yf.Ticker(symbol)
            current_price = stock.info.get('currentPrice', 0)
            
            if current_price:
                cur.execute("""
                    UPDATE stocks 
                    SET current_price = %s, last_updated = now()
                    WHERE stock_id = %s
                """, (current_price, stock_id))
        
        except Exception as e:
            st.error(f"Error updating {symbol}: {str(e)}")
    
    conn.commit()

def add_stock(symbol, name):
    """Add a new stock to track"""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        stock = yf.Ticker(symbol)
        current_price = stock.info.get('currentPrice', 0)
        
        if not current_price:
            raise ValueError("Could not get current price for stock")
        
        cur.execute("""
            INSERT INTO stocks (symbol, name, current_price)
            VALUES (%s, %s, %s)
            RETURNING stock_id
        """, (symbol, name, current_price))
        
        stock_id = cur.fetchone()[0]
        conn.commit()
        return stock_id
    
    except Exception as e:
        conn.rollback()
        raise e

def buy_stock(user_id, stock_id, quantity):
    """Buy stocks for a user"""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Get current stock price
        cur.execute("SELECT current_price FROM stocks WHERE stock_id = %s", (stock_id,))
        current_price = cur.fetchone()[0]
        total_cost = current_price * quantity
        
        # Check if user has enough currency
        user_balance = get_user_currency(user_id)
        if user_balance < total_cost:
            raise ValueError("Insufficient balance")
        
        # Get or create portfolio entry
        cur.execute("""
            SELECT portfolio_id, quantity, average_price 
            FROM stock_portfolios 
            WHERE user_id = %s AND stock_id = %s
        """, (user_id, stock_id))
        portfolio = cur.fetchone()
        
        if portfolio:
            portfolio_id, current_quantity, current_avg_price = portfolio
            new_quantity = current_quantity + quantity
            new_avg_price = ((current_quantity * current_avg_price) + (quantity * current_price)) / new_quantity
            
            cur.execute("""
                UPDATE stock_portfolios 
                SET quantity = %s, average_price = %s, updated_at = now()
                WHERE portfolio_id = %s
            """, (new_quantity, new_avg_price, portfolio_id))
        else:
            cur.execute("""
                INSERT INTO stock_portfolios (user_id, stock_id, quantity, average_price)
                VALUES (%s, %s, %s, %s)
            """, (user_id, stock_id, quantity, current_price))
        
        # Record transaction
        cur.execute("""
            INSERT INTO stock_transactions (user_id, stock_id, type, quantity, price, total_amount)
            VALUES (%s, %s, 'buy', %s, %s, %s)
        """, (user_id, stock_id, quantity, current_price, total_cost))
        
        # Deduct from user's balance
        cur.execute("UPDATE users SET currency = currency - %s WHERE user_id = %s", (total_cost, user_id))
        
        conn.commit()
        return True
    
    except Exception as e:
        conn.rollback()
        raise e

def sell_stock(user_id, stock_id, quantity):
    """Sell stocks for a user"""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Get current stock price
        cur.execute("SELECT current_price FROM stocks WHERE stock_id = %s", (stock_id,))
        current_price = cur.fetchone()[0]
        total_value = current_price * quantity
        
        # Check if user has enough stocks
        cur.execute("""
            SELECT portfolio_id, quantity 
            FROM stock_portfolios 
            WHERE user_id = %s AND stock_id = %s
        """, (user_id, stock_id))
        portfolio = cur.fetchone()
        
        if not portfolio or portfolio[1] < quantity:
            raise ValueError("Insufficient stocks")
        
        portfolio_id, current_quantity = portfolio
        new_quantity = current_quantity - quantity
        
        if new_quantity == 0:
            cur.execute("DELETE FROM stock_portfolios WHERE portfolio_id = %s", (portfolio_id,))
        else:
            cur.execute("""
                UPDATE stock_portfolios 
                SET quantity = %s, updated_at = now()
                WHERE portfolio_id = %s
            """, (new_quantity, portfolio_id))
        
        # Record transaction
        cur.execute("""
            INSERT INTO stock_transactions (user_id, stock_id, type, quantity, price, total_amount)
            VALUES (%s, %s, 'sell', %s, %s, %s)
        """, (user_id, stock_id, quantity, current_price, total_value))
        
        # Add to user's balance
        cur.execute("UPDATE users SET currency = currency + %s WHERE user_id = %s", (total_value, user_id))
        
        conn.commit()
        return True
    
    except Exception as e:
        conn.rollback()
        raise e

def get_user_portfolio(user_id):
    """Get user's stock portfolio"""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT s.symbol, s.name, s.current_price, sp.quantity, sp.average_price,
               (s.current_price * sp.quantity) as current_value,
               ((s.current_price - sp.average_price) * sp.quantity) as profit_loss
        FROM stock_portfolios sp
        JOIN stocks s ON sp.stock_id = s.stock_id
        WHERE sp.user_id = %s
    """, (user_id,))
    
    return cur.fetchall()

def get_stock_history(symbol, days=30):
    """Get historical stock data"""
    stock = yf.Ticker(symbol)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    hist = stock.history(start=start_date, end=end_date)
    return hist

def get_all_stocks():
    """Get all tracked stocks"""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT stock_id, symbol, name, current_price, last_updated
        FROM stocks
        ORDER BY symbol
    """)
    
    return cur.fetchall() 