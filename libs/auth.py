import psycopg2

def login(conn, username, password):
    cur = conn.cursor()
    cur.execute(
        "SELECT username, role FROM users WHERE username=%s AND password=%s",
        (username, password)
    )
    return cur.fetchone()  # (username, role) or None

def signup(conn, username, password):
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users(username,password,role) VALUES(%s,%s,'일반학생')",
            (username, password)
        )
        conn.commit()
        return True
    except psycopg2.IntegrityError:
        return False
