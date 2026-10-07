// UC_BE — 유스케이스 맵(2D와 3D는 목적이 달라 길을 나눴다). 화면 코드를 누르면 샘플 작업의 그 화면으로.
import { h, icon } from "../dom.js";
import { frame } from "../shell.js";

const L2 = "2d-sample-lobby", L3 = "3d-sample-lobby";
const node = (code, name, href) => h(href ? "a" : "div", { class: "ucnode", href }, h("b", {}, code), name);
const arrow = () => h("span", { class: "ucarrow" }, "→");

export async function mount() {
  const fr = frame({ title: "유스케이스 맵" });
  fr.content.append(h("div", { style: { maxWidth: "1180px" } },
    h("div", { class: "page-h" }, h("div", {},
      h("div", { class: "xs muted b", style: { letterSpacing: ".06em" } }, "WINMATE · USE CASE MAP"),
      h("h1", {}, "공간 조감도 생성 — 유스케이스 맵"),
      h("div", { class: "muted small", style: { marginTop: "4px" } }, "2D와 3D는 목적이 달라 만드는 길을 나눴습니다. 화면 코드를 누르면 샘플 작업의 그 화면으로 이동합니다."))),
    h("div", { class: "ucgrid" },
      h("div", { class: "card pad col", style: { gap: "12px" } },
        h("div", { class: "row" }, h("span", { class: "tag k2d" }, "BP"), h("b", {}, "2D 조감도 · 정확한 배치 · 수치 · 수량"), h("span", { class: "small muted" }, "사용자가 직접 편집 · 4단계")),
        h("div", { class: "ucflow" }, node("BP1", "공간 · 치수", `#/2d/${L2}/space`), arrow(), node("BP2", "제품 · 수량", `#/2d/${L2}/products`), arrow(),
          node("BP3", "배치 · 동선", `#/2d/${L2}/layout`), arrow(), node("BP4", "2D 조감도 완성", `#/2d/${L2}/done`), arrow(), node("BP5", "내보내기", `#/2d/${L2}/export`)),
        h("div", { class: "ucflow" }, node("BP1D", "도면 인식 확인", null), node("BP3Z", "존 구획 · 동선 순서", `#/2d/${L2}/zones`),
          h("span", { class: "small muted" }, "BP1D는 새 2D 작업에서 '도면 올려서'로 시작해요"))),
      h("div", { class: "card pad col", style: { gap: "12px" } },
        h("div", { class: "row" }, h("span", { class: "tag k3d" }, "BR"), h("b", {}, "3D 조감도 · 공간 분위기 · 개략"), h("span", { class: "small muted" }, "AI가 Blender로 구성 · 3단계")),
        h("div", { class: "ucflow" }, node("BR1", "요구사항", `#/3d/${L3}/brief`), arrow(), node("BR2", "AI 구성 · 렌더링", `#/3d/${L3}/build`), arrow(),
          node("BR3", "3D 조감도 결과", `#/3d/${L3}/result`), arrow(), node("BR4", "내보내기", `#/3d/${L3}/export`)),
        h("div", { class: "ucflow" }, node("BR1P", "현장 사진으로", "#/3d/3d-sample-control/photos"), node("BR3V", "시점 · 조명 컷", `#/3d/${L3}/cuts`)))),
    h("div", { class: "card pad", style: { marginTop: "14px" } },
      h("div", { class: "card-h" }, h("h3", {}, "두 경로는 무엇이 다른가"), h("span", { class: "sub" }, "같은 공간이라도 쓰임이 다르면 다른 길로 만들어요")),
      h("table", { class: "cmp", style: { marginTop: "8px" } },
        h("tr", {}, h("th", {}, "구분"), h("td", {}, h("b", {}, "2D 조감도"), h("span", { class: "muted" }, " — 사용자가 정해요")), h("td", {}, h("b", {}, "3D 조감도"), h("span", { class: "muted" }, " — AI가 정해요"))),
        h("tr", {}, h("th", {}, "목적"), h("td", {}, "명확한 수치 · 동선 · 제품 개수 등 디테일"), h("td", {}, "'이 공간에서 이런 느낌으로 쓰이겠다'는 개략적 이해")),
        h("tr", {}, h("th", {}, "입력"), h("td", {}, "도면 · 실측 치수 · 제품 · 수량"), h("td", {}, "공간 설명 · 분위기 · 제품 (현장 사진 · 2D 조감도는 선택 참고)")),
        h("tr", {}, h("th", {}, "누가 정하나"), h("td", {}, "사용자가 배치 · 수량을 확정 (AI는 추천 · 경고만)"), h("td", {}, "AI가 요구사항을 분석해 Blender로 인테리어 · 가구 선정 · 배치 · 렌더링")),
        h("tr", {}, h("th", {}, "편집"), h("td", {}, "끌어서 배치, 좌표 · 치수 · 회전, 존 구획, 동선 — 전부"), h("td", {}, "최소한: 시점 · 조명 프리셋, 다른 안 보기, 한 줄 요청, 도입 전 컷 — 가구 / 마감재 개별 편집 없음")),
        h("tr", {}, h("th", {}, "산출물"), h("td", {}, "치수 있는 배치 도면 · 제품 수량표 · 존 구획 · 동선도"), h("td", {}, "렌더 이미지 · 시점별 컷 (항상 'AI 생성 · 개략' 표시)")),
        h("tr", {}, h("th", {}, "제안서로"), h("td", {}, "'공간별 제품' — 공간 맵 SM-A · 수량표 SM-B, '존별 포인트' ZP-A"), h("td", {}, "'조감도' — 공간 전경 BV-A · 두 시점 비교 BV-B")))),
    h("div", { class: "card pad", style: { marginTop: "14px" } },
      h("div", { class: "card-h" }, h("h3", {}, "두 경로 사이"), h("span", { class: "sub" }, "2D → 3D 연결은 선택")),
      h("div", { class: "col", style: { marginTop: "8px", gap: "6px" } },
        h("div", { class: "note" }, h("span", {}, h("b", {}, "이 배치로 3D 조감도 만들기"), " — 2D 완성 · 내보내기 화면에서 시작해요. 제품 위치는 2D 배치 그대로 두고, 인테리어 · 가구 선정 · 렌더링은 AI가 해요.")),
        h("div", { class: "note" }, h("span", {}, h("b", {}, "2D 조감도 연결"), " — 3D 요구사항에서 기존 2D 작업을 고르면 제품 위치가 2D를 따르고, 2D 존 번호는 Blender 카메라로 렌더 위에 표시돼요.")))),
    h("div", { class: "muted small", style: { marginTop: "12px" } }, icon("info", 13), " PRS · SP · SC 같은 다른 기능 화면은 이 PoC 범위 밖이라 버튼만 두고 내보내기 파일(proposal_payload.json)로 넘길 데이터를 보여줘요.")));
}
