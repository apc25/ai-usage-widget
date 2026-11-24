# AI Usage Widget — Troubleshooting & Reference

설치 방법은 [README](../README.md)를 본다. 이 문서는 표시·조작, 동작 방식, 설치 스크립트가 하는 일, 문제 해결을 모은다.

## 표시
- Claude: 5h / 7d / 7d model-scoped(API가 주는 모델명) · ChatGPT: 5h / 7d
- 원 안 숫자는 사용률(%). 색: 70% 미만 초록, 70~90% 노랑, 90% 이상 빨강
- 마우스를 올리면 리셋까지 남은 시간과 마지막 갱신 시각이 뜬다
- 마지막 갱신이 15분 넘게 지나면 흐리게 표시

## 조작
- 왼쪽 드래그: 작업표시줄 안에서 가로 위치 이동
- 우클릭: 새로고침, 배경 투명도(0~100%), 원 크기, 표시 항목, 라벨 표시, 위치 초기화, 종료

설정은 `%LOCALAPPDATA%\AIUsageWidget\settings.json`에 저장된다.

## 동작 방식
사용량 데이터는 Chrome 확장 [AI Usage Monitor](https://github.com/apc25/ai-usage-monitor)가 가져온다.
확장이 5분마다 가져온 결과를 사이드 패널과 이 위젯에 동시에 넘긴다. 사이트 호출은 한 번이다.

위젯은 주 모니터 작업표시줄(`Shell_TrayWnd`)의 자식 창으로 붙는다.
- 별도 "항상 위" 창으로 겹쳐 띄우면, 시작 메뉴를 한 번 연 뒤로 작업표시줄이 더 높은 층으로 올라가서 위젯을 덮는다. 자식 창은 작업표시줄의 일부로 그려져서 이 문제가 없다.
- 전체화면 앱이나 작업표시줄 자동 숨기기로 작업표시줄이 가려지면 위젯도 같이 가려진다.
- 툴팁과 우클릭 메뉴는 작업표시줄과 겹치지 않게 작업표시줄 바로 위에 띄운다.
- 탐색기(explorer)가 재시작되면 위젯이 스스로 다시 실행해서 새 작업표시줄에 붙는다.

위젯은 전달 프로그램이 실행 중인지(= Chrome 확장이 연결돼 있는지)를 이름 있는 Windows 이벤트 `Local\AIUsageWidget.Refresh`의 존재로 판단한다. 연결이 없으면 원을 흐리게 표시하고, 새로고침 메뉴를 막는다. 새로고침은 30초에 한 번까지만 된다.

## 설치 스크립트가 하는 일
`install.ps1`은 기본값으로 이 폴더 옆의 `AI-Usage-Monitor` 폴더를 확장 위치로 본다.
- 확장 ID는 Chrome 프로필에서 확장 폴더 경로로 찾는다. 못 찾으면 `-ExtensionId <id>`로 지정(`chrome://extensions`에서 확인).
- Chrome이 실행할 전달 프로그램을 등록한다. 레지스트리 `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.apc25.ai_usage_widget`에 등록되고, 관련 파일은 `%LOCALAPPDATA%\AIUsageWidget`에 만들어진다.
- 시작프로그램 폴더에 `AI Usage Widget` 바로가기를 만들고, 위젯을 바로 실행한다.
- 확장 폴더나 이 폴더를 옮기면 다시 실행해야 한다. 압축해제 확장의 ID는 폴더 경로에서 정해지기 때문이다.

`uninstall.ps1`은 위 등록을 모두 지운다. 설정 파일은 남긴다.

## 문제 해결: 위젯에 "Chrome 연결 안 됨"
원이 흐리고 툴팁에 "Chrome 연결 안 됨"이 뜨면, 아래를 위에서부터 확인한다.
1. **Chrome이 꺼져 있음** → Chrome을 켜면 확장이 시작되면서 바로 연결된다.
2. **확장 코드(`manifest.json`, `background.js`)를 바꾼 뒤** → 확장이 옛 코드로 돌고 있다.
   `chrome://extensions`에서 🔄를 누르고, 그래도 안 되면 확장을 **삭제한 뒤 압축해제 확장으로 다시 로드**한다.
   🔄로는 반영이 안 되고 삭제 후 다시 로드해서 해결된 경우가 실제로 두 번 있었다.
   자세한 순서는 AI-Usage-Monitor 저장소의 `docs/TROUBLESHOOTING.md` → "🔄 로 반영이 안 될 때".
3. **확장 ID가 바뀜** (다른 폴더에서 로드, 다른 컴퓨터) → `install.ps1`을 다시 실행한다. 같은 폴더를 다시 로드하면 ID는 그대로다.
4. **Python 환경을 바꾸거나 지운 뒤** → `host.bat`이 없는 Python을 가리킨다. 아래 "Python 환경을 바꿨을 때"를 따른다.
5. 그래도 안 되면 `%LOCALAPPDATA%\AIUsageWidget\host.log`에 전달 프로그램 오류가 남았는지 본다.

위젯이 `pythonw`(콘솔 없음)로 실행되기 때문에 오류가 화면에 나오지 않는다. 우클릭 메뉴가 안 뜨는 것처럼 동작이 이상하면 `%LOCALAPPDATA%\AIUsageWidget\widget.log`를 먼저 본다.

## Python 환경을 바꿨을 때
위젯 바로가기와 전달 프로그램(`host.bat`)에는 설치할 때 쓴 Python 경로가 그대로 들어간다.
Anaconda에서 uv venv로 옮기는 것처럼 Python 환경을 바꾸면, 옛 환경을 지우기 전에 다시 설치한다.

1. 실행 중인 위젯을 끈다(우클릭 → 종료). 켜져 있으면 설치 스크립트가 띄운 새 위젯이 lock 때문에 조용히 종료된다.
2. 새 Python으로 다시 설치한다. 새 Python에 PySide6가 설치돼 있어야 한다.
   ```
   powershell -ExecutionPolicy Bypass -File install.ps1 -Python <새 venv>\Scripts\python.exe
   ```
3. 확장이 새 `host.bat`으로 다시 연결하게 한다. Chrome은 로그인할 때 창 없이 백그라운드로 먼저 뜨고, 창을 모두 닫아도 백그라운드에 남는다.
   그래서 창만 닫았다 다시 열면 옛 Python으로 뜬 전달 프로그램이 계속 연결돼 있다. 아래 중 하나를 한다.
   - `chrome://extensions`에서 확장을 다시 로드한다(🔄, 또는 삭제 후 같은 폴더로 다시 로드). 같은 폴더면 확장 ID가 같아서 `install.ps1`을 다시 돌릴 필요는 없다.
   - Chrome을 완전히 종료(⋮ 메뉴 → 종료, 또는 알림 영역 Chrome 아이콘 → 종료)한 뒤 다시 연다.

   다음 로그인부터는 자동으로 새 `host.bat`이 쓰인다.

### uv venv에서 위젯과 함께 콘솔 창이 뜰 때
uv로 만든 venv(uv 0.10.5에서 확인)는 `Scripts\pythonw.exe`가 `python.exe`와 같은 콘솔용 런처다.
그래서 위젯을 띄우면 콘솔(Windows Terminal) 창이 같이 뜨고, 그 창을 닫으면 위젯도 꺼진다.
venv의 `pythonw.exe`를 기본 Python에 들어 있는 GUI용 venv 런처로 바꾸면 콘솔 없이 뜬다.
```
copy <venv>\Scripts\pythonw.exe <백업 폴더>\pythonw.uv-console-launcher.exe
copy <기본 Python>\Lib\venv\scripts\nt\venvwlauncher.exe <venv>\Scripts\pythonw.exe
```
- `<기본 Python>`은 venv의 `pyvenv.cfg`에 있는 `home` 경로다.
- 바꾸기 전에 위젯을 끈다. 실행 중인 `pythonw.exe`는 덮어쓸 수 없다.
- venv를 다시 만들면 원래 런처로 돌아갈 수 있다. 위젯을 띄울 때 콘솔 창이 다시 보이면 같은 방법으로 바꾼다.

## 구성
```
host/host.py      Chrome이 실행하는 전달 프로그램. 확장 → usage.json, 위젯 새로고침 요청 → 확장
widget/main.py    위젯 화면
widget/winapi.py  작업표시줄 핸들, 테마, 전달 프로그램 연결 확인·새로고침 요청
dev/              개발용 가짜 데이터
docs/             이 문서와 README 화면 이미지(예시 값)
```

## 개발용 실행
```
python dev/fake_usage.py          # 가짜 데이터 쓰기 (--stale, --error 옵션)
python widget/main.py
```
