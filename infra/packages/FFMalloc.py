"""This file contains class definition for the infrastructure-compatible FFMalloc unit"""
import os
from ..package import Package
from ..util import run


class FFMalloc(Package):
    """Define package for FFMalloc fast-forward one-time allocator"""

    name = "FFMalloc"
    ffmalloc_lib = "libffmallocst.so"
    rebuild = False
    reinstall = False

    def root_dir(self, ctx):
        """Retrieve the path to the git submodule path"""
        return os.path.join(ctx.paths.root, "external", self.name)

    def ident(self):
        return self.name

    def fetch(self, ctx):
        pass

    def is_fetched(self, ctx):
        return True

    def build(self, ctx):
        """Use the provided build makefile"""
        os.chdir(self.root_dir(ctx))
        run(ctx, ["make", "sharedst"])

    def is_built(self, ctx):
        return not self.rebuild

    def install(self, ctx):
        os.chdir(self.root_dir(ctx))
        run(ctx, ["make", "install_st", f"INSTALL_TARGET={self.root_dir(ctx)}"])
        ctx.ldflags += [f"-L{os.path.join(self.root_dir(ctx), 'lib')}"]

    def install_env(self, ctx):
        prevlibpath = os.getenv("LD_LIBRARY_PATH", "").split(":")
        libpath = os.path.join(self.root_dir(ctx), "lib")
        if os.path.exists(libpath):
            ctx.runenv.setdefault("LD_LIBRARY_PATH", prevlibpath).insert(0, libpath)

    def is_installed(self, ctx):
        return not self.reinstall

    def prepare_run(self, ctx):
        """Insert FFMalloc into LD_PRELOAD"""
        ld_preload = os.getenv("LD_PRELOAD", "").split(":")
        ctx.log.debug(f"Old LD_PRELOAD value: {ld_preload}")
        ctx.runenv.setdefault("LD_PRELOAD", ld_preload).insert(0, self.ffmalloc_lib)

    def clean(self, ctx):
        os.chdir(self.root_dir(ctx))
        run(ctx, ["make", "clean"], allow_error=True)

    def is_clean(self, ctx):
        return False
