// 2D 작업 사본 — 되돌리기 · 자동 저장 · 검증(서버 F4)을 한곳에서
import { api } from "./api.js";
import { debounce } from "./dom.js";

export class Doc2D {
  constructor(project) {
    this.p = project;
    this.v = null;
    this.undoStack = [];
    this.redoStack = [];
    this.ls = new Set();
    this.saveState = "saved";
    this.vseq = 0;
    this.saving = null;
    this._save = debounce(() => this._doSave(), 600);
    this._validate = debounce(() => this._doValidate(), 220);
  }
  static async load(id) {
    const p = await api.get(`/api/projects/${id}`);
    if (p.kind !== "2d") throw Object.assign(new Error("2D 작업이 아니에요"), { status: 400 });
    return new Doc2D(p);
  }
  get id() { return this.p.id; }
  on(fn) { this.ls.add(fn); return () => this.ls.delete(fn); }
  emit(what) { for (const f of [...this.ls]) f(what); }
  setSave(st) { this.saveState = st; this.emit("save"); }

  snapshot() { return JSON.stringify(this.p); }
  commit(fn, opts = {}) {
    this.undoStack.push(this.snapshot());
    if (this.undoStack.length > 100) this.undoStack.shift();
    this.redoStack = [];
    fn(this.p);
    this.touch(opts);
  }
  replace(p, opts = {}) {
    this.undoStack.push(this.snapshot());
    this.redoStack = [];
    p.id = this.p.id;
    this.p = p;
    this.touch(opts);
  }
  undo() {
    if (!this.undoStack.length) return false;
    this.redoStack.push(this.snapshot());
    this.p = JSON.parse(this.undoStack.pop());
    this.touch({});
    return true;
  }
  redo() {
    if (!this.redoStack.length) return false;
    this.undoStack.push(this.snapshot());
    this.p = JSON.parse(this.redoStack.pop());
    this.touch({});
    return true;
  }
  touch({ validate = true, save = true, v = null } = {}) {
    if (v) { this.vseq++; this.v = v; }
    this.emit("change");
    if (v) this.emit("validation");
    if (save) { this.setSave("dirty"); this._save(); }
    if (validate && !v) this._validate();
  }
  revalidate() { this._validate(); }
  async validateNow() { this._validate.cancel(); await this._doValidate(); return this.v; }
  async _doValidate() {
    if (!this.p.space) return;
    const my = ++this.vseq;
    try {
      const v = await api.post("/api/2d/validate", { project: this.p }, { quiet: true });
      if (my === this.vseq) { this.v = v; this.emit("validation"); }
    } catch (e) { console.warn("validate", e); }
  }
  async _doSave() {
    this.setSave("saving");
    const body = { project: this.p };
    const run = api.put(`/api/projects/${this.p.id}`, body, { quiet: true }).then(r => {
      this.p.updated_at = r.updated_at; this.p.version = r.version; this.p.summary = r.summary;
      this.setSave(this._save.pending() ? "dirty" : "saved");
    }).catch(e => { console.warn(e); this.setSave("error"); });
    this.saving = run;
    await run;
    this.saving = null;
  }
  async flush() {
    if (this._save.pending()) await this._save.flush();
    else if (this.saving) await this.saving;
  }
  dirty() { return this._save.pending() || !!this.saving; }
  async bump(extra = {}) {
    await this.flush();
    Object.assign(this.p, extra);
    const r = await api.put(`/api/projects/${this.p.id}`, { project: this.p, bump: true });
    this.p.version = r.version; this.p.updated_at = r.updated_at;
    this.setSave("saved");
    return r;
  }
}

// 화면 공통: 저장 상태 표시를 상단 바에 연결
export function bindSave(doc, fr) {
  fr.setSave(doc.saveState);
  return doc.on(w => { if (w === "save") fr.setSave(doc.saveState); });
}
