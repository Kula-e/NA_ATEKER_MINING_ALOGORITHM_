import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.environ.get("CONTRACT_DATABASE", ROOT / "data" / "contracts.sqlite3"))
PORT = int(os.environ.get("PORT", "8000"))
PRICE_PENCE = 2600
PRICE_CURRENCY = "gbp"
STRIPE_API_BASE = "https://api.stripe.com/v1"
MAX_REQUEST_BYTES = 1_100_000
MAX_ENCRYPTED_PACKAGE_BYTES = 1_000_000
WEBHOOK_TOLERANCE_SECONDS = 300
CONTRACT_RETENTION_SECONDS = 30 * 24 * 60 * 60
PBKDF2_ITERATIONS = 600_000
ADMIN_SESSION_COOKIE = "turksoil_admin_session"
ADMIN_SESSION_TTL_SECONDS = 8 * 60 * 60
ADMIN_PASSWORD_MIN_LENGTH = 16
ADMIN_LOGIN_WINDOW_SECONDS = 15 * 60
ADMIN_LOGIN_MAX_ATTEMPTS = 5
ADMIN_SESSIONS = {}
ADMIN_LOGIN_FAILURES = {}
ADMIN_AUTH_LOCK = threading.Lock()
SERVICES = {
    "Space Mining",
    "Gemstone Mining",
    "Groundwater Mining",
    "Gold Mining & Exploration",
    "Geotechnical Engineering",
    "Geological Mapping",
    "Warehousing",
    "Server Hosting",
    "Water Transportation",
    "Space Exchange",
    "Business Data Analytics",
    "Website Creation",
    "Virtual Resource Monitoring & Sales",
    "Virtual Resource Security",
    "Virtual Minerals",
}


class PaymentError(Exception):
    pass


def configured_base_url():
    base_url = os.environ.get("SITE_BASE_URL", f"http://localhost:{PORT}").rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
        raise PaymentError("SITE_BASE_URL must be an absolute site origin without a path.")
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise PaymentError("SITE_BASE_URL must use HTTPS outside localhost.")
    return base_url


def validate_encrypted_package(package):
    if not isinstance(package, dict) or package.get("format") != "_NA_CRYPTO" or package.get("version") != 1:
        raise ValueError("Unsupported encrypted contract package.")
    kdf = package.get("kdf")
    cipher = package.get("cipher")
    ciphertext = package.get("ciphertext")
    if not isinstance(kdf, dict) or kdf.get("name") != "PBKDF2" or kdf.get("hash") != "SHA-256" or kdf.get("iterations") != PBKDF2_ITERATIONS:
        raise ValueError("Unsupported contract key-derivation parameters.")
    if not isinstance(cipher, dict) or cipher.get("name") != "AES-GCM" or cipher.get("bits") != 256:
        raise ValueError("Unsupported contract encryption parameters.")
    try:
        import base64

        salt = base64.b64decode(kdf["salt"], validate=True)
        iv = base64.b64decode(cipher["iv"], validate=True)
        encrypted = base64.b64decode(ciphertext, validate=True)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Encrypted contract fields are invalid.") from error
    if len(salt) != 16 or len(iv) != 12 or not 16 <= len(encrypted) <= MAX_ENCRYPTED_PACKAGE_BYTES:
        raise ValueError("Encrypted contract data has invalid lengths.")


@contextmanager
def database_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS contract_orders (
                order_id TEXT PRIMARY KEY,
                checkout_session_id TEXT UNIQUE,
                service TEXT NOT NULL,
                encrypted_package TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                paid_at INTEGER
            )
            """
        )
        connection.execute(
            "DELETE FROM contract_orders WHERE created_at < ?",
            (int(time.time()) - CONTRACT_RETENTION_SECONDS,),
        )
        yield connection
        connection.commit()
    except CookieError:
        connection.rollback()
        raise
    finally:
        connection.close()


def stripe_request(path, fields=None, method="GET", idempotency_key=None):
    secret_key = os.environ.get("STRIPE_SECRET_KEY")
    if not secret_key:
        raise PaymentError("Stripe checkout is not configured. Set STRIPE_SECRET_KEY on the server.")
    headers = {"Authorization": f"Bearer {secret_key}", "Accept": "application/json"}
    body = None
    if fields is not None:
        body = urlencode(fields).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    request = Request(f"{STRIPE_API_BASE}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read(1_100_001))
    except HTTPError as error:
        details = error.read(2048).decode("utf-8", "replace")
        raise PaymentError(f"Stripe request failed with HTTP {error.code}: {details}") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise PaymentError(f"Unable to communicate with Stripe: {error}") from error
    if not isinstance(result, dict):
        raise PaymentError("Stripe returned an invalid response.")
    return result


def create_checkout_session(order_id, service):
    base_url = configured_base_url()
    fields = {
        "mode": "payment",
        "success_url": f"{base_url}/?contract_payment=success&session_id={{CHECKOUT_SESSION_ID}}",
        "cancel_url": f"{base_url}/?contract_payment=cancelled",
        "client_reference_id": order_id,
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": PRICE_CURRENCY,
        "line_items[0][price_data][unit_amount]": str(PRICE_PENCE),
        "line_items[0][price_data][product_data][name]": "TURKSOIL LIMITED encrypted contract download",
        "line_items[0][price_data][product_data][description]": f"One _NA_CRYPTO encrypted service contract draft: {service}",
        "metadata[order_id]": order_id,
        "metadata[service]": service,
        "payment_intent_data[metadata][order_id]": order_id,
    }
    return stripe_request("/checkout/sessions", fields, method="POST", idempotency_key=order_id)


def verify_paid_session(session, order):
    return (
        isinstance(session, dict)
        and session.get("id") == order["checkout_session_id"]
        and session.get("client_reference_id") == order["order_id"]
        and (session.get("metadata") or {}).get("order_id") == order["order_id"]
        and session.get("mode") == "payment"
        and session.get("status") == "complete"
        and session.get("payment_status") == "paid"
        and session.get("currency") == PRICE_CURRENCY
        and session.get("amount_total") == PRICE_PENCE
    )


def verify_webhook_signature(payload, signature_header, secret, now=None):
    if not secret or not signature_header:
        return False
    values = {}
    for item in signature_header.split(","):
        key, separator, value = item.partition("=")
        if separator:
            values.setdefault(key, []).append(value)
    timestamps = values.get("t", [])
    if len(timestamps) != 1 or not timestamps[0].isdigit():
        return False
    timestamp = int(timestamps[0])
    current_time = int(time.time()) if now is None else now
    if abs(current_time - timestamp) > WEBHOOK_TOLERANCE_SECONDS:
        return False
    signed_payload = timestamps[0].encode("ascii") + b"." + payload
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, candidate) for candidate in values.get("v1", []))


class ContractPaymentHandler(BaseHTTPRequestHandler):
    server_version = "TurksoilContractServer"
    sys_version = ""

    def log_message(self, format_string, *args):
        print(f"{self.address_string()} - {format_string % args}")

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, status, value):
        payload = json.dumps(value, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def read_json_body(self):
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValueError("Content-Type must be application/json.")
        raw_length = self.headers.get("Content-Length", "")
        if not raw_length.isdigit():
            raise ValueError("A valid Content-Length header is required.")
        length = int(raw_length)
        if length < 1 or length > MAX_REQUEST_BYTES:
            raise ValueError("Request body must be between 1 byte and 1 MB.")
        try:
            value = json.loads(self.rfile.read(length))
        except json.JSONDecodeError as error:
            raise ValueError("Request body must contain valid JSON.") from error
        if not isinstance(value, dict):
            raise ValueError("Request body must be a JSON object.")
        return value

    def verify_same_origin(self):
        origin = self.headers.get("Origin")
        if not origin:
            return False
        try:
            expected = urlparse(configured_base_url())
            actual = urlparse(origin)
        except PaymentError:
            return False
        if actual.scheme != expected.scheme:
            return False
        if actual.netloc.lower() == expected.netloc.lower():
            return True
        loopback_hosts = {"localhost", "127.0.0.1", "::1"}
        return (
            expected.hostname in loopback_hosts
            and actual.hostname in loopback_hosts
            and expected.port == actual.port
        )

    def admin_session_token(self):
        cookies = SimpleCookie()
        try:
            cookies.load(self.headers.get("Cookie", ""))
        except Exception:
            return None
        cookie = cookies.get(ADMIN_SESSION_COOKIE)
        if cookie is None:
            return None
        token = cookie.value
        now = int(time.time())
        with ADMIN_AUTH_LOCK:
            expires_at = ADMIN_SESSIONS.get(token)
            if expires_at is None:
                return None
            if expires_at <= now:
                del ADMIN_SESSIONS[token]
                return None
        return token

    def send_admin_session_cookie(self, token, max_age):
        cookie = f"{ADMIN_SESSION_COOKIE}={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age={max_age}"
        try:
            if urlparse(configured_base_url()).scheme == "https":
                cookie += "; Secure"
        except PaymentError:
            pass
        self.send_header("Set-Cookie", cookie)

    def handle_admin_session(self):
        password = os.environ.get("TURKSOIL_ADMIN_PASSWORD", "")
        self.send_json(200, {
            "authenticated": self.admin_session_token() is not None,
            "available": len(password) >= ADMIN_PASSWORD_MIN_LENGTH,
        })

    def handle_admin_login(self):
        if not self.verify_same_origin():
            self.send_json(403, {"error": "Sign-in request origin is not allowed."})
            return
        password = os.environ.get("TURKSOIL_ADMIN_PASSWORD", "")
        if len(password) < ADMIN_PASSWORD_MIN_LENGTH:
            self.send_json(503, {"error": "Admin sign-in is unavailable. Configure TURKSOIL_ADMIN_PASSWORD with at least 16 characters on the server."})
            return
        remote_address = self.client_address[0]
        now = int(time.time())
        with ADMIN_AUTH_LOCK:
            failures = [stamp for stamp in ADMIN_LOGIN_FAILURES.get(remote_address, []) if now - stamp < ADMIN_LOGIN_WINDOW_SECONDS]
            ADMIN_LOGIN_FAILURES[remote_address] = failures
            if len(failures) >= ADMIN_LOGIN_MAX_ATTEMPTS:
                self.send_json(429, {"error": "Too many sign-in attempts. Try again later."})
                return
        try:
            request_body = self.read_json_body()
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
            return
        supplied_password = request_body.get("password")
        try:
            supplied_bytes = supplied_password.encode("utf-8") if isinstance(supplied_password, str) else b""
        except UnicodeEncodeError:
            supplied_bytes = b""
        if not hmac.compare_digest(supplied_bytes, password.encode("utf-8")):
            with ADMIN_AUTH_LOCK:
                ADMIN_LOGIN_FAILURES.setdefault(remote_address, []).append(now)
            self.send_json(401, {"error": "The password is incorrect."})
            return
        token = secrets.token_urlsafe(32)
        with ADMIN_AUTH_LOCK:
            ADMIN_LOGIN_FAILURES.pop(remote_address, None)
            for old_token, expires_at in list(ADMIN_SESSIONS.items()):
                if expires_at <= now:
                    del ADMIN_SESSIONS[old_token]
            ADMIN_SESSIONS[token] = now + ADMIN_SESSION_TTL_SECONDS
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b'{"authenticated":true}')))
        self.send_admin_session_cookie(token, ADMIN_SESSION_TTL_SECONDS)
        self.end_headers()
        self.wfile.write(b'{"authenticated":true}')

    def handle_admin_logout(self):
        if not self.verify_same_origin():
            self.send_json(403, {"error": "Sign-out request origin is not allowed."})
            return
        token = self.admin_session_token()
        if token is not None:
            with ADMIN_AUTH_LOCK:
                ADMIN_SESSIONS.pop(token, None)
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b'{"authenticated":false}')))
        self.send_admin_session_cookie("", 0)
        self.end_headers()
        self.wfile.write(b'{"authenticated":false}')

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/admin/session":
            self.handle_admin_session()
            return
        if parsed.path == "/api/payment-status":
            secret_key = os.environ.get("STRIPE_SECRET_KEY", "")
            try:
                configured_base_url()
                base_url_ready = True
            except PaymentError:
                base_url_ready = False
            ready = secret_key.startswith(("sk_test_", "sk_live_")) and base_url_ready
            message = "" if ready else "Secure checkout requires a Stripe secret key and a valid site URL configured on the server."
            self.send_json(200, {"ready": ready, "message": message})
            return
        if parsed.path == "/api/contracts/download":
            self.handle_contract_download(parse_qs(parsed.query).get("session_id", [""])[0])
            return
        if parsed.path.startswith("/api/"):
            self.send_json(404, {"error": "API route not found."})
            return
        self.serve_static(parsed.path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/admin/login":
            self.handle_admin_login()
            return
        if parsed.path == "/api/admin/logout":
            self.handle_admin_logout()
            return
        if parsed.path == "/api/stripe/webhook":
            self.handle_stripe_webhook()
            return
        if parsed.path != "/api/checkout-session":
            self.send_json(404, {"error": "API route not found."})
            return
        if not self.verify_same_origin():
            self.send_json(403, {"error": "Checkout request origin is not allowed."})
            return
        try:
            request_body = self.read_json_body()
            service = request_body.get("service")
            package = request_body.get("encryptedContract")
            if not isinstance(service, str) or service not in SERVICES:
                raise ValueError("Choose a supported service.")
            validate_encrypted_package(package)
            encrypted_package = json.dumps(package, separators=(",", ":"))
            if len(encrypted_package.encode("utf-8")) > MAX_ENCRYPTED_PACKAGE_BYTES:
                raise ValueError("Encrypted contract package exceeds the maximum size.")
            if not os.environ.get("STRIPE_SECRET_KEY"):
                raise PaymentError("Stripe checkout is not configured. Set STRIPE_SECRET_KEY on the server.")
            configured_base_url()
            order_id = str(uuid.uuid4())
            with database_connection() as connection:
                connection.execute(
                    "INSERT INTO contract_orders (order_id, service, encrypted_package, status, created_at) VALUES (?, ?, ?, ?, ?)",
                    (order_id, service, encrypted_package, "creating", int(time.time())),
                )
            try:
                checkout = create_checkout_session(order_id, service)
                checkout_url_value = checkout.get("url")
                checkout_url = urlparse(checkout_url_value) if isinstance(checkout_url_value, str) else None
                if (
                    not isinstance(checkout.get("id"), str)
                    or not checkout["id"].startswith("cs_")
                    or checkout_url is None
                    or checkout_url.scheme != "https"
                    or checkout_url.hostname != "checkout.stripe.com"
                ):
                    raise PaymentError("Stripe did not return a valid Checkout session.")
            except PaymentError:
                with database_connection() as connection:
                    connection.execute("DELETE FROM contract_orders WHERE order_id = ?", (order_id,))
                raise
            with database_connection() as connection:
                connection.execute(
                    "UPDATE contract_orders SET checkout_session_id = ?, status = ? WHERE order_id = ?",
                    (checkout["id"], "pending", order_id),
                )
            self.send_json(201, {"checkoutUrl": checkout["url"]})
        except ValueError as error:
            self.send_json(400, {"error": str(error)})
        except PaymentError as error:
            print(f"Checkout setup failed: {error}")
            self.send_json(503, {"error": str(error)})
        except sqlite3.Error as error:
            print(f"Contract order storage failed: {error}")
            self.send_json(500, {"error": "Unable to store this contract order securely."})

    def handle_contract_download(self, session_id):
        if not re.fullmatch(r"cs_(?:test_|live_)?[A-Za-z0-9]+", session_id or ""):
            self.send_json(400, {"error": "A valid Checkout session ID is required."})
            return
        try:
            with database_connection() as connection:
                order = connection.execute(
                    "SELECT order_id, checkout_session_id, service, encrypted_package FROM contract_orders WHERE checkout_session_id = ?",
                    (session_id,),
                ).fetchone()
            if order is None:
                self.send_json(404, {"error": "No contract is associated with this checkout session."})
                return
            checkout = stripe_request(f"/checkout/sessions/{session_id}")
            if not verify_paid_session(checkout, order):
                self.send_json(402, {"error": "Payment has not been confirmed. The encrypted contract is not available."})
                return
            with database_connection() as connection:
                connection.execute(
                    "UPDATE contract_orders SET status = ?, paid_at = COALESCE(paid_at, ?) WHERE order_id = ?",
                    ("paid", int(time.time()), order["order_id"]),
                )
            service_slug = re.sub(r"[^a-z0-9]+", "-", order["service"].lower()).strip("-")
            payload = order["encrypted_package"].encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="turksoil-{service_slug}-draft-na-crypto.json"')
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except PaymentError as error:
            print(f"Contract settlement verification failed: {error}")
            self.send_json(503, {"error": "Payment verification is temporarily unavailable. The encrypted contract has not been released."})
        except sqlite3.Error as error:
            print(f"Contract order lookup failed: {error}")
            self.send_json(500, {"error": "Unable to verify this contract order."})

    def handle_stripe_webhook(self):
        secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
        raw_length = self.headers.get("Content-Length", "")
        if not raw_length.isdigit() or int(raw_length) > MAX_REQUEST_BYTES:
            self.send_json(400, {"error": "Invalid webhook body length."})
            return
        payload = self.rfile.read(int(raw_length))
        if not verify_webhook_signature(payload, self.headers.get("Stripe-Signature", ""), secret):
            self.send_json(400, {"error": "Invalid Stripe webhook signature."})
            return
        try:
            event = json.loads(payload)
            if not isinstance(event, dict):
                raise ValueError("Webhook body must be an object.")
            event_type = event.get("type")
            event_data = event.get("data")
            if not isinstance(event_data, dict) or not isinstance(event_data.get("object"), dict):
                raise ValueError("Webhook event data is missing its session object.")
            session = event_data["object"]
            if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
                order_id = (session.get("metadata") or {}).get("order_id")
                if isinstance(order_id, str):
                    with database_connection() as connection:
                        order = connection.execute(
                            "SELECT order_id, checkout_session_id FROM contract_orders WHERE order_id = ?",
                            (order_id,),
                        ).fetchone()
                        if order and session.get("id") == order["checkout_session_id"]:
                            if verify_paid_session(session, order):
                                connection.execute(
                                    "UPDATE contract_orders SET status = ?, paid_at = COALESCE(paid_at, ?) WHERE order_id = ?",
                                    ("paid", int(time.time()), order_id),
                                )
                            elif session.get("payment_status") != "paid":
                                connection.execute("UPDATE contract_orders SET status = ? WHERE order_id = ?", ("pending", order_id))
            elif event_type == "checkout.session.async_payment_failed":
                order_id = (session.get("metadata") or {}).get("order_id")
                with database_connection() as connection:
                    connection.execute(
                        "UPDATE contract_orders SET status = ? WHERE order_id = ? AND checkout_session_id = ? AND status != ?",
                        ("failed", order_id, session.get("id"), "paid"),
                    )
            self.send_json(200, {"received": True})
        except (ValueError, json.JSONDecodeError) as error:
            self.send_json(400, {"error": f"Invalid Stripe webhook payload: {error}"})
        except sqlite3.Error as error:
            print(f"Stripe webhook storage failed: {error}")
            self.send_json(500, {"error": "Unable to record the Stripe event."})

    def serve_static(self, request_path):
        if request_path not in {"", "/", "/index.html"}:
            self.send_error(404)
            return
        body = (ROOT / "index.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), ContractPaymentHandler)
    cleanup_thread = threading.Thread(target=cleanup_expired_orders, daemon=True)
    cleanup_thread.start()
    print(f"Turksoil contract server listening on http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down Turksoil contract server.")
    finally:
        server.server_close()


def cleanup_expired_orders():
    while True:
        try:
            with database_connection():
                pass
        except sqlite3.Error as error:
            print(f"Expired contract cleanup failed: {error}")
        time.sleep(60 * 60)


if __name__ == "__main__":
    main()
