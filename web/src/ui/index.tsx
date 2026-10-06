/**
 * 공통 UI 키트 — 기능 모듈은 이 컴포넌트와 var(--wm-*) 토큰만 쓴다(00-shell.md §2). 목록 · 사용법: ./README.md
 * 셸 세션(workspace)이 소유한다. 기능에 필요한 컴포넌트가 없으면 docs/requests/workspace.md 에 요청.
 */
import './tokens.css';
import './ui.css';

export {
  cx, Button, ButtonLink, ExternalLink, IconButton, CloseButton, ItemAddButton, Field, Input, TextArea, Select, SearchField, Chip, FilterChip,
  Tabs, Segmented, Toggle, Spinner,
} from './controls';
export type { ButtonProps, ButtonVariant, ButtonSize, ButtonHeight, AddState, SearchFieldProps, TabItem, SegmentedItem, SegmentedProps } from './controls';

export {
  Tag, NeutralTag, Badge, Count, CountPill, KeyChip, CheckChip, MatchChip, TrayChip, MiniChip, SourceBadge, StatusBadge, Avatar, InfoBox, MetaRows,
  Notice, Empty, ErrorState, Progress, Skeleton, Banner,
} from './display';
export type { BadgeTone, StatusTone, MetaRow } from './display';

export { Modal, SideSheet, ConfirmDialog, useConfirm, useFocusTrap, useEscape, focusablesIn, toast, ToastHost } from './overlay';
export type { ModalProps, ConfirmOptions } from './overlay';

export { Img, ImageTile, ImageCard, PhotoBadge, CaseCard, CaseRow, isSameOrigin, focalCss } from './media';
export type { Focal, ImageTileProps, ImageKindTone, CaseCardProps, CaseCardPhoto } from './media';

export {
  PageHeader, NewButton, FilterTabs, ListToolbar, DataTable, TitleCell, RowAction, ListPage, Section, Composer, ChatLine, ContentColumn, ChipRow, EchoBubble,
} from './page';
export type { DataColumn, FilterTab } from './page';

export {
  DRAG_MIME, DRAG_TYPE_ICON, DRAG_TYPE_LABEL, useDragSource, useDropTarget, DropZone, DragGhost, DragGhostLayer, DragHandle, useActiveDrag, getActiveDrag,
  onItemDropped, notifyDropped, cancelActiveDrag, readDragPayload, Dropzone, FileDropzone,
} from './dnd';
export type { DragType, DragPayload, DropState, DropZoneProps, UseDropTargetOptions, DropResult } from './dnd';

export { ProductInput, ProductLegend, Bubble, searchProducts, tokenOf, productName } from './ProductInput';
export type { ProductToken, ProductSearchItem, ProductInputProps } from './ProductInput';

export { Thumb, THUMB_KINDS, templateThumbUrl } from './Thumb';

// 기능 요청으로 더한 부품(2026-10-07) — 선택 카드 · Q 상자 · 키맨 가중치 · 판단 모드 · 출처 카드 · 근거 패널 · 작업 고르기
export { ChoiceCard, ChoiceList, ChoiceCustomInput, QBadge } from './choice';
export type { ChoiceCardProps, QBadgeSize } from './choice';
export {
  WEIGHT_MIN, kmClass, kmColors, equalWeights, distributeWeights, stepWeights, moveWeightBoundary, KeymanAvatar, KeymanDot, WeightBar, WeightStepper,
} from './weights';
export type { WeightItem } from './weights';
export { ModeChip, MODE_LABELS, SourceCard, EvidencePanel } from './evidence';
export type { JudgementMode, SourceCardProps, SourceCardAction, EvidenceFilter } from './evidence';
export { WorkPickerDialog, fetchWorkItems } from './WorkPicker';
export type { WorkPickItem, WorkPickerDialogProps } from './WorkPicker';
export type { ThumbProps } from './Thumb';

export { Icon, PathIcon, BoltIcon, Grip, SlidersIcon, FolderIcon, ICON_PATHS } from './icons';
export type { IconName } from './icons';

export {
  formatDate, formatDateTime, formatBytes, formatKB, formatNumber, relativeTime, greetingFor, resolutionLabel, formatMediaSize, shortFileUrl, displayUrl,
  hostOf, josa,
} from './format';
