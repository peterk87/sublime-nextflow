import re
from typing import Iterator
import sys
from pathlib import Path

import sublime
import sublime_plugin


regex_process = re.compile(r'^process +(\w+) *\{\s*$')
regex_functions = re.compile(r'^def +(\w+) *\([^\)]*\) *\{\s*$')

def find_processes(path: Path) -> Iterator[str]:
    with open(path) as f:
        for l in f:
            m = regex_process.match(l)
            if m:
                yield m.group(1)


def find_functions(path: Path) -> Iterator[str]:
    with open(path) as f:
        for l in f:
            m = regex_functions.match(l)
            if m:
                yield m.group(1)


def relative_path(script_path: Path, import_path: Path) -> str:
    for i, parent_path in enumerate(script_path.parents):
        try:
            if i == 0:
                return './' + str(import_path.relative_to(parent_path))
            else:
                return '../'*i + str(import_path.relative_to(parent_path))
        except ValueError:
            continue
    return str(import_path)


class NextflowIncludeInsertProcessCommand(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        process = kwargs.get('process', None)
        module_path = kwargs.get('module_path', None)
        if process and module_path:
            view = self.view
            if len(view.selection) > 1:
                return
            region = view.selection[0]
            point = region.a
            row, col = view.rowcol(point)
            if col != 0:
                return
            module_path = Path(module_path)
            module_path = module_path.parent / module_path.stem
            script_path = Path(view.file_name())
            view.insert(edit, point, "include { " + process + " } from '" + relative_path(script_path, module_path) + "' addParams( options: modules['" + process.lower() + "'] )")


class NextflowIncludeProcessCommand(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        view = self.view
        if len(view.selection) > 1:
            return
        region = view.selection[0]
        point = region.a
        row, col = view.rowcol(point)
        if col != 0:
            return
        folders = view.window().folders()
        if not view.file_name():
            return
        if not folders:
            return
        root_dir = Path(folders[0])
        nf_files = [(proc, str(p.absolute())) for p in root_dir.rglob('*.nf') for proc in find_processes(p)]

        def on_select(x: int):
            if x == -1:
                return
            proc, nf_path = nf_files[x]
            root = str(root_dir.absolute())
            if nf_path.startswith(root):
                view.run_command(
                    'nextflow_include_insert_process', 
                    dict(process=proc,
                         module_path=nf_path
                    )
                )

        view.window().show_quick_panel(nf_files, on_select=on_select)


class NextflowIncludeInsertFunctionsCommand(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        funcs = kwargs.get('funcs', None)
        module_path = kwargs.get('module_path', None)
        if funcs and module_path:
            view = self.view
            if len(view.selection) > 1:
                return
            region = view.selection[0]
            point = region.a
            row, col = view.rowcol(point)
            if col != 0:
                return
            module_path = Path(module_path)
            module_path = module_path.parent / module_path.stem
            script_path = Path(view.file_name())
            view.insert(edit, point, "include { " + '; '.join(funcs) + " } from '" + relative_path(script_path, module_path) + "'")


class NextflowIncludeFunctionsCommand(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        view = self.view
        if len(view.selection) > 1:
            return
        region = view.selection[0]
        point = region.a
        row, col = view.rowcol(point)
        if col != 0:
            return
        folders = view.window().folders()
        if not view.file_name():
            return
        if not folders:
            return
        root_dir = Path(folders[0])
        nf_files = []
        for p in root_dir.rglob('*.nf'):
            abspath = str(p.absolute())
            funcs = list(find_functions(p))
            if funcs:
                nf_files.append((funcs, abspath))

        def on_select(x: int):
            if x == -1:
                return
            funcs, nf_path = nf_files[x]
            root = str(root_dir.absolute())
            if nf_path.startswith(root):
                view.run_command(
                    'nextflow_include_insert_functions', 
                    dict(funcs=funcs,
                         module_path=nf_path
                    )
                )

        view.window().show_quick_panel([('; '.join(x), y) for x,y in nf_files], on_select=on_select)
