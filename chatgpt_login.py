"""Official local-app ChatGPT plan OAuth. Credentials stay in session memory."""
import base64
import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import parse_qs, urlencode, urlsplit
import uuid

import httpx
import jwt

AUTH = 'https://auth.openai.com'
RESOURCE = 'https://api.openai.com/v1'
PLAN_SCOPE = 'chatgpt.tokens.use.direct'


class LoginError(ValueError):
    pass


def host_id():
    directory = Path(__file__).resolve().parent / '.noteon'
    directory.mkdir(exist_ok=True)
    path = directory / 'host-id'
    if not path.exists():
        try:
            with path.open('x', encoding='utf-8') as file:
                file.write('urn:uuid:' + str(uuid.uuid4()))
        except FileExistsError:
            pass
    return path.read_text(encoding='utf-8').strip()


def load_registration():
    """Only the non-secret account/client mapping is persisted, never tokens."""
    try:
        data = json.loads((Path(__file__).resolve().parent / '.noteon' / 'registration.json').read_text(encoding='utf-8'))
        if isinstance(data.get('client_id'), str) and data['client_id'].startswith('oaiapp_') and isinstance(data.get('sub'), str):
            return {'client_id': data['client_id'], 'sub': data['sub']}
    except (OSError, ValueError, AttributeError):
        pass
    return None


def save_registration(session):
    directory = Path(__file__).resolve().parent / '.noteon'
    directory.mkdir(exist_ok=True)
    temporary = directory / ('registration-' + secrets.token_hex(8) + '.tmp')
    with temporary.open('x', encoding='utf-8') as file:
        if os.name != 'nt':
            os.chmod(temporary, 0o600)
        json.dump({'client_id': session['client_id'], 'sub': session['sub']}, file)
    temporary.replace(directory / 'registration.json')


def validate_identity(token, client_id, nonce):
    signing_key = jwt.PyJWKClient(AUTH + '/.well-known/jwks.json', timeout=20).get_signing_key_from_jwt(token)
    claims = jwt.decode(token, signing_key.key, algorithms=['RS256'], audience=client_id,
                        issuer=AUTH, leeway=5, options={'require': ['exp', 'iat', 'sub', 'nonce']})
    if not secrets.compare_digest(claims['nonce'], nonce) or not claims['sub']:
        raise LoginError('로그인 검증에 실패했습니다. 다시 연결해주세요.')
    return claims


class LoginAttempt:
    def __init__(self, registration=None):
        self.state = secrets.token_urlsafe(32)
        self.nonce = secrets.token_urlsafe(32)
        self.verifier = secrets.token_urlsafe(64)
        self.deadline = time.time() + 600
        self.registration = registration or {}
        self.result = None
        self.error = None
        self.done = False
        self.lock = threading.Lock()
        attempt = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass  # The callback URL contains an authorization code.

            def do_GET(self):
                parsed = urlsplit(self.path)
                query = parse_qs(parsed.query)
                if parsed.path != '/auth/callback':
                    self.send_error(404)
                    return
                with attempt.lock:
                    if (attempt.done or time.time() > attempt.deadline
                            or not secrets.compare_digest(query.get('state', [''])[0], attempt.state)):
                        self.send_error(400, 'Invalid or expired sign-in attempt')
                        return
                    attempt.done = True
                    if query.get('error'):
                        attempt.error = '로그인이 취소되었거나 구독 사용 권한이 허용되지 않았습니다.'
                    else:
                        attempt.result = {k: query.get(k, [''])[0] for k in ('code', 'client_id')}
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.end_headers()
                self.wfile.write('<h2>노트온으로 돌아가서 로그인 완료 확인 버튼을 눌러주세요.</h2>'.encode())
                threading.Thread(target=attempt.server.shutdown, daemon=True).start()

        self.server = HTTPServer(('127.0.0.1', 0), Handler)
        self.redirect = f'http://127.0.0.1:{self.server.server_port}/auth/callback'
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.timer = threading.Timer(600, self.close)
        self.timer.daemon = True
        self.timer.start()
        params = {
            'client_id': self.registration.get('client_id', 'dynamic_agent_client'),
            'ext_agent_host_id': host_id(), 'response_type': 'code', 'redirect_uri': self.redirect,
            'scope': 'openid profile email offline_access resource.invoke ' + PLAN_SCOPE,
            'resource': RESOURCE, 'state': self.state, 'nonce': self.nonce,
            'code_challenge_method': 'S256',
            'code_challenge': base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).rstrip(b'=').decode(),
        }
        if not self.registration:
            params['agent_name_hint'] = 'NoteOn Study'
        self.url = AUTH + '/api/accounts/authorize?' + urlencode(params)

    def close(self):
        self.timer.cancel()
        self.server.shutdown()
        self.server.server_close()

    def finish(self):
        if time.time() > self.deadline:
            self.close()
            raise LoginError('로그인 시간이 만료됐습니다. 다시 시작해주세요.')
        if not self.done:
            raise LoginError('브라우저에서 로그인을 완료한 후 다시 눌러주세요.')
        self.close()
        if self.error:
            raise LoginError(self.error)
        result, self.result = self.result, None  # Authorization codes are one-use.
        if not result or not result['code']:
            raise LoginError('유효한 로그인 결과가 없습니다. 다시 시작해주세요.')
        client_id = self.registration.get('client_id') or result['client_id']
        if (not client_id or client_id == 'dynamic_agent_client'
                or (result['client_id'] and result['client_id'] != client_id)):
            raise LoginError('앱 등록 정보를 검증하지 못했습니다. 다시 시작해주세요.')
        response = httpx.post(AUTH + '/api/accounts/oauth/token', data={
            'grant_type': 'authorization_code', 'client_id': client_id, 'code': result['code'],
            'code_verifier': self.verifier, 'redirect_uri': self.redirect, 'resource': RESOURCE,
        }, timeout=30)
        if not response.is_success:
            raise LoginError(f'로그인 토큰 교환 실패 (HTTP {response.status_code}). 다시 연결하거나 Gemini를 선택해주세요.')
        tokens = response.json()
        try:
            claims = validate_identity(tokens['id_token'], client_id, self.nonce)
        except Exception:
            raise LoginError('로그인 서명을 검증하지 못했습니다. 다시 연결해주세요.') from None
        if self.registration.get('sub') and claims['sub'] != self.registration['sub']:
            raise LoginError('기존 연결과 다른 계정입니다. 연결을 해제한 뒤 다시 로그인해주세요.')
        if PLAN_SCOPE not in tokens.get('scope', '').split() or not tokens.get('access_token'):
            raise LoginError('ChatGPT 구독 사용 권한이 부여되지 않았습니다. 이 계정에서 허용되지 않으면 Gemini를 선택해주세요.')
        return {**tokens, 'client_id': client_id, 'sub': claims['sub'],
                'account_label': claims.get('email') or claims.get('name') or '연결된 ChatGPT 계정',
                '_refresh_lock': threading.Lock(),
                'expires_at': time.time() + int(tokens.get('expires_in', 3600))}


def access_token(session):
    with session['_refresh_lock']:
        if time.time() >= session['expires_at'] - 60:
            if not session.get('refresh_token'):
                raise LoginError('ChatGPT 연결 시간이 만료됐습니다. 다시 로그인해주세요.')
            response = httpx.post(AUTH + '/api/accounts/oauth/token', data={
                'grant_type': 'refresh_token', 'client_id': session['client_id'],
                'refresh_token': session['refresh_token'], 'resource': RESOURCE,
            }, timeout=30)
            if not response.is_success:
                if response.status_code in (400, 401):
                    session.pop('access_token', None)
                    session.pop('refresh_token', None)
                raise LoginError('ChatGPT 연결을 갱신하지 못했습니다. 네트워크를 확인하거나 다시 로그인해주세요.')
            tokens = response.json()
            if not tokens.get('access_token') or PLAN_SCOPE not in tokens.get('scope', session.get('scope', '')).split():
                raise LoginError('구독 사용 권한 갱신에 실패했습니다. 다시 로그인해주세요.')
            session.update({k: tokens[k] for k in ('access_token', 'refresh_token', 'scope') if k in tokens})
            session['expires_at'] = time.time() + int(tokens.get('expires_in', 3600))
    return session['access_token']


def disconnect(session):
    """Attempt remote revocation; the UI clears local tokens in every case."""
    if not session.get('refresh_token'):
        return False
    try:
        config = httpx.get(AUTH + '/.well-known/openid-configuration', timeout=15)
        config.raise_for_status()
        endpoint = config.json()['revocation_endpoint']
        parsed = urlsplit(endpoint)
        if parsed.scheme != 'https' or parsed.hostname != 'auth.openai.com':
            return False
        response = httpx.post(endpoint, data={'token': session['refresh_token'],
                              'token_type_hint': 'refresh_token', 'client_id': session['client_id']}, timeout=15)
        return response.status_code == 200
    except Exception:
        return False


def list_models(session):
    response = httpx.get(RESOURCE + '/models', headers={'Authorization': 'Bearer ' + access_token(session)}, timeout=30)
    if not response.is_success:
        raise LoginError(f'구독 모델 목록 확인 실패 (HTTP {response.status_code}). 이 계정에서 지원되지 않으면 Gemini를 선택해주세요.')
    return [(m['slug'], m.get('display_name', m['slug'])) for m in response.json().get('models', []) if m.get('visibility') == 'list']
