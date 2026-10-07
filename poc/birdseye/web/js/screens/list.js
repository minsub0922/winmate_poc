// BE0 — 작업 목록 · 2D / 3D 유형 선택
import { api, library } from "../api.js";
import { h, icon, replace, when, menu, toast, confirmBox, aitag } from "../dom.js";
import { frame, go, link2d, link3d, openProject } from "../shell.js";
import { miniPlan } from "../plan.js";

const STEP2D = { space: [1, "공간 · 치수"], plan: [1, "도면 인식"], products: [2, "제품 · 수량"], layout: [3, "배치 · 동선"], done: [4, "완성"] };

export async function mount() {
  const fr = frame({ title: "작업 목록" });
  const [lib, data] = await Promise.all([library(), api.get("/api/projects")]);
  const stLabel = Object.fromEntries(lib.space_types.map(s => [s.code, s.label]));
  let items = data.items;
  let filter = "all", q = "", sort = "updated";

  const body = h("div", {});
  fr.content.append(body);

  async function create(kind, then) {
    const p = await api.post("/api/projects", { kind });
    go(kind === "2d" ? link2d(p.id, then || "space") : link3d(p.id, then || "brief"));
  }

  const status = p => {
    const s = p.summary || {};
    if (p.kind === "2d") {
      if (p.status === "done") return { text: "완료", sub: `${s.kinds || 0}종 ${s.total || 0}대 · 존 ${s.zones || 0} · ${s.warnings ? `경고 ${s.warnings}` : "검토 완료"}${s.memos ? ` · 메모 ${s.memos}` : ""}`, pct: 100, need: !!s.warnings };
      const [n, nm] = STEP2D[p.step] || [1, "공간 · 치수"];
      return { text: `${n}/4 · ${nm}`, sub: s.warnings ? `경고 ${s.warnings}` : (s.total ? `${s.kinds}종 ${s.total}대` : ""), pct: n * 25, need: !!s.warnings };
    }
    if ((p.jobs || []).length) return { text: "렌더링 중", sub: `${p.jobs[0]}%`, pct: p.jobs[0] };
    if (p.status === "needs_check") return { text: "확인 필요", sub: p.has_photo_read ? "현장 사진 읽음 · 요구사항 확인" : "요구사항 확인", pct: 33, need: true };
    if (s.renders) return { text: "완료", sub: `컷 ${s.renders}` + (s.concept ? ` · ${s.concept}` : ""), pct: 100 };
    if (p.status === "failed") return { text: "렌더 실패", sub: "다시 시도해 주세요", pct: 66, need: true };
    return { text: "1/3 · 요구사항", sub: "아직 렌더 없음", pct: 33 };
  };
  const counts = () => ({
    all: items.length, "2d": items.filter(p => p.kind === "2d").length, "3d": items.filter(p => p.kind === "3d").length,
    prog: items.filter(p => status(p).pct < 100 && !status(p).need).length, need: items.filter(p => status(p).need).length,
    done: items.filter(p => status(p).pct === 100 && !status(p).need).length,
  });
  const pass = p => {
    const st = status(p);
    if (filter === "2d" && p.kind !== "2d") return false;
    if (filter === "3d" && p.kind !== "3d") return false;
    if (filter === "prog" && !(st.pct < 100 && !st.need)) return false;
    if (filter === "need" && !st.need) return false;
    if (filter === "done" && !(st.pct === 100 && !st.need)) return false;
    if (q) { const hay = `${p.title} ${p.customer || ""} ${p.space_name || ""} ${stLabel[p.space_type] || ""}`.toLowerCase(); if (!hay.includes(q.toLowerCase())) return false; }
    return true;
  };

  function rowMenu(anchor, p) {
    const its = [{ label: "열기", icon: "arrowR", run: () => openProject(p) }];
    if (p.kind === "3d") {
      its.push({ label: "시점 · 조명 컷 추가", icon: "camera", run: () => go(link3d(p.id, "cuts")), disabled: !(p.summary || {}).renders });
      its.push({ label: "다른 안 만들기", icon: "refresh", run: () => go(link3d(p.id, "result") + "?alt=1"), disabled: !(p.summary || {}).renders });
      if (p.linked_2d) its.push({ label: "2D 조감도 열기", icon: "plan", hint: "연결됨", run: () => go(link2d(p.linked_2d, "done")) });
      its.push({ label: "내보내기 · 제안서로", icon: "download", run: () => go(link3d(p.id, "export")), disabled: !(p.summary || {}).renders });
    } else {
      its.push({ label: "이 배치로 3D 조감도 만들기", icon: "cube", run: async () => { const p3 = await api.post(`/api/projects/${p.id}/to3d`); go(link3d(p3.id, "brief")); }, disabled: !(p.summary || {}).total });
      its.push({ label: "내보내기 · 제안서로", icon: "download", run: () => go(link2d(p.id, "export")), disabled: !(p.summary || {}).total });
    }
    its.push({ label: "복제해서 새 안", icon: "copy", run: async () => { await api.post(`/api/projects/${p.id}/duplicate`); toast("복제했어요"); reload(); } });
    its.push("-");
    its.push({ label: "삭제", icon: "trash", danger: true, run: async () => {
      if (await confirmBox("작업 삭제", `'${p.title}' 작업과 렌더 이미지를 지워요. 되돌릴 수 없어요.`, "삭제", "primary")) { await api.del(`/api/projects/${p.id}`); reload(); }
    } });
    menu(anchor, its);
  }

  function thumb(p) {
    if (p.kind === "2d") return h("div", { class: "thumbmini" }, miniPlan(p.mini, 92, 52));
    return h("div", { class: "thumbmini" }, p.thumb ? h("img", { src: p.thumb, alt: "", loading: "lazy" }) : h("div", { style: { display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--faint)" } }, icon("cube", 18)));
  }

  function draw() {
    const c = counts();
    const list = items.filter(pass).sort((a, b) => sort === "name" ? a.title.localeCompare(b.title, "ko") : (b.updated_at || "").localeCompare(a.updated_at || ""));
    const chip = (key, label) => h("button", { class: "chip" + (filter === key ? " on" : ""), onclick: () => { filter = key; draw(); } }, label, h("span", { class: "cnt" }, c[key]));
    const lastRender = items.find(p => p.kind === "3d" && p.thumb);
    const last2d = items.find(p => p.kind === "2d" && p.mini && p.mini.items && p.mini.items.length);
    replace(body,
      h("div", { class: "page-h" },
        h("div", {}, h("div", { class: "row", style: { alignItems: "baseline", gap: "10px" } }, h("h1", {}, "조감도 작업"), h("span", { class: "num b muted" }, items.length)),
          h("div", { class: "muted small", style: { marginTop: "4px" } }, "정확한 배치 · 수량은 2D, 공간 분위기는 3D로 만드세요.")),
        h("div", { class: "spacer" }),
        h("button", { class: "btn ghost sm", title: "샘플 작업 4개를 처음 상태로 다시 만들어요", onclick: async () => {
          if (!await confirmBox("샘플 다시 만들기", "샘플 작업 4개(2D 로비 · 2D 병원 · 3D 로비 · 3D 관제실)를 처음 상태로 되돌려요. 내가 만든 작업은 그대로예요.", "다시 만들기")) return;
          await api.post("/api/samples", { force: true }); toast("샘플을 다시 만들었어요"); reload();
        } }, icon("refresh", 13), "샘플 다시 만들기")),
      h("div", { class: "startcards" },
        h("div", { class: "card startcard" },
          h("div", { class: "thumb" }, last2d ? miniPlan(last2d.mini, 168, 150) : null),
          h("div", { class: "col grow", style: { gap: "0" } },
            h("div", { class: "row" }, h("span", { class: "tag k2d" }, "2D"), h("span", { class: "small muted" }, "정확한 배치 · 수치")),
            h("h2", { style: { marginTop: "6px" } }, "2D 조감도"),
            h("p", { class: "lead" }, "도면과 실측 치수로 제품 위치 · 수량 · 동선을 직접 정해요. 수량표와 견적의 근거가 돼요."),
            h("div", { class: "meta" }, "직접 편집 · 결과: 배치 도면 · 수량표"),
            h("div", { class: "spacer" }),
            h("div", { class: "row", style: { marginTop: "12px" } },
              h("button", { class: "btn primary", onclick: () => create("2d", "space") }, "2D로 시작", icon("arrowR")),
              h("button", { class: "btn", onclick: () => create("2d", "plan") }, icon("upload"), "도면 올려서")))),
        h("div", { class: "card startcard" },
          h("div", { class: "thumb", style: { background: "#d8dde6" } }, lastRender ? h("img", { src: lastRender.thumb, alt: "", style: { width: "100%", height: "100%", objectFit: "cover" } }) : null,
            h("div", { style: { position: "absolute", left: "8px", top: "8px" } }, aitag())),
          h("div", { class: "col grow", style: { gap: "0" } },
            h("div", { class: "row" }, h("span", { class: "tag k3d" }, "3D"), h("span", { class: "small muted" }, "공간 분위기 · 개략")),
            h("h2", { style: { marginTop: "6px" } }, "3D 조감도"),
            h("p", { class: "lead" }, "요구사항만 적으면 AI가 인테리어 · 가구를 고르고 배치해 렌더링해요. 편집은 시점 · 조명 정도."),
            h("div", { class: "meta" }, "AI 자동 구성 (Blender) · 결과: 렌더 이미지"),
            h("div", { class: "spacer" }),
            h("div", { class: "row", style: { marginTop: "12px" } },
              h("button", { class: "btn primary", onclick: () => create("3d", "brief") }, "3D로 시작", icon("arrowR")),
              h("button", { class: "btn", onclick: () => create("3d", "photos") }, icon("camera"), "현장 사진으로"))))),
      h("div", { class: "filters" },
        chip("all", "전체"), chip("2d", "2D"), chip("3d", "3D"), chip("prog", "진행 중"), chip("need", "확인 필요"), chip("done", "완료"),
        h("div", { class: "spacer" }),
        h("label", { class: "search" }, icon("search", 14), h("span", { class: "sr" }, "작업 검색"),
          h("input", { placeholder: "작업 · 고객사 · 공간 검색", value: q, oninput: e => { q = e.target.value; drawTable(); } })),
        h("select", { class: "sel sm", "aria-label": "정렬", onchange: e => { sort = e.target.value; drawTable(); } },
          h("option", { value: "updated", selected: sort === "updated" }, "최근 수정순"), h("option", { value: "name", selected: sort === "name" }, "이름순"))),
      tableBox);
    drawTable(list);
  }
  const tableBox = h("div", { class: "card", style: { overflow: "hidden" } });
  function drawTable() {
    const list = items.filter(pass).sort((a, b) => sort === "name" ? a.title.localeCompare(b.title, "ko") : (b.updated_at || "").localeCompare(a.updated_at || ""));
    if (!list.length) { replace(tableBox, h("div", { class: "empty" }, items.length ? "조건에 맞는 작업이 없어요" : "아직 작업이 없어요 — 위에서 2D 또는 3D로 시작해 보세요")); return; }
    replace(tableBox, h("table", { class: "tbl" },
      h("thead", {}, h("tr", {}, h("th", {}, "작업"), h("th", {}, "유형"), h("th", {}, "진행 상태"), h("th", {}, "쓰인 곳"), h("th", {}, "수정"), h("th", {}, ""))),
      h("tbody", {}, list.map(p => {
        const st = status(p);
        const used = [];
        if (p.linked_2d) used.push(h("span", { class: "tag" }, "2D와 연결"));
        const linked3d = items.filter(x => x.linked_2d === p.id);
        if (linked3d.length) used.push(h("span", { class: "tag" }, `3D ${linked3d.length}개 연결`));
        if (p.proposal) used.push(h("span", { class: "small muted ellipsis", style: { maxWidth: "200px", display: "inline-block", verticalAlign: "middle" }, title: p.proposal }, `제안서 · ${p.proposal}`));
        const actLabel = st.need ? "확인" : st.pct < 100 ? "이어서" : "열기";
        return h("tr", { class: "click", onclick: e => { if (!e.target.closest("button")) openProject(p); } },
          h("td", {}, h("div", { class: "row", style: { gap: "12px" } }, thumb(p),
            h("div", { style: { minWidth: 0 } }, h("div", { class: "projname ellipsis" }, p.title, p.sample ? h("span", { class: "tag", style: { marginLeft: "6px" } }, "샘플") : null),
              h("div", { class: "small muted ellipsis" }, [p.customer, stLabel[p.space_type] || p.space_type].filter(Boolean).join(" · "))))),
          h("td", {}, h("span", { class: "tag " + (p.kind === "2d" ? "k2d" : "k3d") }, p.kind.toUpperCase())),
          h("td", {}, h("div", { class: "prog" }, h("div", { class: "bar2" }, h("i", { style: { width: st.pct + "%" } })), h("span", { class: "b small" }, st.text)),
            st.sub ? h("div", { class: "xs muted", style: { marginTop: "2px" } }, st.sub) : null),
          h("td", {}, used.length ? h("div", { class: "row", style: { flexWrap: "wrap", gap: "4px" } }, used) : h("span", { class: "faint small" }, "아직 없음")),
          h("td", { class: "small muted nowrap" }, when(p.updated_at)),
          h("td", { class: "r nowrap" }, h("button", { class: "btn sm" + (st.need ? " outline" : ""), onclick: () => openProject(p) }, actLabel),
            h("button", { class: "iconbtn ghost", "aria-label": "더 보기", "data-pop-anchor": "", onclick: e => rowMenu(e.currentTarget, p), style: { marginLeft: "4px" } }, icon("more", 16, 3))));
      }))));
  }
  async function reload() { items = (await api.get("/api/projects")).items; draw(); }
  draw();
  const t = setInterval(() => { if (items.some(p => (p.jobs || []).length)) reload(); }, 4000);
  return { unmount: () => clearInterval(t) };
}
