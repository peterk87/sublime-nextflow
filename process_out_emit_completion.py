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


def get_output_channels(path, text, start, end) -> List[Tuple[str, str, Path]]:
    out = []
    for m in regex_output_channel.finditer(text[start:end]):
        chan, emit = m.groups()
        chan = ''.join(x.strip() for x in chan.split('\n'))
        out.append((emit, chan, path))
    return out


def output_section_lines(path: Path, text: str, start: int, end: int) -> List[str]:
    out = []
    lines = text[start:end].split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('script:'):
            break
        out.append((len(out), line, path))
    return out


def get_output_channel_emits(path: Path, proc_name: str) -> List[Tuple[str, str, Path]]:
    text = path.read_text()
    proc_start = find_process_name(proc_name, text)
    if proc_start == -1:
        return []
    proc_end = find_closing_bracket(text, proc_start)
    if proc_end == -1:
        return []
    proc_output_start = find_proc_output_section(text, proc_start, proc_end)
    proc_output_start += proc_start
    out = get_output_channels(path, text, proc_output_start, proc_end)
    if not out:
        out = output_section_lines(path, text, proc_output_start, proc_end)
    return out


def proc_output_html(path: str, proc_name: str, output_channels_text: List[Tuple[str, str, Path]], focus_channel: str = None) -> str:
    out = f'<p>Process: <code>{proc_name}</code></p>'
    out += f'<p>File: <small><code>{path}</code></small></p>'
    out += '<h3>Ouput channels:</h3>'
    for emit, chan, p in output_channels_text:
        out += f'<p>'
        if focus_channel and focus_channel == emit:
            out += '<b>'
        out += f'<code>{emit}: {chan}</code>'
        if focus_channel and focus_channel == emit:
            out += '</b>'
        out += f'</p>'
    return out


class NextflowOutputChannelEventListener(sublime_plugin.ViewEventListener):
    def on_selection_modified_async(self):
        view = self.view
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
        scope = '(variable.channel.process-output-emit.nextflow | keyword.process.out.nextflow)'
        if view.score_selector(point, scope) == 0 and view.score_selector(point-1, scope) == 0:
            return
        
        emit_or_out_word_region = view.word(point)
        emit_or_out_word_substr = view.substr(emit_or_out_word_region)
        focus_channel = None
        if emit_or_out_word_substr == 'out':
            proc_name = view.substr(view.word(emit_or_out_word_region.a - 2))
        else:
            out_word_region = view.word(emit_or_out_word_region.a - 2)
            out_word_substr = view.substr(out_word_region)
            if out_word_substr != 'out':
                print(f'Could not find "out" output channels keyword for process.')
                return
            focus_channel = emit_or_out_word_substr
            proc_name = view.substr(view.word(out_word_region.a - 2))
        window = view.window()

        region = view.find(r'\w+ +as +' + proc_name, 0)
        if region.a != -1 and region.b != -1:
            proc_name = view.substr(view.word(sublime.Region(region.a, region.a)))
        include_str = view.substr(view.find(r'^include +\{\s*' + proc_name + r"\s*[^}]*\}\s+from\s+'[^']+'", 0))
        m = re.match(r".*from\s+'\.\/([^']+)'", include_str)
        output_channels_text = []
        if m:
            nf_path = m.group(1) + '.nf'
            path = root_dir / nf_path
            output_channels_text = get_output_channel_emits(path, proc_name)
            if not output_channels_text:
                window.status_message(f'No input channels in {proc_name}!')
        else:
            for path in root_dir.rglob('**/*.nf'):
                output_channels_text = get_output_channel_emits(path, proc_name)
                if output_channels_text:
                    break
        if not output_channels_text:
            return
        short_path = "." + str(path.absolute()).replace(str(root_dir.absolute()), "")
        view.show_popup(proc_output_html(short_path, proc_name, output_channels_text, focus_channel))

    def on_query_completions(self, prefix, locations):
        view = self.view
        window = view.window()
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
        region = view.find(r'\w+ +as +' + proc_name, 0)
        if region.a != -1 and region.b != -1:
            proc_name = view.substr(view.word(sublime.Region(region.a, region.a)))
        folders = view.window().folders()
        if not folders:
            return
        root_dir = Path(folders[0])
        include_str = view.substr(view.find(r'^include +\{\s*' + proc_name + r"\s*[^}]*\}\s+from\s+'[^']+'", 0))
        m = re.match(r".*from\s+'\.\/([^']+)'", include_str)
        emits = []
        if m:
            nf_path = m.group(1) + '.nf'
            path = root_dir / nf_path
            emits += get_output_channel_emits(path, proc_name)
            if not emits:
                window.status_message(f'No named output channels in {proc_name}!')
        else:
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
                    details=f'<code>{chan}</code><br><p>From ".{str(path.absolute()).replace(str(root_dir.absolute()), "")}"</p>'
                ) for emit, chan, path in emits
            ],
            flags=flags
        )
        return completions
