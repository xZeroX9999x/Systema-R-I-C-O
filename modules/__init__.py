# ============================================================================
#  R-I-C-O Bot v5.0 — Módulos
# ============================================================================

# Este archivo es OBLIGATORIO para que Python reconozca 'modules' como paquete.
# Las importaciones relativas dentro del paquete dependen de su existencia.

from . import config
from . import state
from . import technical
from . import backtest
from . import allocation
from . import context
from . import decision
from . import html_generator

__all__ = [
    'config',
    'state',
    'technical',
    'backtest',
    'allocation',
    'context',
    'decision',
    'html_generator'
]
