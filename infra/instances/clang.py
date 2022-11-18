from typing import Optional, Union
from ..instance import Instance
from ..packages import LLVM, Gperftools
from ..util import FatalError


class Clang(Instance):
    """
    Sets ``clang`` as the compiler. The version of clang used is determined by
    the LLVM package passed to the constructor.

    By default, `-O2` optimization is set in CFLAGS and CXXFLAGS. This can be
    customized by setting **optlevel** to 0/1/2/3/s.

    **alloc** can be **system** (the default) or **tcmalloc**. For custom
    tcmalloc hackery, overwrite the ``gperftools`` property of this package
    with a custom :class:`Gperftools` object.

    :name: clang[-O<optlevel>][-lto][-tcmalloc]
    :param llvm: an LLVM package containing the relevant clang version
    :param optlevel: optimization level for ``-O`` (default: 2)
    :param lto: whether to apply link-time optimizations
    :param alloc: which allocator to use (default: system)
    """

    def __init__(self,
                 llvm: LLVM,
                 *,
                 optlevel: Union[int, str] = 2,
                 lto = False,
                 alloc = 'system'):
        assert optlevel in (0, 1, 2, 3, 's'), 'invalid optimization level'
        assert not (lto and optlevel == 0), 'LTO needs compile-time opts'
        assert alloc in ('system', 'tcmalloc'), 'unsupported allocator'

        self.llvm = llvm
        self.optflag = '-O' + str(optlevel)
        self.lto = lto
        self.alloc = alloc

        if self.alloc == 'tcmalloc':
            self.gperftools = Gperftools('master')

    @property
    def name(self):
        name = 'clang'
        if self.optflag != '-O2':
            name += self.optflag
        if self.lto:
            name += '-lto'
        if self.alloc != 'system':
            name += '-' + self.alloc
        return name

    def dependencies(self):
        yield self.llvm
        if self.alloc == 'tcmalloc':
            yield self.gperftools

    def configure(self, ctx):
        self.llvm.configure(ctx)

        if self.alloc == 'tcmalloc':
            self.gperftools.configure(ctx)
        else:
            assert self.alloc == 'system'

        ctx.cflags += [self.optflag]
        ctx.cxxflags += [self.optflag]

        if self.lto:
            ctx.cflags += ['-flto']
            ctx.cxxflags += ['-flto']
            ctx.ldflags += ['-flto']
            ctx.lib_ldflags += ['-flto']


class ParameterizedClang(Clang):

    def __init__(self, llvm: LLVM, name, extra_cflags=None, extra_cxxflags=None, extra_ldflags=None,
                 extra_lib_ldflags=None, benchmark_env=None,
                 *, optlevel: Union[int, str] = 2, lto=False, alloc='system'):
        super().__init__(llvm, optlevel=optlevel, lto=lto, alloc=alloc)
        self.extra_cflags = extra_cflags or []
        self.extra_cxxflags = extra_cxxflags or []
        self.extra_ldflags = extra_ldflags or []
        self.extra_lib_ldflags = extra_lib_ldflags or []
        self.benchmark_env = benchmark_env or {}
        self.instance_name = name

    def add_all_flags(self, flags):
        self.extra_cflags.extend(flags)
        self.extra_cxxflags.extend(flags)
        self.extra_ldflags.extend(flags)
        self.extra_lib_ldflags.extend(flags)

    def add_linker_flags(self, flags):
        self.extra_ldflags.extend(flags)

    def add_lib_linker_flags(self, flags):
        self.extra_lib_ldflags.extend(flags)

    @property
    def name(self):
        return self.instance_name

    def configure(self, ctx):
        super().configure(ctx)
        ctx.cflags += self.extra_cflags
        ctx.cxxflags += self.extra_cxxflags
        ctx.ldflags += self.extra_ldflags
        ctx.lib_ldflags += self.extra_lib_ldflags
        for env, value in self.benchmark_env.items():
            ctx.benchenv[env] = value


class RandomizingClang(ParameterizedClang):
    def configure(self, ctx):
        super().configure(ctx)
        if 'rngseed' not in ctx:
            raise FatalError('Target %s requires an RNG seed. Currently only the run-random command '
                             'creates such a seed.' % self.name)

        def _replace_placeholder(flag):
            return flag.replace("RNGSEED", ctx.rngseed)

        ctx.cflags = list(map(_replace_placeholder, ctx.cflags))
        ctx.cxxflags = list(map(_replace_placeholder, ctx.cxxflags))
        ctx.ldflags = list(map(_replace_placeholder, ctx.ldflags))
        ctx.lib_ldflags = list(map(_replace_placeholder, ctx.lib_ldflags))
        for env, value in ctx.benchenv.items():
            ctx.benchenv[env] = _replace_placeholder(ctx.benchenv[env])
