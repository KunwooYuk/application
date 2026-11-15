# 📚 노트온 — 강의 자료 AI 학습실

강의 자료를 올리고 **노트 정리 → 영어 해석 → 질문 → 이해도 퀴즈 → 모의시험**으로 학습하는 한국어 웹 앱입니다.

## 실행

Python 3.11 이상을 권장합니다. Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1
```

브라우저에서 `http://127.0.0.1:8501`에 접속합니다. 키 없이도 샘플 자료와 화면을 확인할 수 있습니다. 기존 설치에서 업데이트할 때도 `pip install -r requirements.txt`를 다시 실행하세요.

## AI 연결 — ChatGPT 우선, Gemini 대안

### 1. ChatGPT 구독으로 로그인 (기본)

이 앱을 실행하는 컴퓨터의 브라우저에서 사용하세요. 원격 서버에 올린 앱을 다른 컴퓨터에서 여는 방식은 이 로그인 구현에서 지원하지 않습니다.

1. 왼쪽 AI 연결 방식에서 **ChatGPT 구독으로 로그인** 선택.
2. **ChatGPT 로그인 준비 → Continue with ChatGPT** 클릭.
3. OpenAI 공식 로그인 페이지에서 본인 계정으로 로그인하고 NoteOn Study의 구독 사용 권한을 검토·승인.
4. 앱으로 돌아와 **로그인 완료 확인 → 사용 가능한 모델 불러오기** 클릭.
5. 계정에 표시된 모델 선택 후 샘플 자료로 노트 생성.

OpenAI가 문서화한 로컬 앱용 Sign in with ChatGPT/ChatGPT plan usage 방식입니다. API 키를 발급하는 방식과 다르며, 계정·지역·정책·미리보기 지원 여부와 구독 사용 한도가 적용됩니다. Plus도 이 구독 경로에서 사용 한도가 적용됩니다. 실제 계정에서의 승인과 모델 응답은 사용자 로그인 후에만 검증할 수 있습니다. 실패 시 오류를 확인하고 Gemini를 선택하세요. 이 앱이 계정을 대신 업그레이드하거나 API 크레딧을 구매하지는 않습니다.

인증 토큰은 현재 세션의 서버 메모리에만 보관합니다. 만료 직전 자동 갱신하며, 세션이 사라지면 다시 로그인해야 합니다. 장치 ID와 비밀이 아닌 계정/앱 등록 식별자만 `.noteon/`에 저장하여 재로그인에 재사용합니다. 이 폴더는 Git에서 제외합니다. 사용량과 권한은 [ChatGPT 설정](https://chatgpt.com/settings/usage)에서 확인할 수 있습니다. 연결 해제 시 원격 세션 해제를 시도하고 로컬 토큰을 삭제합니다. 네트워크 실패로 원격 해제가 확인되지 않으면 ChatGPT 설정에서 앱 권한을 해제하세요.

### 2. Gemini API (구독 연결이 안 되는 경우)

1. [Google AI Studio](https://aistudio.google.com/apikey)에서 본인의 API 키 발급.
2. 앱에서 **Gemini API** 선택 후 Gemini 키 입력.
3. 기본 모델 `gemini-3.1-flash-lite`로 샘플 자료 테스트. 계정에서 지원하는 다른 모델로 변경 가능.

무료 등급은 모델·프로젝트별 사용 한도가 있습니다. 무료 사용을 원하면 Google AI Studio에서 무료 등급과 결제 연결 상태를 확인하세요. 무료 등급 입력·출력은 Google 제품 개선에 사용될 수 있으므로 개인정보가 포함된 자료는 보내지 마세요. 앱 자체는 유료 등급을 활성화하지 않습니다. `GEMINI_API_KEY`, `GEMINI_MODEL` 환경변수도 지원합니다.

### 3. OpenAI API (별도 크레딧)

기존 OpenAI API 연결도 유지합니다. 이 방식은 ChatGPT Plus 결제와 별도로 API 크레딧이 필요합니다. 기본 모델 `gpt-4.1-mini`, 환경변수 `OPENAI_API_KEY`, `OPENAI_MODEL`을 지원합니다. **OpenAI API 키와 Gemini 키는 서로 호환되지 않습니다.**

Windows에서는 스크립트 실행이 허용된 환경에서 `.\start.ps1`로 설치와 실행을 한 번에 할 수 있습니다. 스크립트가 차단되면 위의 개별 명령을 사용하세요. 업로드 연습용 `sample-lecture.txt`도 포함되어 있습니다.

## 기능

- PDF, DOCX(표 포함), PPTX, TXT, MD 업로드 및 위치 표시가 있는 원문 확인
- 시험 대비 / 입문 설명 / 코넬 노트 생성 및 Markdown 다운로드
- 영어 원문과 한국어 번역, 전문용어 정리 및 다운로드
- 자료를 바탕으로 문맥을 유지하는 AI 튜터 대화
- 난이도별 3/5/10문항 객관식 퀴즈, 채점, 해설, 오답 복습
- 제한 시간 모의시험과 현재 답안 자동 제출, JSON 결과 내보내기
- 자료 변경 시 기존 노트·대화·시험 초기화

## 데이터와 제한

업로드 자료는 현재 Streamlit 세션 메모리에서 처리합니다. 앱은 원문, API 키, 대화, 로그인 토큰을 파일이나 데이터베이스에 저장하지 않습니다. AI 버튼을 누르거나 질문을 전송하면 자료와 관련 대화가 선택한 업체(OpenAI 또는 Google)에 전송됩니다. 다른 업체로 자동 전환하지 않습니다. OpenAI는 Responses API의 `store=False`를 사용하며 구독 로그인은 스트리밍으로 완료 상태까지 확인합니다. Gemini는 Google의 OpenAI 호환 API를 사용합니다. 업체의 데이터 처리 정책은 별도로 적용됩니다. 노트와 결과를 남기려면 다운로드하세요. 새로고침/세션 종료 시 기록이 사라질 수 있습니다.

파일당 최대 20MB, 전체 추출 텍스트 최대 18만 자입니다. 스캔 PDF, 그림, 수식 이미지에는 별도 OCR이 필요합니다. 텍스트 추출 순서가 원본 레이아웃과 다를 수 있으므로 원문 확인을 권장합니다. 긴 자료는 응답 길이 한도로 전체 번역이나 노트 생성이 실패할 수 있으니 단원별로 나누세요. AI 출처와 정답은 원문으로 확인하세요. 모의시험 타이머는 브라우저가 연결된 동안 작동하며, 재연결 시 경과 시간을 확인합니다. 개인 로컬 사용을 위한 앱이며 공개 서버 운영을 위한 사용자 인증이나 계정별 저장 기능은 포함하지 않습니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

텍스트 인코딩, DOCX/PPTX 추출, 문항 검증, 채점, 화면 흐름, Gemini 요청 형식, ChatGPT 스트림 완료, 로그인 state/PKCE/일회성 코드 및 JWT 서명·대상·nonce를 검증합니다. AI 응답과 토큰 교환은 모의 처리하며 실제 계정 로그인이나 유료 API 호출은 하지 않습니다.

## GitHub에 올리기

GitHub CLI 설치와 로그인 후 프로젝트 폴더에서 실행하세요. API 키나 개인 강의 자료는 커밋하지 마세요. `.gitignore`가 가상환경, `.env`, Streamlit 비밀 설정을 제외합니다.

```powershell
gh auth login
git init -b main
git add .
git commit -m "Build NoteOn AI study app"
gh repo create study-note-ai --private --source . --remote origin --push
```

기존 저장소를 사용할 경우 `git remote add origin <저장소 URL>`과 `git push -u origin main`을 사용합니다. 최초 커밋 전 Git 작성자 이름과 이메일 설정이 필요할 수 있습니다.

## 참고 자료

- 사용자 제공 영상: [Coding Agent CLI · 2-5 GitHub: 버전 관리에서 공유까지, 내 앱과 스킬 올리기](https://www.youtube.com/watch?v=XEVzKcqRnRE). 영상 제목/주제만 확인했으며 영상 본문과 자막은 확인하지 못했습니다.
- [OpenAI Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create)
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
- [로컬 앱의 ChatGPT 구독 사용](https://developers.openai.com/siwc/token-sharing-open-source)
- [구독 로그인 제약](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [Gemini OpenAI 호환 API](https://ai.google.dev/gemini-api/docs/openai)
- [Gemini 무료 등급과 가격](https://ai.google.dev/gemini-api/docs/pricing)

## 구성

`app.py`: 한국어 UI와 학습 상태, `core.py`: 문서 추출·AI 요청·문항 검증·채점, `chatgpt_login.py`: 공식 OAuth 로컬 로그인, `tests/`: 자동 검증.
