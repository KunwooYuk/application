import hashlib
import json
import os
import time
import streamlit as st
from core import MAX_CHARS, QUIZ_SCHEMA, ask, extract, explain_api_error, grade, validate_quiz
from chatgpt_login import LoginAttempt, LoginError, access_token, disconnect, list_models, load_registration, save_registration

st.set_page_config(page_title='노트온 · 나만의 AI 학습실', page_icon='📚', layout='wide')
st.markdown('''<style>
.stApp {background:#f7f8fc} .block-container {max-width:1200px;padding-top:2.5rem}
h1,h2,h3 {color:#242647} [data-testid="stSidebar"] {background:#eef0fa}
.hero {background:linear-gradient(120deg,#27284f,#6058ba);color:white;border-radius:22px;padding:32px;margin-bottom:24px}
.hero h1 {color:white;margin:8px 0}.hero p {color:#e5e2ff}
.stButton>button[kind="primary"] {background:#6255c7;border:0}
</style>''', unsafe_allow_html=True)
with st.sidebar:
    st.title('📚 노트온')
    st.caption('NOTE ON · LEARN YOUR WAY')
    provider = st.selectbox('AI 연결 방식', ['chatgpt', 'gemini', 'openai'], format_func=lambda p: {'chatgpt': 'ChatGPT 구독으로 로그인 (우선 시도)', 'gemini': 'Gemini API (무료 등급 가능)', 'openai': 'OpenAI API (별도 크레딧)'}[p], key='provider')
    key, model = '', ''
    if provider == 'chatgpt':
        if 'chatgpt_registration' not in st.session_state:
            st.session_state.chatgpt_registration = load_registration()
        st.caption('로컬 앱용 공식 로그인 경로입니다. 계정·지역·정책·미리보기 지원 및 구독 사용 한도가 적용됩니다. API 키는 필요하지 않습니다.')
        if st.button('ChatGPT 로그인 준비', key='loginstart'):
            previous = st.session_state.pop('login_attempt', None)
            if previous:
                previous.close()
            try:
                st.session_state.login_attempt = LoginAttempt(st.session_state.get('chatgpt_registration'))
            except Exception:
                st.error('로그인을 시작하지 못했습니다. 앱 폴더의 쓰기 권한과 로컬 포트를 확인하세요.')
        attempt = st.session_state.get('login_attempt')
        if attempt:
            st.link_button('Continue with ChatGPT', attempt.url)
            if st.button('로그인 완료 확인', key='loginfinish'):
                try:
                    session = attempt.finish()
                    st.session_state.chatgpt_session = session
                    st.session_state.chatgpt_registration = {'client_id': session['client_id'], 'sub': session['sub']}
                    try:
                        save_registration(session)
                    except OSError:
                        st.warning('앱 등록 정보를 저장하지 못했습니다. 현재 세션에서는 로그인할 수 있습니다.')
                    st.session_state.pop('chatgpt_models', None)
                    st.session_state.pop('login_attempt', None)
                except LoginError as exc:
                    st.warning(str(exc))
                except Exception:
                    st.error('로그인 연결에 실패했습니다. 네트워크를 확인하거나 Gemini를 선택해주세요.')
        session = st.session_state.get('chatgpt_session')
        if session:
            st.success('ChatGPT 로그인 연결됨')
            st.caption(session['account_label'])
            st.info('Using ChatGPT plan · 이 앱의 AI 요청은 연결한 구독 사용량에 반영됩니다.')
            st.link_button('ChatGPT 사용량·앱 권한 관리', 'https://chatgpt.com/settings/usage')
            if st.button('사용 가능한 모델 불러오기', key='loadmodels'):
                try:
                    st.session_state.chatgpt_models = list_models(session)
                except LoginError as exc:
                    st.warning(str(exc))
                except Exception:
                    st.error('모델 목록을 가져오지 못했습니다. 네트워크를 확인해주세요.')
            models = st.session_state.get('chatgpt_models', [])
            if models:
                names = dict(models)
                model = st.selectbox('구독에서 사용 가능한 모델', list(names), format_func=lambda slug: names[slug])
            else:
                st.info('모델 불러오기 버튼을 먼저 눌러주세요.')
            if st.button('ChatGPT 연결 해제', key='logout'):
                revoked = disconnect(session)
                st.session_state.logout_notice = 'ChatGPT 연결을 해제했습니다.' if revoked else '앱의 연결 정보는 지웠습니다. 원격 권한 해제는 확인하지 못했으므로 ChatGPT 설정에서 앱 연결을 해제해주세요.'
                for field in ['chatgpt_session', 'chatgpt_models']:
                    st.session_state.pop(field, None)
                if attempt:
                    attempt.close()
                    st.session_state.pop('login_attempt', None)
                st.rerun()
        if st.session_state.get('logout_notice'):
            st.info(st.session_state.pop('logout_notice'))
    else:
        label = 'Gemini' if provider == 'gemini' else 'OpenAI'
        key = st.text_input(label + ' API 키', type='password', value=os.getenv('GEMINI_API_KEY' if provider == 'gemini' else 'OPENAI_API_KEY', ''), key=provider+'_key', help='키는 현재 세션 메모리에서만 사용합니다.')
        model = st.text_input('모델', value=os.getenv('GEMINI_MODEL', 'gemini-3.1-flash-lite') if provider == 'gemini' else os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'), key=provider+'_model')
        if provider == 'gemini':
            st.link_button('Google AI Studio에서 키 발급', 'https://aistudio.google.com/apikey')
            st.caption('무료 등급에는 요청 한도가 있으며 입력·출력이 Google 제품 개선에 사용될 수 있습니다. 과금 계정 연결 여부는 Google AI Studio에서 확인하세요.')
        else:
            st.caption('ChatGPT Plus 구독과 API 크레딧은 별개입니다.')
    st.divider()
    st.markdown('**오늘의 학습 흐름**\n\n① 강의 자료 올리기\n\n② 노트로 핵심 잡기\n\n③ 질문하고 번역하기\n\n④ 퀴즈와 모의시험')
    st.info(f'AI 요청 시 추출된 자료와 대화가 {"Google" if provider == "gemini" else "OpenAI"}로 전송됩니다. 선택한 연결 방식만 사용하며 다른 업체로 자동 전환하지 않습니다.')
    if st.button('현재 학습 기록 초기화'):
        pending = st.session_state.get('login_attempt')
        if pending:
            pending.close()
        connected = st.session_state.get('chatgpt_session')
        if connected and not disconnect(connected):
            st.warning('원격 권한 해제를 확인하지 못했습니다. ChatGPT 설정에서 앱 연결을 확인해주세요.')
        for k in list(st.session_state):
            del st.session_state[k]
        st.rerun()

st.markdown('<div class="hero"><small>YOUR PERSONAL STUDY STUDIO</small><h1>복잡한 강의가, 나만의 노트로.</h1><p>읽고, 물어보고, 풀어보세요. 이해가 실력이 되는 학습 공간.</p></div>', unsafe_allow_html=True)
files = st.file_uploader('강의 자료를 올려주세요', type=['pdf', 'docx', 'pptx', 'txt', 'md'], accept_multiple_files=True, help='파일당 20MB · 전체 추출 텍스트 18만 자 · 이미지 OCR 미지원')
sample = st.checkbox('샘플 자료로 둘러보기 (AI 작업에는 API 키 필요)')
source = ''
try:
    if files:
        source = '\n\n'.join(extract(f.name, f.getvalue()) for f in files)
    elif sample:
        source = '[샘플 강의 · 문단 1]\nPhotosynthesis converts light energy into chemical energy. Chlorophyll absorbs light in chloroplasts.\n\n[샘플 강의 · 문단 2]\n광합성의 명반응은 틸라코이드에서 ATP와 NADPH를 만들고 물을 분해해 산소를 방출한다. 캘빈 회로는 스트로마에서 ATP와 NADPH를 사용하여 이산화탄소를 고정한다.'
    if len(source) > MAX_CHARS:
        raise ValueError('전체 자료는 18만 자 이하로 나누어 올려주세요.')
except Exception as exc:
    st.error(f'자료를 읽지 못했습니다: {exc}')
    st.stop()
fingerprint = hashlib.sha256(source.encode()).hexdigest()
if st.session_state.get('source_id') != fingerprint:
    for k in ['notes', 'translation', 'chat', 'quiz', 'exam', 'quiz_result', 'exam_result', 'exam_start']:
        st.session_state.pop(k, None)
    st.session_state.source_id = fingerprint
if not source:
    st.info('자료를 업로드하거나 샘플을 선택하면 학습을 시작할 수 있어요.')
    st.stop()
st.caption(f'자료 준비 완료 · {len(files) if files else 1}개 자료 · {len(source):,}자')
with st.expander('추출된 원문과 출처 확인'):
    st.text(source)


def run(task, history=None, schema=None):
    credential = key.strip()
    if provider == 'chatgpt':
        session = st.session_state.get('chatgpt_session')
        if not session or not model:
            st.warning('왼쪽에서 ChatGPT 로그인 후 사용 가능한 모델을 불러와 선택해주세요.')
            return None
        try:
            credential = access_token(session)
        except LoginError as exc:
            st.warning(str(exc))
            return None
        except Exception:
            st.error('ChatGPT 연결을 갱신하지 못했습니다. 네트워크를 확인하고 다시 시도해주세요.')
            return None
    if not credential:
        st.warning(f'왼쪽에 {"Gemini" if provider == "gemini" else "OpenAI"} API 키를 입력해주세요.')
        return None
    try:
        with st.spinner('자료를 바탕으로 생각하고 있어요…'):
            return ask(credential, model.strip(), source, task, history, schema, provider=provider)
    except Exception as exc:
        st.error(explain_api_error(exc, provider))
        st.caption('문제가 계속되면 위의 진단 코드만 알려주세요. API 키와 자료 내용은 보내지 마세요.')
        return None


notes, translate, chat, quiz, exam = st.tabs(['📝 핵심 노트', '🌐 영어 해석', '💬 AI 튜터', '🎯 이해도 퀴즈', '⏱ 모의시험'])
with notes:
    st.subheader('흩어진 내용을 한눈에')
    style = st.selectbox('노트 스타일', ['시험 대비 핵심 정리', '처음 배우는 사람을 위한 자세한 설명', '코넬 노트'])
    if st.button('학습 노트 만들기', type='primary', key='notesgenerate'):
        result = run(f'{style} 방식의 한국어 마크다운 노트를 작성하세요. 학습 목표, 단원별 핵심 개념, 용어 표, 예시, 흔한 오개념, 복습 체크리스트를 포함하세요. 각 개념에 출처를 붙이세요.')
        if result:
            st.session_state.notes = result
    if st.session_state.get('notes'):
        st.markdown(st.session_state.notes)
        st.download_button('노트 다운로드 (.md)', st.session_state.notes, 'study-notes.md', 'text/markdown')
with translate:
    st.subheader('영어 자료도 내 언어로')
    st.caption('전체 자료를 문단별로 번역하며 전문용어는 영어를 함께 표시합니다.')
    if st.button('한국어로 해석하기', type='primary'):
        result = run('영어 부분을 빠짐없이 한국어로 번역하세요. 원문과 번역을 문단별로 나란히 순서대로 제시하고 출처를 유지하세요. 이미 한국어인 부분은 그대로 보존하세요. 마지막에 주요 영한 전문용어 표를 작성하세요.')
        if result:
            st.session_state.translation = result
    if st.session_state.get('translation'):
        st.markdown(st.session_state.translation)
        st.download_button('해석 다운로드', st.session_state.translation, 'translation.md')
with chat:
    st.subheader('막히는 순간, 바로 질문하세요')
    st.caption('예: “이 개념을 중학생도 이해하도록 설명해줘”, “두 개념의 차이가 뭐야?”')
    history = st.session_state.setdefault('chat', [])
    for message in history:
        with st.chat_message(message['role']):
            st.markdown(message['content'])
    question = st.chat_input('강의 내용에 대해 물어보세요', max_chars=4000)
    if question:
        result = run(question, history)
        if result:
            history.extend([{'role': 'user', 'content': question}, {'role': 'assistant', 'content': result}])
            st.rerun()


def practice(mode, timed=False):
    st.subheader('실전처럼 풀고, 부족한 개념을 찾아보세요' if timed else '얼마나 이해했는지 확인해볼까요?')
    a, b = st.columns(2)
    count = a.selectbox('문항 수', [3, 5, 10], key=mode+'count')
    level = b.selectbox('난이도', ['기초', '보통', '심화'], key=mode+'level')
    minutes = st.number_input('시험 시간 (분)', min_value=1, max_value=180, value=15) if timed else None
    if st.button('새 모의시험 출제' if timed else '새 퀴즈 만들기', key=mode+'generate', type='primary'):
        raw = run(f'자료에 근거한 {level} 난이도 4지선다 문제를 정확히 {count}개 만드세요. '+ ('개념 적용과 상황 분석 중심으로 출제하세요.' if timed else '핵심 개념의 이해도를 확인하세요.') + '각 문항 options는 서로 다른 선택지 4개, answer는 정답 인덱스 0~3, explanation은 정답과 오답의 이유, source는 자료의 출처입니다. 정답을 질문에 노출하지 마세요.', schema=QUIZ_SCHEMA)
        if raw:
            try:
                questions = validate_quiz(raw, count)
                st.session_state[mode] = questions
                st.session_state.pop(mode+'_result', None)
                st.session_state[mode+'_start'] = time.time()
                st.session_state[mode+'_duration'] = (minutes or 0) * 60
                st.session_state[mode+'_generation'] = time.time_ns()
            except (ValueError, KeyError, TypeError):
                st.error('문항 형식이 올바르지 않습니다. 다시 생성해주세요.')
    questions = st.session_state.get(mode)
    if not questions:
        return
    result = st.session_state.get(mode+'_result')
    generation = str(st.session_state[mode+'_generation'])
    if result is None:
        @st.fragment(run_every='1s' if timed else None)
        def answer_form():
            if mode+'_result' in st.session_state:
                return
            expired = timed and time.time() - st.session_state[mode+'_start'] >= st.session_state[mode+'_duration']
            if timed:
                remaining = max(0, int(st.session_state[mode+'_duration'] - (time.time() - st.session_state[mode+'_start'])))
                st.info(f'남은 시간 {remaining//60:02d}:{remaining%60:02d} · 시간 종료 시 현재 답안 자동 제출')
            answers = {}
            for i, q in enumerate(questions):
                answers[str(i)] = st.radio(f'{i+1}. {q["question"]}', range(4), format_func=lambda n, q=q: q['options'][n], index=None, key=mode+generation+str(i), disabled=bool(expired))
            if st.button('답안 제출 및 채점', key=mode+'submit') or expired:
                if not expired and any(v is None for v in answers.values()):
                    st.warning('모든 문항에 답해주세요.')
                else:
                    st.session_state[mode+'_result'] = {'answers': answers, 'correct': grade(questions, answers), 'expired': bool(expired)}
                    st.rerun()
        answer_form()
    else:
        correct = result['correct']
        score = round(sum(correct)/len(questions)*100)
        st.metric('나의 이해도', f'{score}점', f'{sum(correct)} / {len(questions)} 정답')
        if result['expired']:
            st.warning('시간이 종료되어 자동 제출했습니다. 미응답은 오답으로 처리했습니다.')
        if score == 100:
            st.success('모든 문제를 맞혔어요! 심화 문제에 도전해보세요.')
        only_wrong = st.checkbox('틀린 문제만 복습', key=mode+'wrong')
        for i, q in enumerate(questions):
            if only_wrong and correct[i]:
                continue
            with st.expander(f'{"✅" if correct[i] else "🔁"} {i+1}. {q["question"]}', expanded=not correct[i]):
                selected = result['answers'].get(str(i))
                st.write('내 답: ' + (q['options'][selected] if selected is not None else '미응답'))
                st.write('정답: ' + q['options'][q['answer']])
                st.markdown(q['explanation'])
                st.caption(q['source'])
        st.download_button('문제·정답·결과 저장 (.json)', json.dumps({'questions': questions, 'result': result}, ensure_ascii=False, indent=2), mode+'-review.json', 'application/json', key=mode+'download')


with quiz:
    practice('quiz')
with exam:
    practice('exam', timed=True)
