import streamlit as st
import plotly.graph_objects as go
from libs.stocks import (
    update_stock_prices, add_stock, buy_stock, sell_stock,
    get_user_portfolio, get_stock_history, get_all_stocks
)
from libs.currency import get_user_currency
from libs.db import get_conn

def render_stocks_page():
    st.title("📈 모의 주식 투자")
    
    # Debug information
    st.write("Debug - Session State:", st.session_state)
    
    if not st.session_state.get('is_logged_in'):
        st.warning("로그인이 필요합니다.")
        return
    
    user_id = st.session_state.get('user_id')
    if not user_id:
        st.warning("로그인이 필요합니다.")
        return
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Get user role
        cur.execute("SELECT role FROM users WHERE user_id = %s", (user_id,))
        result = cur.fetchone()
        if not result:
            st.error("사용자 정보를 찾을 수 없습니다.")
            return
        
        user_role = result[0]
        st.write("Debug - User Role:", user_role)
        
        # Display user's current balance
        balance = get_user_currency(user_id)
        st.metric("내 잔고", f"{balance:,}원")
        
        # Teacher-specific features in sidebar
        if user_role == 'teacher':
            with st.sidebar:
                st.subheader("👨‍🏫 선생님 기능")
                
                # Add new stock
                with st.expander("➕ 새로운 주식 추가"):
                    symbol = st.text_input("주식 심볼 (예: AAPL, GOOGL)")
                    name = st.text_input("회사 이름")
                    
                    if st.button("추가"):
                        try:
                            add_stock(symbol, name)
                            st.success(f"{name} ({symbol}) 주식이 추가되었습니다!")
                        except Exception as e:
                            st.error(str(e))
                
                # Update stock prices
                if st.button("주가 업데이트"):
                    update_stock_prices()
                    st.success("주가가 업데이트되었습니다!")
        
        # Stock trading interface
        st.subheader("💹 주식 거래")
        
        # Get all available stocks
        stocks = get_all_stocks()
        st.write("Debug - Available Stocks:", stocks)
        
        if not stocks:
            st.warning("거래 가능한 주식이 없습니다.")
            return
        
        # Stock selection
        stock_options = {f"{name} ({symbol})": stock_id for stock_id, symbol, name, _, _ in stocks}
        selected_stock = st.selectbox("주식 선택", options=list(stock_options.keys()))
        stock_id = stock_options[selected_stock]
        
        # Get selected stock details
        selected_stock_details = next((s for s in stocks if s[0] == stock_id), None)
        if selected_stock_details:
            _, symbol, name, current_price, last_updated = selected_stock_details
            st.write(f"현재가: {current_price:,}원")
            st.write(f"마지막 업데이트: {last_updated}")
            
            # Show stock chart
            st.subheader("📊 주가 차트")
            try:
                hist = get_stock_history(symbol)
                fig = go.Figure(data=[go.Candlestick(x=hist.index,
                                                    open=hist['Open'],
                                                    high=hist['High'],
                                                    low=hist['Low'],
                                                    close=hist['Close'])])
                st.plotly_chart(fig)
            except Exception as e:
                st.error(f"차트를 불러오는 중 오류가 발생했습니다: {str(e)}")
        
        # Trading interface
        st.subheader("🔄 거래")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("매수")
            buy_quantity = st.number_input("수량", min_value=1, step=1, key="buy_quantity")
            if st.button("매수"):
                try:
                    buy_stock(user_id, stock_id, buy_quantity)
                    st.success("매수 완료!")
                except Exception as e:
                    st.error(str(e))
        
        with col2:
            st.write("매도")
            sell_quantity = st.number_input("수량", min_value=1, step=1, key="sell_quantity")
            if st.button("매도"):
                try:
                    sell_stock(user_id, stock_id, sell_quantity)
                    st.success("매도 완료!")
                except Exception as e:
                    st.error(str(e))
        
        # Display portfolio
        st.subheader("📊 내 포트폴리오")
        portfolio = get_user_portfolio(user_id)
        st.write("Debug - Portfolio:", portfolio)
        
        if portfolio:
            total_value = sum(row[5] for row in portfolio)
            total_profit_loss = sum(row[6] for row in portfolio)
            
            st.metric("총 자산", f"{total_value:,.0f}원", f"{total_profit_loss:,.0f}원")
            
            for symbol, name, current_price, quantity, avg_price, value, profit_loss in portfolio:
                with st.expander(f"{name} ({symbol})"):
                    st.write(f"보유 수량: {quantity:,}주")
                    st.write(f"평균 매입가: {avg_price:,.0f}원")
                    st.write(f"현재 가격: {current_price:,.0f}원")
                    st.write(f"총 가치: {value:,.0f}원")
                    st.write(f"손익: {profit_loss:,.0f}원")
        else:
            st.info("보유 중인 주식이 없습니다.")
    
    except Exception as e:
        st.error(f"오류가 발생했습니다: {str(e)}")
        st.write("Debug - Error Details:", e) 