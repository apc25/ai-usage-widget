# AI Usage Widget

Claude와 ChatGPT 사용량을 Chrome을 열지 않고도 손쉽게 확인하려고 만든 Windows 11 작업표시줄 위젯.

![작업표시줄 왼쪽에 붙은 위젯](docs/images/widget-taskbar.png)

<img src="docs/images/widget-closeup.png" alt="위젯 확대" width="480">

화면의 숫자는 예시 값이다. 원은 왼쪽부터 Claude 5시간·7일·7일 model-scoped, ChatGPT 5시간·7일이다.

## 설치
사용량은 Chrome 확장 [AI Usage Monitor](https://github.com/apc25/ai-usage-monitor)가 가져온다. 그래서 확장을 먼저 설치해야 한다.

1. AI Usage Monitor 확장을 설치한다. 방법은 그 저장소 README의 "설치"를 따른다.
2. Python 3.10 이상과 PySide6를 설치한다.
   ```
   pip install PySide6
   ```
3. 이 저장소를 확장 폴더와 같은 상위 폴더에 내려받는다.
   ```
   git clone https://github.com/apc25/ai-usage-widget.git
   ```
4. 내려받은 폴더에서 설치 스크립트를 실행한다. 확장 폴더가 다른 곳에 있으면 끝에 `-ExtensionDir <확장 폴더>`를 붙인다.
   ```
   powershell -ExecutionPolicy Bypass -File install.ps1
   ```
5. Chrome 주소창에 `chrome://extensions`를 입력하고, AI Usage Monitor 카드의 🔄(새로고침)를 누른다. 작업표시줄 왼쪽의 위젯이 선명해지면 연결된 것이다.

위젯은 로그인할 때 자동으로 시작한다. 설정 변경과 종료는 위젯을 우클릭해서 한다.
제거는 `powershell -ExecutionPolicy Bypass -File uninstall.ps1`로 한다.

연결이 안 되거나 Python 환경을 바꿨을 때는 [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)를 본다.

## License
MIT License — [LICENSE](LICENSE)

Copyright (c) 2026 apc25

저장소 전체(코드, 문서)에 적용된다. 제3자 자료는 포함돼 있지 않다. 실행에 필요한 PySide6는 저장소에 포함되지 않고 사용자가 따로 설치한다.
