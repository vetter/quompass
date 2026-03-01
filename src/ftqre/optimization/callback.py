"""pymoo Callback for progress reporting during optimization."""

from __future__ import annotations

from typing import Any, Callable


class ProgressCallback:
    """pymoo Callback that reports progress via a user-provided callable.

    Parameters
    ----------
    n_gen : int
        Total number of generations.
    callback : callable
        Called with (current_generation, total_generations) after each gen.
    """

    def __init__(
        self,
        n_gen: int,
        callback: Callable[[int, int], None],
    ) -> None:
        from pymoo.core.callback import Callback

        self._n_gen = n_gen
        self._callback = callback

        class _Callback(Callback):
            def __init__(self_inner) -> None:
                super().__init__()

            def notify(self_inner, algorithm: Any, **kwargs: Any) -> None:
                gen = algorithm.n_gen
                self._callback(gen, self._n_gen)

        self._pymoo_callback = _Callback()

    @property
    def pymoo_callback(self) -> Any:
        """Return the pymoo Callback instance."""
        return self._pymoo_callback
