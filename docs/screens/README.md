# 화면 디자인 원본(보드) — 오프라인으로 보기

웹앱 ①②③ 의 claude.ai 아티팩트 보드를 저장소에 그대로 담았다. **사내망처럼 claude.ai 를 열 수 없는 곳에서도 이 폴더만으로 디자인을 본다.**
아티팩트 링크를 열려고 하지 않는다(인증 · 인증서 문제로 실패한다).

| 경로 | 무엇 | 언제 |
|---|---|---|
| `INDEX.md` | 보드 243개 색인(웹앱 · 보드 코드 · 제목 · 기능 서비스). 조감도는 `BP*`(2D) · `BR*`(3D)가 최신안 | 먼저 |
| `_rendered/<webapp>/<보드>.jpg` | 보드를 그린 화면 그림(1440×900 등) | 레이아웃 · 색 · 간격을 볼 때(이미지로 읽는다) |
| `_rendered/<webapp>/<보드>.txt` | 그린 화면의 글자(예시 값이 채워진 상태) | 문구 · 라벨 · 예시 값을 그대로 옮길 때 |
| `webapp*/<보드>.dc.html` | 원본 템플릿 + 예시 데이터(`renderVals`) + 인라인 스타일 | 정확한 px · 색 값이 필요할 때 |
| `_text/` | 원본 템플릿의 글자(값 자리 `{{…}}` 그대로) | 시나리오 문서가 가리키는 옛 경로 |
| `../_blob/<id>` | 보드가 `/_blob/<id>` 로 부르는 이미지(제품 사진 · 생성 예시 · 로고 등 282개, 아티팩트 에셋 사본 · 확장자 없음) | 자동(아래 서버가 `docs/` 를 열면 그대로 보인다) |
| `_runtime/support.js` | 아티팩트 런타임 대체(템플릿 `{{}}` · `sc-for` · `sc-if` · `dc-import` 를 그린다) | — |
| `_runtime/render.mjs` | `_rendered/` 를 다시 만든다(화면 + PPT 템플릿) | 보드를 고쳤을 때 |

PPT 레이아웃 보드(`docs/templates/source/*`, 캔버스 6개 — 05 보강 캔버스는 `cov/`)도 같은 방식으로 `docs/templates/_rendered/<묶음>/<레이아웃>.jpg · .txt` 에 있다.

```bash
# 브라우저로 살아 있는 보드 보기(네트워크 불필요, 포트는 5000번대)
python3 -m http.server 5099 --directory docs
#   http://localhost:5099/screens/webapp1/CA4.dc.html
#   http://localhost:5099/templates/source/mi/L_MI_RT_B.dc.html

# 그림 · 글자 다시 만들기(web/node_modules 의 playwright · Chromium 필요)
node docs/screens/_runtime/render.mjs                    # 전부(약 3분)
node docs/screens/_runtime/render.mjs screens CA4 PR7    # 일부
```

- 이미지: 아티팩트에서 새 이미지를 쓰는 보드를 가져오면 그 에셋도 `docs/_blob/<id>` 로 함께 가져온다(없으면 그 자리가 빈 칸으로 그려진다).
- 글꼴: 보드는 Google Fonts(Noto Sans KR · Manrope)를 부르지만 오프라인이면 로컬 글꼴로 그린다. 글자 폭이 조금 다를 수 있다.
- 상호작용(팝오버 열기 등 `setState`)은 첫 화면만 그린다. 다른 상태는 보통 별도 보드(예 `TopBar` popover=product)로 있다.
- 수용 기준(동작 · 문구 · 오류)은 `docs/scenarios/<번호>-<기능>.md` 가 정본이다. 보드와 다르면 시나리오를 따른다.
