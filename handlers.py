import struct
from types import FunctionType

from binaryninja import LowLevelILOperation as Op
from collections import defaultdict

fmt = {1: 'B', 2: 'H', 4: 'L', 8: 'Q'}

class Handlers(object):
    _handlers = defaultdict(
        lambda: lambda i: (_ for _ in ()).throw(NotImplementedError(i.operation))
    )

    def __init__(self, emilator):
        self.emilator = emilator

    @classmethod
    def add(cls, operation):
        def add_decorator(handler):
            cls._handlers[operation] = handler
            return handler
        return add_decorator

    def __getitem__(self, op):
        hooks = self.emilator.instr_hooks[op]
        handler = self._handlers[op]

        def call_hooks(expr):
            for hook in hooks:
                hook(expr, self.emilator)

            try:
                return handler(expr, self.emilator)
            except NotImplementedError:
                if not hooks:
                    raise

        return call_hooks


@Handlers.add(Op.LLIL_SET_REG)
def _set_reg(expr, emilator):
    value = emilator.handlers[expr.src.operation](expr.src)
    emilator.set_register_value(expr.dest, value)

@Handlers.add(Op.LLIL_CONST)
def _const(expr, emilator):
    return expr.value

@Handlers.add(Op.LLIL_REG)
def _reg(expr, emilator):
    return emilator.get_register_value(expr.src)

@Handlers.add(Op.LLIL_LOAD)
def _load(expr, emilator):
    addr = emilator.handlers[expr.src.operation](expr.src)

    return emilator.read_memory(addr, expr.size)

@Handlers.add(Op.LLIL_STORE)
def _store(expr, emilator):
    addr = emilator.handlers[expr.dest.operation](expr.dest)
    value = emilator.handlers[expr.src.operation](expr.src)

    pack_fmt = (
            # XXX: Endianness string bug
            '<' if emilator.function.arch.endianness == 'LittleEndian'
            else ''
        ) + fmt[expr.size]

    emilator.write_memory(addr, struct.pack(pack_fmt, value))