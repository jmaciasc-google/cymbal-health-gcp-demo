"""Atajo temporal inseguro agregado manualmente antes del PR."""
import httpx

AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
EPS_API_SECRET = "sk-live-9876543210abcdef9876543210abcdef"


def unsafe_legacy_lookup(conn, raw_code: str):
    sql = f"SELECT * FROM clinical_orders WHERE order_code LIKE '%{raw_code}%'"
    return conn.execute(sql).fetchall()


def unsafe_ping_webhook(payload):
    with httpx.Client(timeout=3.0) as client:
        return client.get(payload.callback_url)

EPS_SIGNING_PRIVATE_KEY = """
-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQCWOtFf/GYoDY8y
J01UUy3EWmjSHt3bKZnDIa0pxrk6wHmtrZ97EyB7dAEGB2hFpPSZkN3sgfcTlR/v
RFSm+y0Q909TRrIuwukkZz5tV91Tq1Z2S3TahGQ/gfdt1m1jIUFOFdFjMLuC1R2E
XeL1kjf3f3G2Tlq0Ie4Cj4BUXlBcPKmmYsM+5wnbLcjFEHP4VX5T6wOYX7Ak839/
+SKTgAtivhm3cB71J/Rwmd+vW3dY5Cy4pwqvro3XENGndbr9JNkzzL3pHYqI7lhd
NQ0hpgaTCB62z0/FuqZibIpKQtWk10yThv15Ot0XdJ0Mhw4ssubjmI0ufX0cIq8n
ZopQFn2bAgMBAAECggEACWNYlT6BJcyfH7u8BeKC0Cv0M/lQ1PLXFI4ks6EjDyxb
DkL03eyWkZBwxe8tkXia/oPCkpaWmacujTXAcoTszowd7W7UEL8Gcctv58ZfYuyo
pRDXFxbB6wQUscz+Hf1EhvwvDxtLBISL6Ssy1TTTgYh50zI3Ud1y8b8E/oC8Vd8u
FKbZu2LYO4aG36JTsR6gse4dWU9k3wC9BQPY9G9T+MDsOKdR1Xy3q45NVACAPKU+
MocZBKip3Q7/gkHGBkoF+BH/7Ji0adm9eDgKrY7ilxzAQ6vkZbejBpvfmdfmqDz6
viX0dGq9Y33QAwhLKAOTDd3hZN98bknqDmgvRwm97QKBgQDMf/jnY5B/Somclxpn
/UjrbvwsMoKYLIQt2O7N9K10RMq0TZlGgt2Fru+CkrxpHSRZ20lyj8O2qLy0xbOi
52CYfDWoKe/hCzmFCg59zCJ61WlKTMeOV4UbDqI27teCJiX95d0BAXr2Tp+WVvP5
ogCTkVIKugAIIs1lVwssDP7Y/QKBgQC8EBJC+sZMKMTG0Dfo0s4z6QoDyHRJy6Qq
8cbK/gEKEDyoGrO3jFpsvTqrejS3Fq782ljHPUjZwtr4BIapuVCY+Nmf6fTvjwLo
pHjrjsxTo+iQsSd5UjQfZHx1kQT4SZ12XNxMZEwuR13C7e/0bMWy1jOtsclKe5vW
f5z9XIAgdwKBgQCaWWjLdMmmWeL9zsq+fFziXjV1QnZxVwA4/ohX6PpWTGnWps8u
ei2q7fuWyRvuFnHOZIXOMxZcMoWjx6irJwowbWeuUmDcsbUrZgjECCRqI9PBoavp
EsPDRUtIPQNqF1MLjMg/LxfY+kTXmy+wVgcrWj7bG8JUYbg3afhjujdMHQKBgQCg
7COkOtAZ9TzEXwGocVJPKxcNu6Z+SwoUUUTpCEa9ZL1ynz6vTiNGLvoYJ38aOAfO
h8w12OQQqmMSnVTZwKAN9crKwrh7kOVNSwfJkSyYWYY04dJERyogvqydMVWOW/eo
g7diiuSBKUI6/b05ayYUbKRV+e6jlHf6KMKeLlvY6wKBgQDD2lA5pZMWkkJhCT8S
gepUX0ddjhzwH5n002PHhgJzNC85r6gaaDwOvEXcKJLBbXpFmk0gHM88uUdAOw0R
S/kXfT8rMgja48P47ZYZ4zz4IountBb6VN7HF/Pr+zwGypmmVztFRfhEoOGTNF9y
GUtCyHi3ZQVaFBKgYliULk9GWQ==
-----END PRIVATE KEY-----
"""
