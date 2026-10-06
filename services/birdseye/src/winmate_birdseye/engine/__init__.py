"""결정적 배치 엔진 be-engine(08-birdseye §7.6) — 모델 호출 없는 순수 함수 묶음."""
from .core import computed_dims, dims_for, generate, main_entrance, merged_params, seat_distance, size_inch, tiny_of
from .ops import apply_ops
from .validate import autofix, merge_fixed, validate

__all__ = ["generate", "validate", "autofix", "apply_ops", "merge_fixed", "merged_params", "computed_dims", "dims_for",
           "seat_distance", "size_inch", "tiny_of", "main_entrance"]
