#!/usr/bin/env python

import re
from typing import Iterator, Tuple, List, Optional
import sys
from pathlib import Path
import json

import sublime
import sublime_plugin


regex_output_section = re.compile(r'\s*output:\s*')
# regex to find output channels with emit
regex_output_channel = re.compile(r'((?:.*,\s+)*.*),\s*emit:\s*(\w+)')

def find_closing_bracket(text: str, start: int) -> int:
    count = 1
    for i in range(start, len(text)):
        c = text[i]
        if c == '{':
            count += 1
        elif c == '}':
            count -= 1
        if count == 0:
            return i
    return -1


def find_process_name(proc_name: str, text: str) -> int:
    m = re.search(r'process\s+' + proc_name + r'\s*{', text)
    if m:
        return m.end()
    return -1


def find_proc_output_section(text: int, start: int, end: int) -> int:
    m = regex_output_section.search(text[start:end])
    if m:
        return m.end()
    return -1


def get_output_channels(text, start, end) -> List[Tuple[str, str]]:
    out = []
    for m in regex_output_channel.finditer(text[start:end]):
        chan, emit = m.groups()
        chan = ''.join(x.strip() for x in chan.split('\n'))
        out.append((emit, chan))
    return out

def get_output_channel_emits(path: Path, proc_name: str) -> List[Tuple[str, str]]:
    text = path.read_text()
    proc_start = find_process_name(proc_name, text)
    if proc_start == -1:
        return []
    proc_end = find_closing_bracket(text, proc_start)
    if proc_end == -1:
        return []
    proc_output_start = find_proc_output_section(text, proc_start, proc_end)
    return get_output_channels(text, proc_output_start, proc_end)

class NextflowOutputChannelEventListener(sublime_plugin.ViewEventListener):
    def on_query_completions(self, prefix, locations):
        view = self.view
        if view.syntax().name != 'Nextflow':
            return
        if len(locations) > 1:
            return
        point = locations[0]
        if not view.score_selector(point - 1, 'source.nextflow meta.definition.workflow.nextflow punctuation.accessor.dot.process-out.nextflow'):
            return
        out_word_region = view.word(point - 2)
        if view.substr(out_word_region) != 'out':
            return
        proc_name_region = view.word(out_word_region.a - 1)
        proc_name = view.substr(proc_name_region)
        if not proc_name:
            return
        folders = view.window().folders()
        if not folders:
            return
        root_dir = Path(folders[0])
        emits = []
        for path in root_dir.rglob('**/*.nf'):
            emits += get_output_channel_emits(path, proc_name)
        if not emits:
            return
        flags = sublime.INHIBIT_REORDER | sublime.INHIBIT_WORD_COMPLETIONS
        completions = sublime.CompletionList(
            completions=[
                sublime.CompletionItem(
                    trigger=emit,
                    annotation=chan,
                ) for emit, chan in emits
            ],
            flags=flags
        )
        return completions
