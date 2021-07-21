#!/usr/bin/env python

import re
from typing import Iterator, Tuple, List, Optional
import sys
from pathlib import Path
import json

import sublime
import sublime_plugin


regex_input_section = re.compile(r'\s*input:\s*')


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


def find_proc_input_section(text: int, start: int, end: int) -> int:
    m = regex_input_section.search(text[start:end])
    if m:
        return m.end()
    return -1


def get_input_channels(text, start, end) -> List[str]:
    out = []
    lines = text[start:end].split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('output:') or line.startswith('script:'):
            break
        out.append(line)
    return out


def get_input_channel_text(path: Path, proc_name: str) -> List[str]:
    text = path.read_text()
    proc_start = find_process_name(proc_name, text)
    if proc_start == -1:
        return []
    proc_end = find_closing_bracket(text, proc_start)
    if proc_end == -1:
        return []
    proc_input_section_start = find_proc_input_section(text, proc_start, proc_end)
    proc_input_section_start += proc_start
    out = get_input_channels(text, proc_input_section_start, proc_end)
    return out


def proc_input_html(path: str, proc_name: str, input_channels_text: List[str]) -> str:
    out = f'<p>Process: <code>{proc_name}</code></p>'
    out += f'<p>File: <small><code>{path}</code></small></p>'
    out += '<h3>Input channels:</h3>'
    for x in input_channels_text:
        out += f'<p><code>{x}</code></p>'
    return out


class NextflowWorkflowProcessCallEventListener(sublime_plugin.EventListener):
    def on_selection_modified_async(self, view):
        if view.syntax().name != 'Nextflow':
            return
        if len(view.selection) > 1:
            return
        folders = view.window().folders()
        if not folders:
            return
        root_dir = Path(folders[0])
        region = view.selection[0]
        point = region.a
        if not view.score_selector(point, 'source.nextflow meta.definition.workflow.nextflow meta.process-call.nextflow - (punctuation.accessor.dot.process-out.nextflow | entity | keyword | variable)'):
            return
        point_before = point - 1
        if not view.score_selector(point_before, 'source.nextflow meta.definition.workflow.nextflow meta.process-call.nextflow - (punctuation.accessor.dot.process-out.nextflow | entity | keyword | variable)'):
            return
        s = view.substr(point_before)
        if s not in (' ', ',', '('):
            return
        regions = [x for x in view.find_by_selector('meta.process-call.nextflow') if x.contains(point)]
        if not regions:
            return
        window = view.window()
        proc_call_str = view.substr(regions[0])
        m = re.match(r'^(\w+)', proc_call_str)
        if not m:
            return
        proc_name = m.group(1)
        region = view.find(r'\w+ +as +' + proc_name, 0)
        if region.a != -1 and region.b != -1:
            proc_name = view.substr(view.word(sublime.Region(region.a, region.a)))
        include_str = view.substr(view.find(r'^include +\{\s*' + proc_name + r"\s*[^}]*\}\s+from\s+'[^']+'", 0))
        m = re.match(r".*from\s+'\.\/([^']+)'", include_str)
        input_channels_text = []
        if m:
            nf_path = m.group(1) + '.nf'
            path = root_dir / nf_path
            input_channels_text = get_input_channel_text(path, proc_name)
            if not input_channels_text:
                window.status_message(f'No input channels in {proc_name}!')
        else:
            for path in root_dir.rglob('**/*.nf'):
                input_channels_text = get_input_channel_text(path, proc_name)
                if input_channels_text:
                    break
        if not input_channels_text:
            return
        short_path = "." + str(path.absolute()).replace(str(root_dir.absolute()), "")
        view.show_popup(proc_input_html(short_path, proc_name, input_channels_text))
