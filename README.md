# 노트북 최저가 스나이핑 알림 봇

삼성 갤럭시북4 / LG 그램 / 레노버 아이디어패드 Slim5 의 최저가를
**하루 2회(09:00·21:00 KST)** 자동 조회해서, **직전 관측 대비 10% 이상 하락**하면
**텔레그램으로 알림**을 보냅니다.

- **데이터 소스**: 네이버쇼핑 검색 API(메인) + 다나와(보조, best-effort)
- **무료 클라우드**: GitHub Actions (서버 없이 크론으로 자동 실행, PC를 켜둘 필요 없음)
- **상태 저장**: `data/price_history.json` 을 저장소에 커밋(별도 DB 불필요)

---

## 구조

```
config.json                  # 감시할 모델 목록 & 하락 임계치(10%)
main.py                      # 실행 진입점 (조회 → 비교 → 알림 → 저장)
naver.py                     # 네이버쇼핑 API 최저가 조회 (메인)
danawa.py                    # 다나와 스크래핑 최저가 조회 (보조)
notifier.py                  # 텔레그램 발송
storage.py                   # price_history.json 읽기/쓰기
data/price_history.json      # 직전 관측값(상태)
.github/workflows/monitor.yml # 하루 2회 자동 실행
```

---

## 설치 & 세팅 (처음 한 번)

### 1. GitHub 저장소 만들기
이 폴더를 GitHub에 올립니다(비공개 저장소 OK, Actions 무료).
```bash
git init
git add .
git commit -m "init: 노트북 가격 모니터"
git branch -M main
git remote add origin https://github.com/<본인아이디>/<레포이름>.git
git push -u origin main
```

### 2. 네이버 검색 API 키 발급 (무료)
1. https://developers.naver.com/apps/#/register 접속 → 로그인
2. **애플리케이션 등록**
   - 사용 API: **검색** 선택
   - 환경 추가: **WEB 설정** → URL 은 `http://localhost` 아무거나 입력
3. 발급된 **Client ID / Client Secret** 을 복사 (하루 25,000회 무료 → 일 2회 x 3모델이면 차고 넘침)

### 3. 텔레그램 봇 만들기
1. 텔레그램에서 **@BotFather** 검색 → `/newbot` → 이름 지정 → **봇 토큰** 획득
2. 방금 만든 내 봇을 검색해서 **아무 메시지나 한 번 전송** (중요: 이걸 해야 chat_id가 잡힘)
3. **chat_id 확인**: 브라우저에서 아래 주소 접속(토큰 넣기)
   ```
   https://api.telegram.org/bot<봇토큰>/getUpdates
   ```
   결과 JSON 에서 `"chat":{"id": 숫자}` 의 숫자가 **chat_id** 입니다.
   (또는 텔레그램에서 **@userinfobot** 에게 말 걸면 내 id를 알려줍니다.)

### 4. GitHub Secrets 등록
저장소 → **Settings → Secrets and variables → Actions → New repository secret** 에서 4개 등록:

| 이름 | 값 |
|------|-----|
| `NAVER_CLIENT_ID` | 네이버 Client ID |
| `NAVER_CLIENT_SECRET` | 네이버 Client Secret |
| `TELEGRAM_BOT_TOKEN` | BotFather 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 내 chat_id |

### 5. 동작 확인
- 저장소 → **Actions 탭 → price-monitor → Run workflow** 로 수동 실행
- 로그에서 각 모델 최저가가 찍히면 성공. 이후 하루 2회 자동 실행됩니다.
- 첫 실행은 "첫 관측"이라 알림이 없고, 다음 실행부터 하락 감지 시 알림이 옵니다.

---

## 로컬에서 테스트하기 (선택)

```bash
pip install -r requirements.txt
cp .env.example .env          # .env 열어서 값 4개 채우기
python main.py test           # 텔레그램 연결 확인 (테스트 메시지 1건)
python main.py                # 실제 1회 조회 실행
```

---

## 커스터마이징

- **감시 모델 추가/변경**: `config.json` 의 `models` 배열 수정
  - `query`: 네이버쇼핑 검색어
  - `include_keywords`: 제목에 **모두** 포함돼야 하는 단어(엉뚱한 모델 방지)
  - `exclude_keywords`: 있으면 제외(케이스/중고/리퍼 등)
  - `min_price`/`max_price`: 액세서리·오탐 걸러내는 가격 범위
- **하락 임계치 변경**: `config.json` 의 `drop_threshold` (0.10 = 10%)
- **실행 시각 변경**: `.github/workflows/monitor.yml` 의 `cron` (UTC 기준. KST-9시간)
  - 예: 하루 3회(08·14·22시 KST) → `0 23,5,13 * * *`

---

## 참고 / 한계
- 다나와는 공식 API가 없어 HTML 구조 변경 시 보조 조회가 실패할 수 있습니다(메인은 네이버라 문제 없음).
- "이전 관측 대비" 하락이라, 완만하게 조금씩 내리면(매회 10% 미만) 알림이 안 뜰 수 있습니다.
  급락/특가 캐치가 목적이라 이렇게 설계했고, 메시지에 **역대최저가**를 함께 표기해 판단을 돕습니다.
- GitHub Actions 크론은 트래픽에 따라 수 분~수십 분 지연될 수 있습니다(알림 용도엔 무방).
