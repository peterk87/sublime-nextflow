#!/usr/bin/env python

import re
from typing import Tuple, List, Optional
from pathlib import Path

import sublime
import sublime_plugin

regex_input_section = re.compile(r'\s*input:\s*')
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


def find_proc_input_section(text: str, start: int, end: int) -> int:
    m = regex_input_section.search(text[start:end])
    if m:
        return m.end()
    return -1


def get_input_channels(text: str, start: int, end: int) -> List[str]:
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
    return get_input_channels(text, proc_input_section_start, proc_end)


def proc_input_html(path: str, proc_name: str, input_channels_text: List[str]) -> str:
    out = f'<p>Process: <code>{proc_name}</code></p>'
    out += f'<p>File: <small><code>{path}</code></small></p>'
    out += '<h3>Input channels:</h3>'
    for x in input_channels_text:
        out += f'<p><code>{x}</code></p>'
    return out


def find_proc_output_section(text: str, start: int, end: int) -> int:
    m = regex_output_section.search(text[start:end])
    if m:
        return m.end()
    return -1


def get_output_channels(text: str, start: int, end: int) -> List[Tuple[str, str]]:
    out = []
    for m in regex_output_channel.finditer(text[start:end]):
        chan, emit = m.groups()
        chan = ''.join(x.strip() for x in chan.split('\n'))
        out.append((emit, chan))
    return out


def output_section_lines(text: str, start: int, end: int) -> List[Tuple[int, str]]:
    out = []
    lines = text[start:end].split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('script:'):
            break
        out.append((len(out), line))
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
    proc_output_start += proc_start
    out = get_output_channels(text, proc_output_start, proc_end)
    if not out:
        out = output_section_lines(text, proc_output_start, proc_end)
    return out


def proc_output_html(path: str, proc_name: str, output_channels_text: List[Tuple[str, str, Path]],
                     focus_channel: str = None) -> str:
    out = f'<p>Process: <code>{proc_name}</code></p>'
    out += f'<p>File: <small><code>{path}</code></small></p>'
    out += '<h3>Ouput channels:</h3>'
    for emit, chan in output_channels_text:
        out += f'<p>'
        if focus_channel and focus_channel == emit:
            out += '<b>'
        out += f'<code>{emit}: {chan}</code>'
        if focus_channel and focus_channel == emit:
            out += '</b>'
        out += f'</p>'
    return out


def proc_info_html(
        path: str,
        proc_name: str,
        input_channels_text: List[str],
        output_channels_text: List[Tuple[str, str, Path]],
) -> str:
    out = f'<p>Process: <code>{proc_name}</code></p>'
    out += f'<p>File: <small><code>{path}</code></small></p>'
    out += '<h3>Input channels:</h3>'
    for x in input_channels_text:
        out += f'<p><code>{x}</code></p>'
    out += '<h3>Ouput channels:</h3>'
    for emit, chan in output_channels_text:
        out += f'<p><code>{emit}: {chan}</code></p>'
    return out


def show_proc_info(root_dir: Path, view: sublime.View, point: int) -> None:
    proc_name = view.substr(view.word(point))
    m, proc_name = find_import_proc_name(proc_name, view)
    path: Optional[Path] = None
    input_channels_text = []
    output_channels_text = []
    if m:
        nf_path = m.group(1) + '.nf'
        path = root_dir / nf_path
        input_channels_text = get_input_channel_text(path, proc_name)
        output_channels_text = get_output_channel_emits(path, proc_name)
        if not input_channels_text:
            view.window().status_message(f'No input channels in {proc_name}!')
    else:
        for path in root_dir.rglob('**/*.nf'):
            input_channels_text = get_input_channel_text(path, proc_name)
            output_channels_text = get_output_channel_emits(path, proc_name)
            if input_channels_text or output_channels_text:
                break
    if not (input_channels_text and output_channels_text):
        return
    if path is None:
        return
    short_path = "." + str(path.absolute()).replace(str(root_dir.absolute()), "")
    view.show_popup(proc_info_html(short_path, proc_name, input_channels_text, output_channels_text))


def find_import_proc_name(proc_name: str, view: sublime.View) -> Tuple[Optional[re.Match], str]:
    region = view.find(r'\w+ +as +' + proc_name, 0)
    if region.a != -1 and region.b != -1:
        proc_name = view.substr(view.word(sublime.Region(region.a, region.a)))
    include_str = view.substr(view.find(r'^include +\{\s*' + proc_name + r"\s*[^}]*\}\s+from\s+'[^']+'", 0))
    m = re.match(r".*from\s+'\./([^']+)'", include_str)
    return m, proc_name


def show_output_channel_popup(root_dir: Path, view: sublime.View, point: int) -> None:
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

    m, proc_name = find_import_proc_name(proc_name, view)
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


class NextflowWorkflowProcessCallEventListener(sublime_plugin.EventListener):
    def on_selection_modified_async(self, view):
        """Show popups for process calls and output channel property access

        When the cursor is navigated over:

        - a process name (entity.name.class.process.nextflow)
        - process out keyword (e.g. FASTQC.out) (keyword.process.out.nextflow)
        - named output channel (e.g. FASTQC.out.html) (variable.channel.process-output-emit.nextflow)

        A popup will be shown with info about the process input/output channels. For named output channels, the accessed output channel will be highlighted.
        """
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
        point_before = point - 1
        # if cursor on process name, then show popup with input/output channel info
        if view.score_selector(point,
                               'source.nextflow meta.definition.workflow.nextflow entity.name.class.process.nextflow'):
            show_proc_info(root_dir, view, point)
            return
        out_chan_scope = '(variable.channel.process-output-emit.nextflow | keyword.process.out.nextflow)'
        if view.score_selector(point, out_chan_scope) or view.score_selector(point - 1, out_chan_scope):
            show_output_channel_popup(root_dir, view, point)
            return
        # if cursor on or after `out` or named output channel, then show popup with process output channel info
        # highlighting named process
        proc_call_input_scope = 'source.nextflow meta.definition.workflow.nextflow meta.process-call.nextflow - (' \
                                'punctuation.accessor.dot.process-out.nextflow | entity | keyword | variable) '
        if not view.score_selector(point,proc_call_input_scope):
            return
        if not view.score_selector(point_before,proc_call_input_scope):
            return
        s = view.substr(point_before)
        if s not in (' ', ',', '('):
            return
        regions = [x for x in view.find_by_selector('meta.process-call.nextflow') if x.contains(point)]
        if not regions:
            return
        proc_call_str = view.substr(regions[0])
        m = re.match(r'^(\w+)', proc_call_str)
        if not m:
            return
        proc_name = m.group(1)
        m, proc_name = find_import_proc_name(proc_name, view)
        input_channels_text = []
        path: Optional[Path] = None
        if m:
            nf_path = m.group(1) + '.nf'
            path = root_dir / nf_path
            input_channels_text = get_input_channel_text(path, proc_name)
            if not input_channels_text:
                view.window().status_message(f'No input channels in {proc_name}!')
        else:
            for path in root_dir.rglob('**/*.nf'):
                input_channels_text = get_input_channel_text(path, proc_name)
                if input_channels_text:
                    break
        if not input_channels_text:
            return
        if path is None:
            return
        short_path = "." + str(path.absolute()).replace(str(root_dir.absolute()), "")
        view.show_popup(proc_input_html(short_path, proc_name, input_channels_text))

    def on_query_completions(self, view, prefix, locations):
        window = view.window()
        if view.syntax().name != 'Nextflow':
            return
        if len(locations) > 1:
            return
        point = locations[0]
        if not view.score_selector(point - 1,
                                   'source.nextflow meta.definition.workflow.nextflow punctuation.accessor.dot.process-out.nextflow'):
            return
        out_word_region = view.word(point - 2)
        if view.substr(out_word_region) != 'out':
            return
        proc_name_region = view.word(out_word_region.a - 1)
        proc_name = view.substr(proc_name_region)
        if not proc_name:
            return
        # region = view.find(r'\w+ +as +' + proc_name, 0)
        # if region.a != -1 and region.b != -1:
        #     proc_name = view.substr(view.word(sublime.Region(region.a, region.a)))
        folders = view.window().folders()
        if not folders:
            return
        root_dir = Path(folders[0])
        # include_str = view.substr(view.find(r'^include +\{\s*' + proc_name + r"\s*[^}]*\}\s+from\s+'[^']+'", 0))
        # m = re.match(r".*from\s+'\./([^']+)'", include_str)
        m, proc_name = find_import_proc_name(proc_name, view)
        emits = []
        path = None
        if m:
            nf_path = m.group(1) + '.nf'
            path = root_dir / nf_path
            emits = get_output_channel_emits(path, proc_name)
            if not emits:
                window.status_message(f'No named output channels in {proc_name}!')
        else:
            for path in root_dir.rglob('**/*.nf'):
                emits = get_output_channel_emits(path, proc_name)
                if emits:
                    break
        if not emits:
            return
        if path is None:
            return
        flags = sublime.INHIBIT_REORDER | sublime.INHIBIT_WORD_COMPLETIONS
        return sublime.CompletionList(
            completions=[
                sublime.CompletionItem(
                    trigger=emit,
                    annotation=chan,
                    details=f'<code>{chan}</code><br><p>From ".{str(path.absolute()).replace(str(root_dir.absolute()), "")}"</p>',
                )
                for emit, chan in emits
            ],
            flags=flags,
        )
