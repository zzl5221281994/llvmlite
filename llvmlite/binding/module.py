from __future__ import print_function, absolute_import
from ctypes import (c_char_p, byref, POINTER, c_bool, create_string_buffer,
                    c_void_p, cast)

from . import ffi
from .linker import link_modules
from .common import _encode_string
from .value import ValueRef


def parse_assembly(llvmir):
    """
    Create Module from a LLVM IR string
    """
    context = ffi.lib.LLVMPY_GetGlobalContext()
    llvmir = _encode_string(llvmir)
    strbuf = c_char_p(llvmir)
    with ffi.OutputString() as errmsg:
        mod = ModuleRef(ffi.lib.LLVMPY_ParseAssembly(context, strbuf, errmsg))
        if errmsg:
            mod.close()
            raise RuntimeError("LLVM IR parsing error\n{0}".format(errmsg))
    return mod


class ModuleRef(ffi.ObjectRef):
    """
    A reference to a LLVM module.
    """

    def __str__(self):
        with ffi.OutputString() as outstr:
            ffi.lib.LLVMPY_PrintModuleToString(self, outstr)
            return str(outstr)

    def _dispose(self):
        ffi.lib.LLVMPY_DisposeModule(self)

    def get_function(self, name):
        """
        Get a ValueRef pointing to the function named *name*.
        NameError is raised if the symbol isn't found.
        """
        p = ffi.lib.LLVMPY_GetNamedFunction(self, _encode_string(name))
        if not p:
            raise NameError(name)
        return ValueRef(p, module=self)

    def get_global_variable(self, name):
        """
        Get a ValueRef pointing to the global variable named *name*.
        NameError is raised if the symbol isn't found.
        """
        p = ffi.lib.LLVMPY_GetNamedGlobalVariable(self, _encode_string(name))
        if not p:
            raise NameError(name)
        return ValueRef(p, module=self)

    def verify(self):
        """
        Verify the module IR's correctness.  RuntimeError is raised on error.
        """
        with ffi.OutputString() as outmsg:
            if ffi.lib.LLVMPY_VerifyModule(self, outmsg):
                raise RuntimeError(str(outmsg))

    @property
    def data_layout(self):
        """
        This module's data layout specification, as a string.
        """
        # LLVMGetDataLayout() points inside a std::string managed by LLVM.
        with ffi.OutputString(owned=False) as outmsg:
            ffi.lib.LLVMPY_GetDataLayout(self, outmsg)
            return str(outmsg)

    @data_layout.setter
    def data_layout(self, strrep):
        ffi.lib.LLVMPY_SetDataLayout(self,
                                     create_string_buffer(
                                         strrep.encode('utf8')))

    @property
    def triple(self):
        """
        This module's target "triple" specification, as a string.
        """
        # LLVMGetTarget() points inside a std::string managed by LLVM.
        with ffi.OutputString(owned=False) as outmsg:
            ffi.lib.LLVMPY_GetTarget(self, outmsg)
            return str(outmsg)

    @triple.setter
    def triple(self, strrep):
        ffi.lib.LLVMPY_SetTarget(self,
                                 create_string_buffer(
                                     strrep.encode('utf8')))

    def link_in(self, other, preserve=False):
        link_modules(self, other, preserve)
        if not preserve:
            other.detach()

    @property
    def global_variables(self):
        """
        Return an iterator over this module's global variables.
        The iterator will yield a ValueRef for each global variable.
        """
        gi = ffi.lib.LLVMPY_ModuleGlobalIter(self)
        return _GlobalsIterator(gi, module=self)


class _GlobalsIterator(ffi.ObjectRef):
    def __init__(self, ptr, module):
        ffi.ObjectRef.__init__(self, ptr)
        # Keep Module alive
        self._module = module

    def _dispose(self):
        ffi.lib.LLVMPY_DisposeGlobalIter(self)

    def __next__(self):
        vp = ffi.lib.LLVMPY_GlobalIterNext(self)
        if vp:
            return ValueRef(vp, self._module)
        else:
            raise StopIteration

    next = __next__

    def __iter__(self):
        return self


# =============================================================================
# Set function FFI

ffi.lib.LLVMPY_ParseAssembly.argtypes = [ffi.LLVMContextRef,
                                         c_char_p,
                                         POINTER(c_char_p)]
ffi.lib.LLVMPY_ParseAssembly.restype = ffi.LLVMModuleRef

ffi.lib.LLVMPY_GetGlobalContext.restype = ffi.LLVMContextRef

ffi.lib.LLVMPY_DisposeModule.argtypes = [ffi.LLVMModuleRef]

ffi.lib.LLVMPY_PrintModuleToString.argtypes = [ffi.LLVMModuleRef,
                                               POINTER(c_char_p)]

ffi.lib.LLVMPY_GetNamedFunction.argtypes = [ffi.LLVMModuleRef,
                                            c_char_p]
ffi.lib.LLVMPY_GetNamedFunction.restype = ffi.LLVMValueRef

ffi.lib.LLVMPY_VerifyModule.argtypes = [ffi.LLVMModuleRef,
                                        POINTER(c_char_p)]
ffi.lib.LLVMPY_VerifyModule.restype = c_bool

ffi.lib.LLVMPY_GetDataLayout.argtypes = [ffi.LLVMModuleRef, POINTER(c_char_p)]
ffi.lib.LLVMPY_SetDataLayout.argtypes = [ffi.LLVMModuleRef, c_char_p]

ffi.lib.LLVMPY_GetTarget.argtypes = [ffi.LLVMModuleRef, POINTER(c_char_p)]
ffi.lib.LLVMPY_SetTarget.argtypes = [ffi.LLVMModuleRef, c_char_p]

ffi.lib.LLVMPY_GetNamedGlobalVariable.argtypes = [ffi.LLVMModuleRef, c_char_p]
ffi.lib.LLVMPY_GetNamedGlobalVariable.restype = ffi.LLVMValueRef

ffi.lib.LLVMPY_ModuleGlobalIter.argtypes = [ffi.LLVMModuleRef]
ffi.lib.LLVMPY_ModuleGlobalIter.restype = ffi.LLVMGlobalsIterator

ffi.lib.LLVMPY_DisposeGlobalIter.argtypes = [ffi.LLVMGlobalsIterator]

ffi.lib.LLVMPY_GlobalIterNext.argtypes = [ffi.LLVMGlobalsIterator]
ffi.lib.LLVMPY_GlobalIterNext.restype = ffi.LLVMValueRef
