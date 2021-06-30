#!/usr/bin/env python

from typing import List, Tuple, Optional
import subprocess as sp

import pickle
from pathlib import Path

import sublime
import sublime_plugin
import threading

pkgs_fetch_lock = threading.Lock()


def run_conda_search() -> List[Tuple[str, str, str, str]]:
    p = sp.Popen(['conda', 'search', ], stdout=sp.PIPE, stderr=sp.PIPE)
    stdout, stderr = p.communicate()
    stdout =  stdout.decode()
    lines = stdout.split('\n')
    for i, line in enumerate(lines):
        if line[0] == '#':
            break
    
    return [tuple(line.strip().split()) for line in lines[i+1:] if line.split()]


def cache_pkgs_list(pkgs: List[Tuple[str, str, str, str]]) -> None:
    cache_dir = Path(sublime.cache_path()) / 'sublime-nextflow'
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / 'conda_search.pickle'
    with open(cache_path, 'wb') as fh:
        pickle.dump(pkgs, fh)


def fetch_pkgs() -> None:
    pkgs = run_conda_search()
    cache_pkgs_list(pkgs)


def get_cached_pkgs_list() -> Optional[List[Tuple[str, str, str, str]]]:
    cache_dir = Path(sublime.cache_path()) / 'sublime-nextflow'
    cache_path = cache_dir / 'conda_search.pickle'
    if not cache_path.exists():
        return None
    with open(cache_path, 'rb') as fh:
        return pickle.load(fh)


class NextflowCondaPackagesInfoFetchCommand(sublime_plugin.WindowCommand):
    def run(self):
        with pkgs_fetch_lock:
            thread = threading.Thread(target=fetch_pkgs)
            thread.daemon = True
            thread.start()


class NextflowCondaPackagesEventListener(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        if view.syntax().name != 'Nextflow':
            return
        if len(locations) > 1:
            return
        point = locations[0]
        if not view.score_selector(point, 'source.nextflow meta.definition.process.nextflow meta.definition.conda-directive.nextflow string'):
            return
        pkgs = get_cached_pkgs_list()
        if pkgs:
            print(f'Retrieved {len(pkgs)} Conda packages from cache')
        else:
            print('Running nextflow_conda_packages_info_fetch command')
            view.run_command('nextflow_conda_packages_info_fetch')
            return
        pkgs = pkgs[::-1]
        flags = sublime.INHIBIT_REORDER | sublime.INHIBIT_WORD_COMPLETIONS
        completions = sublime.CompletionList(
            completions=[
                sublime.CompletionItem(
                    trigger=f'{name}={version}={build}' if channel.startswith('pkgs/') else f'{channel}::{name}={version}={build}',
                    annotation=f'{channel}::{name}={version}={build}',
                ) for name,version,build,channel in pkgs
            ],
            flags=flags
        )
        return completions
