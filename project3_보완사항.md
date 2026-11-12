# project3 보완 사항 (학원에서 수정용)

> - 대상: `ft/congestion-page` 브랜치의 "버스 이용수요" 화면 (`/admin/congestion`)과 관련 API
> - 이 문서는 **git 저장소 밖**에 있습니다 (커밋하지 마세요).
> - 아래 코드 조각은 **예시**입니다. 실제로 실행해 보며 만든 것이 아니라서 학원 환경에서 테스트하며 맞춰야 합니다.
> - 줄 번호는 이 브랜치(`fa7f386`) 기준이며 코드가 바뀌면 달라집니다. 파일·함수 이름으로 찾으세요.
> - 이 브랜치는 `rabo1226` 님의 작업 브랜치이고 dev보다 4커밋 뒤처져 있습니다. 수정은 **별도 브랜치**(예: `ft/security-fix`)에서 하세요.

---

## 0. 작업 전에

| 확인 | 내용 |
|---|---|
| 브랜치 | dev를 먼저 최신화하고, 필요하면 이 브랜치에 dev를 병합해서 충돌부터 확인 (dev에 11/6 디자인 개편이 있음) |
| 실행 환경 | MariaDB(DB `project-3`), 웹(8080), 예측 서버(8000). 예측 서버 키(`application.yaml`의 `py.api.key`)와 `ai_service/.env`의 `PREDICT_API_KEY`가 **같아야** 함 |
| 예측 가능 기간 | 예측 모델은 **2026-12-03까지**만 예측함 (`http://127.0.0.1:8000/health`의 `warnings`로 확인) |
| Gradle 오류 | `Failed to clean up stale outputs`가 나면 `./gradlew --stop` 후 다시 `./gradlew bootRun` (OneDrive 폴더에서 자주 생김) |

---

## 1. 보안 (우선순위 순)

### 1-1. 관리자 확인이 없는 API 3개 ★ 가장 먼저

| 파일 | 메서드 | 문제 |
|---|---|---|
| `controller/AdminApiController.java` | `routes()` (`GET /admin/api/routes`) | 관리자 확인 없음 |
| 같은 파일 | `geometry()` (`GET /admin/api/routes/{routeNo}/geometry`) | 관리자 확인 없음 |
| 같은 파일 | `road()` (`GET /admin/api/routes/{routeNo}/road`) | **카카오 일 한도(1,000건)를 소모**하는데 로그인 없이 호출 가능. 코드 주석에도 "로그인 구현 후 관리자만 부를 수 있게 해야 함"이라고 남아 있음 |

같은 파일의 다른 API(`priority`, `report-counts`)가 이미 쓰는 방식을 그대로 적용합니다.

```java
@GetMapping(value = "/routes/{routeNo}/road", produces = MediaType.APPLICATION_JSON_VALUE)
public ResponseEntity<Object> road(@PathVariable String routeNo, @RequestParam int brtId, HttpSession session) {
    if (AdminUtil.checkAdmin(session) != null) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
            .body(new ApiError("FORBIDDEN", "관리자만 사용할 수 있습니다."));
    }
    // ... 기존 코드
}
```

`routes()`는 반환 타입이 `String`이라 `ResponseEntity<Object>`로 바꿔야 할 수 있습니다. 세 메서드 모두 매개변수에 `HttpSession session`을 추가합니다.

**확인 방법**
1. 로그아웃(또는 시크릿 창) 상태에서 `http://localhost:8080/admin/api/routes`를 열면 403이 나와야 함
2. 관리자로 로그인한 상태에서 `/admin/congestion`의 지도와 도로 선이 예전처럼 나와야 함
3. 화면 JS(`dashboard_map.js`)가 403을 만났을 때 오류 안내를 내는지 확인 (도로 선은 실패하면 직선으로 대체되는 구조)

### 1-2. 관리자 AI 호출 제한이 없음

시민용 AI(`ReportApiController`의 `refine`, `suggest`)에는 **세션당 5초 간격 제한**이 있는데, `AdminAiController`(`/admin/api/ai/insight`, `/ask`, `/route`)에는 없습니다. Gemini 한도(분당 15회, 하루 500회)는 시민용과 **같은 프로젝트에서 공유**합니다.

`AdminAiController.java`에서 관리자 확인 바로 뒤에, 시민용과 같은 방식으로 넣습니다.

```java
private static final String AI_TIME_KEY = "adminAiLastCall";
private static final long AI_COOLDOWN_MILLIS = 3000;   // 값은 팀에서 조정

// 각 엔드포인트의 checkAdmin 확인 다음에
long now = System.currentTimeMillis();
Long last = (Long) session.getAttribute(AI_TIME_KEY);
if (last != null && now - last < AI_COOLDOWN_MILLIS) {
    return fail(HttpStatus.TOO_MANY_REQUESTS, "잠시 후 다시 시도해 주세요.");
}
session.setAttribute(AI_TIME_KEY, now);
```

- 한계: 세션 단위라서 계정·세션을 여러 개 쓰면 우회됩니다. 전체 합계 제한이 필요하면 별도 작업(분당 12회 정도, 한도 15에 여유 3)을 합니다.
- 화면은 이미 서버가 준 `message`를 그대로 보여주는 구조(`callAi`)라서 문구 처리는 추가로 필요 없습니다.

**확인 방법**: AI 분석 버튼을 연달아 눌러 429 안내 문구가 나오는지.

### 1-3. 로그인 후 세션 재발급 없음 (세션 고정)

`MemberController`의 로그인 처리에서 `session.setAttribute("loginInfo", loginInfo)`만 하고 세션 ID를 바꾸지 않습니다.

```java
// 로그인 성공 직후, loginInfo를 저장하기 전에
request.changeSessionId();   // 메서드 매개변수에 HttpServletRequest request 추가
session.setAttribute("loginInfo", loginInfo);
```

`changeSessionId()`는 세션 속성을 유지하므로, "로그인 후 원래 가려던 화면으로 이동"(`LoginRedirectUtil`)이 세션에 저장해 둔 주소는 그대로 남습니다. 위험도는 낮은 편입니다 (`tracking-modes: cookie`라 주소에 세션 ID가 붙지 않음).

**확인 방법**: 개발자 도구(Application → Cookies)에서 로그인 전후로 `JSESSIONID` 값이 바뀌는지, 로그인 후 원래 가려던 화면으로 이동하는지.

### 1-4. CSRF 방어 없음

토큰이나 `Origin` 검사가 코드 어디에도 없습니다. 영향받는 요청은 관리자 POST 전체(`/admin/route/add`, `/edit`, `/delete`, `/admin/report/{no}`, `/admin/api/ai/*`)입니다. 최신 Chrome은 `SameSite`가 없는 쿠키를 기본으로 `Lax`로 취급해 대부분 막아 주지만, **설정으로 보장된 것이 아니라 브라우저에 의존**합니다.

**단계 1 (가장 간단)**: `application.yaml`에 쿠키 설정을 명시합니다. (이 파일은 gitignore라 직접 수정)

```yaml
server:
  servlet:
    session:
      tracking-modes: cookie
      cookie:
        same-site: lax
        http-only: true
```

**단계 2 (권장)**: 변경 요청(POST/PUT/DELETE)이 같은 출처에서 왔는지 `Origin`을 확인하는 인터셉터를 `WebConfig`에 등록합니다. 예시입니다(실행 검증 안 됨).

```java
public class SameOriginInterceptor implements HandlerInterceptor {
    @Override
    public boolean preHandle(HttpServletRequest req, HttpServletResponse res, Object handler) throws IOException {
        String m = req.getMethod();
        if (m.equals("GET") || m.equals("HEAD") || m.equals("OPTIONS")) return true;
        String origin = req.getHeader("Origin");
        if (origin == null) return true;                     // Origin을 안 보내는 요청은 통과 (필요하면 Referer로 대체)
        String self = req.getScheme() + "://" + req.getHeader("Host");
        if (origin.equals(self)) return true;
        res.sendError(HttpServletResponse.SC_FORBIDDEN, "허용되지 않은 요청 출처입니다.");
        return false;
    }
}

// WebConfig.java
@Override
public void addInterceptors(InterceptorRegistry registry) {
    registry.addInterceptor(new SameOriginInterceptor()).addPathPatterns("/admin/**", "/api/**");
}
```

**확인 방법**: 화면에서 노선 추가·신고 처리·AI 호출이 정상 동작하는지(같은 출처는 통과해야 함), 다른 출처에서 만든 폼으로 POST하면 403이 나는지.

### 1-5. 세션 만료 시간 명시

`setMaxInactiveInterval`과 yaml의 `server.servlet.session.timeout` 설정이 모두 없어 서버 기본값(보통 30분)에 의존합니다. 발표·운영 기준으로 원하는 값을 yaml에 명시하세요.

```yaml
server:
  servlet:
    session:
      timeout: 30m
```

---

## 2. 여러 접속자가 동시에 쓸 때 (선택, 지금은 손대지 않기로 함)

| 항목 | 현황 | 수정 방향 |
|---|---|---|
| AI 분석 전역 잠금 | `AiService`의 `analyzeRoute`, `getInsight`가 `synchronized`라 Gemini 호출(최대 30초) 동안 **다른 관리자의 분석이 모두 대기** | 키별 진행 중 요청 공유(`ConcurrentHashMap<키, CompletableFuture>`) + 캐시 만료(TTL). 잠금을 걷어내면 캐시용 `HashMap`을 `ConcurrentHashMap`으로 반드시 교체 |
| 신고 상태 변경 경합 | `AdminService`가 "현재 상태 읽기 → 되돌림 검사 → `UPDATE`" 순서이고 `UPDATE`에 현재 상태 조건이 없음. 두 관리자가 동시에 처리하면 `완료 → 처리중`으로 되돌아가거나 답변이 덮어써질 수 있음 | `UPDATE ... WHERE REPORT_NO=? AND STATUS=#{읽은 상태}`로 바꾸고 영향 행이 0이면 "다른 관리자가 먼저 처리했습니다" 반환 |
| 예측 서버 호출 | 캐시 없이 노선 클릭마다 호출 | 짧은 TTL 캐시 (효과 작음) |

이미 잘 되어 있는 것: 화면의 응답 순서 꼬임 방지(요청 번호), 예측 서버 호출 시간 제한, 파이썬 쪽 모델 교체 잠금.

---

## 3. 화면 디자인 (발표용 PC 기준)

1366×800, 1280×720, 1024×768, 1920×1080에서 측정한 결과입니다.

| 해상도 | 예측 카드 높이 / 내용 높이 | 일별 차트 | 시간대별 차트 | 잘린 설명 글 |
|---|---|---|---|---|
| 1920×1080 | 383 / 736px | 보임 | **스크롤해야 보임** | 1개 |
| 1366×800 | 271px | 맨 아래 걸침 | **스크롤해야 보임** | 2개 |
| 1280×720 | 243 / 789px | **스크롤해야 보임** | **스크롤해야 보임** | 2개 |
| 1024×768 | 258 / 914px | **스크롤해야 보임** | **스크롤해야 보임** | 2개 |

| 순위 | 항목 | 내용 | 수정 방향 |
|---|---|---|---|
| 1 | **예측 카드 높이** | 핵심 차트(특히 시간대별)가 작은 카드 안 스크롤에 가려짐 | 지도/예측 높이 비율 조정, 일별/시간대별 탭 또는 접기, 카드 최소 높이 |
| 2 | **노선 설명 글 넘침** | 노선 설명 `small`이 `white-space: nowrap`이라 칸 폭(199px)보다 글이 길어(214px) 버튼 밖으로 넘치고 목록에 1px 가로 스크롤이 생김 (`congestion.css`의 `.route-btn small`) | 줄바꿈 허용 또는 말줄임(…) + `title`로 전체 표시. 목록 패널이 300px 고정이라 해상도와 무관하게 발생 |
| 3 | 노선 색 | 134번 주황 / 115번 빨강 / 215번 분홍이 비슷하고 색약에서 구분 어려움. "미처리" 배지도 빨강이라 빨강 노선과 의미가 겹침. 프로젝터는 색 재현이 약해 더 흐려질 수 있음 | 색약 안전 팔레트로 교체(`colorOf`), 빨강 계열 제외, 비교 노선은 선 모양(점선)으로도 구분 |
| 4 | 목록 제목 가려짐 | 노선 선택 시 "노선 목록" 제목이 위로 밀려 일부 잘림 (재현 조건은 아직 정확히 모름) | 제목 고정(sticky) 또는 선택 항목을 `scrollIntoView({block:'nearest'})` |
| 5 | 선택 전 체크 칸의 빈 공간 | 코드 주석상 **의도된 설계**("자리는 늘 차지해서 목록이 밀리지 않음") | 작성자 의도 확인 후 결정 |
| 낮음 | 모바일 헤더·탭 한글 중간 줄바꿈, 모바일에서 지도가 목록 아래 | 발표를 PC로 하면 우선순위 낮음. 헤더·탭은 `admin_layout` 공통이라 다른 관리자 화면에도 영향 | `word-break: keep-all`, `white-space: nowrap`, 탭 가로 스크롤 |

- **확인 필요**: 발표용 PC의 실제 **해상도와 Windows 화면 배율** (1920×1080에 배율 150%면 실제로는 1280×720처럼 보임).
- **임시 대처**: 브라우저 배율을 75~80%로 줄이면(Ctrl + 마이너스) 시간대별 차트가 보일 가능성이 높음 (발표 PC에서 직접 확인).
- dev의 디자인 개편(`admin_tokens.css` 등)을 병합하면 위 측정값이 달라질 수 있으니 **병합 후 다시 측정**하세요.

---

## 4. 수정 후 점검 체크리스트

- [ ] 로그아웃 상태에서 `/admin/api/routes`, `/geometry`, `/road`가 403
- [ ] 로그인 후 지도·도로 선·예측·AI 분석이 정상
- [ ] AI 버튼 연타 시 429 안내 문구
- [ ] 로그인 전후 `JSESSIONID`가 바뀌고, 로그인 후 원래 화면으로 이동
- [ ] 노선 추가·수정·삭제와 신고 처리가 정상 (SameOrigin 인터셉터 적용 시)
- [ ] 발표용 PC 해상도에서 시간대별 차트가 보이는지
- [ ] `git status`에 `application.yaml`, `.env`, 이 문서가 올라오지 않았는지
