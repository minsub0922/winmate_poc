"""files API 스키마 — 이 모델들이 contracts/files.json 의 components 가 된다.

- FileMeta: 파일 레코드(바이너리는 blob, 메타는 DocStore). `url` · `thumb_url` 은 게이트웨이 경로.
- ParsedDocument: 문서 파싱 결과(쪽 · 블록 · 표 · 시트 · 메일). 자식 파일(추출 이미지 · 첨부)은 file id 로 가리킨다.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Kind = Literal["pdf", "pptx", "docx", "xlsx", "image", "text", "email", "svg", "zip", "other"]
Source = Literal["upload", "generated", "derived", "export"]
ParseStatus = Literal["none", "pending", "parsing", "done", "failed", "unsupported"]
BlockType = Literal["title", "heading", "body", "list", "table", "image", "note", "caption"]
Cell = str | int | float | bool | None


class ErrorInfo(BaseModel):
    code: str
    message: str


class DocProps(BaseModel):
    """문서 속성(PDF 정보 사전 · OOXML docProps · 메일 머리 · 사진 EXIF). 없는 값은 null."""

    model_config = ConfigDict(extra="allow")

    author: str | None = Field(None, description="작성자(PDF Author · dc:creator · 메일 보낸 사람 · EXIF Artist)")
    title: str | None = None
    subject: str | None = None
    created: str | None = Field(None, description="작성 시각(ISO 8601 UTC). 사진은 촬영 시각")
    modified: str | None = None
    last_modified_by: str | None = None
    producer: str | None = Field(None, description="만든 프로그램(PDF Producer · OOXML Application)")
    company: str | None = None


class FileMeta(BaseModel):
    id: str = Field(description="file_<ULID>")
    name: str = Field(description="파일 이름(NFC 정규화, 경로 제거). HEIC 는 변환 뒤 .jpg")
    mime: str
    size: int = Field(description="바이트 수(저장된 바이너리 기준)")
    sha256: str
    kind: Kind
    source: Source
    confidential: bool
    owner: str = Field(description="올린 사용자 id(X-User-Id)")
    owner_name: str
    project_id: str | None
    parent_id: str | None = Field(description="자식 파일(추출 이미지 · 메일 첨부)이면 원본 file id")
    width: int | None = Field(None, description="이미지 · SVG 가로(px, EXIF 회전 반영)")
    height: int | None = None
    pages: int | None = Field(None, description="쪽 수(PDF 쪽 · PPTX 슬라이드 · XLSX 시트 · DOCX 추정 쪽)")
    meta: dict[str, Any] = Field(default_factory=dict, description="부가 정보(original_mime · exif · encoding · format · depth …)")
    created_at: str
    updated_at: str | None = None
    url: str = Field(description="/api/files/v1/files/{id}/content")
    thumb_url: str = Field(description="/api/files/v1/files/{id}/thumbnail")
    purpose: str | None = Field(None, description="용도 태그(예 rq.source · logo · site_photo)")
    folder: str | None = Field(None, description="공유 폴더 경로(예 'B2B 제안서/A 커피')")
    doc_props: DocProps | None = None
    parse_status: ParseStatus = Field(
        "none", description="none(요청 전) · pending · parsing · done · failed · unsupported. 업로드(source=upload)는 올리자마자 파싱을 시작한다"
    )
    parse_error: ErrorInfo | None = None


class FileList(BaseModel):
    items: list[FileMeta]
    next_cursor: str | None = None


class BytesUpload(BaseModel):
    """서비스 간 저장(내부). 바이트는 base64."""

    name: str = Field(min_length=1, max_length=512)
    mime: str = Field("application/octet-stream", description="모르면 비워 두면 내용으로 판별")
    data_b64: str
    source: Source = "generated"
    confidential: bool = False
    project_id: str | None = None
    meta: dict[str, Any] | None = None
    parent_id: str | None = Field(None, description="원본 file id(주면 confidential · project_id 를 이어받는다)")
    purpose: str | None = None
    folder: str | None = None


class FilePatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=512)
    confidential: bool | None = None
    project_id: str | None = None
    meta: dict[str, Any] | None = Field(None, description="얕은 병합. 값이 null 인 키는 지운다")
    purpose: str | None = None
    folder: str | None = None


class CopyRequest(BaseModel):
    folder: str | None = Field(None, description="복사본을 둘 폴더(예 'B2B 제안서/A 커피')")
    project_id: str | None = None
    name: str | None = Field(None, min_length=1, max_length=512)


class ParseAccepted(BaseModel):
    file_id: str
    parse_status: ParseStatus
    parser_version: str


# ── ParsedDocument ─────────────────────────────────────────────


class Block(BaseModel):
    type: BlockType
    text: str = ""
    bbox: list[float] | None = Field(None, description="[x0, y0, x1, y1] 쪽 크기 대비 0..1(왼쪽 위 원점)")
    level: int | None = Field(None, description="제목 수준(1 = 가장 큼)")
    font_size: float | None = Field(None, description="글자 크기(pt), 알 때만")
    line: int | None = Field(None, description="텍스트 파일의 시작 줄 번호(1부터)")
    file_id: str | None = Field(None, description="image 블록의 추출 이미지 file id")


class PageImage(BaseModel):
    file_id: str
    bbox: list[float] | None = None


class Page(BaseModel):
    no: int = Field(description="1부터")
    text: str = ""
    title: str | None = Field(None, description="쪽 · 슬라이드 제목(추정)")
    blocks: list[Block] = Field(default_factory=list)
    tables: list[list[list[str]]] = Field(default_factory=list)
    image_file_ids: list[str] = Field(default_factory=list)
    images: list[PageImage] = Field(default_factory=list, description="쪽 안 이미지 위치(bbox)")
    notes: str | None = Field(None, description="발표자 노트(PPTX)")
    layout: str | None = Field(None, description="슬라이드 레이아웃 이름(PPTX)")
    hidden: bool | None = Field(None, description="숨긴 슬라이드면 true")
    section: str | None = Field(None, description="PowerPoint 구역 이름")
    size: list[float] | None = Field(None, description="[가로, 세로] pt")


class Sheet(BaseModel):
    name: str
    rows: list[list[Cell]] = Field(description="값(수식은 마지막 계산값). 시트당 2000행까지")
    dims: str | None = Field(None, description="예 A1:F120")
    merged: list[str] = Field(default_factory=list, description="병합 범위(예 A1:C1). 값은 왼쪽 위 칸에만 있다")
    hidden: bool = False
    row_count: int = Field(0, description="읽은 행 수(잘렸으면 truncated)")
    truncated: bool = False


class Attachment(BaseModel):
    name: str
    mime: str
    size: int
    file_id: str | None = None
    inline: bool = False


class EmailInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subject: str | None = None
    from_: str | None = Field(None, alias="from")
    to: list[str] = Field(default_factory=list)
    cc: list[str] = Field(default_factory=list)
    date: str | None = Field(None, description="ISO 8601 UTC")
    body: str = ""
    attachments: list[str] = Field(default_factory=list, description="첨부(본문 안 그림 제외) file id")
    attachment_list: list[Attachment] = Field(default_factory=list, description="첨부 전체(이름 · 형식 · 크기 · 본문 안 그림 여부)")


class SlideSize(BaseModel):
    width_emu: int
    height_emu: int
    width_mm: float
    height_mm: float
    aspect: str = Field(description="예 16:9 · 4:3")


class DocMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    author: str | None = None
    title: str | None = None
    subject: str | None = None
    created: str | None = None
    modified: str | None = None
    slide_size: SlideSize | None = None
    producer: str | None = None


class ParsedDocument(BaseModel):
    file_id: str
    kind: Kind
    title: str | None = None
    text: str = Field("", description="쪽 순서 본문(최대 500,000자)")
    page_count: int = 0
    pages: list[Page] = Field(default_factory=list)
    sheets: list[Sheet] | None = None
    email: EmailInfo | None = None
    meta: DocMeta = Field(default_factory=DocMeta)
    warnings: list[str] = Field(
        default_factory=list,
        description="예 scanned_page:3(글자 층 없는 쪽 → i2t), text_truncated, layout_skipped_after:300, children_skipped:depth",
    )
    parser_version: str
