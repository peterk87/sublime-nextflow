#!/usr/bin/env python

from typing import List, Tuple, Optional
from datetime import datetime
import re
from urllib.request import urlopen
from urllib.parse import unquote_plus
import pickle
from pathlib import Path

import sublime
import sublime_plugin
import threading

container_fetch_lock = threading.Lock()


regex_sing_img = re.compile(r'^<a href="([^"]+)">[^<]+<\/a>\s*(\d{2}-\w{3}-\d{4} \d{2}:\d{2})\s*(\d+)$')

GALAXY_SINGULARITY_IMAGES_URL = 'https://depot.galaxyproject.org/singularity/'
BASE_QUAYIO_DOCKER_URL = 'quay.io/biocontainers/'


def format_size_mb(size: str) -> str:
    size_mb = int(size) / (1024**2)
    return f'{size_mb:0.1f} MB'


def to_isodatetime(s: str, fmt: str = '%d-%b-%Y %H:%M') -> str:
    return datetime.strptime(s, fmt).isoformat()


def get_images() -> List[Tuple[str, str, str]]:
    """Get list of tuples with image name, date modified and size in MB"""
    images = []
    print(f'Fetching Biocontainers image info from {GALAXY_SINGULARITY_IMAGES_URL}')
    with urlopen(GALAXY_SINGULARITY_IMAGES_URL) as response:
        for line in response:
            line = line.decode('utf-8').strip()
            if not line:
                continue
            m = regex_sing_img.match(line)
            if m:
                image_name, dt, size = m.groups()
                image_name = unquote_plus(image_name)
                isodate = to_isodatetime(dt)
                size_mb = format_size_mb(size)
                images.append((image_name, isodate, size_mb))
    print(f'Fetched info for {len(images)} Biocontainer images from {GALAXY_SINGULARITY_IMAGES_URL}')
    return images


def cache_images_list(images: List[Tuple[str, str, str]]) -> None:
    cache_dir = Path(sublime.cache_path()) / 'sublime-nextflow'
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / 'singularity_images.pickle'
    with open(cache_path, 'wb') as fh:
        pickle.dump(images, fh)


def fetch_images(window: sublime.Window) -> None:
    images = get_images()
    cache_images_list(images)
    window.status_message(f'Retrieved and cached info for {len(images)} Biocontainer images from {GALAXY_SINGULARITY_IMAGES_URL}')


def get_cached_images_list() -> Optional[List[Tuple[str, str, str]]]:
    cache_dir = Path(sublime.cache_path()) / 'sublime-nextflow'
    cache_path = cache_dir / 'singularity_images.pickle'
    if not cache_path.exists():
        return None
    with open(cache_path, 'rb') as fh:
        return pickle.load(fh)


class NextflowBiocontainerInfoFetchCommand(sublime_plugin.WindowCommand):
    def run(self):
        with container_fetch_lock:
            self.window.status_message('Fetching Biocontainers Docker and Singularity images information...')
            thread = threading.Thread(target=fetch_images, args=(self.window, ))
            thread.daemon = True
            thread.start()


class NextflowBiocontainerDirectiveInsertCommand(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        container = kwargs.get('container', None)
        if container:
            view = self.view
            if len(view.selection) > 1:
                return
            region = view.selection[0]
            point = region.a
            row, col = view.rowcol(point)
            pad_col = ' ' * col
            name = container[0]
            text = "if (workflow.containerEngine == 'singularity' && !params.singularity_pull_docker_container) {\n"
            text += f"{pad_col}  container '{GALAXY_SINGULARITY_IMAGES_URL}{name}'\n"
            text += f"{pad_col}" + "} else {\n"
            text += f"{pad_col}  container '{BASE_QUAYIO_DOCKER_URL}{name}'\n"
            text += f"{pad_col}" + "}\n"
            view.insert(edit, point, text)


class NextflowBiocontainerSelectCommand(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        view = self.view
        if len(view.selection) > 1:
            return
        region = view.selection[0]
        point = region.a
        window = view.window()
        singularity_images = get_cached_images_list()
        if singularity_images:
            window.status_message(f'Retrieved {len(singularity_images)} singularity images from cache')
        else:
            window.status_message(f'Getting singularity images from {GALAXY_SINGULARITY_IMAGES_URL}')
            singularity_images = get_images()
            window.status_message(f'Retrieved {len(singularity_images)} singularity images')
            cache_images_list(singularity_images)
            window.status_message(f'Cached info for {len(singularity_images)} singularity images')

        def on_select(x: int):
            if x == -1:
                return
            container = singularity_images[x]
            view.run_command('nextflow_biocontainer_directive_insert', dict(container=container))

        view.window().show_quick_panel([f'{name} ({dt}) [{size_mb}]' for name, dt, size_mb in singularity_images], on_select=on_select)
