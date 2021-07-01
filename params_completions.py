import re
from typing import Iterator
import sys
from pathlib import Path
import json

import sublime
import sublime_plugin


regex_params = re.compile(
    r'\nparams\s*\{\n\s*(.*)',
    flags=re.MULTILINE | re.UNICODE | re.DOTALL
)
regex_param_val = re.compile(r'^(\w+)\s*=\s*(\S+).*$')


def params_list(nf_config):
    params_match = regex_params.search(nf_config)
    if params_match:
        brackets = 1
        regex_param_val = re.compile(r'^(\w+)\s*=\s*(\S+).*$')
        param_val = []
        for l in params_match.group(1).split('\n'):
            l = l.strip()
            if not l or l.startswith('//'):
                continue
            m = regex_param_val.match(l)
            if m:
                param_val.append(m.groups())
            elif l.startswith('}'):
                brackets -= 1
            else:
                print("NOMATCH", l)
            if brackets == 0:
                break
        return param_val
    else:
        return None


def get_param_info(nf_schema: dict, param: str) -> dict:
    for defn in nf_schema['definitions'].values():
        try:
            return defn['properties'][param]
        except KeyError:
            continue
    return {}

def format_param_info(param_info: dict) -> str:
    param_type = param_info.get('type', 'string')
    default = param_info.get('default', '?')
    description = param_info.get('description', 'N/A')
    out = ''
    out += f'<p>{description}</p>'
    out += (
        f'<p><b>Type:</b> <code>{param_type}</code></p>'
        f'<p><b>Default:</b> <code>{default}</code></p>'
    )
    if 'pattern' in param_info:
        out += f'<p><b>Pattern:</b> <code>{param_info["pattern"]}</code><p>'
    if 'enum' in param_info:
        enum = param_info['enum']
        if isinstance(enum, list):
            enum = ', '.join(sorted(enum))
        out += f'<p><b>Enum:</b> {enum}</p>'
    if 'help_text' in param_info:
        out += f'<p><i>{param_info["help_text"]}</i><p>'
    return out


class NextflowParamsEventListener(sublime_plugin.EventListener):
    def on_query_completions(self, view, prefix, locations):
        if view.syntax().name != 'Nextflow':
            return
        if len(locations) > 1:
            return
        point = locations[0]
        if not view.score_selector(point-1, 'source.nextflow punctuation.params.dot'):
            return
        folders = view.window().folders()
        if not folders:
            return
        root_dir = Path(folders[0])
        nf_config_path = root_dir / 'nextflow.config'
        if not nf_config_path.exists():
            print(f'Cannot get params completions. "{nf_config_path}" does not exist!')
            return None

        with open(nf_config_path) as f:
            nf_config = f.read()
        params_values = params_list(nf_config)
        if params_values:
            flags = sublime.INHIBIT_REORDER | sublime.INHIBIT_WORD_COMPLETIONS
            completions = sublime.CompletionList(
                completions=[
                    sublime.CompletionItem(
                        trigger=x,
                        annotation=f'default: {y}',
                        details=f'<i>nextflow.config</i>: <code>params.<b>{x}</b> = {y}</code>'
                    ) for x,y in params_values
                ],
                flags=flags
            )
            return completions

    def on_selection_modified_async(self, view):
        if view.syntax().name != 'Nextflow':
            return
        if len(view.selection) > 1:
            return
        region = view.selection[0]
        point = region.a
        if not view.score_selector(point, 'source.nextflow entity.name.parameter.nextflow'):
            return
        folders = view.window().folders()
        if not folders:
            return
        root_dir = Path(folders[0])
        nf_schema_path = root_dir / 'nextflow_schema.json'
        if not nf_schema_path.exists():
            return

        scope_region = view.extract_scope(point)
        param_text = view.substr(scope_region)
        with open(nf_schema_path) as f:
            nf_schema = json.load(f)
        param_info = get_param_info(nf_schema, param_text)
        view.show_popup(format_param_info(param_info))
