#!/usr/bin/env python
import re
from typing import Iterator, Tuple, List
import sys
from pathlib import Path
import json

import sublime
import sublime_plugin

regex_withlabel = re.compile(r'\s*withLabel\s*:\s*(?:[\'\"])?(\w+)(?:[\'\"])?\s*\{\s*')


def get_config_labels(path: Path) -> List[Tuple[int, str, str]]:
    out = []
    text = path.read_text()
    for m in regex_withlabel.finditer(text):
        start, end = m.span()
        bracket_count = 1
        end_bracket = -1
        for i in range(end+1, len(text)):
            c = text[i]
            if c == '{':
                bracket_count += 1
            elif c == '}':
                bracket_count -= 1
            if bracket_count == 0:
                end_bracket = i
                break
        subtext = '\n'.join(x.strip() for x in text[end:end_bracket].strip().split('\n'))
        out.append((path.name, m.group(1), subtext))
    return out


class NextflowProcessLabelEventListener(sublime_plugin.ViewEventListener):
    def on_query_completions(self, prefix, locations):
        view = self.view
        if view.syntax().name != 'Nextflow':
            return
        if len(locations) > 1:
            return
        point = locations[0]
        if not view.score_selector(point, 'source.nextflow meta.definition.process.nextflow'):
            return
        if not view.substr(view.line(point)).strip().startswith('label'):
            return
        folders = view.window().folders()
        if not folders:
            return
        root_dir = Path(folders[0])
        labels = []
        for path in root_dir.rglob('**/*.config'):
            labels += get_config_labels(path)
        if not labels:
            return
        flags = sublime.INHIBIT_REORDER | sublime.INHIBIT_WORD_COMPLETIONS
        completions = sublime.CompletionList(
            completions=[
                sublime.CompletionItem(
                    trigger=f"'{label_name}'",
                    annotation=f'{config_name}: {label_name}',
                    details='|'.join(f'<code>{x.replace(" ", "")}</code>' for x in text.split('\n'))
                ) for config_name, label_name, text in labels
            ],
            flags=flags
        )
        return completions
