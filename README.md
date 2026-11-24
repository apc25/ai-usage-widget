# AI Usage Widget

Windows 11 작업표시줄 왼쪽 빈 공간에 Claude / ChatGPT 사용량을 원형 그래프로 띄우는 위젯.

사용량 데이터는 Chrome 확장 [AI Usage Monitor](https://github.com/apc25/ai-usage-monitor)가 가져온다.
확장이 5분마다 가져온 결과를 사이드 패널과 이 위젯에 동시에 넘긴다. 사이트 호출은 한 번이다.

## 표시
- Claude: 5h / 7d / 7d model-scoped(API가 주는 모델명) · ChatGPT: 5h / 7d
- 원 안 숫자는 사용률(%). 색: 70% 미만 초록, 70~90% 노랑, 90% 이상 빨강
- 마우스를 올리면 리셋까지 남은 시간과 마지막 갱신 시각이 뜬다
- 마지막 갱신이 15분 넘게 지나면 흐리게 표시

## 동작 방식
위젯은 주 모니터 작업표시줄(`Shell_TrayWnd`)의 자식 창으로 붙는다.
- 별도 "항상 위" 창으로 겹쳐 띄우면, 시작 메뉴를 한 번 연 뒤로 작업표시줄이 더 높은 층으로 올라가서 위젯을 덮는다. 자식 창은 작업표시줄의 일부로 그려져서 이 문제가 없다.
- 전체화면 앱이나 작업표시줄 자동 숨기기로 작업표시줄이 가려지면 위젯도 같이 가려진다.
- 툴팁과 우클릭 메뉴는 작업표시줄과 겹치지 않게 작업표시줄 바로 위에 띄운다.
- 탐색기(explorer)가 재시작되면 위젯이 스스로 다시 실행해서 새 작업표시줄에 붙는다.

## 조작
- 왼쪽 드래그: 작업표시줄 안에서 가로 위치 이동
- 우클릭: 배경 투명도(0~100%), 원 크기, 표시 항목, 라벨 표시, 위치 초기화, 종료

설정은 `%LOCALAPPDATA%\AIUsageWidget\settings.json`에 저장된다.

## 요구 사항
- Windows 11, Python 3.10+ (PySide6)
- Chrome에 AI Usage Monitor 확장(압축해제)이 로드돼 있을 것

## 설치
기본값으로 이 폴더 옆의 `AI-Usage-Monitor` 폴더를 확장 위치로 본다.
```
powershell -ExecutionPolicy Bypass -File install.ps1
```
- 확장 ID는 Chrome 프로필에서 확장 폴더 경로로 찾는다. 못 찾으면 `-ExtensionId <id>`로 지정(`chrome://extensions`에서 확인).
- Chrome이 실행할 전달 프로그램을 등록한다. 레지스트리 `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.apc25.ai_usage_widget`에 등록되고, 관련 파일은 `%LOCALAPPDATA%\AIUsageWidget`에 만들어진다.
- 시작프로그램 폴더에 `AI Usage Widget` 바로가기를 만들고, 위젯을 바로 실행한다.
- 설치 후 `chrome://extensions`에서 확장을 새로고침하면 확장이 위젯에 연결된다.
- 확장 폴더나 이 폴더를 옮기면 다시 실행해야 한다. 압축해제 확장의 ID는 폴더 경로에서 정해지기 때문이다.

제거: `powershell -ExecutionPolicy Bypass -File uninstall.ps1` (설정 파일은 남김)

## 구성
```
host/host.py      Chrome이 실행하는 전달 프로그램. 확장 → usage.json, 위젯 새로고침 요청 → 확장
widget/main.py    위젯 화면
widget/winapi.py  작업표시줄 핸들, 테마, 전달 프로그램 연결 확인·새로고침 요청
dev/              개발용 가짜 데이터
```
위젯은 전달 프로그램이 실행 중인지(= Chrome 확장이 연결돼 있는지)를 이름 있는 Windows 이벤트 `Local\AIUsageWidget.Refresh`의 존재로 판단한다. 연결이 없으면 원을 흐리게 표시하고, 새로고침 메뉴를 막는다. 새로고침은 30초에 한 번까지만 된다.

## 문제 해결: 위젯에 "Chrome 연결 안 됨"
원이 흐리고 툴팁에 "Chrome 연결 안 됨"이 뜨면, 아래를 위에서부터 확인한다.
1. **Chrome이 꺼져 있음** → Chrome을 켜면 확장이 시작되면서 바로 연결된다.
2. **확장 코드(`manifest.json`, `background.js`)를 바꾼 뒤** → 확장이 옛 코드로 돌고 있다.
   `chrome://extensions`에서 🔄를 누르고, 그래도 안 되면 확장을 **삭제한 뒤 압축해제 확장으로 다시 로드**한다.
   🔄로는 반영이 안 되고 삭제 후 다시 로드해서 해결된 경우가 실제로 두 번 있었다.
   자세한 순서는 AI-Usage-Monitor 저장소의 `docs/TROUBLESHOOTING.md` → "🔄 로 반영이 안 될 때".
3. **확장 ID가 바뀜** (다른 폴더에서 로드, 다른 컴퓨터) → `install.ps1`을 다시 실행한다. 같은 폴더를 다시 로드하면 ID는 그대로다.
4. 그래도 안 되면 `%LOCALAPPDATA%\AIUsageWidget\host.log`에 전달 프로그램 오류가 남았는지 본다.

위젯이 `pythonw`(콘솔 없음)로 실행되기 때문에 오류가 화면에 나오지 않는다. 우클릭 메뉴가 안 뜨는 것처럼 동작이 이상하면 `%LOCALAPPDATA%\AIUsageWidget\widget.log`를 먼저 본다.

## 개발용 실행
```
python dev/fake_usage.py          # 가짜 데이터 쓰기 (--stale, --error 옵션)
python widget/main.py
```

## License
MIT License — [LICENSE](LICENSE)

Copyright (c) 2026 apc25

저장소 전체(코드, 문서)에 적용된다. 제3자 자료는 포함돼 있지 않다. 실행에 필요한 PySide6는 저장소에 포함되지 않고 사용자가 따로 설치한다.
